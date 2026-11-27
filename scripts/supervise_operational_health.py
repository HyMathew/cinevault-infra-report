"""Run scheduled CineVault probes and deliver incident events through a file inbox."""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from scripts.check_operational_health import MAX_JSON_BYTES, utc_timestamp

SCHEMA = """
CREATE TABLE IF NOT EXISTS results (
    slot TEXT PRIMARY KEY, deadline TEXT NOT NULL, finished TEXT NOT NULL,
    reason TEXT NOT NULL, api INTEGER, web INTEGER
);
CREATE TABLE IF NOT EXISTS observations (
    slot TEXT PRIMARY KEY, deadline TEXT NOT NULL, reason TEXT NOT NULL, incident TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY, body TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0
);
"""
PROBE = Path(__file__).with_name("check_operational_health.py")


def stamp(instant):
    return instant.isoformat(timespec="microseconds")


def known_utc(value):
    instant = utc_timestamp(value)
    if instant is None:
        raise argparse.ArgumentTypeError("A known UTC timestamp is required")
    return instant


def monitor_db(path):
    connection = sqlite3.connect(path, timeout=5)
    try:
        connection.executescript(SCHEMA)
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.Error:
        connection.close()
        raise


def status(summary, service):
    value = summary.get("health", {}).get(service, {}).get("http_status")
    if type(value) is int and 100 <= value <= 599:
        return value
    return None


def measure(options, slot, deadline):
    remaining = (deadline - datetime.now(UTC)).total_seconds()
    if remaining <= 0:
        return "runner_timeout", None, None
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(PROBE),
                *options,
                "--backup-verified-since-utc",
                slot,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=remaining,
        )
    except subprocess.TimeoutExpired:
        return "runner_timeout", None, None
    if result.returncode not in (0, 1):
        return "probe_execution_failed", None, None
    try:
        summary = json.loads(result.stdout)
        api, web = status(summary, "api"), status(summary, "web")
        valid = summary["state"] == ("ok" if result.returncode == 0 else "check_failed")
        if not valid or (result.returncode == 0 and (api, web) != (200, 200)):
            raise ValueError
    except (AttributeError, KeyError, ValueError):
        return "invalid_probe_result", None, None
    if result.returncode == 0:
        return "healthy", api, web
    return (
        (
            "web_http_error"
            if api == 200 and web is not None and web != 200
            else "probe_failed"
        ),
        api,
        web,
    )


def record(args, slot, deadline):
    options = args.options[1:] if args.options[:1] == ["--"] else args.options
    if not options:
        raise ValueError
    with closing(monitor_db(args.database)) as connection:
        stored = connection.execute(
            "SELECT * FROM results WHERE slot=?", (slot,)
        ).fetchone()
        if stored is None:
            reason, api, web = measure(options, slot, deadline)
            with connection:
                connection.execute(
                    "INSERT OR IGNORE INTO results VALUES (?, ?, ?, ?, ?, ?)",
                    (slot, stamp(deadline), stamp(datetime.now(UTC)), reason, api, web),
                )
                stored = connection.execute(
                    "SELECT * FROM results WHERE slot=?", (slot,)
                ).fetchone()
        if stored["deadline"] != stamp(deadline):
            raise ValueError
    return {"slot_utc": slot, "reason": stored["reason"]}, int(
        stored["reason"] != "healthy"
    )


