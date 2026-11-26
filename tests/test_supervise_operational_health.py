import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import supervise_operational_health as supervisor


@pytest.fixture
def operator(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    origin = datetime.now(UTC) - timedelta(hours=1)
    return tmp_path / "watch.sqlite", inbox, origin


def slot_args(database, slot, seconds=6):
    return [
        "--database",
        str(database),
        "--slot-utc",
        supervisor.stamp(slot),
        "--deadline-seconds",
        str(seconds),
    ]


def watched(database, inbox, slot, capsys, seconds=6):
    code = supervisor.main(
        ["watch", *slot_args(database, slot, seconds), "--inbox", str(inbox)]
    )
    result = capsys.readouterr()
    assert not result.err or code == 2
    return code, json.loads(result.out) if result.out else None


def prepared_result(database, slot, *, reason="healthy", late=False, web=200):
    deadline = slot + timedelta(seconds=6)
    with closing(supervisor.monitor_db(database)) as connection, connection:
        connection.execute(
            "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?)",
            (
                supervisor.stamp(slot),
                supervisor.stamp(deadline),
                supervisor.stamp(deadline + timedelta(microseconds=int(late))),
                reason,
                200,
                web,
            ),
        )


def incident_messages(inbox):
    messages = [json.loads(path.read_bytes()) for path in inbox.glob("*.json")]
    return sorted(messages, key=lambda event: event["slot_utc"])


def test_incident_lifecycle_replay_and_next_incident(operator, capsys):
    database, inbox, start = operator
    windows = [start + timedelta(seconds=10 * interval) for interval in range(5)]
    first, changed, repeat, recovered, next_incident = windows
    for slot in (changed, repeat):
        prepared_result(database, slot, reason="web_http_error", web=502)
    prepared_result(database, recovered)

    for slot, reason in zip(
        windows,
        (
            "missing_result",
            "web_http_error",
            "web_http_error",
            "healthy",
            "missing_result",
        ),
        strict=True,
    ):
        assert watched(database, inbox, slot, capsys)[0] == int(reason != "healthy")
        assert watched(database, inbox, slot, capsys)[1]["reason"] == reason
    assert watched(database, inbox, first, capsys)[1]["reason"] == "missing_result"
    messages = incident_messages(inbox)
    assert [entry["event"] for entry in messages] == [
        "opened",
        "updated",
        "recovered",
        "opened",
    ]
    assert messages[1]["api_http"] == 200 and messages[1]["web_http"] == 502
    assert len({entry["event_id"] for entry in messages}) == 4
    assert len({entry["incident_id"] for entry in messages[:3]}) == 1
    assert messages[0]["incident_id"] != messages[-1]["incident_id"]
    target = inbox / (messages[2]["event_id"] + ".json")
    assert supervisor.main(["receive", "--event", str(target)]) == 0
    received = json.loads(capsys.readouterr().out)
    assert received["event_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert received["received_at_utc"] >= messages[2]["observed_at_utc"]
    assert received["incident_id"] == messages[0]["incident_id"]


def test_failed_inbox_recovers_the_same_event(operator, capsys):
    database, inbox, slot = operator
    unavailable = inbox / "offline"
    assert watched(database, unavailable, slot, capsys) == (2, None)
    with closing(supervisor.monitor_db(database)) as connection:
        (pending,) = connection.execute("SELECT id, body FROM events WHERE delivered=0")
    unavailable.mkdir()
    assert watched(database, unavailable, slot, capsys)[0] == 1
    assert watched(database, unavailable, slot, capsys)[0] == 1
    (path,) = unavailable.glob("*.json")
    assert path.name == pending["id"] + ".json"
    assert path.read_bytes() == pending["body"].encode()


def test_pending_late_and_out_of_order(operator, capsys):
    database, inbox, slot = operator
    future = datetime.now(UTC) + timedelta(seconds=60)
    assert watched(database, inbox, future, capsys)[1]["reason"] == "pending"
    assert not database.exists() and not list(inbox.iterdir())
    prepared_result(database, slot, late=True)
    assert watched(database, inbox, slot, capsys)[1]["reason"] == "missing_result"
    assert watched(database, inbox, slot, capsys, seconds=7) == (2, None)
    assert watched(database, inbox, slot - timedelta(seconds=1), capsys) == (2, None)
    assert len(list(inbox.glob("*.json"))) == 1


def test_simultaneous_observers_record_a_single_event(operator):
    database, inbox, slot = operator
    deadline = supervisor.stamp(slot + timedelta(seconds=6))
    slot = supervisor.stamp(slot)
    with closing(supervisor.monitor_db(database)):
        pass

    def watch():
        result = supervisor.evaluate(database, slot, deadline)
        supervisor.deliver(database, inbox)
        return result

    with ThreadPoolExecutor(max_workers=4) as workers:
        assert list(workers.map(lambda _: watch(), range(8))) == ["missing_result"] * 8
    assert len(list(inbox.iterdir())) == 1
    assert len(incident_messages(inbox)) == 1


@pytest.mark.parametrize("same_bytes", [True, False])
def test_windows_replace_contention_checks_published_bytes(
    operator, capsys, monkeypatch, same_bytes
):
    database, inbox, slot = operator

    def competing_writer(source, target):
        target.write_bytes(source.read_bytes() if same_bytes else b"conflict")
        raise PermissionError("concurrent reader")

    monkeypatch.setattr(Path, "replace", competing_writer)
    code, _ = watched(database, inbox, slot, capsys)
    assert code == (1 if same_bytes else 2)
    (target,) = inbox.iterdir()
    with closing(supervisor.monitor_db(database)) as connection:
        (event,) = connection.execute("SELECT delivered, body FROM events")
    assert event["delivered"] == int(same_bytes)
    assert target.read_bytes() == (
        event["body"].encode() if same_bytes else b"conflict"
    )


def test_runner_retry_preserves_the_first_result(operator, capsys, monkeypatch):
    database, _inbox, _origin = operator
    slot = datetime.now(UTC) - timedelta(seconds=1)
    calls = []

    def measure(options, slot, deadline):
        calls.append((options, slot, deadline))
        return "healthy", 200, 200

    monkeypatch.setattr(supervisor, "measure", measure)
    args = ["run", *slot_args(database, slot), "--", "--timeout-seconds", "2"]
    assert supervisor.main(args) == supervisor.main(args) == 0
    assert len(calls) == 1 and calls[0][0] == ["--timeout-seconds", "2"]
    assert (
        supervisor.main(
            ["run", *slot_args(database, slot, 7), "--", "--timeout-seconds", "2"]
        )
        == 2
    )
    assert len(calls) == 1
    assert "timeout-seconds" not in capsys.readouterr().err
