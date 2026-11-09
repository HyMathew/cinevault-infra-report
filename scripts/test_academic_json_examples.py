"""Offline regression checks: examples must detect deliberately corrupted fixtures."""

import copy
import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import academic_json_examples as examples

sys.dont_write_bytecode = True
API = Path(__file__).resolve().parents[2] / "cinevault-api"
sys.path.insert(0, str(API))

from app.metadata import MetadataUnavailable
from app.repository import StorageError
from jsonschema.exceptions import ValidationError


class AcademicExamplesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts, cls.manifest = examples.load_artifacts(examples.DESTINATION)

    def setUp(self):
        self.data = copy.deepcopy(self.artifacts)
        self.network = patch.object(
            socket.socket, "connect", side_effect=AssertionError("No network")
        )
        self.network.start()
        self.addCleanup(self.network.stop)

    def validate(self):
        return examples.validate_artifacts(API, self.data)

    def test_complete_current_examples_pass(self):
        result = self.validate()
        specification = json.loads(
            (API / "docs/openapi-v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            set(result["openapi_components"]),
            set(specification["components"]["schemas"]),
        )
        self.assertEqual(result["http_exchange_count"], 93)
        self.assertEqual(result["openapi_operation_count"], 44)

    def test_source_fingerprint_ignores_only_utf8_line_endings(self):
        with tempfile.TemporaryDirectory(
            prefix="cinevault-source-newlines-"
        ) as temporary:
            root = Path(temporary)
            lf, crlf = root / "lf.py", root / "crlf.py"
            content = 'title = "Été fictif"\ncount = 1\n'.encode()
            lf.write_bytes(content)
            crlf.write_bytes(content.replace(b"\n", b"\r\n"))
            self.assertNotEqual(
                examples.sha256(lf.read_bytes()), examples.sha256(crlf.read_bytes())
            )
            self.assertEqual(examples.source_sha256(lf), examples.source_sha256(crlf))
            crlf.write_bytes(content.replace(b"count = 1", b"count = 2"))
            self.assertNotEqual(
                examples.source_sha256(lf), examples.source_sha256(crlf)
            )

    def test_source_verification_accepts_crlf_but_rejects_real_change(self):
        with tempfile.TemporaryDirectory(
            prefix="cinevault-source-verification-"
        ) as temporary:
            root = Path(temporary)
            source = root / "sample.py"
            source.write_bytes(b"count = 1\n")
            manifest = {
                "source_fingerprint_mode": "sha256:utf8-lf:v1",
                "api_source_sha256": {"sample.py": examples.sha256(b"count = 1\n")},
            }
            source.write_bytes(b"count = 1\r\n")
            examples.verify_source_fingerprints(root, manifest)
            source.write_bytes(b"count = 2\r\n")
            with self.assertRaises(AssertionError):
                examples.verify_source_fingerprints(root, manifest)

    def test_missing_component_is_detected(self):
        del self.data["openapi-components.json"]["Copy"]
        with self.assertRaises(AssertionError):
            self.validate()

    def test_each_technical_schema_rejects_invalid_field_types(self):
        schemas = examples.technical_schemas()
        invalid = {
            "LegacyCatalogue": {"films": "not-an-array"},
            "Health": {"status": True},
            "RecoveryReport": {
                **self.data["recovery-report.synthetic.json"],
                "closed_reservations": True,
            },
            "MetadataCache": {
                **self.data["metadata-cache.synthetic.json"],
                "count": "one",
            },
            "ClientContext": {
                **self.data["client-context.synthetic.json"],
                "body_utf8": {},
            },
        }
        for name, value in invalid.items():
            with self.subTest(schema=name), self.assertRaises(ValidationError):
                examples.schema_validate(schemas, {"$ref": "#/$defs/" + name}, value)

    def test_technical_schema_roots_reject_unknown_fields(self):
        schemas = self.data["technical-schemas.json"]
        fixtures = {
            "LegacyCatalogue": self.data["legacy-catalogue.synthetic.json"],
            "Health": {"status": "ok"},
            "RecoveryReport": self.data["recovery-report.synthetic.json"],
            "MetadataCache": self.data["metadata-cache.synthetic.json"],
            "ClientContext": self.data["client-context.synthetic.json"],
        }
        for name, value in fixtures.items():
            with self.subTest(schema=name), self.assertRaises(ValidationError):
                examples.schema_validate(
                    schemas, {"$ref": "#/$defs/" + name}, {**value, "unknown": "field"}
                )

    def test_cache_schema_permits_generic_values_but_not_derived_cache_metadata(self):
        schemas = self.data["technical-schemas.json"]
        value = {
            "version": 1,
            "window_start": 0,
            "count": 0,
            "blocked_until": 0,
            "entries": {
                "a" * 64: {
                    "stored_at": 0,
                    "expires_at": 86400,
                    "stale_until": 691200,
                    "value": {"arbitrary": ["JSON", 1, None]},
                }
            },
        }
        examples.schema_validate(schemas, {"$ref": "#/$defs/MetadataCache"}, value)
        value["entries"]["a" * 64]["value"]["cache"] = {}
        with self.assertRaises(ValidationError):
            examples.schema_validate(schemas, {"$ref": "#/$defs/MetadataCache"}, value)

    def test_context_schema_accepts_ipv6_and_checks_ip_format(self):
        schemas = self.data["technical-schemas.json"]
        value = self.data["client-context.synthetic.json"]
        value["headers"]["X-CineVault-Client-IP"] = "::1"
        value["headers"]["X-Optional-Example"] = "allowed HTTP header"
        examples.schema_validate(schemas, {"$ref": "#/$defs/ClientContext"}, value)
        value["headers"]["X-CineVault-Client-IP"] = "999.999.999.999"
        with self.assertRaises(ValidationError):
            examples.schema_validate(schemas, {"$ref": "#/$defs/ClientContext"}, value)

    def test_technical_schemas_are_enforced_by_full_artifact_validation(self):
        health = next(
            exchange
            for exchange in self.data["http-exchanges.json"]
            if exchange["name"] == "health"
        )
        health["response_body"] = {"status": True}
        with self.assertRaises(ValidationError):
            self.validate()

    def test_missing_openapi_operation_is_detected(self):
        self.data["http-exchanges.json"] = [
            exchange
            for exchange in self.data["http-exchanges.json"]
            if not (
                exchange["method"] == "DELETE"
                and exchange["path"].startswith("/api/v1/copies/")
            )
        ]
        with self.assertRaisesRegex(AssertionError, "Missing OpenAPI operations"):
            self.validate()

    def test_all_reported_schema_pointers_resolve_in_source_openapi(self):
        result = self.validate()
        specification = json.loads(
            (API / "docs/openapi-v1.json").read_text(encoding="utf-8")
        )
        for pointer in result["http_schema_locations"]:
            with self.subTest(pointer=pointer):
                self.assertIsInstance(examples.resolve(specification, pointer), dict)

    def test_uuid_format_is_checked(self):
        self.data["openapi-components.json"]["Stored_id"] = "not-a-uuid"
        with self.assertRaises(ValidationError):
            self.validate()

    def test_uri_format_is_checked(self):
        self.data["openapi-components.json"]["MetadataSearch"]["items"][0][
            "source_url"
        ] = "not a URI"
        with self.assertRaises(ValidationError):
            self.validate()

    def test_uri_checker_checks_syntax_without_restricting_all_uris_to_https(self):
        for value in [
            "https://example.invalid/a%20b?q=x#y",
            "urn:cinevault:example",
            "mailto:person@example.invalid",
            "http://[::1]/",
        ]:
            with self.subTest(value=value):
                self.assertTrue(examples.valid_uri(value))
        for value in [
            "not a URI",
            "https://example.invalid/%xx",
            "https://[not-ipv6]/",
            "https://example.invalid/\ud800",
        ]:
            with self.subTest(value=ascii(value)):
                self.assertFalse(examples.valid_uri(value))

    def test_forged_resource_etag_is_detected(self):
        self.data["openapi-components.json"]["Movie"]["_etag"] = '"' + "0" * 64 + '"'
        with self.assertRaises(AssertionError):
            self.validate()

    def test_invalid_loan_branch_is_detected(self):
        self.data["lifecycle.json"]["loans"]["pending"]["copy_id"] = self.data[
            "openapi-components.json"
        ]["Copy"]["id"]
        with self.assertRaises(ValidationError):
            self.validate()

    def test_broken_store_reference_is_detected(self):
        self.data["enterprise-store.synthetic.json"]["loans"][0]["borrower_id"] = (
            "99999999-9999-4999-8999-999999999999"
        )
        with self.assertRaises(ValueError):
            self.validate()

    def test_invalid_admission_sum_is_detected_by_code(self):
        self.data["registration-admission.synthetic.json"]["total"] += 1
        with self.assertRaises(ValueError):
            self.validate()

    def test_invalid_cache_duration_is_detected_by_code(self):
        entry = next(
            iter(self.data["metadata-cache.synthetic.json"]["entries"].values())
        )
        entry["expires_at"] += 1
        with self.assertRaises(MetadataUnavailable):
            self.validate()

    def test_bad_signed_context_is_detected(self):
        self.data["client-context.synthetic.json"]["headers"][
            "X-CineVault-Client-Signature"
        ] = "0" * 64
        with self.assertRaises(AssertionError):
            self.validate()

    def test_bad_legacy_record_is_detected_by_repository(self):
        self.data["legacy-catalogue.synthetic.json"]["films"][0]["annee"] = "2001"
        with self.assertRaises(StorageError):
            self.validate()

    def test_recovery_digest_must_match_published_target(self):
        self.data["recovery-report.synthetic.json"]["target_sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            self.validate()

    def test_manifest_cannot_name_files_outside_fixture_directory(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["artifact_sha256"]["../outside.json"] = "0" * 64
        with tempfile.TemporaryDirectory(
            prefix="cinevault-fixture-manifest-test-"
        ) as temporary:
            destination = Path(temporary)
            (destination / "manifest.json").write_bytes(examples.encoded(manifest))
            with self.assertRaises(AssertionError):
                examples.load_artifacts(destination)


if __name__ == "__main__":
    unittest.main()
