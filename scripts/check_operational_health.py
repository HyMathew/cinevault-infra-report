"""Check CineVault health endpoints and operator-supplied evidence once."""

import argparse
import json
import math
import re
import socket
import ssl
import stat
from datetime import UTC, datetime, timedelta
from http.client import HTTPException
from ipaddress import ip_address
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

SERVICES = ("api", "web")
SWARM_ROLES = ("web", "api", "manager")
TLS_ROLES = ("proxy", "mongodb")
TLS_FIELDS = {"connect_host", "server_name", "port", "ca_file", "min_remaining_hours"}
DNS_LABEL = re.compile(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?")
MAX_JSON_BYTES = 4 * 1024 * 1024
MIB = 1024**2


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Arguments invalides. Utiliser --help.\n")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def health_url(value):
    try:
        url = urlsplit(value)
        valid = (
            url.scheme in ("http", "https")
            and url.hostname
            and (url.port is None or url.port > 0)
            and not any(char in value for char in "@?#\\")
            and all(33 <= ord(char) <= 126 for char in value)
        )
    except ValueError:
        valid = False
    if not valid:
        raise argparse.ArgumentTypeError("Expected a direct HTTP or HTTPS URL.")
    return value


def utc_timestamp(value):
    if value == "unknown":
        return None
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Expected an ISO 8601 UTC timestamp."
        ) from error
    if timestamp.utcoffset() != timedelta(0):
        raise argparse.ArgumentTypeError("Expected an ISO 8601 UTC timestamp.")
    return timestamp


def probe(opener, url, timeout):
    try:
        with opener.open(url, timeout=timeout) as response:
            status = response.status
    except HTTPError as error:
        with error:
            status = error.code
    except (OSError, ValueError, HTTPException):
        return {"state": "unreachable"}
    return {
        "state": "ok" if status == 200 else "unexpected_status",
        "http_status": status,
    }


def read_evidence(path):
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            return None, "invalid"
        with path.open("rb") as source:
            raw = source.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            return None, "invalid"
        if not raw.strip():
            return None, "empty"
        value = json.loads(raw.decode("utf-8-sig"))
        if isinstance(value, dict):
            return value, None
    except FileNotFoundError:
        return None, "missing"
    except OSError:
        return None, "unreadable"
    except (ValueError, RecursionError):
        pass
    return None, "invalid"


def tls_host(value):
    if not isinstance(value, str):
        return False
    try:
        ip_address(value)
        return "%" not in value
    except ValueError:
        return len(value) <= 253 and all(
            DNS_LABEL.fullmatch(label) for label in value.split(".")
        )


def tls_policy(path):
    targets, failure = read_evidence(path)
    if failure or not targets or targets.keys() - TLS_ROLES:
        raise argparse.ArgumentTypeError("Expected a policy for proxy and/or mongodb.")
    for target in targets.values():
        if (
            not isinstance(target, dict)
            or target.keys() != TLS_FIELDS
            or not tls_host(target["connect_host"])
            or not tls_host(target["server_name"])
            or type(target["port"]) is not int
            or not 1 <= target["port"] <= 65535
            or not isinstance(target["ca_file"], str)
            or not Path(target["ca_file"]).is_absolute()
            or "\x00" in target["ca_file"]
            or type(target["min_remaining_hours"]) is not int
            or target["min_remaining_hours"] <= 0
        ):
            raise argparse.ArgumentTypeError("Invalid TLS target.")
    return targets


