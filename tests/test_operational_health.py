import io
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from ssl import SSLCertVerificationError
from threading import Thread
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from scripts import check_operational_health as operational_health
from scripts import show_operational_status as operator_status
from scripts.check_operational_health import main, probe_tls
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


def test_readout_labels_and_preserves_probe_observations(arguments, endpoints, capsys):
    arguments["environment"] = "synthetic"
    assert main(argv(arguments)) == 0
    receipt = json.loads(capsys.readouterr().out)
    now = datetime.now(UTC)
    view = operator_status.summarize(receipt, "synthetic", now, 5)
    assert view["environment"] == "synthetic" and view["receipt_state"] == "recent"
    assert view["signals"]["api_http"] == {
        "state_at_observation": "ok",
        "http_status": 200,
    }
    assert view["signals"]["mongodb_tls"] == {"state": "unavailable"}
    assert view["independent_evidence"]["mongodb_runtime"] == "unavailable"
    assert view["independent_evidence"]["alert_delivery"] == "unavailable"
    assert PRIVATE not in json.dumps(view)

    endpoints[1]["web"] = 503
    assert main(argv(arguments)) == 1
    receipt = json.loads(capsys.readouterr().out)
    view = operator_status.summarize(receipt, "synthetic", datetime.now(UTC), 5)
    assert view["signals"]["web_http"] == {
        "state_at_observation": "unexpected_status",
        "http_status": 503,
    }


def test_readout_refuses_old_unlabeled_or_wrong_environment(arguments, capsys):
    arguments["environment"] = "synthetic"
    assert main(argv(arguments)) == 0
    receipt = json.loads(capsys.readouterr().out)
    now = datetime.now(UTC)
    stale = operator_status.summarize(
        receipt, "synthetic", now + timedelta(minutes=6), 5
    )
    assert stale["receipt_state"] == "stale"
    assert "http_status" not in stale["signals"]["api_http"]
    for value, environment in (
        (receipt, "stable"),
        ({}, "synthetic"),
        (None, "synthetic"),
    ):
        view = operator_status.summarize(value, environment, now, 5)
        assert view["receipt_state"] == "unavailable"
        assert view["signals"]["api_http"] == {"state": "unavailable"}


def run(arguments, capsys):
    code = main(argv(arguments))
    result = capsys.readouterr()
    assert PRIVATE not in result.out + result.err
    assert "http://" not in result.out + result.err
    assert result.err == ""
    return code, json.loads(result.out)


@pytest.fixture
def tls_target(tmp_path):
    return {
        "connect_host": "127.0.0.1",
        "server_name": f"{PRIVATE.lower().replace('_', '-')}.test",
        "port": 8443,
        "ca_file": str(tmp_path / f"{PRIVATE}.pem"),
        "min_remaining_hours": 48,
    }


def test_tls_probe_verifies_name_and_checks_remaining_lifetime(tls_target, monkeypatch):
    context = MagicMock()
    connection = MagicMock()
    socket = context.wrap_socket.return_value.__enter__.return_value
    socket.getpeercert.return_value = {
        "notAfter": (datetime.now(UTC) + timedelta(hours=36)).strftime(
            "%b %d %H:%M:%S %Y GMT"
        )
    }
    socket.version.return_value = "TLSv1.3"
    monkeypatch.setattr(operational_health.ssl, "SSLContext", lambda _: context)
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr(operational_health.socket, "create_connection", connect)

    result = probe_tls(tls_target, 5)
    assert result["state"] == "expires_soon"
    assert result["tls_protocol"] == "TLSv1.3"
    assert 35 * 3600 < result["remaining_seconds"] <= 36 * 3600
    connect.assert_called_once_with(("127.0.0.1", 8443), timeout=5)
    context.load_verify_locations.assert_called_once_with(cafile=tls_target["ca_file"])
    context.wrap_socket.assert_called_once_with(
        connection.__enter__.return_value, server_hostname=tls_target["server_name"]
    )
    assert probe_tls({**tls_target, "min_remaining_hours": 24}, 5)["state"] == "ok"

    context.wrap_socket.side_effect = SSLCertVerificationError(1, PRIVATE)
    assert probe_tls(tls_target, 5) == {"state": "certificate_invalid"}


def test_tls_checks_set_exit_status_without_exposing_configuration(
    arguments, tls_target, endpoints, capsys, tmp_path, monkeypatch
):
    policy = tmp_path / "tls.json"
    policy.write_text(json.dumps({"proxy": tls_target, "mongodb": tls_target}))
    arguments["tls-policy"] = str(policy)
    probe = MagicMock(side_effect=[{"state": "ok"}, {"state": "certificate_invalid"}])
    monkeypatch.setattr(operational_health, "probe_tls", probe)
    code, output = run(arguments, capsys)
    assert code == 1
    assert output["tls_certificates"] == {
        "state": "certificate_check_failed",
        "targets": {
            "proxy": {"state": "ok"},
            "mongodb": {"state": "certificate_invalid"},
        },
    }
    assert probe.call_count == 2

    _, _, requests = endpoints
    requests.clear()
    policy.write_text(json.dumps({"proxy": {**tls_target, "port": True}}))
    with pytest.raises(SystemExit) as error:
        main(argv(arguments))
    assert error.value.code == 2
    assert not requests
    assert PRIVATE not in capsys.readouterr().err