def evaluate(database, slot, deadline):
    with closing(monitor_db(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT * FROM observations WHERE slot=?", (slot,)
        ).fetchone()
        if existing is not None:
            if existing["deadline"] != deadline:
                raise ValueError
            return existing["reason"]
        previous = connection.execute(
            "SELECT * FROM observations ORDER BY slot DESC LIMIT 1"
        ).fetchone()
        if previous is not None and previous["slot"] > slot:
            raise ValueError
        result = connection.execute(
            "SELECT * FROM results WHERE slot=?", (slot,)
        ).fetchone()
        if result is not None and result["deadline"] != deadline:
            raise ValueError
        reason, api, web = "missing_result", None, None
        if result is not None and slot <= result["finished"] <= deadline:
            reason, api, web = result["reason"], result["api"], result["web"]
        incident = previous["incident"] if previous is not None else None
        transition = None
        if reason == "healthy":
            if incident is not None:
                transition = "recovered"
        elif incident is None:
            incident, transition = uuid4().hex, "opened"
        elif reason != previous["reason"]:
            transition = "updated"
        if transition is not None:
            event_id = uuid4().hex
            event = {
                "event_id": event_id,
                "incident_id": incident,
                "event": transition,
                "observed_at_utc": stamp(datetime.now(UTC)),
                "slot_utc": slot,
                "deadline_utc": deadline,
                "reason": reason,
                "api_http": api,
                "web_http": web,
            }
            body = json.dumps(event, sort_keys=True) + "\n"
            connection.execute(
                "INSERT INTO events(id, body) VALUES (?, ?)", (event_id, body)
            )
        connection.execute(
            "INSERT INTO observations VALUES (?, ?, ?, ?)",
            (slot, deadline, reason, incident if reason != "healthy" else None),
        )
        return reason


def _publish_event(source, target):
    # Windows rename refuses an existing destination. POSIX rename
    # would replace it, so publish with a hard link there.
    if os.name == "nt":
        source.rename(target)
    else:
        target.hardlink_to(source)


def deliver(database, inbox):
    if not inbox.is_dir():
        raise OSError
    with closing(monitor_db(database)) as connection:
        pending = connection.execute(
            "SELECT id, body FROM events WHERE delivered=0 ORDER BY rowid"
        ).fetchall()
        for entry in pending:
            target = inbox / (entry["id"] + ".json")
            raw = entry["body"].encode("utf-8")
            if not target.exists():
                path = None
                try:
                    with NamedTemporaryFile(
                        dir=inbox, prefix=".incident-", delete=False
                    ) as temporary:
                        path = Path(temporary.name)
                        temporary.write(raw)
                        temporary.flush()
                        os.fsync(temporary.fileno())
                    try:
                        _publish_event(path, target)
                    except FileExistsError:
                        pass
                finally:
                    if path is not None:
                        path.unlink(missing_ok=True)
            if target.read_bytes() != raw:
                raise ValueError
            with connection:
                connection.execute(
                    "UPDATE events SET delivered=1 WHERE id=?", (entry["id"],)
                )


def receive(path):
    with path.open("rb") as source:
        raw = source.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError
    event = json.loads(raw)
    if not isinstance(event, dict) or any(
        not isinstance(event.get(key), str)
        or not re.fullmatch("[0-9a-f]{32}", event[key])
        for key in ("event_id", "incident_id")
    ):
        raise ValueError
    if path.name != event["event_id"] + ".json" or event.get("event") not in (
        "opened",
        "updated",
        "recovered",
    ):
        raise ValueError
    received = datetime.now(UTC)
    observed = known_utc(event["observed_at_utc"])
    if observed > received:
        raise ValueError
    return {
        "event_id": event["event_id"],
        "incident_id": event["incident_id"],
        "event": event["event"],
        "received_at_utc": stamp(received),
        "event_sha256": hashlib.sha256(raw).hexdigest(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", allow_abbrev=False)
    watch = commands.add_parser("watch", allow_abbrev=False)
    receiver = commands.add_parser("receive", allow_abbrev=False)
    for command in (run, watch):
        command.add_argument("--database", required=True, type=Path)
        command.add_argument("--slot-utc", required=True, type=known_utc)
        command.add_argument(
            "--deadline-seconds",
            required=True,
            type=int,
            choices=range(1, 3601),
            metavar="1..3600",
        )
    run.add_argument("options", nargs=argparse.REMAINDER)
    watch.add_argument("--inbox", required=True, type=Path)
    receiver.add_argument("--event", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "receive":
            print(json.dumps(receive(args.event), sort_keys=True))
            return 0
        current = datetime.now(UTC)
        deadline = args.slot_utc + timedelta(seconds=args.deadline_seconds)
        slot = stamp(args.slot_utc)
        if args.command == "run":
            if args.slot_utc > current:
                raise ValueError
            output, code = record(args, slot, deadline)
        elif current < deadline:
            output, code = {"slot_utc": slot, "reason": "pending"}, 3
        else:
            reason = evaluate(args.database, slot, stamp(deadline))
            deliver(args.database, args.inbox)
            output, code = (
                {"slot_utc": slot, "reason": reason},
                int(reason != "healthy"),
            )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        OverflowError,
        RecursionError,
        sqlite3.Error,
        argparse.ArgumentTypeError,
    ):
        print(
            "Operational supervision failed; check configuration, state and inbox.",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(output, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
