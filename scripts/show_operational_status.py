"""Render an offline, private view of the latest labeled CineVault probe receipt."""

import argparse
import json
import math
from datetime import UTC, datetime
from pathlib import Path

if __package__:
    from .check_operational_health import ENVIRONMENTS, read_evidence, utc_timestamp
else:
    from check_operational_health import ENVIRONMENTS, read_evidence, utc_timestamp

SIGNALS = {
    "web_http": ("health", "web"),
    "api_http": ("health", "api"),
    "http_collection_window": ("collection",),
    "api_http_errors": ("collection", "services", "api"),
    "web_http_errors": ("collection", "services", "web"),
    "backup": ("backup",),
    "restore": ("restore",),
    "off_host_backup": ("backup_verification",),
    "proxy_tls": ("tls_certificates", "targets", "proxy"),
    "mongodb_tls": ("tls_certificates", "targets", "mongodb"),
    "swarm_web_capacity": ("swarm_capacity", "nodes", "web"),
    "swarm_api_capacity": ("swarm_capacity", "nodes", "api"),
    "swarm_manager_capacity": ("swarm_capacity", "nodes", "manager"),
}
UNAVAILABLE_STATES = {
    "missing",
    "invalid",
    "empty",
    "unreadable",
    "timestamp_missing",
    "trust_unavailable",
    "backup_receipt_unavailable",
}
DEGRADED_STATES = {
    "unreachable",
    "unexpected_status",
    "stale",
    "threshold_exceeded",
    "service_check_failed",
    "archive_mismatch",
    "verification_predates_attempt",
    "certificate_invalid",
    "handshake_failed",
    "expires_soon",
    "node_check_failed",
    "future_timestamp",
}


def section(receipt, keys):
    result = receipt
    for key in keys:
        result = result.get(key) if isinstance(result, dict) else None
    return result if isinstance(result, dict) else {}


def observed_signal(value):
    state = value.get("state")
    if not isinstance(state, str) or state in UNAVAILABLE_STATES:
        return {"state": "unavailable"}
    if state not in DEGRADED_STATES and state != "ok":
        return {"state": "unavailable"}
    result = {"state_at_observation": state}
    status = value.get("http_status")
    if type(status) is int and 100 <= status <= 599:
        result["http_status"] = status
    for key in ("age_seconds", "capture_age_seconds"):
        number = value.get(key)
        if type(number) is int and number >= 0:
            result[key + "_at_observation"] = number
    for key in (
        "requests",
        "error_5xx_count",
        "available_memory_mib",
        "available_docker_disk_mib",
    ):
        number = value.get(key)
        if type(number) is int and number >= 0:
            result[key] = number
    percent = value.get("error_5xx_percent")
    if type(percent) in (int, float) and 0 <= percent <= 100:
        result["error_5xx_percent"] = percent
    stamp = value.get("expires_at_utc")
    if isinstance(stamp, str):
        try:
            expiration = utc_timestamp(stamp)
        except argparse.ArgumentTypeError:
            expiration = None
        if expiration is not None:
            result["expires_at_utc"] = expiration.isoformat()
    return result


def summarize(receipt, environment, now, max_age_minutes):
    report = {
        "source": "check_operational_health.py",
        "environment": environment,
        "observed_at_utc": None,
        "receipt_state": "unavailable",
        "signals": {name: {"state": "unavailable"} for name in SIGNALS},
        "independent_evidence": {
            "mongodb_runtime": "unavailable",
            "swarm_services": "unavailable",
            "deployed_images": "unavailable",
            "attestations": "unavailable",
            "alert_delivery": "unavailable",
        },
    }
    measurement = section(receipt, ("measurement",))
    if (
        receipt is None
        or measurement.get("schema") != 1
        or measurement.get("environment") != environment
        or receipt.get("state") not in ("ok", "check_failed")
    ):
        return report
    try:
        start = utc_timestamp(measurement.get("started_at_utc"))
        end = utc_timestamp(measurement.get("finished_at_utc"))
    except (argparse.ArgumentTypeError, TypeError):
        return report
    if start is None or end is None or not start <= end <= now:
        return report
    report["observed_at_utc"] = end.isoformat()
    elapsed = (now - start).total_seconds()
    report["age_seconds"] = int(elapsed)
    if elapsed > max_age_minutes * 60:
        report["receipt_state"] = "stale"
        report["signals"] = {name: {"state": "stale"} for name in SIGNALS}
        return report
    report["receipt_state"] = "recent"
    report["probe_state_at_observation"] = receipt["state"]
    report["signals"] = {
        name: observed_signal(section(receipt, keys)) for name, keys in SIGNALS.items()
    }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    parser.add_argument("--max-age-minutes", type=float, required=True)
    args = parser.parse_args(argv)
    if not math.isfinite(args.max_age_minutes) or args.max_age_minutes <= 0:
        parser.error("--max-age-minutes must be positive and finite")
    receipt, _ = read_evidence(args.receipt)
    report = summarize(
        receipt, args.environment, datetime.now(UTC), args.max_age_minutes
    )
    print(json.dumps(report, indent=2))
    return int(report["receipt_state"] != "recent")


if __name__ == "__main__":
    raise SystemExit(main())
