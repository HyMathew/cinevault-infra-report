"""Operator orchestration. Transport, service scheduling and volume creation are external."""

import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .security import (
    connection_config,
    database_name,
    initialize_directory,
    key_lines,
    private_path,
    read_private,
    require,
    unlinked_path,
    write_private,
)
from .streams import (
    AGE_VERSION,
    TOOLS_VERSION,
    authenticate,
    ciphertext_snapshot,
    encrypt_dump,
    executable,
    restore_stream,
    rotate_stream,
)


@contextmanager
def workspace(directory):
    directory = private_path(directory, directory=True)
    with tempfile.TemporaryDirectory(prefix="cvmb-", dir=directory) as path:
        yield private_path(Path(path), directory=True)


@contextmanager
def encrypted_output(path):
    path = unlinked_path(path)
    private_path(path.parent, directory=True)
    require(
        path.name.endswith(".cvmb.age") and not path.exists(),
        "new_cvmb_age_output_required",
    )
    pending = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".pending")
    try:
        with os.fdopen(
            os.open(
                pending,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
                0o600,
            ),
            "wb",
        ) as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        # link is atomic and refuses any existing destination, on POSIX and NTFS.
        # rename/replace would overwrite on POSIX; never use either here.
        os.link(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def digest_file(path):
    digest = hashlib.sha256()
    with unlinked_path(path).open("rb") as stream:
        while data := stream.read(65536):
            digest.update(data)
    return digest.hexdigest()


def private_config(path, work, filename):
    data = read_private(path)
    config, endpoint, principal = connection_config(data)
    snapshot = write_private(work / filename, json.dumps(config).encode())
    return config, endpoint, principal, snapshot


def external_identity(identity, archive):
    identity = unlinked_path(identity)
    directory = unlinked_path(archive).parent
    require(
        not identity.is_relative_to(directory),
        "identity_must_be_outside_backup_directory",
    )
    # String anchors can differ for the same directory (Windows verbatim/DOS
    # aliases). Compare existing ancestor identities after refusing all links;
    # no resolving or rewriting of a legitimate external input is necessary.
    if directory.exists():
        require(
            not any(
                parent.exists() and parent.samefile(directory)
                for parent in identity.parents
            ),
            "identity_must_be_outside_backup_directory",
        )


def backup(args, age, work):
    from .mongo import connect, frozen, instance_digest, version

    database_name(args.database)
    external_identity(args.source_config, args.output)
    external_identity(args.freeze_config, args.output)
    source_config, source_endpoint, source_principal, source_file = private_config(
        args.source_config, work, "source.json"
    )
    freeze_config, freeze_endpoint, freeze_principal, _ = private_config(
        args.freeze_config, work, "freeze.json"
    )
    require(source_endpoint == freeze_endpoint, "source_freezer_endpoints_differ")
    require(
        source_principal != freeze_principal, "source_freezer_principals_must_differ"
    )
    dump = executable(args.mongodump, TOOLS_VERSION, mongo=True)
    recipients = write_private(
        work / "recipients.txt",
        key_lines(read_private(args.recipients_file), identity=False),
    )
    started = time.monotonic()
    with connect(source_config) as source, connect(freeze_config) as freezer:
        server_version = version(source)
        with encrypted_output(args.output) as output:  # noqa: SIM117 - show file publication outside transaction lifetime.
            with frozen(source, freezer, args.database, args.freeze_seconds) as freeze:
                manifest = {
                    "format": 1,
                    "source_database": args.database,
                    "created_utc": datetime.now(UTC).isoformat(),
                    "mongo_version": server_version,
                    "tools_version": TOOLS_VERSION,
                    "source_instance_sha256": instance_digest(freeze["instance"]),
                    "inventory": freeze["inventory"],
                }
                archive_size, _ = encrypt_dump(
                    age,
                    recipients,
                    [
                        dump,
                        "--config",
                        source_file,
                        "--db",
                        args.database,
                        "--archive",
                        "--gzip",
                        "--readPreference=primary",
                        "--numParallelCollections=1",
                    ],
                    manifest,
                    output,
                    min(freeze["deadline"], started + args.timeout),
                )
    return {
        "status": "ENCRYPTED_BACKUP_CREATED",
        "ciphertext_sha256": digest_file(args.output),
        "archive_bytes": archive_size,
        "freeze_seconds": freeze["freeze_seconds"],
        "duration_seconds": round(time.monotonic() - started, 3),
        "coordinator_aborted_unchanged": True,
        "inventory_unchanged_during_dump": True,
    }


def read_operation(args, age, work):
    if args.command == "restore":
        require(
            re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256),
            "trusted_sha256_required",
        )
    identity = write_private(
        work / "identity.txt",
        key_lines(read_private(args.identity_file), identity=True),
    )
    external_identity(args.identity_file, args.input)
    deadline = time.monotonic() + args.timeout
    with ciphertext_snapshot(args.input, work, deadline) as (ciphertext, cipher_digest):
        if args.command == "restore":
            require(
                cipher_digest == args.expected_sha256,
                "ciphertext_trusted_digest_mismatch",
            )
        expected = authenticate(age, identity, ciphertext, deadline)
        if args.command == "restore":
            from .mongo import claim_target, connect, finish_target

            database_name(args.database)
            external_identity(args.target_config, args.input)
            restore = executable(args.mongorestore, TOOLS_VERSION, mongo=True)
            config, _, _, config_file = private_config(
                args.target_config, work, "target.json"
            )
            with connect(config) as target:
                operation = uuid.uuid4().hex
                database = claim_target(target, args.database, expected[0], operation)
                source = expected[0]["source_database"]
                restore_stream(
                    age,
                    identity,
                    ciphertext,
                    [
                        restore,
                        "--config",
                        config_file,
                        "--archive",
                        "--gzip",
                        "--nsInclude",
                        source + ".*",
                        "--nsFrom",
                        source + ".*",
                        "--nsTo",
                        args.database + ".*",
                        "--stopOnError",
                        "--numParallelCollections=1",
                    ],
                    expected,
                    deadline,
                )
                finish_target(database, expected[0]["inventory"], operation, deadline)
        elif args.command == "rotate":
            external_identity(args.identity_file, args.output)
            recipients = write_private(
                work / "recipients.txt",
                key_lines(read_private(args.recipients_file), identity=False),
            )
            with encrypted_output(args.output) as output:
                rotate_stream(
                    age, identity, ciphertext, recipients, expected, output, deadline
                )
        result = {
            "status": {
                "verify": "CIPHERTEXT_AUTHENTICATED",
                "rotate": "ROTATED_COPY_CREATED",
                "restore": "ISOLATED_RESTORE_VERIFIED",
            }[args.command],
            "ciphertext_sha256": cipher_digest,
            "archive_bytes": expected[1],
        }
        if args.command == "rotate":
            result["rotated_ciphertext_sha256"] = digest_file(args.output)
        return result