def probe_tls(target, timeout):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    try:
        context.load_verify_locations(cafile=target["ca_file"])
    except (OSError, ValueError):
        return {"state": "trust_unavailable"}
    try:
        with (
            socket.create_connection(
                (target["connect_host"], target["port"]), timeout=timeout
            ) as connection,
            context.wrap_socket(
                connection, server_hostname=target["server_name"]
            ) as tls,
        ):
            certificate = tls.getpeercert()
            protocol = tls.version()
    except ssl.SSLCertVerificationError:
        return {"state": "certificate_invalid"}
    except ssl.SSLError:
        return {"state": "handshake_failed"}
    except (OSError, ValueError):
        return {"state": "unreachable"}
    try:
        expires_at = datetime.fromtimestamp(
            ssl.cert_time_to_seconds(certificate["notAfter"]), UTC
        )
    except (KeyError, ValueError, OverflowError, OSError):
        return {"state": "certificate_invalid"}
    remaining = (expires_at - datetime.now(UTC)).total_seconds()
    limit = target["min_remaining_hours"]
    return {
        "state": "ok" if remaining >= limit * 3600 else "expires_soon",
        "expires_at_utc": expires_at.isoformat(),
        "remaining_seconds": max(0, int(remaining)),
        "min_remaining_hours": limit,
        "tls_protocol": protocol,
    }


def service_summary(group, max_5xx):
    if not isinstance(group, dict):
        return {"state": "invalid"}
    counts = group.get("status_counts")
    total = group.get("requests")
    percent = group.get("error_5xx_percent")
    if (
        type(total) is not int
        or total <= 0
        or not isinstance(counts, dict)
        or any(
            not re.fullmatch(r"[1-5][0-9]{2}", status)
            or type(count) is not int
            or count <= 0
            for status, count in counts.items()
        )
        or sum(counts.values()) != total
    ):
        return {"state": "invalid"}
    errors = sum(count for status, count in counts.items() if status.startswith("5"))
    rate = errors * 100 / total
    if type(percent) not in (float, int) or round(rate, 3) != percent:
        return {"state": "invalid"}
    return {
        "state": "threshold_exceeded" if rate > max_5xx else "ok",
        "requests": total,
        "error_5xx_count": errors,
        "error_5xx_percent": percent,
    }


def collection(path, age_seconds, max_age_hours, max_5xx):
    value, failure = read_evidence(path)
    if failure:
        return {"state": failure}
    services = value.get("services")
    ignored = value.get("ignored_lines")
    if (
        not isinstance(services, dict)
        or not isinstance(value.get("routes"), list)
        or type(ignored) is not int
        or ignored < 0
        or services.keys() - SERVICES
    ):
        return {"state": "invalid"}
    checks = {
        name: service_summary(services[name], max_5xx)
        if name in services
        else {"state": "missing"}
        for name in SERVICES
    }
    if not services:
        state = "empty"
    elif age_seconds is None:
        state = "timestamp_missing"
    elif age_seconds / 3600 > max_age_hours:
        state = "stale"
    elif all(check["state"] == "ok" for check in checks.values()):
        state = "ok"
    else:
        state = "service_check_failed"
    return {
        "state": state,
        "age_seconds": int(age_seconds) if age_seconds is not None else None,
        "ignored_lines": ignored,
        "services": checks,
    }


def read_backup_receipt(path, expected_status):
    value, failure = read_evidence(path)
    if failure:
        return None, failure
    digest = value.get("ciphertext_sha256")
    size = value.get("archive_bytes")
    if (
        value.get("status") != expected_status
        or not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
        or type(size) is not int
        or size <= 0
    ):
        return None, "invalid"
    return value, None


def receipt_age(failure, age_seconds, max_age_hours):
    if failure:
        return {"state": failure}
    if age_seconds is None:
        return {"state": "timestamp_missing"}
    return {
        "state": "stale" if age_seconds / 3600 > max_age_hours else "ok",
        "age_seconds": int(age_seconds),
    }


