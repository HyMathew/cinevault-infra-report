"""Real browser -> Flask web -> HTTP API -> disposable JSON contract, with no API mocks."""

import argparse
import hashlib
import http.client
import http.server
import json
import logging
import re
import secrets
import shutil
import socket
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


class LostCreationResponseProxy:
    """Owned loopback fault injector; upstream is still the actual HTTP API."""

    def __init__(self, upstream):
        endpoint = urlsplit(upstream)
        if (
            endpoint.scheme != "http"
            or endpoint.hostname != "127.0.0.1"
            or not endpoint.port
            or endpoint.username
            or endpoint.password
            or endpoint.path
            or endpoint.query
            or endpoint.fragment
        ):
            raise ValueError("Fault proxy requires an owned loopback API origin")
        self._lock = threading.Lock()
        self._armed = None
        self._attempts = []
        self.errors = []
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def forward(self):
                connection = None
                try:
                    self.connection.settimeout(5)
                    target = urlsplit(self.path)
                    if (
                        target.scheme
                        or target.netloc
                        or not target.path.startswith("/")
                    ):
                        raise ValueError("Nonlocal request target refused")
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 <= length <= 1024 * 1024:
                        raise ValueError("Fault proxy input exceeds fixture bound")
                    body = self.rfile.read(length)
                    if len(body) != length:
                        raise ValueError("Truncated fixture request")
                    hop = {
                        "host",
                        "connection",
                        "proxy-connection",
                        "transfer-encoding",
                        "content-length",
                        "keep-alive",
                        "te",
                        "trailer",
                        "upgrade",
                    }
                    headers = {
                        name: value
                        for name, value in self.headers.items()
                        if name.lower() not in hop
                    }
                    connection = http.client.HTTPConnection(
                        endpoint.hostname, endpoint.port, timeout=5
                    )
                    connection.request(
                        self.command, self.path, body=body, headers=headers
                    )
                    response = connection.getresponse()
                    payload = response.read(2 * 1024 * 1024 + 1)
                    if len(payload) > 2 * 1024 * 1024:
                        raise ValueError("Fault proxy response exceeds fixture bound")
                    dropped = False
                    if self.command == "POST" and target.path in (
                        "/api/v1/loans",
                        "/api/v1/reservations",
                    ):
                        result = json.loads(payload)
                        with owner._lock:
                            dropped = (
                                response.status == 201 and owner._armed == target.path
                            )
                            if dropped:
                                owner._armed = None
                            owner._attempts.append(
                                {
                                    "path": target.path,
                                    "key_hash": hashlib.sha256(
                                        self.headers.get("Idempotency-Key", "").encode()
                                    ).hexdigest(),
                                    "body_hash": hashlib.sha256(body).hexdigest(),
                                    "identity": result.get("id"),
                                    "status": response.status,
                                    "replayed": response.getheader(
                                        "Idempotency-Replayed"
                                    )
                                    == "true",
                                    "dropped": dropped,
                                }
                            )
                    if dropped:
                        # The API returned 201. Deliver no HTTP response to the web client.
                        self.close_connection = True
                        try:
                            self.connection.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                        self.connection.close()
                        return
                    self.send_response(response.status)
                    for name, value in response.getheaders():
                        if name.lower() not in hop:
                            self.send_header(name, value)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except (OSError, ValueError, http.client.HTTPException) as exc:
                    with owner._lock:
                        owner.errors.append(type(exc).__name__)
                    self.close_connection = True
                finally:
                    if connection is not None:
                        connection.close()

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = forward

        class Server(http.server.ThreadingHTTPServer):
            daemon_threads = False
            block_on_close = True

        self.server = Server(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        try:
            self.thread.start()
        except BaseException:
            self.server.server_close()
            raise
        self.url = "http://127.0.0.1:" + str(self.server.server_port)

    def arm(self, path):
        with self._lock:
            if self._armed is not None or path not in (
                "/api/v1/loans",
                "/api/v1/reservations",
            ):
                raise ValueError("Only one expected creation response can be armed")
            self._armed = path

    def creation_attempts(self, path):
        with self._lock:
            return [dict(row) for row in self._attempts if row["path"] == path]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=10)
        return not self.thread.is_alive()


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