def retention_plan(args):
    require(
        7 <= args.keep_days <= 3650
        and 2 <= args.keep_minimum <= 10000
        and 1 <= args.maximum_age_hours <= 168,
        "invalid_retention_policy",
    )
    directory = private_path(args.directory, directory=True)
    files = [path for path in directory.glob("*.cvmb.age") if path.is_file()]
    for path in files:
        unlinked_path(path)
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    now = time.time()
    expired = [
        path.name
        for path in files[args.keep_minimum :]
        if now - path.stat().st_mtime >= args.keep_days * 86400
    ]
    # Deliberately a plan: no automatic deletion based solely on timestamps.
    return {
        "status": "RETENTION_PLAN_ONLY",
        "delete_candidates": expired,
        "retained_minimum": args.keep_minimum,
        "keep_days": args.keep_days,
        "freshness_due": not files
        or now - files[0].stat().st_mtime > args.maximum_age_hours * 3600,
        "freshness_is_mtime_only_not_restore_evidence": True,
    }


def execute(args):
    if args.command == "init-directory":
        initialize_directory(args.directory)
        return {"status": "PRIVATE_DIRECTORY_CREATED"}
    if args.command == "retention-plan":
        return retention_plan(args)
    require(1 <= args.timeout <= 3600, "timeout_bound_1_to_3600_seconds")
    age = executable(args.age, AGE_VERSION)
    with workspace(args.work_dir) as work:
        return (
            backup(args, age, work)
            if args.command == "backup"
            else read_operation(args, age, work)
        )
