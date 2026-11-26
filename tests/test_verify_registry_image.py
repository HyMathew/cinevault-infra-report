import hashlib
import io
import json
import subprocess
from urllib.parse import parse_qs, urlsplit

import pytest

from scripts import verify_registry_image as registry

IMAGE = "application/vnd.oci.image.manifest.v1+json"
INDEX = "application/vnd.oci.image.index.v1+json"
CONFIG_TYPE = "application/vnd.oci.image.config.v1+json"
CONFIG = "sha256:" + "5" * 64
NAMESPACE = "example/cinevault-api"
TOKEN = "synthetic-anonymous-token"
OFFICIAL = "ghcr.io/hymathew/cinevault-api"
REPOSITORY = "HyMathew/cinevault-api"
REVISION = "1" * 40
SUBJECT = "c" * 64
SOURCE = registry.QUALIFICATION_REF
RUN = 12345
WORKFLOW = ".github/workflows/tests.yml"
REFERENCE = f"{OFFICIAL}@sha256:{SUBJECT}"


def document(value):
    raw = json.dumps(value, separators=(",", ":")).encode()
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    return raw, digest


def manifest_data(*, config=CONFIG):
    return document(
        {
            "schemaVersion": 2,
            "mediaType": IMAGE,
            "config": {"digest": config, "mediaType": CONFIG_TYPE, "size": 321},
            "layers": [{"digest": "sha256:" + "8" * 64, "size": 1234}],
        }
    )


class RegistryFixture:
    def __init__(self, manifests):
        self.manifests = manifests
        self.requests = []

    def open(self, request, *, timeout):
        url = urlsplit(request.full_url)
        assert timeout == 15 and url.scheme == "https" and url.netloc == "ghcr.io"
        self.requests.append(url.path)
        if url.path == "/token":
            assert request.get_header("Authorization") is None
            assert parse_qs(url.query) == {
                "scope": [f"repository:{NAMESPACE}:pull"],
                "service": ["ghcr.io"],
            }
            response = io.BytesIO(json.dumps({"token": TOKEN}).encode())
            response.headers = {}
        else:
            assert request.get_header("Authorization") == "Bearer " + TOKEN
            digest = url.path.rsplit("/", 1)[-1]
            assert url.path == f"/v2/{NAMESPACE}/manifests/{digest}" and not url.query
            kind, raw = self.manifests[digest]
            response = io.BytesIO(raw)
            response.headers = {"Content-Type": kind, "Docker-Content-Digest": digest}
        return response


def reference(digest):
    return f"ghcr.io/{NAMESPACE}@{digest}"


def test_manifest_identity_depends_on_exact_body_and_configuration():
    raw, digest = manifest_data()
    fixture = RegistryFixture({digest: (IMAGE, raw)})
    result = registry.verify(reference(digest), CONFIG, opener=fixture)
    assert (
        result["registry_subject_digest"]
        == result["registry_platform_manifest_digest"]
        == digest
    )
    assert (
        result["registry_config_digest"] == CONFIG and result["layer_descriptors"] == 1
    )
    assert result["platform_selected_from_index"] is None
    with pytest.raises(
        registry.RegistryVerificationError, match="configuration differs"
    ):
        registry.verify(reference(digest), "sha256:" + "1" * 64, opener=fixture)
    with pytest.raises(
        registry.RegistryVerificationError, match="scanned OCI manifest"
    ):
        registry.verify(reference(digest), CONFIG, "sha256:" + "3" * 64, opener=fixture)
    fixture.manifests[digest] = IMAGE, raw + b"\n"
    with pytest.raises(registry.RegistryVerificationError, match="manifest bytes"):
        registry.verify(reference(digest), CONFIG, opener=fixture)


def test_index_must_resolve_one_linux_amd64_manifest_by_digest():
    raw, child = manifest_data()
    linux = {
        "digest": child,
        "size": len(raw),
        "mediaType": IMAGE,
        "platform": {"os": "linux", "architecture": "amd64"},
    }
    arm = {**linux, "platform": {"os": "linux", "architecture": "arm64"}}
    index, top = document(
        {"schemaVersion": 2, "mediaType": INDEX, "manifests": [arm, linux]}
    )
    fixture = RegistryFixture({top: (INDEX, index), child: (IMAGE, raw)})
    result = registry.verify(reference(top), CONFIG, child, opener=fixture)
    assert result["registry_subject_digest"] == top
    assert result["registry_platform_manifest_digest"] == child
    assert result["platform_selected_from_index"] == "linux/amd64"
    assert len(fixture.requests) == 3
    bad, ambiguous = document(
        {"schemaVersion": 2, "mediaType": INDEX, "manifests": [linux, linux]}
    )
    fixture.manifests[ambiguous] = INDEX, bad
    with pytest.raises(registry.RegistryVerificationError, match="no unique"):
        registry.verify(reference(ambiguous), CONFIG, opener=fixture)
    bad, wrong_size = document(
        {"schemaVersion": 2, "mediaType": INDEX, "manifests": [{**linux, "size": 1}]}
    )
    fixture.manifests[wrong_size] = INDEX, bad
    with pytest.raises(registry.RegistryVerificationError, match="disagrees"):
        registry.verify(reference(wrong_size), CONFIG, opener=fixture)


@pytest.mark.parametrize(
    "ref",
    [
        "ghcr.io/example/cinevault-api:latest",
        "ghcr.io.evil.invalid/example/cinevault-api@sha256:" + "0" * 64,
        "https://ghcr.io/example/cinevault-api@sha256:" + "0" * 64,
    ],
)
def test_mutable_or_non_ghcr_reference_never_connects(ref):
    fixture = RegistryFixture({})
    with pytest.raises(registry.RegistryVerificationError, match="immutable GHCR"):
        registry.verify(ref, CONFIG, opener=fixture)
    assert not fixture.requests