@pytest.mark.parametrize(
    ("proxy_result", "web_result", "exit_code"),
    [
        (
            {"state": "ok", "http_health": {"state": "ok", "http_status": 200}},
            {"state": "ok", "http_status": 200},
            0,
        ),
        (
            {
                "state": "ok",
                "http_health": {"state": "unexpected_status", "http_status": 302},
            },
            {"state": "unexpected_status", "http_status": 302},
            1,
        ),
        ({"state": "certificate_invalid"}, {"state": "certificate_invalid"}, 1),
    ],
)
def test_proxy_health_uses_the_authenticated_connection(
    arguments,
    tls_target,
    endpoints,
    capsys,
    tmp_path,
    monkeypatch,
    proxy_result,
    web_result,
    exit_code,
):
    policy = tmp_path / "tls.json"
    policy.write_text(json.dumps({"proxy": tls_target}), encoding="utf-8")
    url = f"https://{tls_target['server_name']}:{tls_target['port']}/health"
    arguments.update({"tls-policy": str(policy), "web-url": url})
    proxy = MagicMock(return_value=dict(proxy_result))
    monkeypatch.setattr(operational_health, "probe_tls", proxy)

    result = main([*argv(arguments), "--web-via-proxy-tls"])
    captured = capsys.readouterr()
    assert result == exit_code
    assert tls_target["server_name"] not in captured.out + captured.err
    assert captured.err == ""
    assert json.loads(captured.out)["health"]["web"] == web_result
    assert endpoints[2] == [f"/api/{PRIVATE}"]
    assert proxy.call_args.kwargs["health_target"].geturl() == url


@pytest.mark.parametrize(
    "url",
    [
        "http://staging.test:8443/health",
        "https://other.test:8443/health",
        "https://staging.test:8444/health",
    ],
)
def test_proxy_health_rejects_a_different_origin_before_requests(
    url,
    arguments,
    tls_target,
    endpoints,
    capsys,
    tmp_path,
):
    policy = tmp_path / "tls.json"
    policy.write_text(
        json.dumps({"proxy": {**tls_target, "server_name": "staging.test"}}),
        encoding="utf-8",
    )
    arguments.update({"tls-policy": str(policy), "web-url": url})
    with pytest.raises(SystemExit) as error:
        main([*argv(arguments), "--web-via-proxy-tls"])
    assert error.value.code == 2
    assert not endpoints[2]
    assert not capsys.readouterr().out


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


@pytest.fixture
def backup_verification(arguments, tmp_path):
    path = tmp_path / f"verified-{PRIVATE}.json"
    arguments["backup-verification-receipt"] = str(path)
    value = {
        "status": "BACKUP_FRESHNESS_VERIFIED",
        "ciphertext_sha256": "a" * 64,
        "archive_bytes": 27,
        "created_utc": timestamp(2),
        "checked_at_utc": timestamp(0.5),
        "maximum_age_hours": 24,
    }
    return path, value


def test_off_host_verification_missing_then_recovers(
    arguments, capsys, backup_verification
):
    path, value = backup_verification
    assert run(arguments, capsys)[1]["backup_verification"] == {"state": "missing"}
    path.write_text(json.dumps(value), encoding="utf-8")
    code, output = run(arguments, capsys)
    assert code == 0 and output["restore"]["state"] == "ok"
    check = output["backup_verification"]
    assert check["state"] == "ok"
    assert check["capture_age_seconds"] >= 7200
    assert check["verification_age_seconds"] >= 1800
    assert value["ciphertext_sha256"] not in json.dumps(output)


@pytest.mark.parametrize(
    ("offset_microseconds", "expected_code", "expected_state"),
    [(-1, 0, "ok"), (0, 0, "ok"), (1, 1, "verification_predates_attempt")],
)
def test_off_host_verification_respects_attempt_boundary(
    arguments,
    capsys,
    backup_verification,
    offset_microseconds,
    expected_code,
    expected_state,
):
    path, value = backup_verification
    checked_at = datetime.fromisoformat(value["checked_at_utc"])
    arguments["backup-verified-since-utc"] = (
        checked_at + timedelta(microseconds=offset_microseconds)
    ).isoformat()
    path.write_text(json.dumps(value), encoding="utf-8")
    code, output = run(arguments, capsys)
    assert code == expected_code
    assert output["backup"]["state"] == "ok"
    assert output["backup_verification"]["state"] == expected_state


@pytest.mark.parametrize("cutoff", ["unknown", "9999-12-31T00:00:00Z", "bad"])
def test_verification_cutoff_must_be_known_and_past(
    arguments, endpoints, capsys, backup_verification, cutoff
):
    arguments["backup-verified-since-utc"] = cutoff
    with pytest.raises(SystemExit) as error:
        main(argv(arguments))
    assert error.value.code == 2
    assert not capsys.readouterr().out
    assert endpoints[2] == []