def exercise_lost_creation(
    page, context, base, film_path, kind, folder, args, report, check, fault
):
    """A committed upstream creation must remain one entity after a manual replay."""
    action, label, table, operation, event = (
        ("emprunter", "Demander un prêt", "loans", "loan.request", "loan.requested")
        if kind == "loan"
        else (
            "reserver",
            "Réserver ce film",
            "reservations",
            "reservation.create",
            "reservation.created",
        )
    )
    form = page.locator(f"form[action$='/{action}']")
    original_key = form.locator("input[name='operation_key']").input_value()
    fault.arm("/api/v1/" + table)
    with page.expect_response(
        lambda response: (
            urlsplit(response.url).path == film_path + "/" + action
            and response.request.method == "POST"
        )
    ) as submitted:
        page.get_by_role("button", name=label, exact=True).click()
    settle(page)
    check(kind + " lost response becomes recovery503", submitted.value.status == 503)
    check(
        kind + " uncertain page preserves original operation key",
        page.get_by_role(
            "heading", name="Vérifiez votre demande.", exact=True
        ).is_visible()
        and page.locator("input[name='operation_key']").input_value() == original_key,
    )
    snapshot = json.loads((folder / "enterprise.json").read_text(encoding="utf-8"))
    check(
        kind + " upstream201 persisted exactly one entity before replay",
        len(snapshot[table]) == 1,
    )
    identity = snapshot[table][0]["id"]
    receipt_before = [
        row for row in snapshot["idempotency_records"] if row["operation"] == operation
    ]
    check(
        kind + " committed receipt matches created entity",
        len(receipt_before) == 1 and receipt_before[0]["response"]["id"] == identity,
    )
    capture(page, "actual-uncertain-" + kind + ".png", args, report)
    listing_label = "Mes emprunts" if kind == "loan" else "Mes réservations"
    listing_href = page.get_by_role(
        "link", name=listing_label, exact=True
    ).get_attribute("href")
    availability_href = page.get_by_role(
        "link", name="Disponibilité du film", exact=True
    ).get_attribute("href")
    reconciliation = context.new_page()
    try:
        reconciliation.goto(base + listing_href)
        settle(reconciliation)
        check(
            kind + " owner GET reconciles persisted creation",
            reconciliation.locator("article.circulation-entry").count() == 1,
        )
        reconciliation.goto(base + availability_href)
        settle(reconciliation)
        check(
            kind + " availability GET remains readable",
            reconciliation.get_by_role(
                "heading", name="Voyage dans les images — essai réel", exact=True
            ).is_visible(),
        )
    finally:
        reconciliation.close()
    check(
        kind + " no automatic creation retry",
        len(fault.creation_attempts("/api/v1/" + table)) == 1,
    )
    with page.expect_response(
        lambda response: (
            urlsplit(response.url).path == film_path + "/" + action
            and response.request.method == "POST"
        )
    ) as replayed:
        page.get_by_role("button", name="Réessayer la même demande", exact=True).click()
    settle(page)
    check(kind + " manual same-key replay is confirmed", replayed.value.status == 303)
    current = json.loads((folder / "enterprise.json").read_text(encoding="utf-8"))
    check(
        kind + " replay leaves exactly one original entity",
        len(current[table]) == 1 and current[table][0]["id"] == identity,
    )
    check(
        kind + " replay leaves one creation audit",
        len(
            [
                row
                for row in current["audit_events"]
                if row["action"] == event and row["entity_id"] == identity
            ]
        )
        == 1,
    )
    check(
        kind + " replay preserves exactly one unchanged receipt",
        [row for row in current["idempotency_records"] if row["operation"] == operation]
        == receipt_before,
    )
    attempts = fault.creation_attempts("/api/v1/" + table)
    check(
        kind + " actual upstream replay keeps key body ID and replay header",
        len(attempts) == 2
        and attempts[0]["key_hash"] == attempts[1]["key_hash"]
        and attempts[0]["body_hash"] == attempts[1]["body_hash"]
        and attempts[0]["identity"] == attempts[1]["identity"] == identity
        and attempts[0]["status"] == attempts[1]["status"] == 201
        and attempts[0]["dropped"]
        and not attempts[1]["dropped"]
        and attempts[1]["replayed"],
    )
    report.setdefault("lost_creation_responses", []).append(
        {
            "operation": operation,
            "upstream201_before_connection_closed": True,
            "manual_replay_same_key_and_body": True,
            "upstream_idempotency_replayed": True,
            "persisted_entities": 1,
            "creation_audits": 1,
            "receipts": 1,
        }
    )


