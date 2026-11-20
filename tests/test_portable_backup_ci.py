"""Real-child regressions for the qualification runner's output and time bounds."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_portable_backup.py"
SPEC = importlib.util.spec_from_file_location("portable_backup_ci", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class LogBoundTests(unittest.TestCase):
    def test_overflow_fails_and_never_writes_more_than_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "child.txt"
            with (
                patch.object(runner, "MAX_LOG_BYTES", 1024),
                self.assertRaisesRegex(RuntimeError, "byte limit"),
            ):
                runner.run_logged(
                    [
                        sys.executable,
                        "-c",
                        "import sys;sys.stdout.buffer.write(b'x'*100000)",
                    ],
                    path,
                    timeout=5,
                )
            self.assertLessEqual(path.stat().st_size, 1024)
            self.assertIn(b"log byte limit exceeded", path.read_bytes())

    def test_success_preserves_actual_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "child.txt"
            runner.run_logged(
                [
                    sys.executable,
                    "-c",
                    "import sys;sys.stdout.buffer.write(b'actual-output\\n')",
                ],
                path,
                timeout=5,
            )
            self.assertEqual(path.read_bytes(), b"actual-output\n")

    def test_nonzero_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "child.txt"
            with self.assertRaisesRegex(RuntimeError, "subprocess failed"):
                runner.run_logged(
                    [sys.executable, "-c", "raise SystemExit(7)"], path, timeout=5
                )

    def test_timeout_terminates_real_child(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "child.txt"
            with self.assertRaises(subprocess.TimeoutExpired):
                runner.run_logged(
                    [sys.executable, "-c", "import time;time.sleep(30)"],
                    path,
                    timeout=0.2,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