def test_verified_capture_must_also_meet_current_policy(
    arguments, capsys, backup_verification
):
    path, value = backup_verification
    value.update(created_utc=timestamp(25), maximum_age_hours=48)
    path.write_text(json.dumps(value), encoding="utf-8")
    code, output = run(arguments, capsys)
    assert code == 1
    assert output["backup"]["state"] == "ok"
    assert output["backup_verification"]["state"] == "stale"


@pytest.mark.parametrize(
    ("changes", "state"),
    [
        ({"ciphertext_sha256": "b" * 64}, "archive_mismatch"),
        ({"archive_bytes": 28}, "archive_mismatch"),
        ({"status": "CIPHERTEXT_AUTHENTICATED"}, "invalid"),
        ({"maximum_age_hours": 1}, "invalid"),
        ({"maximum_age_hours": True}, "invalid"),
        ({"checked_at_utc": "unknown"}, "timestamp_missing"),
        ({"created_utc": "2026-11-25T02:09:19+01:00"}, "invalid"),
        ({"checked_at_utc": "9999-12-31T00:00:00Z"}, "future_timestamp"),
        ({"created_utc": "9999-12-31T00:00:00Z"}, "future_timestamp"),
    ],
)
def test_rejects_invalid_off_host_verification(
    arguments, capsys, backup_verification, changes, state
):
    path, value = backup_verification
    path.write_text(json.dumps({**value, **changes}), encoding="utf-8")
    code, output = run(arguments, capsys)
    assert code == 1
    assert output["backup_verification"] == {"state": state}


def test_swarm_capacity_reports_each_threshold_and_recovers(
    arguments, capsys, tmp_path
):
    snapshot = tmp_path / f"capacity-{PRIVATE}.json"
    arguments.update(
        {
            "swarm-capacity-snapshot": str(snapshot),
            "max-capacity-age-hours": "1",
            "min-available-memory-mib": "1024",
            "min-docker-free-mib": "3072",
        }
    )
    capacity = {
        "timestamp_utc": timestamp(),
        "available_ram_bytes": 1024 * 1024**2,
        "docker_available_disk_bytes": 3072 * 1024**2,
        "discarded": PRIVATE,
    }
    nodes = {role: capacity.copy() for role in ("web", "api", "manager")}
    nodes["web"]["available_ram_bytes"] -= 1
    nodes["api"]["docker_available_disk_bytes"] -= 1
    snapshot.write_text(json.dumps({"nodes": nodes}), encoding="utf-8")
    code, output = run(arguments, capsys)
    checks = output["swarm_capacity"]["nodes"]
    assert code == 1
    assert checks["web"]["below_threshold"] == ["memory"]
    assert checks["api"]["below_threshold"] == ["docker_disk"]
    assert checks["manager"]["state"] == "ok"

    snapshot.write_text(
        json.dumps({"nodes": {role: capacity for role in nodes}}), encoding="utf-8"
    )
    code, output = run(arguments, capsys)
    assert code == 0
    assert output["swarm_capacity"]["state"] == "ok"


def test_swarm_capacity_rejects_missing_stale_and_future_data(
    arguments, capsys, tmp_path
):
    snapshot = tmp_path / "capacity.json"
    arguments.update(
        {
            "swarm-capacity-snapshot": str(snapshot),
            "max-capacity-age-hours": "1",
            "min-available-memory-mib": "1",
            "min-docker-free-mib": "1",
        }
    )
    code, output = run(arguments, capsys)
    assert code == 1
    assert output["swarm_capacity"]["state"] == "missing"

    resources = {"available_ram_bytes": 1024**2, "docker_available_disk_bytes": 1024**2}
    snapshot.write_text(
        json.dumps(
            {
                "nodes": {
                    "web": {**resources, "timestamp_utc": timestamp(2)},
                    "api": {**resources, "timestamp_utc": timestamp(-2)},
                },
            }
        ),
        encoding="utf-8",
    )
    code, output = run(arguments, capsys)
    checks = output["swarm_capacity"]["nodes"]
    assert code == 1
    assert checks["web"]["state"] == "stale"
    assert checks["api"]["state"] == "future_timestamp"
    assert checks["manager"]["state"] == "missing"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("api-url", f"http://{PRIVATE}@127.0.0.1/health"),
        ("api-url", f"http://127.0.0.1/health?token={PRIVATE}"),
        ("timeout-seconds", "nan"),
        ("max-5xx-percent", "101"),
        ("min-docker-free-mib", "3072"),
        ("swarm-capacity-snapshot", "partial.json"),
        ("backup-finished-at-utc", "2026-11-21T04:00:00"),
        ("restore-finished-at-utc", "9999-12-31T00:00:00Z"),
        ("backup-verified-since-utc", "2020-01-01T00:00:00Z"),
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
