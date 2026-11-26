"""Exercise the join between Actions artifacts, the scanner and release provenance."""

import base64
import json
import zipfile

import pytest

from scripts import check_staging_image_release as release

REPO = "HyMathew/cinevault-api"
COMMIT = "a" * 40
RUN, ATTEMPT = 12345, 2
PLATFORM = "sha256:" + "c" * 64


@pytest.fixture
def metadata(monkeypatch):
    run = {
        "id": RUN,
        "run_attempt": ATTEMPT,
        "repository": {"full_name": REPO},
        "head_repository": {"full_name": REPO},
        "head_sha": COMMIT,
        "head_branch": release.REF,
        "path": ".github/workflows/tests.yml",
        "event": "workflow_dispatch",
        "status": "completed",
        "conclusion": "success",
    }
    jobs = [
        {
            "name": name,
            "run_id": RUN,
            "run_attempt": ATTEMPT,
            "status": "completed",
            "conclusion": "success",
            "started_at": "2026-11-26T12:00:00Z",
            "completed_at": "2026-11-26T12:03:00Z",
        }
        for name in release.ARCHIVES.values()
    ]
    artifacts = [
        {
            "id": idx,
            "name": name,
            "expired": False,
            "workflow_run": {"id": RUN, "head_sha": COMMIT},
            "created_at": "2026-11-26T12:02:00Z",
            "size_in_bytes": 100,
            "digest": "sha256:" + "b" * 64,
        }
        for idx, name in enumerate(release.ARCHIVES, 10)
    ]
    base = f"repos/{REPO}/actions/runs/{RUN}"
    responses = {
        base: run,
        f"{base}/attempts/{ATTEMPT}/jobs?per_page=100": {
            "jobs": jobs,
            "total_count": len(jobs),
        },
        f"{base}/artifacts?per_page=100": {
            "artifacts": artifacts,
            "total_count": len(artifacts),
        },
    }
    monkeypatch.setattr(release, "gh_api", responses.__getitem__)
    return run, jobs, artifacts


def test_selects_only_artifacts_produced_in_the_requested_attempt(metadata):
    _, _, artifacts = metadata
    assert set(release.release_metadata(REPO, RUN, ATTEMPT, COMMIT)) == set(
        release.ARCHIVES
    )
    artifacts[0]["created_at"] = "2026-11-25T12:02:00Z"
    with pytest.raises(ValueError, match="requested attempt"):
        release.release_metadata(REPO, RUN, ATTEMPT, COMMIT)


@pytest.mark.parametrize(("field", "value"), [("event", "push"), ("run_attempt", 1)])
def test_rejects_a_different_workflow_or_attempt(metadata, field, value):
    run, _, _ = metadata
    run[field] = value
    with pytest.raises(ValueError, match="workflow identity"):
        release.release_metadata(REPO, RUN, ATTEMPT, COMMIT)


def archive(tmp_path, *, kind, severity=None, tampered=False):
    def raw(value):
        return json.dumps(value, sort_keys=True).encode()

    config_bytes = raw({"rootfs": {"diff_ids": ["sha256:" + "e" * 64]}})
    config = release.sha(config_bytes)
    manifest = raw({"config": {"digest": config, "size": len(config_bytes)}})
    metadata = {
        "config": base64.b64encode(config_bytes).decode(),
        "manifest": base64.b64encode(manifest).decode(),
        "imageID": config,
    }
    raw_grype = raw(
        {
            "source": {"target": metadata},
            "matches": []
            if severity is None
            else [{"vulnerability": {"severity": severity}}],
        }
    )
    raw_syft = raw({"source": {"metadata": metadata}, "artifacts": ["fixture"]})
    identity = config if kind == "docker-config" else PLATFORM
    proof = {
        "archive_identity_kind": kind,
        "archive_config_digest": config,
        "archive_oci_manifest_digest": None if kind == "docker-config" else PLATFORM,
        "archive_sha256": "sha256:" + "f" * 64,
        "docker_image_id": identity,
        "grype_config_digest": config,
        "sbom_config_digest": config,
        "scan_report_sha256": release.sha(raw_grype),
        "sbom_sha256": release.sha(raw_syft),
        "grype_manifest_digest": release.sha(manifest),
        "sbom_manifest_digest": release.sha(manifest),
        "sbom_components": 1,
    }
    folder = "image-" + "b" * 32
    reference = "ghcr.io/hymathew/cinevault-api@" + PLATFORM
    audit = {
        "attempt_directory": folder,
        "scan_passed": True,
        "scanner_exit_code": 0,
        "health_passed": True,
        "cleanup_passed": True,
        "runtime_uid": 10001,
        "image_id": identity,
        "image": "cinevault-api:ci-" + COMMIT,
        "scan_provenance": proof,
        "severity_counts": {} if severity is None else {severity: 1},
        "build_provenance": {
            "source_commit": COMMIT,
            "config_digest": config,
            "manifest_digest": PLATFORM,
            "source_tar_digest": "sha256:" + "a" * 64,
        },
    }
    publication = {
        "repository": REPO,
        "published": True,
        "source_commit": COMMIT,
        "digest": PLATFORM,
        "registry_ref": reference,
        "tag": "ghcr.io/hymathew/cinevault-api:sha-" + COMMIT,
        "publication_channel": "candidate",
        "image_id": identity,
        "scan_provenance": proof,
    }
    path = tmp_path / "audit.zip"
    with zipfile.ZipFile(path, "w") as zipped:
        zipped.writestr("image-check.json", raw(audit))
        zipped.writestr("registry-publication.json", raw(publication))
        zipped.writestr(
            folder + "/build-metadata.json", raw({"containerimage.digest": PLATFORM})
        )
        zipped.writestr(folder + "/image-vulnerabilities.json", raw_grype)
        zipped.writestr(
            folder + "/image-sbom.json", raw_syft + b" " if tampered else raw_syft
        )
    return path, reference, config


