import io
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from uuid import uuid4

import pytest

from scripts.check_operational_health import main
from scripts.summarize_http_logs import summarize

PRIVATE = "PRIVATE_PROBE_SENTINEL"


@pytest.fixture
def endpoints():
    statuses = {"api": 200, "web": 200}
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            service = self.path.split("/")[1]
            self.send_response(statuses[service])
            if statuses[service] == 302:
                self.send_header("Location", "/web/health")
            self.end_headers()
            self.wfile.write(PRIVATE.encode())

        def log_message(self, *_args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}", statuses, requests
        finally:
            server.shutdown()
            thread.join()


def timestamp(hours_ago=0):
    return (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()


def http_summary(api_status=200, *, services=("api", "web")):
    events = [
        json.dumps(
            {
                "service": service,
                "method": "GET",
                "route": f"/{PRIVATE}",
                "request_id": uuid4().hex,
                "status": api_status if service == "api" else 200,
                "duration_ms": 2.5,
            }
        )
        for service in services
    ]
    return summarize(io.StringIO("\n".join(events)))


@pytest.fixture
def arguments(tmp_path, endpoints):
    base_url, _, _ = endpoints
    summary_path = tmp_path / f"summary-{PRIVATE}.json"
    backup_path = tmp_path / "backup.json"
    restore_path = tmp_path / "restore.json"
    summary_path.write_text(json.dumps(http_summary()), encoding="utf-8")
    for path, status, digest in (
        (backup_path, "ENCRYPTED_BACKUP_CREATED", "a" * 64),
        (restore_path, "ISOLATED_RESTORE_VERIFIED", "b" * 64),
    ):
        path.write_text(
            json.dumps(
                {"status": status, "ciphertext_sha256": digest, "archive_bytes": 27}
            ),
            encoding="utf-8",
        )
    return {
        "api-url": f"{base_url}/api/{PRIVATE}",
        "web-url": f"{base_url}/web/health",
        "timeout-seconds": "1",
        "http-summary": str(summary_path),
        "summary-ended-at-utc": timestamp(),
        "max-summary-age-hours": "1",
        "max-5xx-percent": "2",
        "backup-receipt": str(backup_path),
        "backup-finished-at-utc": timestamp(1),
        "max-backup-age-hours": "24",
        "restore-receipt": str(restore_path),
        "restore-finished-at-utc": timestamp(72),
        "max-restore-age-hours": "168",
    }


def argv(arguments):
    return [token for key, value in arguments.items() for token in (f"--{key}", value)]


def run(arguments, capsys):
    code = main(argv(arguments))
    result = capsys.readouterr()
    assert PRIVATE not in result.out + result.err
    assert "http://" not in result.out + result.err
    assert result.err == ""
    return code, json.loads(result.out)


def test_real_http_api_outage_recovery_and_redirect_refusal(
    arguments, endpoints, capsys
):
    _, statuses, requests = endpoints
    for http_status, exit_code, state in (
        (200, 0, "ok"),
        (503, 1, "unexpected_status"),
        (200, 0, "ok"),
        (302, 1, "unexpected_status"),
    ):
        statuses["api"] = http_status
        code, output = run(arguments, capsys)
        assert code == exit_code
        assert output["health"]["api"] == {"state": state, "http_status": http_status}
        assert output["health"]["web"] == {"state": "ok", "http_status": 200}
    assert requests == [f"/api/{PRIVATE}", "/web/health"] * 4


def test_cli_reports_web_failure_and_missing_restore(arguments, endpoints):
    _, statuses, _ = endpoints
    statuses["web"] = 503
    Path(arguments["restore-receipt"]).unlink()
    arguments["restore-finished-at-utc"] = "unknown"
    script = Path(__file__).resolve().parents[1] / "scripts/check_operational_health.py"
    result = subprocess.run(
        [sys.executable, "-B", str(script), *argv(arguments)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1
    assert result.stderr == ""
    assert PRIVATE not in result.stdout
    output = json.loads(result.stdout)
    assert output["health"]["api"] == {"state": "ok", "http_status": 200}
    assert output["health"]["web"] == {"state": "unexpected_status", "http_status": 503}
    assert output["restore"]["state"] == "missing"


def test_reports_missing_timestamp_without_guessing_from_the_file(arguments, capsys):
    arguments["backup-finished-at-utc"] = "unknown"
    code, output = run(arguments, capsys)
    assert code == 1
    assert output["backup"]["state"] == "timestamp_missing"


@pytest.mark.parametrize(
    ("summary", "state"),
    [(None, "missing"), (http_summary(services=()), "empty"), (PRIVATE, "invalid")],
)
def test_rejects_missing_empty_and_malformed_collection(
    arguments, capsys, summary, state
):
    path = Path(arguments["http-summary"])
    if summary is None:
        path.unlink()
    else:
        path.write_text(json.dumps(summary), encoding="utf-8")
    code, output = run(arguments, capsys)
    assert code == 1
    assert output["collection"]["state"] == state


def test_rejects_inconsistent_http_counts(arguments, capsys):
    summary = http_summary()
    summary["services"]["api"]["requests"] = 4
    Path(arguments["http-summary"]).write_text(json.dumps(summary), encoding="utf-8")
    code, output = run(arguments, capsys)
    assert code == 1
    assert output["collection"]["services"]["api"]["state"] == "invalid"


def test_applies_error_threshold_per_service_and_detects_partial_collection(
    arguments, capsys
):
    path = Path(arguments["http-summary"])
    path.write_text(json.dumps(http_summary(503, services=("api",))), encoding="utf-8")
    code, output = run(arguments, capsys)
    assert code == 1
    assert output["collection"]["services"]["api"]["state"] == "threshold_exceeded"
    assert output["collection"]["services"]["web"]["state"] == "missing"


def test_rejects_stale_collection_and_backup_with_available_restore(arguments, capsys):
    arguments["summary-ended-at-utc"] = timestamp(2)
    arguments["backup-finished-at-utc"] = timestamp(25)
    code, output = run(arguments, capsys)
    assert code == 1
    assert output["collection"]["state"] == "stale"
    assert output["backup"]["state"] == "stale"
    assert output["restore"]["state"] == "ok"


def test_qualification_receipt_is_not_a_restore_receipt(arguments, capsys):
    Path(arguments["restore-receipt"]).write_text(
        json.dumps({"passed": True, "finished_at_utc": timestamp()}), encoding="utf-8"
    )
    code, output = run(arguments, capsys)
    assert code == 1
    assert output["restore"]["state"] == "invalid"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("api-url", f"http://{PRIVATE}@127.0.0.1/health"),
        ("api-url", f"http://127.0.0.1/health?token={PRIVATE}"),
        ("timeout-seconds", "nan"),
        ("max-5xx-percent", "101"),
        ("backup-finished-at-utc", "2026-11-21T04:00:00"),
        ("restore-finished-at-utc", "9999-12-31T00:00:00Z"),
    ],
)
def test_invalid_inputs_fail_before_network(arguments, endpoints, capsys, key, value):
    arguments[key] = value
    with pytest.raises(SystemExit) as error:
        main(argv(arguments))
    result = capsys.readouterr()
    assert error.value.code == 2
    assert PRIVATE not in result.out + result.err
    assert endpoints[2] == []