def candidate_result(*, certificate=None, subject=None):
    uri = "https://github.com/" + REPOSITORY
    return {
        "verificationResult": {
            "signature": {
                "certificate": {
                    "sourceRepositoryURI": uri,
                    "sourceRepositoryRef": SOURCE,
                    "sourceRepositoryDigest": REVISION,
                    "buildSignerURI": f"{uri}/{WORKFLOW}@{SOURCE}",
                    "buildSignerDigest": REVISION,
                    "issuer": registry.ISSUER,
                    "runnerEnvironment": "github-hosted",
                    "runInvocationURI": f"{uri}/actions/runs/{RUN}/attempts/2",
                    **(certificate or {}),
                }
            },
            "statement": {
                "predicateType": registry.PREDICATE,
                "subject": [
                    {"name": OFFICIAL, "digest": {"sha256": subject or SUBJECT}}
                ],
            },
            "verifiedTimestamps": [{}],
        }
    }


def test_cli_binds_the_crypto_verifier_to_the_exact_subject_and_source(
    monkeypatch, capsys
):
    def gh_command(args, **options):
        assert args[:4] == ["gh", "attestation", "verify", f"oci://{REFERENCE}"]
        assert args[args.index("--repo") + 1] == REPOSITORY
        assert args[args.index("--signer-workflow") + 1] == f"{REPOSITORY}/{WORKFLOW}"
        assert args[args.index("--signer-digest") + 1] == REVISION
        assert args[args.index("--source-digest") + 1] == REVISION
        assert args[args.index("--source-ref") + 1] == SOURCE
        assert args[args.index("--predicate-type") + 1] == registry.PREDICATE
        assert "--deny-self-hosted-runners" in args
        assert options["env"]["GH_PROMPT_DISABLED"] == "1"
        assert options["stdin"] == subprocess.DEVNULL and options["timeout"] <= 90
        return subprocess.CompletedProcess(
            args, 0, json.dumps([candidate_result()]).encode(), b""
        )

    monkeypatch.setattr(registry.subprocess, "run", gh_command)
    monkeypatch.setattr(registry, "verify", lambda *_: {"passed": True})
    args = [
        "--reference",
        REFERENCE,
        "--config-digest",
        CONFIG,
        "--platform-manifest-digest",
        "sha256:" + SUBJECT,
        "--source-commit",
        REVISION,
        "--source-ref",
        SOURCE,
        "--run-id",
        str(RUN),
    ]
    assert registry.main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["provenance"] == {
        "signature_verified": True,
        "source_commit": REVISION,
        "source_ref": SOURCE,
        "workflow": f"{REPOSITORY}/{WORKFLOW}",
        "workflow_run": RUN,
        "workflow_attempt": 2,
    }


@pytest.mark.parametrize(
    "row",
    [
        candidate_result(
            certificate={
                "runInvocationURI": "https://github.com/HyMathew/cinevault-api/actions/runs/1/attempts/2"
            }
        ),
        candidate_result(certificate={"buildSignerURI": "elsewhere"}),
        candidate_result(certificate={"runnerEnvironment": "self-hosted"}),
        candidate_result(certificate={"sourceRepositoryDigest": "0" * 40}),
        candidate_result(subject="9" * 64),
    ],
)
def test_verified_but_wrong_signature_identity_is_rejected(monkeypatch, row):
    monkeypatch.setattr(registry, "attest", lambda *_: [row])
    with pytest.raises(registry.RegistryVerificationError, match="workflow run"):
        registry.verify_attestation(REFERENCE, REVISION, SOURCE, RUN)


def test_failed_cryptographic_verification_cannot_return_a_success_receipt(
    monkeypatch, capsys
):
    result = subprocess.CompletedProcess(
        [], 1, json.dumps([candidate_result()]).encode(), b"PRIVATE_STDERR"
    )
    monkeypatch.setattr(registry.subprocess, "run", lambda *_args, **_options: result)
    monkeypatch.setattr(registry, "verify", lambda *_: {"passed": True})
    assert (
        registry.main(
            [
                "--reference",
                REFERENCE,
                "--config-digest",
                CONFIG,
                "--platform-manifest-digest",
                "sha256:" + SUBJECT,
                "--source-commit",
                REVISION,
                "--source-ref",
                SOURCE,
                "--run-id",
                str(RUN),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert not captured.err and "PRIVATE_STDERR" not in captured.out
    assert not json.loads(captured.out)["passed"]


def test_partial_provenance_arguments_fail_before_registry(monkeypatch, capsys):
    monkeypatch.setattr(registry, "verify", lambda *_: pytest.fail("network contacted"))
    assert (
        registry.main(
            [
                "--reference",
                REFERENCE,
                "--config-digest",
                CONFIG,
                "--source-commit",
                REVISION,
            ]
        )
        == 1
    )
    assert not json.loads(capsys.readouterr().out)["passed"]


def test_provenance_requires_scanned_platform_before_registry(monkeypatch, capsys):
    monkeypatch.setattr(registry, "verify", lambda *_: pytest.fail("network contacted"))
    args = [
        "--reference",
        REFERENCE,
        "--config-digest",
        CONFIG,
        "--source-commit",
        REVISION,
        "--source-ref",
        SOURCE,
        "--run-id",
        str(RUN),
    ]
    assert registry.main(args) == 1
    assert "scanned platform manifest digest is required" in capsys.readouterr().out
