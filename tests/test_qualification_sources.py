import hashlib
import json
import subprocess

import pytest

from scripts import qualification_sources as gate

API = "a" * 40
WEB = "b" * 40


def test_manifest_matches_the_exact_bytes(tmp_path):
    manifest = tmp_path / "sources.json"
    raw = json.dumps({"api": API, "web": WEB}).encode()
    manifest.write_bytes(raw)
    assert gate.load_sources(manifest) == (
        {"api": API, "web": WEB},
        hashlib.sha256(raw).hexdigest(),
    )


@pytest.mark.parametrize(
    "raw",
    [
        '{"api":"main","web":"' + WEB + '"}',
        '{"api":"' + API + '","web":"' + API + '"}',
        '{"api":"' + API + '","api":"' + API + '","web":"' + WEB + '"}',
        '{"api":"' + API + '","web":"' + WEB + '","infra":"' + WEB + '"}',
        '{"api":"' + API + '"}',
        " " * 1025,
    ],
)
def test_manifest_rejects_missing_ambiguous_or_moving_inputs(tmp_path, raw):
    manifest = tmp_path / "sources.json"
    manifest.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError):
        gate.load_sources(manifest)


def test_source_receipt_refuses_dirty_wrong_and_nested_checkouts(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git = ["git", "-C", str(repo)]
    subprocess.run([*git, "init", "-q"], check=True)
    folder = repo / "app"
    folder.mkdir()
    source = folder / "file.txt"
    source.write_text("qualification\n", encoding="utf-8")
    subprocess.run([*git, "add", "app"], check=True)
    subprocess.run(
        [
            *git,
            "-c",
            "user.name=Qualification",
            "-c",
            "user.email=qualification@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Fixture",
        ],
        check=True,
    )
    commit = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
    assert gate.verify_checkout("api", repo, commit) == commit
    with pytest.raises(ValueError, match="checkout root"):
        gate.verify_checkout("api", folder, commit)
    with pytest.raises(ValueError, match="does not match"):
        gate.verify_checkout("api", repo, API)
    (folder / "new.txt").write_text("untracked", encoding="utf-8")
    with pytest.raises(ValueError, match="must be clean"):
        gate.verify_checkout("api", repo, commit)