@pytest.mark.parametrize(
    ("kind", "platform"), [("docker-config", None), ("oci-manifest", PLATFORM)]
)
def test_binds_build_scan_catalogue_and_publication(tmp_path, kind, platform):
    path, reference, config = archive(tmp_path, kind=kind)
    with zipfile.ZipFile(path) as zipped:
        assert release.inspect_audit(zipped, REPO, COMMIT) == (
            reference,
            config,
            platform,
            PLATFORM,
        )


@pytest.mark.parametrize("severity", ["High", "Critical"])
def test_rejects_a_red_scan_even_if_the_audit_claims_success(tmp_path, severity):
    path, _, _ = archive(tmp_path, kind="oci-manifest", severity=severity)
    with (
        zipfile.ZipFile(path) as zipped,
        pytest.raises(ValueError, match="vulnerability gate"),
    ):
        release.inspect_audit(zipped, REPO, COMMIT)


def test_rejects_changed_sbom_and_artifact_bytes(tmp_path):
    path, _, _ = archive(tmp_path, kind="oci-manifest", tampered=True)
    with (
        zipfile.ZipFile(path) as zipped,
        pytest.raises(ValueError, match="SBOM checksum"),
    ):
        release.inspect_audit(zipped, REPO, COMMIT)
    with pytest.raises(ValueError, match="GitHub size and SHA-256"):
        release.read_artifact(
            path, {"size_in_bytes": path.stat().st_size, "digest": PLATFORM}
        )


def test_registry_and_live_attestation_follow_the_exact_local_attempt(
    monkeypatch, tmp_path, metadata
):
    _, _, artifacts = metadata
    audited, reference, config = archive(tmp_path, kind="oci-manifest")
    proof = tmp_path / "provenance.zip"
    ref = "refs/heads/" + release.REF
    name, value = reference.split("@sha256:")
    repo_url = "https://github.com/" + REPO
    signer = {
        "sourceRepositoryURI": repo_url,
        "sourceRepositoryRef": ref,
        "sourceRepositoryDigest": COMMIT,
        "buildSignerURI": f"{repo_url}/.github/workflows/tests.yml@{ref}",
        "buildSignerDigest": COMMIT,
        "issuer": release.registry.ISSUER,
        "runnerEnvironment": "github-hosted",
        "runInvocationURI": f"{repo_url}/actions/runs/{RUN}/attempts/{ATTEMPT}",
    }
    row = {
        "verificationResult": {
            "signature": {"certificate": signer},
            "verifiedTimestamps": [True],
            "statement": {
                "predicateType": release.registry.PREDICATE,
                "subject": [{"name": name, "digest": {"sha256": value}}],
            },
        }
    }

    def save_proof():
        with zipfile.ZipFile(proof, "w") as zipped:
            zipped.writestr("image-attestation-verification.json", json.dumps([row]))
        for path, artifact in zip((audited, proof), artifacts, strict=True):
            artifact.update(
                size_in_bytes=path.stat().st_size, digest=release.sha(path.read_bytes())
            )

    save_proof()
    called = []

    def registry_manifest(used, image_config, platform):
        called.append("manifest")
        assert (used, image_config, platform) == (reference, config, PLATFORM)
        return {"passed": True, "registry_reference": used}

    def attestation(used, commit, source_ref, run, *, expected_attempt):
        called.append("attestation")
        assert (used, commit, source_ref, run, expected_attempt) == (
            reference,
            COMMIT,
            ref,
            RUN,
            ATTEMPT,
        )
        return {"signature_verified": True, "workflow_attempt": expected_attempt}

    monkeypatch.setattr(release.registry, "verify", registry_manifest)
    monkeypatch.setattr(release.registry, "verify_attestation", attestation)
    evidence = release.check("api", COMMIT, RUN, ATTEMPT, audited, proof)
    assert evidence["passed"] and evidence["provenance"]["workflow_attempt"] == ATTEMPT
    assert called == ["manifest", "attestation"]
    called.clear()
    signer["runInvocationURI"] = f"{repo_url}/actions/runs/{RUN}/attempts/1"
    save_proof()
    with pytest.raises(ValueError, match="verified provenance"):
        release.check("api", COMMIT, RUN, ATTEMPT, audited, proof)
    assert called == []
