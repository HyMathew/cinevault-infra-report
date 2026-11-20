"""Bounded framing and subprocess streams; cryptography belongs solely to age."""

import hashlib
import json
import os
import stat
import struct
import subprocess
import threading
import time
from contextlib import contextmanager, suppress
from datetime import datetime
from pathlib import Path

from .security import database_name, require, strict_json, unlinked_path

MAGIC = b"CVMB1\n"
MAX_HEADER = 1024 * 1024
CHUNK = 65536
TOOLS_VERSION = "100.20.0"
AGE_VERSION = "v1.3.2"


def deadline_check(deadline):
    require(time.monotonic() < deadline, "operation_deadline_exceeded")


def read_exact(stream, count):
    result = bytearray()
    while len(result) < count:
        chunk = stream.read(count - len(result))
        require(bool(chunk), "truncated_envelope")
        result.extend(chunk)
    return bytes(result)


def validate_manifest(value):
    require(
        isinstance(value, dict)
        and set(value)
        == {
            "format",
            "source_database",
            "created_utc",
            "mongo_version",
            "tools_version",
            "source_instance_sha256",
            "inventory",
        },
        "invalid_manifest",
    )
    require(
        type(value["format"]) is int
        and value["format"] == 1
        and value["tools_version"] == TOOLS_VERSION,
        "unsupported_manifest_version",
    )
    database_name(value["source_database"])
    require(isinstance(value["created_utc"], str), "invalid_capture_time")
    captured = datetime.fromisoformat(value["created_utc"])
    require(
        captured.utcoffset() is not None and captured.utcoffset().total_seconds() == 0,
        "utc_capture_time_required",
    )
    require(
        isinstance(value["mongo_version"], str) and value["mongo_version"] == "8.0.34",
        "unsupported_mongo_version",
    )
    inventory = value["inventory"]
    require(
        isinstance(inventory, dict) and set(inventory) == {"revision", "collections"},
        "invalid_inventory",
    )
    require(
        type(inventory["revision"]) is int and 0 <= inventory["revision"] < 2**63 - 1,
        "invalid_coordinator_revision",
    )
    require(
        isinstance(inventory["collections"], dict)
        and "coordination" in inventory["collections"]
        and 1 <= len(inventory["collections"]) <= 128,
        "invalid_collection_inventory",
    )
    import re

    require(
        isinstance(value["source_instance_sha256"], str)
        and re.fullmatch(r"[0-9a-f]{64}", value["source_instance_sha256"]),
        "invalid_source_instance_digest",
    )

    for name, collection in inventory["collections"].items():
        require(
            re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name) is not None,
            "invalid_collection_name",
        )
        require(
            set(collection)
            == {
                "count",
                "documents_sha256",
                "options_sha256",
                "indexes_sha256",
                "index_count",
            },
            "invalid_collection_inventory",
        )
        require(
            type(collection["count"]) is int
            and collection["count"] >= 0
            and type(collection["index_count"]) is int
            and collection["index_count"] >= 1,
            "invalid_inventory_count",
        )
        for key in ("documents_sha256", "options_sha256", "indexes_sha256"):
            require(
                isinstance(collection[key], str)
                and re.fullmatch(r"[0-9a-f]{64}", collection[key]),
                "invalid_inventory_digest",
            )
    return value


