"""Qualify portable backup contracts with real, hash-pinned public executables.

This does not run MongoDB or qualify a native restore. Workspaces/tools stay
outside artifacts; only receipts, test logs, license text and metadata are saved.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
import unittest
import uuid
import venv
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "tools/mongodb_backup/requirements.lock"
UPSTREAM = ROOT / "tools/mongodb_backup/upstream.lock.json"
MAX_LOG_BYTES = 8 * 1024 * 1024
LOG_LIMIT_MARKER = b"\n[qualification log byte limit exceeded]\n"
EXPECTED_CONTRACT_TESTS = 47
WINDOWS_ONLY_SKIP = (
    (
        "test_mongodb_backup.BoundaryTests."
        "test_secret_location_refuses_windows_aliases_of_backup_directory"
    ),
    "Windows filesystem aliases only",
)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def run_logged(command, path, *, timeout, env=None):
    """Stream at most 8 MiB per child; terminate and fail on overflow/timeout."""
    expired = threading.Event()
    overflow = False
    with path.open("wb") as log:
        process = subprocess.Popen(
            [str(x) for x in command],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        def stop_child():
            if process.poll() is None:
                try:
                    process.kill()
                except OSError:
                    pass  # A concurrent normal exit is harmless; wait still reaps it.

        def expire():
            expired.set()
            stop_child()

        timer = threading.Timer(timeout, expire)
        timer.daemon = True
        timer.start()
        written = 0
        try:
            while chunk := process.stdout.read(65536):
                available = MAX_LOG_BYTES - len(LOG_LIMIT_MARKER) - written
                if len(chunk) > available:
                    log.write(chunk[: max(0, available)])
                    log.write(LOG_LIMIT_MARKER)
                    overflow = True
                    stop_child()
                    break
                log.write(chunk)
                written += len(chunk)
            returncode = process.wait(timeout=10)
        finally:
            timer.cancel()
            stop_child()
            process.stdout.close()
            process.wait(timeout=10)
    if expired.is_set():
        raise subprocess.TimeoutExpired(command, timeout)
    if overflow:
        raise RuntimeError("Qualification log byte limit exceeded")
    if returncode:
        raise RuntimeError("Qualification subprocess failed; inspect its named log")


def flat_tests(suite):
    for case in suite:
        if isinstance(case, unittest.TestSuite):
            yield from flat_tests(case)
        else:
            yield case


def test_contract(result, test_ids):
    """Prevent an absent age binary, unexpected skip or shrinking suite going green."""
    age_ids = [
        name
        for name in test_ids
        if name.startswith("test_mongodb_backup.AgeIntegration.")
    ]
    skipped = [(case.id(), reason) for case, reason in result.skipped]
    expected_skips = [] if os.name == "nt" else [WINDOWS_ONLY_SKIP]
    passed = (
        len(test_ids) == result.testsRun == EXPECTED_CONTRACT_TESTS
        and len(set(test_ids)) == len(test_ids)
        and len(age_ids) == 7
        and not any(name in {item[0] for item in skipped} for name in age_ids)
        and skipped == expected_skips
        and result.wasSuccessful()
    )
    return {
        "passed": passed,
        "expected_test_count": EXPECTED_CONTRACT_TESTS,
        "tests_run": result.testsRun,
        "tests_passed": result.testsRun
        - len(result.failures)
        - len(result.errors)
        - len(skipped),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": skipped,
        "real_age_test_count": len(age_ids),
        "real_age_test_ids": age_ids,
        "expected_skip_policy": "none"
        if os.name == "nt"
        else "one exact Windows-alias-only test",
    }


def binary_metadata(tools):
    labels = (
        {"age-windows", "mongo-windows"}
        if os.name == "nt"
        else {"age-linux", "mongo-ubuntu2404"}
    )
    entries = [
        entry
        for entry in json.loads(UPSTREAM.read_text())["archives"]
        if entry["label"] in labels
    ]
    assert len(entries) == 2
    binaries = []
    for spec in entries:
        directory = tools / ("age" if spec["label"].startswith("age-") else "mongodb")
        for name, pin in spec["binaries"].items():
            path = directory / name
            assert (
                path.is_file()
                and not path.is_symlink()
                and path.stat().st_size < 128 * 1024 * 1024
            )
            assert digest(path) == pin["sha256"]
            output = subprocess.run(
                [str(path), "--version"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            assert output.returncode == 0
            version = (output.stdout + output.stderr).strip()
            if name.startswith("age"):
                assert version == "v1.3.2"
            else:
                assert re.search(
                    r"^"
                    + re.escape(name.removesuffix(".exe"))
                    + r" version: 100\.20\.0$",
                    version,
                    re.MULTILINE,
                )
            binaries.append(
                {
                    "name": name,
                    "sha256": pin["sha256"],
                    "bytes": path.stat().st_size,
                    "version_output": version,
                }
            )
    assert len(binaries) == 4
    return binaries


def collect_notices(tools, report):
    """Copy bounded license text only; hash large upstream analysis/SBOM files."""
    records = []
    total = 0
    for path in sorted(tools.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        name = path.name.lower()
        if not (
            name.startswith(("license", "notice", "third-party"))
            or name.endswith((".cdx.json", ".sast.json", ".sarif.json"))
        ):
            continue
        relative = path.relative_to(tools)
        record = {
            "path": relative.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
            "copied": False,
        }
        if name.startswith(("license", "notice", "third-party")):
            assert path.stat().st_size <= 2 * 1024 * 1024
            total += path.stat().st_size
            assert total <= 8 * 1024 * 1024
            target = report / "notices/upstream" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
            record["copied"] = True
        records.append(record)
    assert {
        record["path"].split("/", 1)[0] for record in records if record["copied"]
    } == {"age", "mongodb"}, "Both installed releases must preserve license notices"
    python = []
    for name in ("pymongo", "dnspython"):
        dist = importlib.metadata.distribution(name)
        notices = []
        for member in dist.files or []:
            if (
                not Path(str(member))
                .name.lower()
                .startswith(("license", "notice", "copying"))
            ):
                continue
            path = Path(dist.locate_file(member))
            assert (
                path.is_file()
                and not path.is_symlink()
                and path.stat().st_size <= 2 * 1024 * 1024
            )
            target = report / "notices/python" / name / Path(str(member)).name
            target.parent.mkdir(parents=True, exist_ok=True)
            assert not target.exists(), "License basename collision"
            target.write_bytes(path.read_bytes())
            notices.append(
                {
                    "name": target.name,
                    "sha256": digest(target),
                    "bytes": target.stat().st_size,
                }
            )
        assert notices, "Installed distribution license metadata is missing"
        python.append(
            {
                "name": dist.metadata["Name"],
                "version": dist.version,
                "license_expression": dist.metadata.get("License-Expression"),
                "license_field": dist.metadata.get("License"),
                "notices": notices,
            }
        )
    write_json(
        report / "notices.json",
        {
            "upstream": records,
            "python": python,
            "large_analysis_files_hashed_not_uploaded": True,
        },
    )


def worker(args):
    import dns
    import pymongo

    sys.path.insert(0, str(ROOT))
    report = args.report_dir.resolve()
    report.mkdir(parents=True, exist_ok=True)
    receipt = {
        "passed": False,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "scope": "Portable offline contracts with actual age; no native MongoDB restore",
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "pymongo": pymongo.version,
        "pymongo_c_extension": pymongo.has_c(),
        "dnspython": dns.__version__,
        "requirements_lock_sha256": digest(LOCK),
        "upstream_lock_sha256": digest(UPSTREAM),
    }
    stage = "source_and_binary_preflight"
    try:
        assert (os.name == "nt" and sys.version_info[:2] == (3, 13)) or (
            sys.platform == "linux" and sys.version_info[:2] == (3, 12)
        )
        assert (
            pymongo.version == "4.20.0"
            and pymongo.has_c()
            and dns.__version__ == "2.9.2"
        )
        source_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        ).stdout.strip()
        assert re.fullmatch("[0-9a-f]{40}", source_sha)
        if os.environ.get("GITHUB_SHA"):
            assert source_sha == os.environ["GITHUB_SHA"]
        receipt["source_git_sha"] = source_sha
        receipt["source_tree_dirty"] = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            ).stdout.strip()
        )
        source_files = [
            ROOT / "tests/test_mongodb_backup.py",
            ROOT / "tests/test_portable_backup_ci.py",
            Path(__file__).resolve(),
            ROOT / ".github/workflows/mongodb-backup.yml",
            ROOT / "docs/operations/MONGODB_BACKUP.md",
            *sorted((ROOT / "tools/mongodb_backup").glob("*")),
        ]
        receipt["source_files_sha256"] = {
            path.relative_to(ROOT).as_posix(): digest(path)
            for path in source_files
            if path.is_file() and path.suffix != ".pyc"
        }
        receipt["github_run_id"] = os.environ.get("GITHUB_RUN_ID")
        receipt["binaries"] = binary_metadata(args.tools_directory.resolve())
        extension = ".exe" if os.name == "nt" else ""
        os.environ["AGE_TEST_BINARY"] = str(
            args.tools_directory.resolve() / "age" / ("age" + extension)
        )
        stage = "license_inventory"
        collect_notices(args.tools_directory.resolve(), report)
        stage = "all_contract_tests_real_age_enabled"
        suite = unittest.defaultTestLoader.discover(
            str(ROOT / "tests"), pattern="test_mongodb_backup.py"
        )
        test_ids = [case.id() for case in flat_tests(suite)]
        with (report / "unittest.txt").open("w", encoding="utf-8") as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        receipt["tests"] = test_contract(result, test_ids)
        receipt["passed"] = receipt["tests"]["passed"]
    except Exception as error:  # noqa: BLE001 - preserve a fixed failure receipt, no upstream input text.
        receipt["error_type"] = type(error).__name__
    finally:
        receipt["failed_stage"] = None if receipt["passed"] else stage
        receipt["finished_at_utc"] = datetime.now(UTC).isoformat()
        write_json(report / "receipt.json", receipt)
        print(
            json.dumps(
                {
                    "passed": receipt["passed"],
                    "tests": receipt.get("tests"),
                    "failed_stage": receipt["failed_stage"],
                }
            )
        )
    return 0 if receipt["passed"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--tools-directory", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        assert args.tools_directory is not None
        return worker(args)
    report = args.report_dir.resolve()
    assert report.is_relative_to(ROOT.resolve()) and report != ROOT.resolve()
    report.mkdir(parents=True, exist_ok=False)
    receipt = {
        "passed": False,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "scope": "Public pinned installer and offline crypto contracts; no server/deployment",
        "requirements_lock_sha256": digest(LOCK),
        "upstream_lock_sha256": digest(UPSTREAM),
    }
    stage = "private_environment"
    started = time.monotonic()
    try:
        runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
        workspace = runner_temp / ("cv-backup-ci-" + uuid.uuid4().hex)
        assert workspace.parent == runner_temp and not workspace.exists()
        workspace.mkdir(mode=0o700)
        venv.EnvBuilder(with_pip=True).create(workspace / "environment")
        python = (
            workspace
            / "environment"
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        stage = "hash_locked_binary_dependencies"
        run_logged(
            [
                python,
                "-m",
                "pip",
                "--isolated",
                "install",
                "--index-url",
                "https://pypi.org/simple",
                "--only-binary=:all:",
                "--require-hashes",
                "-r",
                LOCK,
            ],
            report / "pip-install.txt",
            timeout=180,
        )
        run_logged([python, "-m", "pip", "check"], report / "pip-check.txt", timeout=30)
        private = workspace / "private"
        for directory in (private, private / "work", private / "tmp"):
            run_logged(
                [
                    python,
                    "-B",
                    "-W",
                    "error",
                    "-m",
                    "tools.mongodb_backup",
                    "init-directory",
                    "--directory",
                    directory,
                ],
                report / ("init-" + directory.name + ".txt"),
                timeout=30,
            )
        env = {
            **os.environ,
            "TEMP": str(private / "tmp"),
            "TMP": str(private / "tmp"),
            "TMPDIR": str(private / "tmp"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        stage = "public_pinned_release_installer"
        run_logged(
            [
                python,
                "-B",
                "-W",
                "error",
                "-m",
                "tools.mongodb_backup.install_tools",
                "--destination",
                private / "tools",
                "--work-dir",
                private / "work",
            ],
            report / "public-installer.txt",
            timeout=360,
            env=env,
        )
        stage = "strict_worker"
        run_logged(
            [
                python,
                "-B",
                "-W",
                "error",
                Path(__file__).resolve(),
                "--worker",
                "--tools-directory",
                private / "tools",
                "--report-dir",
                report,
            ],
            report / "worker.txt",
            timeout=300,
            env=env,
        )
        receipt["passed"] = (
            json.loads((report / "receipt.json").read_bytes())["passed"] is True
        )
        receipt["ephemeral_workspace_retained_until_runner_teardown"] = True
    except Exception as error:  # noqa: BLE001 - fixed receipt plus separate public diagnostic logs.
        receipt["error_type"] = type(error).__name__
    finally:
        receipt["failed_stage"] = None if receipt["passed"] else stage
        receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
        receipt["finished_at_utc"] = datetime.now(UTC).isoformat()
        write_json(report / "bootstrap.json", receipt)
        print(json.dumps(receipt))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
