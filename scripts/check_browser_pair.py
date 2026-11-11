"""Real browser -> Flask web -> HTTP API -> disposable JSON contract, with no API mocks."""

import argparse
import hashlib
import json
import logging
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from urllib.parse import urlsplit

import check_enterprise_pair as pair

BROWSER_PINS = {
    "playwright": "1.64.1",
    "pyee": "14.0.0",
    "greenlet": "3.5.6",
    "typing-extensions": "4.16.0",
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-root", type=Path, required=True)
    parser.add_argument("--web-root", type=Path, required=True)
    parser.add_argument("--api-python", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--screens-dir", type=Path, required=True)
    parser.add_argument("--browser-channel", choices=("chrome", "chromium"))
    args = parser.parse_args(argv)
    args.api_root, args.web_root = args.api_root.resolve(), args.web_root.resolve()
    # Preserve an environment's bin/python symlink. Resolving it selects the base interpreter.
    args.api_python = args.api_python.absolute()
    args.report, args.screens_dir = args.report.resolve(), args.screens_dir.resolve()
    for source in (args.api_root, args.web_root):
        if (
            not (source / "app/__init__.py").is_file()
            or not (source / "requirements.txt").is_file()
        ):
            parser.error(
                "Each source root must contain its Flask application and runtime lock"
            )
    if args.api_root == args.web_root:
        parser.error("API and web sources must be distinct")
    if not args.api_python.is_file():
        parser.error("--api-python must name an existing interpreter")
    if any(
        output.is_relative_to(source)
        for source in (args.api_root, args.web_root)
        for output in (args.report, args.screens_dir)
    ):
        parser.error("Outputs must remain outside both application source trees")
    if args.report.exists() or args.screens_dir.exists():
        parser.error(
            "Report and screenshots must be new paths; previous evidence is preserved"
        )
    if args.report == args.screens_dir:
        parser.error("Report and screenshot directory must be distinct paths")
    return args


def source_identity(root):
    """Git checkouts retain their commit; archives retain the same application byte fingerprint."""
    try:
        top = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if Path(top).resolve() == root.resolve():
            return {"kind": "git", **pair.source_identity(root)}
    except (OSError, subprocess.CalledProcessError):
        pass
    files = sorted(
        path
        for path in (root / "app").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    ) + [root / "requirements.txt"]
    hashes = [
        (
            path.relative_to(root).as_posix(),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in files
    ]
    return {
        "kind": "archive",
        "commit": None,
        "source_clean": None,
        "application_sha256": hashlib.sha256(json.dumps(hashes).encode()).hexdigest(),
    }


def settle(page):
    page.wait_for_load_state("networkidle")


def login(page, base, username, password):
    page.goto(base + "/connexion")
    page.get_by_label("Identifiant", exact=True).fill(username)
    page.get_by_label("Mot de passe", exact=True).fill(password)
    page.get_by_role("button", name="Me connecter", exact=True).click()
    page.wait_for_url("**/profil")
    settle(page)


def capture(page, name, args, report):
    # Capture only selected post-submission states; no password form is retained.
    destination = args.screens_dir / name
    page.screenshot(path=str(destination), full_page=True)
    report["screens"].append(
        {
            "file": name,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "viewport": page.viewport_size,
            "path": urlsplit(page.url).path,
        }
    )


def exercise_browser(browser, base, config, folder, args, report):
    from playwright.sync_api import Error as BrowserError

    def check(name, value):
        if not value:
            report["failed_check"] = name
            raise AssertionError(name)
        report["checks"].append(name)

    blocked = []
    origin = urlsplit(base)

    def local_only(route):
        target = urlsplit(route.request.url)
        if (
            target.scheme == origin.scheme
            and target.hostname == origin.hostname
            and target.port == origin.port
            and target.username is None
            and target.password is None
        ):
            route.continue_()
        else:
            blocked.append(target.scheme)
            route.abort()

    admin_context = browser.new_context(
        viewport={"width": 1280, "height": 900}, service_workers="block"
    )
    member_context = browser.new_context(
        viewport={"width": 390, "height": 844}, service_workers="block"
    )
    try:
        for context in (admin_context, member_context):
            context.set_default_timeout(10000)
            context.route("**/*", local_only)
        admin, member = admin_context.new_page(), member_context.new_page()
        report["stage"] = "admin_login"
        login(admin, base, "pair-admin", config["password"])
        check(
            "real signed-context login and bearer cookie",
            admin.get_by_role("heading", name="Mon profil", exact=True).count() == 1,
        )
        report["stage"] = "movie_create"
        admin.goto(base + "/films/nouveau")
        admin.locator("#titre").fill("Voyage dans les images — essai réel")
        admin.locator("#realisateur").fill("Créateur fictif")
        admin.locator("#annee").fill("2026")
        admin.locator("#support").select_option("dvd")
        admin.locator("#synopsis").fill(
            "Film fictif réservé à cette validation locale."
        )
        admin.get_by_role("button", name="Ajouter un acteur", exact=True).click()
        settle(admin)
        admin.get_by_label("Acteur 1", exact=True).fill("Élodie, Martin")
        admin.get_by_role("button", name="Créer le film", exact=True).click()
        settle(admin)
        film_path = urlsplit(admin.url).path
        check(
            "browser movie creation with atomic initial copy",
            re.fullmatch(r"/films/[0-9a-f-]{36}", film_path) is not None,
        )
        capture(admin, "actual-film-desktop.png", args, report)
        report["stage"] = "member_registration"
        member_name, member_password = (
            "qa-member-" + uuid.uuid4().hex[:8],
            secrets.token_urlsafe(24),
        )
        member.goto(base + "/inscription")
        member.get_by_label("Identifiant", exact=True).fill(member_name)
        member.get_by_label("Nom affiché", exact=True).fill("Membre de validation")
        member.get_by_label("Mot de passe", exact=True).fill(member_password)
        member.get_by_label("Confirmer le mot de passe", exact=True).fill(
            member_password
        )
        member.get_by_role("button", name="Créer mon compte", exact=True).click()
        member.wait_for_url("**/connexion")
        login(member, base, member_name, member_password)
        report["stage"] = "profile_and_csrf"
        member.get_by_label("Nom affiché", exact=True).fill("Lecteur des images")
        member.get_by_role("button", name="Enregistrer mon profil", exact=True).click()
        settle(member)
        check(
            "real profile mutation persisted",
            member.get_by_label("Nom affiché", exact=True).input_value()
            == "Lecteur des images",
        )
        refused = member_context.request.post(
            base + "/profil", form={"display_name": "Without CSRF"}
        )
        check("real web rejects missing CSRF", refused.status == 400)
        member.goto(base + "/profil")
        check(
            "rejected CSRF did not alter profile",
            member.get_by_label("Nom affiché", exact=True).input_value()
            == "Lecteur des images",
        )
        capture(member, "actual-profile-mobile.png", args, report)
        check(
            "member management route denied",
            member.goto(base + "/films/nouveau").status == 403,
        )
        report["stage"] = "private_collection"
        member.goto(base + film_path)
        member.get_by_role("link", name="Ajouter à ma collection", exact=True).click()
        member.get_by_label("Dans ma collection", exact=True).select_option("favorite")
        member.get_by_role("button", name="Ajouter à ma collection", exact=True).click()
        settle(member)
        check(
            "real private collection mutation",
            member.get_by_role(
                "heading", name="Voyage dans les images — essai réel", exact=True
            ).count()
            == 1,
        )
        capture(member, "actual-collection-mobile.png", args, report)
        admin.goto(base + "/ma-collection")
        check(
            "other actor cannot list private entry",
            admin.get_by_role(
                "heading", name="Voyage dans les images — essai réel", exact=True
            ).count()
            == 0,
        )
        report["stage"] = "loan_request_and_approval"
        member.goto(base + film_path)
        member.get_by_role("button", name="Demander un prêt", exact=True).click()
        settle(member)
        admin.goto(base + "/emprunts?scope=all")
        admin.get_by_role("link", name="Attribuer un exemplaire", exact=True).click()
        admin.locator("#copy_id").select_option(index=1)
        admin.get_by_role("button", name="Valider le prêt", exact=True).click()
        settle(admin)
        check(
            "real manager approval",
            admin.locator("form[action$='/retour']").count() == 1,
        )
        report["stage"] = "reservation_and_return"
        admin.goto(base + film_path)
        admin.get_by_role("button", name="Réserver ce film", exact=True).click()
        settle(admin)
        check(
            "real reservation when copy unavailable",
            urlsplit(admin.url).path == "/reservations",
        )
        admin.goto(base + "/emprunts?scope=all")
        admin.locator("form[action$='/retour'] button").click()
        settle(admin)
        member.goto(base + "/emprunts?scope=mine")
        capture(member, "actual-returned-loan-mobile.png", args, report)
        admin.goto(base + "/reservations?scope=mine")
        check(
            "queue priority exposed after return",
            admin.get_by_text(
                "Un exemplaire est disponible pour cette réservation prioritaire.",
                exact=True,
            ).count()
            == 1,
        )
        capture(admin, "actual-ready-reservation-desktop.png", args, report)

        report["stage"] = "browser_network_policy"
        before = len(blocked)
        probe = member_context.new_page()
        refused = False
        try:
            probe.goto("https://example.invalid/cinevault-gate-probe")
        except BrowserError:
            refused = True
        finally:
            probe.close()
        check(
            "nonlocal browser request refused before network dispatch",
            refused and len(blocked) == before + 1,
        )
    finally:
        admin_context.close()
        member_context.close()
    report["stage"] = "final_json_invariants"
    document = json.loads((folder / "enterprise.json").read_text(encoding="utf-8"))
    check(
        "real JSON retained one film and one initial copy",
        len(document["movies"]) == len(document["copies"]) == 1,
    )
    check(
        "actor comma preserved through actual browser and HTTP",
        document["movies"][0]["actors"] == ["Élodie, Martin"],
    )
    check(
        "real loan is returned and reservation remains waiting",
        [r["status"] for r in document["loans"]] == ["returned"]
        and [r["status"] for r in document["reservations"]] == ["waiting"],
    )
    account = next(
        user for user in document["users"] if user["username"] == member_name
    )
    check(
        "profile persisted in actual JSON",
        account["display_name"] == "Lecteur des images",
    )
    check(
        "private favorite belongs to member",
        len(document["collections"]) == 1
        and document["collections"][0]["kind"] == "favorite"
        and document["collections"][0]["owner_id"] == account["id"],
    )
    check(
        "loan borrower is the registered member",
        document["loans"][0]["borrower_id"] == account["id"],
    )


def run_pair(args):
    report = {
        "passed": False,
        "started_at": datetime.now(UTC).isoformat(),
        "stage": "initialize",
        "scope": "Real local browser, Flask web and HTTP API, disposable JSON; no API mocks",
        "checks": [],
        "screens": [],
        "limits": [
            "JSON backend only; no MongoDB, Docker, Swarm, TLS or production deployment",
            "Sequential circulation case, not global FIFO/concurrency or load validation",
            "Browser request routing is not an operating-system network sandbox",
            "No complete accessibility, cross-browser or keyboard campaign",
        ],
    }
    folder = Path(tempfile.mkdtemp(prefix="cinevault-browser-pair-"))
    process = server = thread = browser = None
    log = None
    api_start_attempted = False
    try:
        args.screens_dir.mkdir(parents=True, exist_ok=False)
        report["api_source"], report["web_source"] = (
            source_identity(args.api_root),
            source_identity(args.web_root),
        )
        report["browser_packages"] = {
            name: metadata.version(name) for name in BROWSER_PINS
        }
        if report["browser_packages"] != BROWSER_PINS:
            raise RuntimeError("Browser environment differs from the lock")
        sys.path.insert(0, str(args.web_root))
        import app as web_module
        from playwright.sync_api import sync_playwright
        from werkzeug.serving import make_server

        if not Path(web_module.__file__).resolve().is_relative_to(args.web_root):
            raise RuntimeError("Unexpected web application import")
        log_path = folder / "api.log"
        log_path.touch(mode=0o600)
        log = log_path.open("w", encoding="utf-8")
        report["stage"] = "start_api"
        api_start_attempted = True
        process, config, api_url = pair.start_api(args, folder, log)
        endpoint = urlsplit(api_url)
        if (
            endpoint.scheme != "http"
            or endpoint.hostname != "127.0.0.1"
            or not endpoint.port
        ):
            raise RuntimeError("API endpoint is not owned loopback")
        key = folder / "web-session.key"
        key.write_bytes(secrets.token_bytes(32))
        key.chmod(0o600)
        web = web_module.create_app(
            {
                "TESTING": True,
                "SECRET_KEY_FILE": str(key),
                "ENTERPRISE_ENABLED": True,
                "API_URL": api_url,
                "CLIENT_CONTEXT_KEY": bytes.fromhex(config["context_key"]),
                "SESSION_COOKIE_SECURE": False,
            }
        )
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        server = make_server("127.0.0.1", 0, web, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:" + str(server.server_port)
        report["stage"] = "launch_browser"
        with sync_playwright() as pw:
            options = {"headless": True}
            if args.browser_channel:
                options["channel"] = args.browser_channel
            browser = pw.chromium.launch(**options)
            try:
                report["browser"] = browser.version
                report["browser_channel"] = (
                    args.browser_channel or "playwright-default-chromium"
                )
                exercise_browser(browser, base, config, folder, args, report)
            finally:
                browser.close()
                report["browser_closed"] = True
        report["passed"] = True
    except (Exception, KeyboardInterrupt) as exc:  # noqa: BLE001 - sanitized CLI failure boundary
        # Exception text and page content can contain credentials/URLs: keep types and named stages only.
        report["error_type"] = type(exc).__name__
    finally:
        if server is not None:
            try:
                if thread is not None and thread.is_alive():
                    server.shutdown()
                server.server_close()
                if thread is not None and thread.ident is not None:
                    thread.join(timeout=10)
            except (OSError, RuntimeError) as exc:
                report["web_cleanup_error_type"] = type(exc).__name__
        report["web_thread_stopped"] = thread is None or not thread.is_alive()
        if process is not None:
            try:
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
                process.wait(timeout=10)
                if process.stdout:
                    process.stdout.close()
                report["owned_api_exit"] = process.returncode
            except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                report["api_cleanup_error_type"] = type(exc).__name__
        report["api_process_stopped"] = (
            process is not None and process.poll() is not None
        ) or not api_start_attempted
        report["api_clean_exit"] = (
            process is not None and process.returncode == 0
        ) or not api_start_attempted
        if log is not None:
            log.close()
        report["temporary_data_removed"] = False
        if report["web_thread_stopped"] and report["api_process_stopped"]:
            try:
                shutil.rmtree(folder)
                report["temporary_data_removed"] = not folder.exists()
            except OSError as exc:
                report["data_cleanup_error_type"] = type(exc).__name__
        else:
            # Retain only this private owned workspace when a live writer cannot be excluded.
            report["retained_owned_workspace"] = folder.name
        report["passed"] = bool(
            report["passed"]
            and report["web_thread_stopped"]
            and report["api_process_stopped"]
            and report["api_clean_exit"]
            and report["temporary_data_removed"]
            and report.get("browser_closed", False)
        )
        report["finished_at"] = datetime.now(UTC).isoformat()
    return report


def main(argv=None):
    args = parse_args(argv)
    report = run_pair(args)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "checks": len(report["checks"]),
                "screens": len(report["screens"]),
                "temporary_data_removed": report["temporary_data_removed"],
            }
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