def header(value):
    data = json.dumps(
        validate_manifest(value), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    require(len(data) <= MAX_HEADER, "manifest_too_large")
    return MAGIC + struct.pack(">I", len(data)) + data


def read_header(stream):
    require(read_exact(stream, len(MAGIC)) == MAGIC, "invalid_envelope_magic")
    length = struct.unpack(">I", read_exact(stream, 4))[0]
    require(0 < length <= MAX_HEADER, "manifest_length_invalid")
    return validate_manifest(strict_json(read_exact(stream, length)))


class Child:
    """Every blocking pipe is bounded by a watchdog and every child is reaped."""

    def __init__(self, args, *, deadline, stdin=None, stdout=None):
        deadline_check(deadline)
        self.deadline = deadline
        self.process = subprocess.Popen(
            [str(arg) for arg in args],
            stdin=stdin,
            stdout=stdout,
            stderr=subprocess.DEVNULL,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.timer = threading.Timer(max(0.01, deadline - time.monotonic()), self._kill)
        self.timer.daemon = True
        self.timer.start()

    def _kill(self):
        if self.process.poll() is None:
            with suppress(ProcessLookupError):
                self.process.kill()

    def __enter__(self):
        return self

    def finish(self):
        result = self.process.wait(timeout=max(0.01, self.deadline - time.monotonic()))
        deadline_check(self.deadline)
        require(result == 0, "external_tool_failed")

    def __exit__(self, *_):
        self.timer.cancel()
        self._kill()
        self.process.wait()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None:
                # Buffered writers can flush into an already failed peer during
                # cleanup; preserve the original checked failure and reap both.
                with suppress(OSError):
                    stream.close()


def executable(path, version, *, mongo=False):
    require(
        path is not None and Path(path).is_absolute(), "absolute_tool_path_required"
    )
    path = unlinked_path(path)
    require(path.is_file(), "tool_missing")
    result = subprocess.run(
        [str(path), "--version"], capture_output=True, timeout=10, check=False
    )
    require(result.returncode == 0, "tool_version_failed")
    text = result.stdout.decode("utf-8", errors="strict").strip()
    require(
        (text.splitlines()[0].split()[-1] == version) if mongo else text == version,
        "tool_version_not_pinned",
    )
    return path


def pump(source, target, deadline):
    digest = hashlib.sha256()
    size = 0
    while True:
        deadline_check(deadline)
        data = source.read(CHUNK)
        if not data:
            break
        if target is not None:
            target.write(data)
        digest.update(data)
        size += len(data)
    return size, digest.hexdigest()


@contextmanager
def ciphertext_snapshot(path, workspace, deadline):
    path = unlinked_path(path)
    expected = path.stat()
    require(stat.S_ISREG(expected.st_mode), "ciphertext_file_required")
    # Private fresh copy is the sole input to both passes; input is never reopened.
    destination = workspace / "snapshot.age"
    with (
        os.fdopen(
            os.open(
                path,
                os.O_RDONLY
                | getattr(os, "O_BINARY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_NONBLOCK", 0),
            ),
            "rb",
        ) as source,
        os.fdopen(
            os.open(
                destination,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
                0o600,
            ),
            "w+b",
        ) as copy,
    ):
        opened = os.fstat(source.fileno())
        current = unlinked_path(path).stat()
        require(
            stat.S_ISREG(opened.st_mode)
            and (opened.st_dev, opened.st_ino)
            == (expected.st_dev, expected.st_ino)
            == (current.st_dev, current.st_ino),
            "ciphertext_file_changed",
        )
        _, digest = pump(source, copy, deadline)
        copy.flush()
        deadline_check(deadline)
        copy.seek(0)
        yield copy, digest


def authenticate(age, identity, ciphertext, deadline):
    ciphertext.seek(0)
    with Child(
        [age, "--decrypt", "--identity", identity],
        deadline=deadline,
        stdin=ciphertext,
        stdout=subprocess.PIPE,
    ) as child:
        value = read_header(child.process.stdout)
        size, digest = pump(child.process.stdout, None, deadline)
        child.finish()
    require(size > 0, "empty_mongo_archive")
    ciphertext.seek(0)
    return value, size, digest


def encrypt_dump(age, recipients, dump_args, manifest, output, deadline):
    with Child(
        [age, "--encrypt", "--recipients-file", recipients],
        deadline=deadline,
        stdin=subprocess.PIPE,
        stdout=output,
    ) as encryptor:
        encryptor.process.stdin.write(header(manifest))
        with Child(
            dump_args,
            deadline=deadline,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
        ) as dump:
            size, digest = pump(dump.process.stdout, encryptor.process.stdin, deadline)
            dump.finish()
        require(size > 0, "empty_mongo_archive")
        encryptor.process.stdin.close()
        encryptor.finish()
    return size, digest


def restore_stream(age, identity, ciphertext, restore_args, expected, deadline):
    ciphertext.seek(0)
    with Child(
        [age, "--decrypt", "--identity", identity],
        deadline=deadline,
        stdin=ciphertext,
        stdout=subprocess.PIPE,
    ) as decryptor:
        require(
            read_header(decryptor.process.stdout) == expected[0],
            "verified_snapshot_changed",
        )
        with Child(
            restore_args,
            deadline=deadline,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
        ) as restore:
            observed = pump(decryptor.process.stdout, restore.process.stdin, deadline)
            decryptor.finish()
            restore.process.stdin.close()
            restore.finish()
    require(observed == expected[1:], "verified_snapshot_changed")


def rotate_stream(age, identity, ciphertext, recipients, expected, output, deadline):
    ciphertext.seek(0)
    with Child(
        [age, "--decrypt", "--identity", identity],
        deadline=deadline,
        stdin=ciphertext,
        stdout=subprocess.PIPE,
    ) as decryptor:
        require(
            read_header(decryptor.process.stdout) == expected[0],
            "verified_snapshot_changed",
        )
        with Child(
            [age, "--encrypt", "--recipients-file", recipients],
            deadline=deadline,
            stdin=subprocess.PIPE,
            stdout=output,
        ) as encryptor:
            encryptor.process.stdin.write(header(expected[0]))
            observed = pump(decryptor.process.stdout, encryptor.process.stdin, deadline)
            decryptor.finish()
            encryptor.process.stdin.close()
            encryptor.finish()
    require(observed == expected[1:], "verified_snapshot_changed")
