"""Offline contract tests; these do not qualify a real MongoDB restoration."""

import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class InitialContract(unittest.TestCase):
    def test_public_cli_is_available_without_private_helpers(self):
        result = subprocess.run(
            [sys.executable, "-m", "tools.mongodb_backup", "--help"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b"backup", result.stdout)
        self.assertIn(b"restore", result.stdout)

    def test_streaming_module_rejects_untrusted_envelope_before_database_use(self):
        path = ROOT / "tools/mongodb_backup/streams.py"
        self.assertTrue(path.exists(), "Missing authenticated streaming implementation")
        from tools.mongodb_backup.streams import read_header

        for data in (b"", b"not an envelope", b"CVMB1\n\x00\x10\x00\x01"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                read_header(io.BytesIO(data))

    def test_private_files_and_namespace_module_exists(self):
        path = ROOT / "tools/mongodb_backup/security.py"
        self.assertTrue(path.exists(), "Missing private-file and namespace gates")
        from tools.mongodb_backup.security import database_name

        for value in ("admin", "config", "local", "../db", "x.*", "a/b", "", "a\x00b"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                database_name(value)


def manifest():
    return {
        "format": 1,
        "source_database": "cinevault",
        "created_utc": "2026-11-13T00:00:00+00:00",
        "mongo_version": "8.0.34",
        "tools_version": "100.20.0",
        "source_instance_sha256": "f" * 64,
        "inventory": {
            "revision": 6,
            "collections": {
                "coordination": {
                    "count": 1,
                    "documents_sha256": "0" * 64,
                    "options_sha256": "1" * 64,
                    "indexes_sha256": "2" * 64,
                    "index_count": 1,
                }
            },
        },
    }


class BoundaryTests(unittest.TestCase):
    def test_ciphertext_copy_deadline_stops_before_authentication_or_target(self):
        import hashlib
        from types import SimpleNamespace

        from tools.mongodb_backup.operations import read_operation, workspace

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / "work"
            work.mkdir(mode=0o700)
            backups = root / "backups"
            backups.mkdir()
            identity = root / "identity.txt"
            identity.write_bytes(b"AGE-SECRET-KEY-1" + b"A" * 58 + b"\n")
            identity.chmod(0o600)
            ciphertext = backups / "input.cvmb.age"
            ciphertext.write_bytes(b"abcdefghijkl")
            args = SimpleNamespace(
                command="restore",
                input=ciphertext,
                identity_file=identity,
                expected_sha256=hashlib.sha256(b"abcdefghijkl").hexdigest(),
                timeout=1,
            )
            with (
                patch("tools.mongodb_backup.security.windows_acl"),
                patch("tools.mongodb_backup.streams.CHUNK", 4),
                patch(
                    "tools.mongodb_backup.streams.time.monotonic", side_effect=[0, 0, 2]
                ),
                patch(
                    "tools.mongodb_backup.operations.authenticate",
                    side_effect=AssertionError("copy must stop before authentication"),
                ),
                patch(
                    "tools.mongodb_backup.mongo.connect",
                    side_effect=AssertionError("target must remain untouched"),
                ),
                workspace(work) as temporary_work,
            ):
                with self.assertRaisesRegex(ValueError, "operation_deadline_exceeded"):
                    read_operation(args, "unused-age", temporary_work)
                self.assertEqual(
                    (temporary_work / "snapshot.age").read_bytes(), b"abcd"
                )
            self.assertEqual(list(work.iterdir()), [])
            self.assertEqual(ciphertext.read_bytes(), b"abcdefghijkl")

    def test_ciphertext_snapshot_refuses_replacement_before_descriptor_open(self):
        from tools.mongodb_backup.streams import ciphertext_snapshot

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, replacement = root / "input.age", root / "replacement.age"
            path.write_bytes(b"original ciphertext")
            replacement.write_bytes(b"replacement ciphertext")
            original_open = os.open

            def replace_before_open(target, flags, *args, **kwargs):
                if Path(target) == path:
                    replacement.replace(path)
                return original_open(target, flags, *args, **kwargs)

            with (
                patch(
                    "tools.mongodb_backup.streams.os.open",
                    side_effect=replace_before_open,
                ),
                self.assertRaisesRegex(ValueError, "ciphertext_file_changed"),
                ciphertext_snapshot(path, root, time.monotonic() + 10),
            ):
                self.fail("Replaced input must not be yielded")

    def test_secret_location_normalizes_parent_segments_for_both_paths(self):
        from tools.mongodb_backup.operations import external_identity
        from tools.mongodb_backup.security import unlinked_path

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            keys, backups = root / "keys", root / "backups"
            keys.mkdir()
            backups.mkdir()
            inside, outside = backups / "synthetic.txt", keys / "synthetic.txt"
            inside.write_bytes(b"synthetic private input")
            outside.write_bytes(b"synthetic private input")
            archive = backups / "new.cvmb.age"
            for identity, destination in (
                (keys / ".." / "backups" / inside.name, archive),
                (inside, keys / ".." / "backups" / archive.name),
            ):
                with (
                    self.subTest(identity=identity, archive=destination),
                    self.assertRaisesRegex(ValueError, "outside_backup_directory"),
                ):
                    external_identity(identity, destination)
            legitimate = backups / ".." / "keys" / outside.name
            external_identity(legitimate, archive)
            self.assertEqual(unlinked_path(legitimate), outside)
            self.assertEqual(
                unlinked_path(legitimate).read_bytes(), outside.read_bytes()
            )

    def test_parent_normalization_never_hides_a_link_component(self):
        from tools.mongodb_backup.security import unlinked_path

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real, link = root / "real", root / "linked"
            real.mkdir()
            if os.name == "nt":
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link), str(real)],
                    capture_output=True,
                    check=True,
                )
            else:
                link.symlink_to(real, target_is_directory=True)
            try:
                with self.assertRaisesRegex(ValueError, "linked_path_refused"):
                    unlinked_path(link / ".." / "safe.txt")
            finally:
                link.rmdir() if os.name == "nt" else link.unlink()

    @unittest.skipUnless(os.name == "nt", "Windows filesystem aliases only")
    def test_secret_location_refuses_windows_aliases_of_backup_directory(self):
        import ctypes

        from tools.mongodb_backup.operations import external_identity
        from tools.mongodb_backup.security import read_private, unlinked_path

        get_short = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
        get_short.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        get_short.restype = ctypes.c_uint

        def short(path):
            count = get_short(str(path), None, 0)
            self.assertGreater(count, 0)
            buffer = ctypes.create_unicode_buffer(count)
            self.assertGreater(get_short(str(path), buffer, count), 0)
            return Path(buffer.value)

        def verbatim(path):
            return Path("\\\\?\\" + str(path))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backups, keys = (
                root / "backups with a long name",
                root / "private key files",
            )
            backups.mkdir()
            keys.mkdir()
            inside, outside = (
                backups / "synthetic-identity.txt",
                keys / "synthetic-identity.txt",
            )
            inside.write_bytes(b"synthetic private input")
            outside.write_bytes(b"synthetic private input")
            inside.chmod(0o600)
            outside.chmod(0o600)
            archive = backups / "new.cvmb.age"
            short_inside, short_backups = short(inside), short(backups)
            self.assertTrue(short_inside.samefile(inside))
            self.assertTrue(short_backups.samefile(backups))
            for identity, output in (
                (verbatim(inside), archive),
                (short_inside, archive),
                (inside, verbatim(archive)),
                (inside, short_backups / archive.name),
            ):
                with (
                    self.subTest(identity=identity, output=output),
                    self.assertRaisesRegex(ValueError, "outside_backup_directory"),
                ):
                    external_identity(identity, output)
            for identity in (outside, verbatim(outside), short(outside)):
                with self.subTest(legitimate_identity=identity):
                    external_identity(identity, archive)
                    self.assertTrue(unlinked_path(identity).samefile(outside))
                    self.assertEqual(read_private(identity), b"synthetic private input")

    def test_private_input_replacement_between_check_and_open_refused(self):
        from tools.mongodb_backup.security import read_private

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            replacement = Path(directory) / "replacement.json"
            path.write_bytes(b"original synthetic configuration")
            replacement.write_bytes(b"replacement synthetic configuration")
            path.chmod(0o600)
            replacement.chmod(0o600)
            original_open = os.open

            def replace_before_open(target, flags, *args, **kwargs):
                if Path(target) == path:
                    replacement.replace(path)
                return original_open(target, flags, *args, **kwargs)

            with (
                patch(
                    "tools.mongodb_backup.security.os.open",
                    side_effect=replace_before_open,
                ),
                self.assertRaises(ValueError),
            ):
                read_private(path)

    def test_cli_does_not_accept_abbreviated_sensitive_file_flags(self):
        from tools.mongodb_backup.__main__ import parser

        with (
            patch("sys.stderr", new_callable=io.StringIO),
            self.assertRaises(SystemExit),
        ):
            parser().parse_args(
                ["verify", "--work-dir", "w", "--input", "i", "--identity", "k"]
            )

    def test_manifest_rejects_duplicate_keys_and_boolean_format(self):
        import struct

        from tools.mongodb_backup.streams import MAGIC, header, read_header

        value = manifest()
        value["format"] = True
        with self.assertRaises(ValueError):
            header(value)
        data = (
            json.dumps(manifest(), separators=(",", ":"))
            .encode()
            .replace(b'"format":1', b'"format":1,"format":1')
        )
        with self.assertRaises(ValueError):
            read_header(io.BytesIO(MAGIC + struct.pack(">I", len(data)) + data))

    def test_official_installer_is_present_and_refuses_wrong_digest(self):
        self.assertTrue(
            (ROOT / "tools/mongodb_backup/install_tools.py").exists(),
            "Missing independent verified tool installer",
        )
        from tools.mongodb_backup.install_tools import extract_verified

        with tempfile.TemporaryDirectory() as path:
            source = Path(path) / "untrusted.zip"
            source.write_bytes(b"not the pinned upstream archive")
            with self.assertRaises(ValueError):
                extract_verified(
                    source, {"sha256": "0" * 64, "binaries": {}}, Path(path) / "new"
                )
            self.assertFalse((Path(path) / "new").exists())

    def test_envelope_roundtrip_and_length_bound(self):
        from tools.mongodb_backup.streams import MAGIC, MAX_HEADER, header, read_header

        value = manifest()
        stream = io.BytesIO(header(value) + b"archive")
        self.assertEqual(read_header(stream), value)
        self.assertEqual(stream.read(), b"archive")
        with self.assertRaises(ValueError):
            read_header(io.BytesIO(MAGIC + (MAX_HEADER + 1).to_bytes(4, "big")))

    def test_manifest_rejects_wildcard_namespace_or_missing_coordinator(self):
        from tools.mongodb_backup.streams import header

        for change in ("namespace", "coordinator", "type", "digest", "tools", "server"):
            value = manifest()
            if change == "namespace":
                value["source_database"] = "source.*"
            elif change == "coordinator":
                value["inventory"]["collections"].clear()
            elif change == "type":
                value["inventory"]["revision"] = True
            elif change == "digest":
                value["inventory"]["collections"]["coordination"][
                    "documents_sha256"
                ] = "garbage"
            elif change == "tools":
                value["tools_version"] = "older"
            else:
                value["mongo_version"] = "9.0"
            with self.subTest(change=change), self.assertRaises(ValueError):
                header(value)

    def test_native_key_gate_refuses_plugins_ssh_and_empty_files(self):
        from tools.mongodb_backup.security import key_lines

        for data in (
            b"",
            b"# comment",
            b"age1yubikey1something",
            b"ssh-ed25519 AAAA",
            b"AGE-PLUGIN-FOO-1XYZ",
        ):
            for identity in (True, False):
                with (
                    self.subTest(data=data, identity=identity),
                    self.assertRaises(ValueError),
                ):
                    key_lines(data, identity=identity)

    def test_connection_config_is_authenticated_primary_scoped(self):
        from tools.mongodb_backup.security import connection_config

        base = "mongodb://fixture:synthetic@127.0.0.1:27017/?replicaSet=rs&authSource=auth&authMechanism=SCRAM-SHA-256"
        self.assertEqual(
            connection_config(json.dumps({"uri": base}).encode())[0]["uri"], base
        )
        for uri in (
            base + "&readPreference=secondary",
            base + "&tlsInsecure=true",
            base.replace("127.0.0.1", "example.test"),
            base.replace("fixture:synthetic@", ""),
            base.replace("/?", "/admin?"),
            base.replace("mongodb://", "mongodb+srv://"),
        ):
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                connection_config(json.dumps({"uri": uri}).encode())

    def test_cli_error_never_exposes_config_content(self):
        from tools.mongodb_backup.__main__ import main

        sentinel = "SENSITIVE_SENTINEL_SHOULD_NOT_APPEAR"
        with (
            patch(
                "tools.mongodb_backup.operations.execute",
                side_effect=RuntimeError(sentinel),
            ),
            patch("sys.stderr", new_callable=io.StringIO) as error,
        ):
            self.assertEqual(main(["init-directory", "--directory", "unused"]), 1)
            self.assertNotIn(sentinel, error.getvalue())

    def test_partial_encrypted_output_removed_and_existing_file_preserved(self):
        from tools.mongodb_backup.operations import encrypted_output

        with (
            tempfile.TemporaryDirectory() as path,
            patch("tools.mongodb_backup.operations.private_path"),
        ):
            output = Path(path) / "backup.cvmb.age"
            with self.assertRaises(RuntimeError), encrypted_output(output) as stream:
                stream.write(b"only partial encrypted data")
                raise RuntimeError("failure after dump")
            self.assertEqual(list(Path(path).iterdir()), [])
            output.write_bytes(b"existing must survive")
            with self.assertRaises(ValueError), encrypted_output(output):
                self.fail("Must not yield an existing destination")
            self.assertEqual(output.read_bytes(), b"existing must survive")

    def test_publish_race_never_overwrites_destination(self):
        from tools.mongodb_backup.operations import encrypted_output

        with (
            tempfile.TemporaryDirectory() as path,
            patch("tools.mongodb_backup.operations.private_path"),
        ):
            output = Path(path) / "backup.cvmb.age"
            with self.assertRaises(FileExistsError), encrypted_output(output) as stream:
                stream.write(b"candidate encrypted data")
                output.write_bytes(b"concurrent owner")
            self.assertEqual(output.read_bytes(), b"concurrent owner")
            self.assertEqual(len(list(Path(path).iterdir())), 1)

    def test_retention_preview_keeps_minimum_and_never_deletes(self):
        from types import SimpleNamespace

        from tools.mongodb_backup.operations import retention_plan

        with (
            tempfile.TemporaryDirectory() as path,
            patch(
                "tools.mongodb_backup.operations.private_path", return_value=Path(path)
            ),
        ):
            for i in range(10):
                entry = Path(path) / f"snapshot-{i}.cvmb.age"
                entry.write_bytes(b"encrypted fixture")
                os.utime(entry, (1 + i, 1 + i))
            result = retention_plan(
                SimpleNamespace(
                    directory=Path(path),
                    keep_days=30,
                    keep_minimum=7,
                    maximum_age_hours=24,
                )
            )
            self.assertEqual(len(result["delete_candidates"]), 3)
            self.assertTrue(result["freshness_due"])
            self.assertEqual(len(list(Path(path).iterdir())), 10)

    def test_deadline_kills_and_reaps_blocked_child(self):
        from tools.mongodb_backup.streams import Child, pump

        started = time.monotonic()
        with (
            self.assertRaises((ValueError, subprocess.TimeoutExpired)),
            Child(
                [sys.executable, "-c", "import time;time.sleep(10)"],
                deadline=started + 0.2,
                stdout=subprocess.PIPE,
            ) as child,
        ):
            pump(child.process.stdout, None, child.deadline)
            child.finish()
        self.assertIsNotNone(child.process.returncode)
        self.assertLess(time.monotonic() - started, 3)

    def test_private_mode_and_links_are_rejected(self):
        from tools.mongodb_backup.security import private_path, unlinked_path

        with tempfile.TemporaryDirectory() as path:
            target = Path(path) / "synthetic.json"
            target.write_text("{}")
            if os.name == "nt":
                subprocess.run(
                    ["icacls", str(target), "/grant", "*S-1-1-0:(R)"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
            else:
                target.chmod(0o644)
            with self.assertRaises(ValueError):
                private_path(target)
            link = Path(path) / "linked.json"
            try:
                link.symlink_to(target)
            except OSError:
                pass  # Windows may not grant symlink privilege; ACL gate above ran.
            else:
                with self.assertRaises(ValueError):
                    unlinked_path(link)


class MongoContract(unittest.TestCase):
    def finalization_fixture(self):
        from unittest.mock import MagicMock

        from tools.mongodb_backup.mongo import MARKER

        database = MagicMock()
        state = {"marker": True}
        marker = database[MARKER]
        marker.find_one.return_value = {
            "_id": "owned-operation",
            "state": "QUARANTINED_UNTIL_VERIFIED",
        }
        marker.drop.side_effect = lambda: state.update(marker=False)
        database.list_collection_names.side_effect = lambda: (
            [MARKER] if state["marker"] else []
        )
        return database, marker, state

    def test_finalization_resolves_effective_drop_with_lost_ack_without_replay(self):
        from pymongo.errors import AutoReconnect

        from tools.mongodb_backup.mongo import finish_target

        database, marker, state = self.finalization_fixture()

        def lost_ack():
            state["marker"] = False
            raise AutoReconnect("synthetic lost ACK")

        marker.drop.side_effect = lost_ack
        with (
            patch(
                "tools.mongodb_backup.mongo.primary", return_value={"same": "primary"}
            ),
            patch(
                "tools.mongodb_backup.mongo.fingerprint",
                return_value=manifest()["inventory"],
            ),
        ):
            finish_target(
                database,
                manifest()["inventory"],
                "owned-operation",
                time.monotonic() + 10,
            )
        self.assertFalse(state["marker"])
        marker.drop.assert_called_once_with()

    def test_finalization_unknown_when_readback_fails_after_effective_drop(self):
        from pymongo.errors import AutoReconnect

        from tools.mongodb_backup.mongo import finish_target

        database, marker, state = self.finalization_fixture()
        database.list_collection_names.side_effect = AutoReconnect(
            "synthetic read failure"
        )
        with (
            patch(
                "tools.mongodb_backup.mongo.primary", return_value={"same": "primary"}
            ),
            patch(
                "tools.mongodb_backup.mongo.fingerprint",
                return_value=manifest()["inventory"],
            ),
            self.assertRaisesRegex(ValueError, "^finalization_unknown$"),
        ):
            finish_target(
                database,
                manifest()["inventory"],
                "owned-operation",
                time.monotonic() + 10,
            )
        self.assertFalse(state["marker"])
        marker.drop.assert_called_once_with()

    def test_finalization_unknown_preserves_marker_without_replaying_drop(self):
        from tools.mongodb_backup.mongo import finish_target

        database, marker, state = self.finalization_fixture()
        marker.drop.side_effect = None
        with (
            patch(
                "tools.mongodb_backup.mongo.primary", return_value={"same": "primary"}
            ),
            patch(
                "tools.mongodb_backup.mongo.fingerprint",
                return_value=manifest()["inventory"],
            ),
            self.assertRaisesRegex(ValueError, "^finalization_unknown$"),
        ):
            finish_target(
                database,
                manifest()["inventory"],
                "owned-operation",
                time.monotonic() + 10,
            )
        self.assertTrue(state["marker"])
        marker.drop.assert_called_once_with()

    def test_finalization_unknown_for_changed_primary_or_inventory(self):
        from pymongo.errors import AutoReconnect

        from tools.mongodb_backup.mongo import finish_target

        for change in ("primary", "inventory"):
            database, marker, state = self.finalization_fixture()
            if change == "inventory":

                def lost_ack(state=state):
                    state["marker"] = False
                    raise AutoReconnect("synthetic lost ACK")

                marker.drop.side_effect = lost_ack
            identities = (
                [{"id": "one"}, {"id": "two"}]
                if change == "primary"
                else [{"id": "one"}] * 3
            )
            inventories = (
                [manifest()["inventory"], {"changed": True}]
                if change == "inventory"
                else [manifest()["inventory"]] * 2
            )
            with (
                self.subTest(change=change),
                patch("tools.mongodb_backup.mongo.primary", side_effect=identities),
                patch(
                    "tools.mongodb_backup.mongo.fingerprint", side_effect=inventories
                ),
                self.assertRaisesRegex(ValueError, "^finalization_unknown$"),
            ):
                finish_target(
                    database,
                    manifest()["inventory"],
                    "owned-operation",
                    time.monotonic() + 10,
                )
            self.assertFalse(state["marker"])
            marker.drop.assert_called_once_with()

    def test_finalization_expired_budget_never_drops_marker(self):
        from tools.mongodb_backup.mongo import finish_target

        database, marker, state = self.finalization_fixture()
        with (
            patch(
                "tools.mongodb_backup.mongo.fingerprint",
                return_value=manifest()["inventory"],
            ),
            self.assertRaisesRegex(ValueError, "operation_deadline_exceeded"),
        ):
            finish_target(
                database,
                manifest()["inventory"],
                "owned-operation",
                time.monotonic() - 1,
            )
        self.assertTrue(state["marker"])
        marker.drop.assert_not_called()

    def test_finalization_confirms_normal_drop_and_exact_inventory(self):
        from tools.mongodb_backup.mongo import finish_target

        database, marker, state = self.finalization_fixture()
        with (
            patch(
                "tools.mongodb_backup.mongo.primary", return_value={"same": "primary"}
            ),
            patch(
                "tools.mongodb_backup.mongo.fingerprint",
                side_effect=[manifest()["inventory"]],
            ),
        ):
            finish_target(
                database,
                manifest()["inventory"],
                "owned-operation",
                time.monotonic() + 10,
            )
        self.assertFalse(state["marker"])
        marker.drop.assert_called_once_with()

    def test_finalization_expiry_after_drop_stops_readback_without_replay(self):
        from tools.mongodb_backup.mongo import finish_target

        database, marker, state = self.finalization_fixture()
        clock = [0]

        def drop_at_expiry():
            state["marker"] = False
            clock[0] = 2

        marker.drop.side_effect = drop_at_expiry
        with (
            patch(
                "tools.mongodb_backup.mongo.time.monotonic",
                side_effect=lambda: clock[0],
            ),
            patch(
                "tools.mongodb_backup.mongo.primary", return_value={"same": "primary"}
            ),
            patch(
                "tools.mongodb_backup.mongo.fingerprint",
                return_value=manifest()["inventory"],
            ),
            self.assertRaisesRegex(ValueError, "^finalization_unknown$"),
        ):
            finish_target(database, manifest()["inventory"], "owned-operation", 1)
        self.assertFalse(state["marker"])
        marker.drop.assert_called_once_with()
        database.list_collection_names.assert_not_called()

    def test_unknown_finalization_cli_emits_no_success_or_upstream_detail(self):
        from pymongo.errors import AutoReconnect

        from tools.mongodb_backup.__main__ import main
        from tools.mongodb_backup.mongo import finish_target

        database, _, _ = self.finalization_fixture()
        database.list_collection_names.side_effect = AutoReconnect(
            "synthetic secret sentinel"
        )

        def operation(_):
            finish_target(
                database,
                manifest()["inventory"],
                "owned-operation",
                time.monotonic() + 10,
            )

        with (
            patch(
                "tools.mongodb_backup.mongo.primary", return_value={"same": "primary"}
            ),
            patch(
                "tools.mongodb_backup.mongo.fingerprint",
                return_value=manifest()["inventory"],
            ),
            patch("tools.mongodb_backup.operations.execute", side_effect=operation),
            patch("sys.stdout", new_callable=io.StringIO) as output,
            patch("sys.stderr", new_callable=io.StringIO) as error,
        ):
            result = main(["init-directory", "--directory", "unused"])
        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("finalization_unknown", error.getvalue())
        self.assertNotIn("synthetic secret sentinel", error.getvalue())

    def test_different_primary_refused_before_coordinator_write(self):
        from unittest.mock import MagicMock

        from tools.mongodb_backup.mongo import frozen

        source, freezer = MagicMock(), MagicMock()
        with (
            patch(
                "tools.mongodb_backup.mongo.primary",
                side_effect=[{"id": "one"}, {"id": "two"}],
            ),
            self.assertRaisesRegex(ValueError, "primary_mismatch"),
            frozen(source, freezer, "cinevault", 30),
        ):
            self.fail("A different server must never be frozen")
        freezer.start_session.assert_not_called()

    def test_unchanged_inventory_required_after_dump(self):
        from unittest.mock import MagicMock

        from bson import Int64

        from tools.mongodb_backup.mongo import frozen

        source, freezer = MagicMock(), MagicMock()
        session = freezer.start_session.return_value.__enter__.return_value
        session.in_transaction = True
        held = {"revision": Int64(7)}
        freezer.__getitem__.return_value.coordination.find_one_and_update.return_value = held
        freezer.__getitem__.return_value.coordination.find_one.return_value = held
        with (
            patch(
                "tools.mongodb_backup.mongo.primary", return_value={"same": "primary"}
            ),
            patch(
                "tools.mongodb_backup.mongo.fingerprint",
                side_effect=[manifest()["inventory"], {"changed": True}],
            ),
            self.assertRaisesRegex(ValueError, "source_changed"),
            frozen(source, freezer, "cinevault", 30),
        ):
            pass
        session.abort_transaction.assert_called()

    def test_fingerprint_preserves_bson_int64_and_index_key_order(self):
        from unittest.mock import MagicMock

        from bson import Int64

        from tools.mongodb_backup.mongo import fingerprint

        database = MagicMock()
        database.list_collections.return_value = [
            {"name": "coordination", "type": "collection", "options": {}}
        ]
        collection = database.__getitem__.return_value
        index = {"name": "compound", "v": 2, "key": {"first": 1, "second": -1}}
        collection.list_indexes.side_effect = lambda: iter([index])
        document = {"_id": "business", "revision": Int64(6)}
        database.coordination.find_one.side_effect = lambda *a, **kw: document
        collection.find.return_value.sort.return_value.batch_size.return_value.__enter__.return_value = iter(
            [document]
        )
        before = fingerprint(database, time.monotonic() + 10)
        document["revision"] = 6
        with self.assertRaises(ValueError):
            fingerprint(database, time.monotonic() + 10)
        document["revision"] = Int64(6)
        index["key"] = {"second": -1, "first": 1}
        collection.find.return_value.sort.return_value.batch_size.return_value.__enter__.return_value = iter(
            [document]
        )
        after = fingerprint(database, time.monotonic() + 10)
        self.assertNotEqual(
            before["collections"]["coordination"]["indexes_sha256"],
            after["collections"]["coordination"]["indexes_sha256"],
        )

    def test_ttl_background_writers_refused(self):
        from unittest.mock import MagicMock

        from tools.mongodb_backup.mongo import fingerprint

        database = MagicMock()
        database.list_collections.return_value = [
            {"name": "sessions", "type": "collection"}
        ]
        database.__getitem__.return_value.list_indexes.return_value = [
            {"name": "ttl", "key": {"until": 1}, "expireAfterSeconds": 0}
        ]
        with self.assertRaisesRegex(ValueError, "ttl_writers"):
            fingerprint(database, time.monotonic() + 10)

    def test_freeze_checks_server_transaction_and_aborts_on_dump_failure(self):
        from unittest.mock import MagicMock

        from bson import Int64

        from tools.mongodb_backup.mongo import frozen

        source, freezer = MagicMock(), MagicMock()
        session = freezer.start_session.return_value.__enter__.return_value
        session.in_transaction = True
        held = {"_id": "business", "revision": Int64(7)}
        coordinate = freezer.__getitem__.return_value.coordination
        coordinate.find_one_and_update.return_value = held
        coordinate.find_one.return_value = held
        source.__getitem__.return_value.coordination.find_one.return_value = {
            "revision": Int64(6)
        }
        with (
            patch(
                "tools.mongodb_backup.mongo.primary", return_value={"same": "primary"}
            ),
            patch(
                "tools.mongodb_backup.mongo.fingerprint",
                return_value=manifest()["inventory"],
            ),
        ):
            with (
                self.assertRaises(RuntimeError),
                frozen(source, freezer, "cinevault", 30),
            ):
                raise RuntimeError("dump failed")
            session.abort_transaction.assert_called()
            session.abort_transaction.reset_mock()
            with frozen(source, freezer, "cinevault", 30) as result:
                self.assertEqual(result["inventory"]["revision"], 6)
            coordinate.find_one.assert_called_with({"_id": "business"}, session=session)
            self.assertIn("freeze_seconds", result)
            update = coordinate.find_one_and_update.call_args.args
            self.assertEqual(update[1], {"$inc": {"revision": Int64(1)}})
            self.assertIs(type(update[1]["$inc"]["revision"]), Int64)

    def test_expired_transaction_or_changed_source_not_accepted(self):
        from unittest.mock import MagicMock

        from bson import Int64

        from tools.mongodb_backup.mongo import frozen

        source, freezer = MagicMock(), MagicMock()
        session = freezer.start_session.return_value.__enter__.return_value
        session.in_transaction = True
        freezer.__getitem__.return_value.coordination.find_one_and_update.return_value = {
            "revision": Int64(7)
        }
        freezer.__getitem__.return_value.coordination.find_one.return_value = None
        with (
            patch(
                "tools.mongodb_backup.mongo.primary", return_value={"same": "primary"}
            ),
            patch(
                "tools.mongodb_backup.mongo.fingerprint",
                return_value=manifest()["inventory"],
            ),
            self.assertRaisesRegex(ValueError, "freeze_not_alive"),
            frozen(source, freezer, "cinevault", 30),
        ):
            pass
        session.abort_transaction.assert_called()

    def test_existing_target_and_source_name_refused_without_writes(self):
        from unittest.mock import MagicMock

        from tools.mongodb_backup.mongo import claim_target

        client = MagicMock()
        with self.assertRaises(ValueError):
            claim_target(client, "cinevault", manifest(), "operation")
        with (
            patch(
                "tools.mongodb_backup.mongo.primary", return_value={"new": "primary"}
            ),
            patch("tools.mongodb_backup.mongo.version", return_value="8.0.34"),
        ):
            client.__getitem__.return_value.list_collection_names.return_value = [
                "existing"
            ]
            with self.assertRaisesRegex(ValueError, "not_empty"):
                claim_target(client, "restored", manifest(), "operation")
        client.__getitem__.return_value.create_collection.assert_not_called()

    def test_failed_restore_verification_preserves_quarantine_marker(self):
        from unittest.mock import MagicMock

        from tools.mongodb_backup.mongo import MARKER, finish_target

        database = MagicMock()
        database.__getitem__.return_value.find_one.return_value = {
            "_id": "owned",
            "state": "QUARANTINED_UNTIL_VERIFIED",
        }
        with (
            patch(
                "tools.mongodb_backup.mongo.fingerprint",
                return_value={"wrong": "inventory"},
            ),
            self.assertRaisesRegex(ValueError, "quarantined"),
        ):
            finish_target(
                database, manifest()["inventory"], "owned", time.monotonic() + 10
            )
        database[MARKER].drop.assert_not_called()


class AgeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.age = Path(os.environ.get("AGE_TEST_BINARY", ""))
        if not cls.age.is_file():
            raise unittest.SkipTest(
                "Set AGE_TEST_BINARY to pinned official age; no fake crypto result"
            )
        cls.keygen = cls.age.with_name("age-keygen" + cls.age.suffix)

    def setUp(self):
        from tools.mongodb_backup.security import initialize_directory

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = initialize_directory(Path(self.temp.name) / "private")
        self.identity = self.path / "identity.txt"
        subprocess.run(
            [self.keygen, "--output", self.identity], capture_output=True, check=True
        )
        self.recipients = self.path / "recipients.txt"
        public = subprocess.run(
            [self.keygen, "-y", self.identity], capture_output=True, check=True
        )
        self.recipients.write_bytes(public.stdout)
        self.recipients.chmod(0o600)

    def encrypted(self, destination=None):
        import time

        from tools.mongodb_backup.streams import encrypt_dump

        destination = destination or self.path / "fixture.age"
        with destination.open("wb") as output:
            encrypt_dump(
                self.age,
                self.recipients,
                [
                    sys.executable,
                    "-c",
                    "import sys;sys.stdout.buffer.write(b'fixture' * 40000)",
                ],
                manifest(),
                output,
                time.monotonic() + 20,
            )
        return destination

    def test_real_age_roundtrip_stream_rotation_and_fresh_ciphertext(self):
        import time

        from tools.mongodb_backup.security import key_lines, read_private
        from tools.mongodb_backup.streams import authenticate, rotate_stream

        key_lines(read_private(self.identity), identity=True)
        key_lines(read_private(self.recipients), identity=False)
        source = self.encrypted()
        rotated = self.path / "rotated.age"
        identity2 = self.path / "new-identity.txt"
        subprocess.run([self.keygen, "-o", identity2], capture_output=True, check=True)
        recipient2 = self.path / "new-recipients.txt"
        recipient2.write_bytes(
            subprocess.run(
                [self.keygen, "-y", identity2], capture_output=True, check=True
            ).stdout
        )
        recipient2.chmod(0o600)
        with source.open("rb") as encrypted, rotated.open("wb") as output:
            expected = authenticate(
                self.age, self.identity, encrypted, time.monotonic() + 20
            )
            self.assertEqual(expected[1], 280000)
            rotate_stream(
                self.age,
                self.identity,
                encrypted,
                recipient2,
                expected,
                output,
                time.monotonic() + 20,
            )
        self.assertNotEqual(source.read_bytes(), rotated.read_bytes())
        with rotated.open("rb") as encrypted:
            self.assertEqual(
                authenticate(self.age, identity2, encrypted, time.monotonic() + 20),
                expected,
            )
            with self.assertRaises(ValueError):
                authenticate(self.age, self.identity, encrypted, time.monotonic() + 20)

    def test_wrong_key_tamper_truncation_and_trailing_data_refused(self):
        import time

        from tools.mongodb_backup.streams import authenticate

        source = self.encrypted().read_bytes()
        wrong = self.path / "wrong.txt"
        subprocess.run([self.keygen, "-o", wrong], capture_output=True, check=True)
        damaged = (
            source[:-1],
            source + b"extra",
            source[:-20] + bytes([source[-20] ^ 1]) + source[-19:],
        )
        for index, data in enumerate(damaged):
            target = self.path / f"damaged-{index}.age"
            target.write_bytes(data)
            with (
                self.subTest(index=index),
                target.open("rb") as encrypted,
                self.assertRaises(ValueError),
            ):
                authenticate(self.age, self.identity, encrypted, time.monotonic() + 20)
        good = self.path / "fixture.age"
        with good.open("rb") as encrypted, self.assertRaises(ValueError):
            authenticate(self.age, wrong, encrypted, time.monotonic() + 20)

    def test_dump_failure_after_output_is_not_success(self):
        import time

        from tools.mongodb_backup.streams import encrypt_dump

        with (
            (self.path / "failure.age").open("wb") as output,
            self.assertRaises(ValueError),
        ):
            encrypt_dump(
                self.age,
                self.recipients,
                [
                    sys.executable,
                    "-c",
                    "import sys;sys.stdout.buffer.write(b'partial');sys.stdout.flush();sys.exit(3)",
                ],
                manifest(),
                output,
                time.monotonic() + 20,
            )

    def test_corruption_refused_before_any_mongo_target_contact(self):
        import hashlib
        from types import SimpleNamespace

        from tools.mongodb_backup.operations import read_operation

        archive_dir = self.path / "backups"
        work = self.path / "work"
        archive_dir.mkdir(mode=0o700)
        work.mkdir(mode=0o700)
        good = self.encrypted().read_bytes()
        target = archive_dir / "fixture.cvmb.age"
        for index, data in enumerate((good[:-1], good + b"extra")):
            target.write_bytes(data)
            args = SimpleNamespace(
                command="restore",
                identity_file=self.identity,
                input=target,
                timeout=20,
                expected_sha256=hashlib.sha256(data).hexdigest(),
                database="isolated_restore",
                target_config=self.path / "unused.json",
                mongorestore=Path("unused"),
            )
            attempt = work / str(index)
            attempt.mkdir(mode=0o700)
            with (
                patch("tools.mongodb_backup.mongo.connect") as connect,
                self.assertRaises(ValueError),
            ):
                read_operation(args, self.age, attempt)
            connect.assert_not_called()
        self.assertFalse(
            any(
                file.suffix in {".archive", ".bson", ".gz"}
                for file in self.path.rglob("*")
            )
        )

    def test_public_cli_verify_and_rotation_cleanup_without_plaintext_files(self):
        archive_dir, work = self.path / "backups", self.path / "work"
        archive_dir.mkdir(mode=0o700)
        work.mkdir(mode=0o700)
        source = self.encrypted(archive_dir / "fixture.cvmb.age")
        command = [
            sys.executable,
            "-W",
            "error",
            "-m",
            "tools.mongodb_backup",
            "--age",
            str(self.age),
        ]
        common = [
            "--work-dir",
            str(work),
            "--input",
            str(source),
            "--identity-file",
            str(self.identity),
        ]
        result = subprocess.run(
            command + ["verify"] + common, cwd=ROOT, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(
            json.loads(result.stdout)["status"], "CIPHERTEXT_AUTHENTICATED"
        )
        rotated = archive_dir / "rotation.cvmb.age"
        result = subprocess.run(
            command
            + ["rotate"]
            + common
            + ["--recipients-file", str(self.recipients), "--output", str(rotated)],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(json.loads(result.stdout)["status"], "ROTATED_COPY_CREATED")
        self.assertEqual(list(work.iterdir()), [])
        self.assertEqual({path.suffix for path in archive_dir.iterdir()}, {".age"})

    def test_verified_second_pass_sends_exact_archive_to_consumer(self):
        import hashlib

        from tools.mongodb_backup.streams import authenticate, restore_stream

        target = self.encrypted()
        expected_digest = hashlib.sha256(b"fixture" * 40000).hexdigest()
        consumer = [
            sys.executable,
            "-c",
            "import sys,hashlib;sys.exit(0 if hashlib.sha256(sys.stdin.buffer.read()).hexdigest()==sys.argv[1] else 7)",
            expected_digest,
        ]
        with target.open("rb") as encrypted:
            expected = authenticate(
                self.age, self.identity, encrypted, time.monotonic() + 20
            )
            restore_stream(
                self.age,
                self.identity,
                encrypted,
                consumer,
                expected,
                time.monotonic() + 20,
            )

    def test_real_age_post_quantum_native_identity_supported(self):
        from tools.mongodb_backup.security import key_lines, read_private
        from tools.mongodb_backup.streams import authenticate

        self.identity = self.path / "pq-identity.txt"
        subprocess.run(
            [self.keygen, "-pq", "-o", self.identity], capture_output=True, check=True
        )
        self.recipients.write_bytes(
            subprocess.run(
                [self.keygen, "-y", self.identity], capture_output=True, check=True
            ).stdout
        )
        self.recipients.chmod(0o600)
        key_lines(read_private(self.identity), identity=True)
        key_lines(read_private(self.recipients), identity=False)
        with self.encrypted().open("rb") as encrypted:
            self.assertEqual(
                authenticate(self.age, self.identity, encrypted, time.monotonic() + 20)[
                    1
                ],
                280000,
            )


if __name__ == "__main__":
    unittest.main()