def exercise_browser(browser, base, config, folder, args, report, fault):
    from playwright.sync_api import Error as BrowserError

    def check(name, value):
        if not value:
            report["failed_check"] = name
            raise AssertionError(name)
        report["checks"].append(name)

    blocked, console_messages, page_errors = [], [], []
    origin = urlsplit(base)

    def watch(page):
        page.on("pageerror", lambda error: page_errors.append(type(error).__name__))
        page.on(
            "console",
            lambda message: console_messages.append(
                (message.type, message.text, message.location)
            ),
        )

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
            context.on("page", watch)
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
        exercise_lost_creation(
            member,
            member_context,
            base,
            film_path,
            "loan",
            folder,
            args,
            report,
            check,
            fault,
        )
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
        exercise_lost_creation(
            admin,
            admin_context,
            base,
            film_path,
            "reservation",
            folder,
            args,
            report,
            check,
            fault,
        )
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
        check("fault proxy had no unexpected transport error", not fault.errors)
        expected_messages, unexpected = (
            {"uncertain503": 0, "authorization403": 0, "blocked_probe": 0},
            [],
        )
        for level, message, location in console_messages:
            if level not in ("warning", "error"):
                continue
            source = urlsplit(location.get("url", ""))
            expected_503 = (
                source.scheme == origin.scheme
                and source.netloc == origin.netloc
                and source.path in (film_path + "/emprunter", film_path + "/reserver")
                and re.match(
                    r"^Failed to load resource: the server responded with a status of 503(?:\s|$)",
                    message,
                )
            )
            expected_block = (
                source.hostname == "example.invalid"
                and source.path == "/cinevault-gate-probe"
                and "net::ERR_FAILED" in message
            )
            expected_403 = (
                source.scheme == origin.scheme
                and source.netloc == origin.netloc
                and source.path == "/films/nouveau"
                and re.match(
                    r"^Failed to load resource: the server responded with a status of 403(?:\s|$)",
                    message,
                )
            )
            if expected_503:
                expected_messages["uncertain503"] += 1
            elif expected_403:
                expected_messages["authorization403"] += 1
            elif expected_block:
                expected_messages["blocked_probe"] += 1
            else:
                unexpected.append(
                    {
                        "type": level,
                        "message_sha256": hashlib.sha256(message.encode()).hexdigest(),
                    }
                )
        report["console_health"] = {
            "page_error_types": page_errors,
            "unexpected": unexpected,
            "expected_negative_response_messages": expected_messages,
        }
        check("no uncaught browser page errors", not page_errors)
        check("no unexpected browser console error or warning", not unexpected)
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
            "Response connection closure is injected by an owned local proxy after real API 201; not a physical network fault or Mongo commit-ack experiment",
        ],
    }
    folder = Path(tempfile.mkdtemp(prefix="cinevault-browser-pair-"))
    process = server = thread = browser = fault = None
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
        fault = LostCreationResponseProxy(api_url)
        key = folder / "web-session.key"
        key.write_bytes(secrets.token_bytes(32))
        key.chmod(0o600)
        web = web_module.create_app(
            {
                "TESTING": True,
                "SECRET_KEY_FILE": str(key),
                "ENTERPRISE_ENABLED": True,
                "API_URL": fault.url,
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
                exercise_browser(browser, base, config, folder, args, report, fault)
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
        report["fault_proxy_stopped"] = fault is None
        if fault is not None:
            try:
                report["fault_proxy_stopped"] = fault.close()
            except (OSError, RuntimeError) as exc:
                report["fault_proxy_cleanup_error_type"] = type(exc).__name__
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
        if (
            report["web_thread_stopped"]
            and report["api_process_stopped"]
            and report["fault_proxy_stopped"]
        ):
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
            and report["fault_proxy_stopped"]
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
