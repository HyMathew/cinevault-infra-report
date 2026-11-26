import json
from datetime import UTC, datetime

import pytest

from scripts import check_staging_image_pair as pair


@pytest.fixture
def requested(tmp_path):
    entries = {}
    for index, role in enumerate(pair.ROLES, 1):
        entries[role] = {
            "commit": str(index) * 40,
            "run": 123 + index,
            "attempt": index,
            "audit_zip": f"{role}/image-audit.zip",
            "provenance_zip": f"{role}/image-verified-provenance.zip",
        }
    path = tmp_path / "pair.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path, entries


def verified_evidence(role, commit, run, attempt):
    reference = f"ghcr.io/hymathew/cinevault-{role}@sha256:" + "1" * 64
    return {
        "passed": True,
        "registry_reference": reference,
        "provenance": {
            "signature_verified": True,
            "source_commit": commit,
            "source_ref": pair.release.registry.QUALIFICATION_REF,
            "workflow_run": run,
            "workflow_attempt": attempt,
        },
    }


def test_pair_preserves_both_exact_attempts_and_relative_paths(
    requested, monkeypatch, capsys
):
    path, entries = requested
    calls = []

    def check(role, commit, run, attempt, audit, provenance):
        calls.append(role)
        entry = entries[role]
        assert (commit, run, attempt) == (
            entry["commit"],
            entry["run"],
            entry["attempt"],
        )
        assert audit == path.parent / entry["audit_zip"]
        assert provenance == path.parent / entry["provenance_zip"]
        return verified_evidence(role, commit, run, attempt)

    monkeypatch.setattr(pair.release, "check", check)
    assert pair.main(["--manifest", str(path)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["passed"] is True and calls == ["api", "web"]
    assert datetime.fromisoformat(receipt["verified_at_utc"]).tzinfo == UTC
    for role in calls:
        assert (
            receipt["images"][role]["provenance"]["workflow_attempt"]
            == entries[role]["attempt"]
        )
        assert (
            receipt["compose_environment"][f"CINEVAULT_STAGE_{role.upper()}_IMAGE"]
            == (receipt["images"][role]["registry_reference"])
        )


@pytest.mark.parametrize("failing", [("api",), ("web",), ("api", "web")])
def test_one_or_two_failed_images_produce_no_deployment_values(
    requested, monkeypatch, capsys, failing
):
    path, _ = requested
    calls = []

    def check(role, commit, run, attempt, *_):
        calls.append(role)
        if role in failing:
            raise pair.release.registry.RegistryVerificationError(
                "publication workflow did not succeed"
            )
        return verified_evidence(role, commit, run, attempt)

    monkeypatch.setattr(pair.release, "check", check)
    assert pair.main(["--manifest", str(path)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert calls == ["api", "web"]
    assert output == {
        "passed": False,
        "errors": {role: "publication workflow did not succeed" for role in failing},
    }


@pytest.mark.parametrize("mismatch", ["role", "attempt", "signature", "source_ref"])
def test_pair_cannot_export_a_different_role_or_attempt(
    requested, monkeypatch, capsys, mismatch
):
    path, _ = requested

    def check(role, commit, run, attempt, *_):
        evidence = verified_evidence(role, commit, run, attempt)
        if role == "web":
            if mismatch == "role":
                evidence["registry_reference"] = evidence["registry_reference"].replace(
                    "cinevault-web", "cinevault-api"
                )
            elif mismatch == "attempt":
                evidence["provenance"]["workflow_attempt"] += 1
            elif mismatch == "signature":
                evidence["provenance"]["signature_verified"] = False
            else:
                evidence["provenance"]["source_ref"] = "refs/heads/main"
        return evidence

    monkeypatch.setattr(pair.release, "check", check)
    assert pair.main(["--manifest", str(path)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "passed": False,
        "errors": {"web": "returned evidence does not match the requested publication"},
    }


@pytest.mark.parametrize("invalid", ["missing", "boolean", "duplicate", "too_large"])
def test_invalid_pair_is_rejected_before_network(
    requested, monkeypatch, capsys, invalid
):
    path, entries = requested
    if invalid == "missing":
        entries.pop("web")
    if invalid == "boolean":
        entries["web"]["attempt"] = True
    raw = json.dumps(entries)
    if invalid == "duplicate":
        raw = raw[:-1] + ', "api": {}}'
    if invalid == "too_large":
        raw += " " * pair.MAX_MANIFEST_BYTES
    path.write_text(raw, encoding="utf-8")

    def unexpected(*_):
        pytest.fail("Malformed pair reached the publication verifier")

    monkeypatch.setattr(pair.release, "check", unexpected)
    assert pair.main(["--manifest", str(path)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["passed"] is False
    assert "compose_environment" not in output
    assert str(path) not in json.dumps(output)
