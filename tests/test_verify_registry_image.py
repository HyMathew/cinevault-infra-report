import hashlib
import io
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from scripts import verify_registry_image as registry

IMAGE = "application/vnd.oci.image.manifest.v1+json"
INDEX = "application/vnd.oci.image.index.v1+json"
CONFIG_TYPE = "application/vnd.oci.image.config.v1+json"
CONFIG = "sha256:" + "5" * 64
NAMESPACE = "example/cinevault-api"
TOKEN = "synthetic-anonymous-token"


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