def backup_verification(path, backup, now, max_age_hours):
    proof, failure = read_backup_receipt(path, "BACKUP_FRESHNESS_VERIFIED")
    if failure:
        return {"state": failure}
    if backup is None:
        return {"state": "backup_receipt_unavailable"}
    if any(proof[key] != backup[key] for key in ("ciphertext_sha256", "archive_bytes")):
        return {"state": "archive_mismatch"}

    capture = proof.get("created_utc")
    checked = proof.get("checked_at_utc")
    maximum = proof.get("maximum_age_hours")
    if (
        not isinstance(capture, str)
        or not isinstance(checked, str)
        or type(maximum) is not int
        or not 1 <= maximum <= 168
    ):
        return {"state": "invalid"}
    try:
        capture = utc_timestamp(capture)
        checked = utc_timestamp(checked)
    except argparse.ArgumentTypeError:
        return {"state": "invalid"}
    if capture is None or checked is None:
        return {"state": "timestamp_missing"}
    if max(capture, checked) > now:
        return {"state": "future_timestamp"}
    if not timedelta(0) <= checked - capture <= timedelta(hours=maximum):
        return {"state": "invalid"}

    age = (now - capture).total_seconds()
    return {
        "state": "stale" if age / 3600 > max_age_hours else "ok",
        "capture_age_seconds": int(age),
        "verification_age_seconds": int((now - checked).total_seconds()),
    }


def capacity_node(value, now, max_age_hours, min_memory_mib, min_disk_mib):
    if not isinstance(value, dict):
        return {"state": "invalid"}
    memory = value.get("available_ram_bytes")
    disk = value.get("docker_available_disk_bytes")
    timestamp = value.get("timestamp_utc")
    if (
        type(memory) is not int
        or type(disk) is not int
        or min(memory, disk) < 0
        or not isinstance(timestamp, str)
    ):
        return {"state": "invalid"}
    try:
        observed_at = utc_timestamp(timestamp)
    except argparse.ArgumentTypeError:
        return {"state": "invalid"}
    if observed_at is None:
        return {"state": "timestamp_missing"}
    age = (now - observed_at).total_seconds()
    if age < 0:
        return {"state": "future_timestamp"}
    below_threshold = [
        metric
        for metric, free, limit in (
            ("memory", memory, min_memory_mib),
            ("docker_disk", disk, min_disk_mib),
        )
        if free < limit * MIB
    ]
    state = "ok"
    if age > max_age_hours * 3600:
        state = "stale"
    elif below_threshold:
        state = "threshold_exceeded"
    return {
        "state": state,
        "age_seconds": int(age),
        "available_memory_mib": memory // MIB,
        "available_docker_disk_mib": disk // MIB,
        "below_threshold": below_threshold,
    }


def swarm_capacity(path, now, max_age_hours, min_memory_mib, min_disk_mib):
    value, failure = read_evidence(path)
    if failure:
        return {"state": failure}
    nodes = value.get("nodes")
    if not isinstance(nodes, dict) or nodes.keys() - SWARM_ROLES:
        return {"state": "invalid"}
    checks = {
        role: capacity_node(
            nodes[role], now, max_age_hours, min_memory_mib, min_disk_mib
        )
        if role in nodes
        else {"state": "missing"}
        for role in SWARM_ROLES
    }
    ok = all(check["state"] == "ok" for check in checks.values())
    return {"state": "ok" if ok else "node_check_failed", "nodes": checks}


