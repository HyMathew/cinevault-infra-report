"""Check the HTTPS staging overlay without deploying a stack."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None, reason="Docker CLI is required"
)
ROOT = Path(__file__).resolve().parents[1]
BASE = ["stack.mongodb-staging.yaml"]
TLS = [*BASE, "stack.mongodb-staging.https.yaml"]


def sample_images():
    return {
        "CINEVAULT_STAGE_API_IMAGE": "ghcr.io/hymathew/cinevault-api@sha256:"
        + "a" * 64,
        "CINEVAULT_STAGE_WEB_IMAGE": "ghcr.io/hymathew/cinevault-web@sha256:"
        + "b" * 64,
        "CINEVAULT_STAGE_MONGO_IMAGE": "cinevault-mongo-local:staging-fixture",
        "CINEVAULT_STAGE_PROXY_IMAGE": "docker.io/library/caddy@sha256:" + "c" * 64,
    }


def docker(args, overrides):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("CINEVAULT_STAGE_")
    }
    return subprocess.run(
        ["docker", *args],
        cwd=ROOT,
        env={**env, **overrides},
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def file_flags(flag, sources):
    return [arg for source in sources for arg in (flag, source)]


def render(files, overrides):
    stacked = docker(["stack", "config", *file_flags("-c", files)], overrides)
    assert stacked.returncode == 0, stacked.stderr
    composed = docker(
        [
            "compose",
            *file_flags("-f", files),
            "config",
            "--format",
            "json",
            "--no-path-resolution",
        ],
        overrides,
    )
    assert composed.returncode == 0, composed.stderr
    return json.loads(composed.stdout)


@pytest.mark.parametrize("replicas", [0, 1])
def test_https_variant_preserves_network_and_secret_boundaries(replicas):
    variables = {**sample_images(), "CINEVAULT_STAGE_APP_REPLICAS": str(replicas)}
    config = render(TLS, variables)
    services = config["services"]
    assert set(services) == {"api", "mongo", "web", "https"}
    assert {name: set(service["networks"]) for name, service in services.items()} == {
        "web": {"front", "edge"},
        "api": {"front", "data"},
        "mongo": {"data"},
        "https": {"edge"},
    }
    for name in ("front", "data", "edge"):
        network = config["networks"][name]
        assert network["driver"] == "overlay"
        assert network["internal"]
        assert network["driver_opts"] == {"encrypted": ""}
    assert not config["networks"]["edge"].get("attachable")
    assert all(not service.get("ports") for service in services.values())
    assert services["web"]["environment"]["COOKIE_SECURE"] == "true"
    assert services["mongo"]["deploy"]["replicas"] == 1
    assert all(
        services[role]["deploy"]["replicas"] == replicas
        for role in ("web", "api", "https")
    )

    https = services["https"]
    assert https["image"] == variables["CINEVAULT_STAGE_PROXY_IMAGE"]
    assert https["user"] == "10001:10001"
    assert https["read_only"] and https["cap_drop"] == ["ALL"]
    assert https["deploy"]["placement"]["constraints"] == [
        "node.labels.cinevault == web"
    ]
    assert {secret["source"] for secret in https["secrets"]} == {
        "https_cert",
        "https_key",
    }
    for secret in https["secrets"]:
        assert secret["source"] == secret["target"]
        assert secret["uid"] == secret["gid"] == "10001"
        assert str(secret["mode"]) in {"0400", "256"}
        resolved_secret = config["secrets"][secret["source"]]
        assert resolved_secret["external"] is True
        assert resolved_secret["name"] == f"cvstage_{secret['source']}_v1"
    assert all(
        not any(
            secret["source"].startswith("https_")
            for secret in services[role]["secrets"]
        )
        for role in ("mongo", "api", "web")
    )


def test_base_variant_keeps_private_http_and_needs_no_proxy():
    variables = sample_images()
    variables.pop("CINEVAULT_STAGE_PROXY_IMAGE")
    services = render(BASE, variables)["services"]
    assert set(services) == {"api", "mongo", "web"}
    assert services["web"]["environment"]["COOKIE_SECURE"] == "false"
    assert services["web"]["deploy"]["replicas"] == 0
    missing = docker(["stack", "config", *file_flags("-c", TLS)], variables)
    assert missing.returncode != 0 and "CINEVAULT_STAGE_PROXY_IMAGE" in missing.stderr
