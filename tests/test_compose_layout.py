"""Verify the local Compose modes using Docker's actual interpolation."""

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
KEY_FILES = {
    "CINEVAULT_AUTH_KEY_FILE": "fixture-auth",
    "CINEVAULT_WEB_KEY_FILE": "fixture-web",
    "CINEVAULT_CLIENT_CONTEXT_KEY_FILE": "fixture-context",
}


def compose(variables, *, enterprise=False):
    args = ["docker", "compose", "--env-file", os.devnull, "-f", "compose.yaml"]
    if enterprise:
        args += ["-f", "compose.enterprise.yaml"]
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"SECRET_KEY", "COOKIE_SECURE", *KEY_FILES}
    }
    return subprocess.run(
        [*args, "config", "--format", "json", "--no-path-resolution"],
        cwd=ROOT,
        env={**env, **variables},
        capture_output=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )


def test_academic_compose_preserves_key_and_loopback_boundary():
    result = compose({"SECRET_KEY": "fixture-key"})
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)["services"]
    api, web = config["cinevault-api"], config["cinevault-web"]
    assert web["environment"]["SECRET_KEY"] == "fixture-key"
    assert web["environment"]["COOKIE_SECURE"] == "false"
    assert not api.get("ports")
    assert [(p["host_ip"], p["published"], p["target"]) for p in web["ports"]] == [
        ("127.0.0.1", "8080", 5000)
    ]


def test_enterprise_compose_uses_only_file_secrets_without_environment_key():
    result = compose(KEY_FILES, enterprise=True)
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    api, web = (config["services"][name] for name in ("cinevault-api", "cinevault-web"))
    assert api["environment"]["STORAGE_BACKEND"] == "json"
    assert api["environment"]["ENTERPRISE_DATA_FILE"] == "/data/enterprise.json"
    assert web["environment"]["SECRET_KEY"] == ""
    assert web["environment"]["SECRET_KEY_FILE"] == "/run/secrets/web_session"
    assert {secret["source"] for secret in web["secrets"]} == {
        "web_session",
        "client_context",
    }
    assert {secret["source"] for secret in api["secrets"]} == {
        "auth_throttle",
        "client_context",
    }
    assert {secret["file"] for secret in config["secrets"].values()} == set(
        KEY_FILES.values()
    )
    assert not api.get("ports")


@pytest.mark.parametrize("missing_key", KEY_FILES)
def test_enterprise_compose_requires_each_file_path_even_with_a_legacy_key(missing_key):
    variables = {key: value for key, value in KEY_FILES.items() if key != missing_key}
    result = compose({**variables, "SECRET_KEY": "fixture-key"}, enterprise=True)
    assert result.returncode != 0
    assert missing_key in result.stderr