def main(argv=None):
    parser = Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--api-url", required=True, type=health_url)
    parser.add_argument("--web-url", required=True, type=health_url)
    parser.add_argument("--timeout-seconds", required=True, type=float)
    parser.add_argument("--http-summary", required=True, type=Path)
    timestamp_options = {
        "required": True,
        "type": utc_timestamp,
        "help": "ISO 8601 UTC timestamp, or 'unknown' to report a missing timestamp",
    }
    parser.add_argument("--summary-ended-at-utc", **timestamp_options)
    parser.add_argument("--max-summary-age-hours", required=True, type=float)
    parser.add_argument("--max-5xx-percent", required=True, type=float)
    parser.add_argument("--backup-receipt", required=True, type=Path)
    parser.add_argument(
        "--backup-verification-receipt",
        type=Path,
        help="Receipt from verify --maximum-age-hours for the off-host copy",
    )
    parser.add_argument("--backup-finished-at-utc", **timestamp_options)
    parser.add_argument("--max-backup-age-hours", required=True, type=float)
    parser.add_argument("--restore-receipt", required=True, type=Path)
    parser.add_argument("--restore-finished-at-utc", **timestamp_options)
    parser.add_argument("--max-restore-age-hours", required=True, type=float)
    parser.add_argument("--swarm-capacity-snapshot", type=Path)
    parser.add_argument("--max-capacity-age-hours", type=float)
    parser.add_argument("--min-available-memory-mib", type=int)
    parser.add_argument("--min-docker-free-mib", type=int)
    parser.add_argument(
        "--tls-policy", type=Path, help="JSON policy for staging TLS certificates"
    )
    args = parser.parse_args(argv)
    limits = (
        args.max_summary_age_hours,
        args.max_backup_age_hours,
        args.max_restore_age_hours,
    )
    if (
        not 0 < args.timeout_seconds <= 300
        or not 0 <= args.max_5xx_percent <= 100
        or any(not math.isfinite(limit) or limit <= 0 for limit in limits)
    ):
        parser.error("Invalid threshold.")
    capacity_options = (
        args.max_capacity_age_hours,
        args.min_available_memory_mib,
        args.min_docker_free_mib,
    )
    if args.swarm_capacity_snapshot is None:
        if any(option is not None for option in capacity_options):
            parser.error("Swarm capacity snapshot required.")
    elif any(
        option is None or option <= 0 for option in capacity_options
    ) or not math.isfinite(args.max_capacity_age_hours):
        parser.error("All Swarm capacity thresholds must be positive.")
    targets = {}
    if args.tls_policy is not None:
        try:
            targets = tls_policy(args.tls_policy)
        except argparse.ArgumentTypeError:
            parser.error("Invalid TLS policy.")
    now = datetime.now(UTC)
    timestamps = (
        args.summary_ended_at_utc,
        args.backup_finished_at_utc,
        args.restore_finished_at_utc,
    )
    ages = [
        (now - timestamp).total_seconds() if timestamp is not None else None
        for timestamp in timestamps
    ]
    if any(age is not None and age < 0 for age in ages):
        parser.error("Evidence timestamp is in the future.")
    summary_age, backup_age, restore_age = ages

    opener = build_opener(ProxyHandler({}), NoRedirect())
    health = {
        "api": probe(opener, args.api_url, args.timeout_seconds),
        "web": probe(opener, args.web_url, args.timeout_seconds),
    }
    backup, backup_failure = read_backup_receipt(
        args.backup_receipt, "ENCRYPTED_BACKUP_CREATED"
    )
    _, restore_failure = read_backup_receipt(
        args.restore_receipt, "ISOLATED_RESTORE_VERIFIED"
    )
    checks = {
        "collection": collection(
            args.http_summary,
            summary_age,
            args.max_summary_age_hours,
            args.max_5xx_percent,
        ),
        "backup": receipt_age(
            backup_failure,
            backup_age,
            args.max_backup_age_hours,
        ),
        "restore": receipt_age(
            restore_failure,
            restore_age,
            args.max_restore_age_hours,
        ),
    }
    if args.backup_verification_receipt is not None:
        checks["backup_verification"] = backup_verification(
            args.backup_verification_receipt, backup, now, args.max_backup_age_hours
        )
    if args.swarm_capacity_snapshot is not None:
        checks["swarm_capacity"] = swarm_capacity(
            args.swarm_capacity_snapshot, now, *capacity_options
        )
    if targets:
        certificates = {
            role: probe_tls(targets[role], args.timeout_seconds)
            for role in TLS_ROLES
            if role in targets
        }
        checks["tls_certificates"] = {
            "state": "ok"
            if all(check["state"] == "ok" for check in certificates.values())
            else "certificate_check_failed",
            "targets": certificates,
        }
    ok = all(check["state"] == "ok" for check in (*health.values(), *checks.values()))
    print(
        json.dumps(
            {"state": "ok" if ok else "check_failed", "health": health, **checks},
            sort_keys=True,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
