"""Run from the infrastructure repository: python -m tools.mongodb_backup."""

import argparse
import json
import sys
from pathlib import Path


def parser():
    value = argparse.ArgumentParser(
        description="CineVault encrypted MongoDB backup", allow_abbrev=False
    )
    value.add_argument("--age", type=Path, required=False)
    commands = value.add_subparsers(dest="command", required=True)
    for name in ("backup", "restore", "verify", "rotate"):
        command = commands.add_parser(name, allow_abbrev=False)
        command.add_argument("--work-dir", type=Path, required=True)
        command.add_argument(
            "--timeout",
            type=int,
            default=300,
            help="Cooperative copy/stream budget after credential/tool preflight; blocking OS I/O is not preempted",
        )
        if name in ("restore", "verify", "rotate"):
            command.add_argument("--input", type=Path, required=True)
            command.add_argument("--identity-file", type=Path, required=True)
        if name in ("backup", "rotate"):
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--recipients-file", type=Path, required=True)
        if name == "backup":
            command.add_argument("--database", required=True)
            command.add_argument("--source-config", type=Path, required=True)
            command.add_argument("--freeze-config", type=Path, required=True)
            command.add_argument("--mongodump", type=Path, required=True)
            command.add_argument("--freeze-seconds", type=int, default=30)
            command.add_argument(
                "--acknowledge-coordinator-writers-only",
                action="store_true",
                required=True,
            )
        if name == "restore":
            command.add_argument("--expected-sha256", required=True)
            command.add_argument("--database", required=True)
            command.add_argument("--target-config", type=Path, required=True)
            command.add_argument("--mongorestore", type=Path, required=True)
            command.add_argument(
                "--acknowledge-isolated-target", action="store_true", required=True
            )
    directory = commands.add_parser("init-directory", allow_abbrev=False)
    directory.add_argument("--directory", type=Path, required=True)
    retention = commands.add_parser("retention-plan", allow_abbrev=False)
    retention.add_argument("--directory", type=Path, required=True)
    retention.add_argument("--keep-days", type=int, default=30)
    retention.add_argument("--keep-minimum", type=int, default=7)
    retention.add_argument("--maximum-age-hours", type=int, default=24)
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        from .operations import execute

        receipt = execute(args)
    except KeyboardInterrupt:
        print(
            "Operation interrupted; no success receipt. Keep any target isolated and verify its finalization before reuse.",
            file=sys.stderr,
        )
        return 130
    except ValueError as error:
        from .security import BackupError

        code = (
            str(error)
            if isinstance(error, BackupError)
            else "invalid_configuration_or_envelope"
        )
        print("Operation refused: " + code, file=sys.stderr)
        return 1
    except Exception:  # noqa: BLE001 - upstream errors can expose credentials/data.
        # Drivers and tools can include credentials, data or private paths in errors.
        print(
            "Operation refused or failed; no success receipt. Check prerequisites and isolated target.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
