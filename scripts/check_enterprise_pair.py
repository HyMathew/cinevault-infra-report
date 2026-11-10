"""Exercise the real web-to-API HTTP boundary with disposable synthetic state.

The API runs in a separate process and interpreter. The web application uses
its real Flask routes, session, CSRF and HTTP client. This is not a Docker or
browser gate; those checks are separate.
"""

import argparse
import hashlib
import json
import logging
import queue
import secrets
import subprocess
import sys
import tempfile
import threading
from html.parser import HTMLParser
from pathlib import Path


class SubmittedForm(HTMLParser):
    """Collect the unmodified editing form with browser text normalization."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.fields = []
        self.active = False
        self.textarea = None
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.active = attrs.get(
                "method", "get"
            ).lower() == "post" and not attrs.get("action")
        if not self.active or "name" not in attrs:
            return
        if tag == "input" and attrs.get("type", "text") not in (
            "submit",
            "button",
            "checkbox",
        ):
            self.fields.append((attrs["name"], attrs.get("value", "")))
        if tag == "textarea":
            self.textarea, self.text = attrs["name"], []

    def handle_data(self, value):
        if self.active and self.textarea is not None:
            self.text.append(value)

    def handle_endtag(self, tag):
        if tag == "textarea" and self.textarea is not None:
            value = "".join(self.text).replace("\r\n", "\n").replace("\r", "\n")
            value = value.removeprefix("\n")
            self.fields.append((self.textarea, value.replace("\x00", "\ufffd")))
            self.textarea = None
        if tag == "form":
            self.active = False


def serve_api(source):
    config = json.loads(sys.stdin.readline())
    sys.path.insert(0, str(source))
    from app import create_app
    from app.bootstrap import bootstrap_admin
    from app.storage_v2 import V2Store
    from werkzeug.serving import make_server

    store = V2Store(config["store"])
    store.initialize()
    bootstrap_admin(store, "pair-admin", "Gestionnaire synthétique", config["password"])
    app = create_app(
        {
            "DATA_FILE": config["legacy"],
            "ENTERPRISE_ENABLED": True,
            "ENTERPRISE_DATA_FILE": config["store"],
            "AUTH_THROTTLE_KEY": bytes.fromhex(config["throttle_key"]),
            "CLIENT_CONTEXT_KEY": bytes.fromhex(config["context_key"]),
            "CLIENT_CONTEXT_REQUIRED": True,
            "METADATA_ENABLED": False,
        }
    )
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(json.dumps({"port": server.server_port}), flush=True)
    try:
        # Pipe ownership also closes the Windows venv interpreter descendant.
        sys.stdin.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


def start_api(args, folder, log):
    config = {
        "store": str(folder / "enterprise.json"),
        "legacy": str(folder / "legacy.json"),
        "password": secrets.token_urlsafe(24),
        "throttle_key": secrets.token_hex(32),
        "context_key": secrets.token_hex(32),
    }
    process = subprocess.Popen(
        [
            str(args.api_python),
            str(Path(__file__).resolve()),
            "--serve-api",
            str(args.api_root),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=log,
        text=True,
        encoding="utf-8",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        process.stdin.write(json.dumps(config) + "\n")
        process.stdin.flush()
        ready = queue.Queue()
        threading.Thread(
            target=lambda: ready.put(process.stdout.readline()), daemon=True
        ).start()
        line = ready.get(timeout=30)
        port = json.loads(line)["port"]
        assert type(port) is int and 1 <= port <= 65535
        return process, config, f"http://127.0.0.1:{port}"
    except BaseException:
        process.stdin.close()
        process.wait(timeout=10)
        process.stdout.close()
        raise


def source_identity(root):
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
        "commit": subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip(),
        "application_sha256": hashlib.sha256(json.dumps(hashes).encode()).hexdigest(),
        "source_clean": not subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                "app",
                "requirements.txt",
            ],
            text=True,
        ).strip(),
    }


def run_pair(args):
    sys.path.insert(0, str(args.web_root))
    from app import create_app
    from app.api_client import APIError
    from werkzeug.datastructures import MultiDict

    cases = [
        (
            ["Élodie, Martin", 'Nom "cité"', "Prénom\rNom", "Un\nAutre", "Cinéma 🎬"],
            ["Drame, comédie", 'Genre "cité"', "Genre\rSuite", "Genre\nSuite"],
        ),
        (["Nom\x00Interne", "Nom\\suite", "Nom & <texte>"], ["Genre\x00Interne"]),
        (
            ["🎬" * 58 + "\r" + "🎞" * 61] * 30,
            [f"G{i:02}" + "🎬" * 75 + "\rZ" for i in range(30)],
        ),
    ]
    checks = []
    with tempfile.TemporaryDirectory(prefix="cinevault-pair-") as temporary:
        folder = Path(temporary)
        with (folder / "api.log").open("w", encoding="utf-8") as log:
            process, config, base_url = start_api(args, folder, log)
            try:
                session_key = folder / "web-session.key"
                session_key.write_bytes(secrets.token_bytes(32))
                app = create_app(
                    {
                        "TESTING": True,
                        "SECRET_KEY_FILE": str(session_key),
                        "ENTERPRISE_ENABLED": True,
                        "API_URL": base_url,
                        "CLIENT_CONTEXT_KEY": bytes.fromhex(config["context_key"]),
                        "SESSION_COOKIE_SECURE": False,
                    }
                )
                client = app.test_client()
                login = client.get("/connexion")
                fields = dict(SubmittedForm(login.get_data(as_text=True)).fields)
                response = client.post(
                    "/connexion",
                    data={
                        "csrf_token": fields["csrf_token"],
                        "username": "pair-admin",
                        "password": config["password"],
                    },
                )
                assert response.status_code == 303, "Real web/API login failed"
                token = client.get_cookie("cinevault_auth").value
                api = app.extensions["cinevault_api"]
                checks.append("signed client context, login and real bearer session")
                for index, (actors, genres) in enumerate(cases):
                    data = {
                        "titre": f"Film synthétique {index}",
                        "realisateur": "Créateur fictif",
                        "annee": 2000,
                        "acteurs": actors,
                        "genres": genres,
                        "support": "dvd",
                        "synopsis": "Texte synthétique.",
                    }
                    movie = api.create(data, token=token)
                    identity = movie["id"]
                    path = f"/films/{identity}/modifier"
                    edit = client.get(path)
                    assert edit.status_code == 200
                    form = SubmittedForm(edit.get_data(as_text=True))
                    response = client.post(path, data=MultiDict(form.fields))
                    assert response.status_code == 303, (
                        f"Unchanged form rejected, case {index}, status {response.status_code}; "
                        f"submitted names {[name for name, _ in form.fields]}"
                    )
                    saved = api.request("GET", f"/api/v1/movies/{identity}")
                    assert saved["actors"] == actors, (
                        f"Actor data changed, case {index}"
                    )
                    assert saved["genres"] == genres, (
                        f"Genre data changed, case {index}"
                    )
                    # A second real API write makes the original editing form stale.
                    api.update(
                        identity,
                        data | {"titre": f"Version concurrente {index}"},
                        token=token,
                        version=saved["_etag"],
                    )
                    stale = client.post(path, data=MultiDict(form.fields))
                    assert stale.status_code == 412, (
                        "Stale edit overwrote a concurrent change"
                    )
                    assert (
                        api.request("GET", f"/api/v1/movies/{identity}")["title"]
                        == f"Version concurrente {index}"
                    )
                    checks.append(
                        f"case {index}: exact actor/genre persistence and stale-edit rejection"
                    )
                for _ in range(5):
                    try:
                        api.account_request(
                            token,
                            "PUT",
                            "/me/password",
                            json={
                                "current_password": "incorrect synthetic password",
                                "new_password": secrets.token_urlsafe(24),
                            },
                        )
                    except APIError as error:
                        assert error.status == 401
                    else:
                        raise AssertionError(
                            "An incorrect current password was accepted"
                        )
                try:
                    api.account_request(
                        token,
                        "PUT",
                        "/me/password",
                        json={
                            "current_password": config["password"],
                            "new_password": secrets.token_urlsafe(24),
                        },
                    )
                except APIError as error:
                    assert error.status == 429 and error.retry_after is not None
                else:
                    raise AssertionError("Reauthentication budget was bypassed")
                assert api.me(token)["username"] == "pair-admin"
                checks.append(
                    "real HTTP reauthentication: five failures then429 even with correct secret"
                )
                store = folder / "enterprise.json"
                assert store.is_file()
                document = json.loads(store.read_text(encoding="utf-8"))
                assert len(document["movies"]) == len(cases)
                checks.append(
                    "real JSON store remains readable with all synthetic films"
                )
                return {
                    "passed": True,
                    "checks": checks,
                    "api_source": source_identity(args.api_root),
                    "web_source": source_identity(args.web_root),
                    "limits": [
                        "Flask test client drives web routes; API uses real loopback HTTP.",
                        "No Docker, Swarm, TLS or browser validation is claimed by this gate.",
                    ],
                }
            finally:
                process.stdin.close()
                process.wait(timeout=10)
                process.stdout.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve-api", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--api-root", type=Path)
    parser.add_argument("--web-root", type=Path)
    parser.add_argument("--api-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.serve_api:
        serve_api(args.serve_api.resolve())
        return
    if not args.api_root or not args.web_root:
        parser.error("--api-root and --web-root are required")
    args.api_root, args.web_root = args.api_root.resolve(), args.web_root.resolve()
    for root in (args.api_root, args.web_root):
        if not (root / "app/__init__.py").is_file():
            parser.error("Each source root must contain the expected Flask application")
    result = json.dumps(run_pair(args), ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(result + "\n", encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
