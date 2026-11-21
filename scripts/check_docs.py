"""Offline checks of published document structure and local links, not runtime QA."""

import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def check_pedagogical_evidence():
    folder = ROOT / "evidence/academic-20261109"
    manifest = json.loads((folder / "manifest.json").read_bytes())
    files = manifest["files"]
    assert set(files) == {
        "exercice-a.jpg",
        "exercice-b-formulaire.jpg",
        "exercice-c-fiche.jpg",
        "browser-json-chain.json",
        "vscode-api.jpg",
        "vscode-web.jpg",
    }
    for name, expected in files.items():
        source = folder / name
        assert source.is_file() and not source.is_symlink(), name
        content = source.read_bytes()
        assert (len(content), hashlib.sha256(content).hexdigest()) == (
            expected["bytes"],
            expected["sha256"],
        ), f"Published evidence differs from its manifest: {name}"


def main():
    check_pedagogical_evidence()
    documents = []
    for directory in (ROOT, ROOT / "docs", ROOT / "report", ROOT / "evidence"):
        files = directory.glob("*.md") if directory == ROOT else directory.rglob("*.md")
        documents.extend(
            path
            for path in files
            if not {".render-tools", "superpowers"}.intersection(path.parts)
        )
    for path in documents:
        content = path.read_text(encoding="utf-8")
        assert "\0" not in content, f"NUL in {path.relative_to(ROOT)}"
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", content):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if target:
                resolved = (path.parent / target).resolve()
                assert resolved.is_relative_to(ROOT), (
                    f"Out-of-repository link: {target}"
                )
                assert resolved.exists(), f"Missing local link: {target} in {path.name}"
    diagrams = list((ROOT / "docs").glob("*diagrams/*.svg"))
    diagrams.extend((ROOT / "report/enterprise-2.1/figures").glob("*.svg"))
    for path in diagrams:
        assert ElementTree.parse(path).getroot().tag.endswith("svg"), path.name
    chapters = json.loads((ROOT / "report/chapters.json").read_text(encoding="utf-8"))
    assert len(chapters) == len({item["id"] for item in chapters}) == 30
    assert all(item["title"] and all(item["paragraphs"]) for item in chapters)
    updated = json.loads(
        (ROOT / "report/enterprise-2.1/chapters.json").read_text(encoding="utf-8")
    )
    original_ids = [item["id"] for item in chapters]
    updated_ids = [item["id"] for item in updated]
    assert [
        identity for identity in updated_ids if identity in original_ids
    ] == original_ids
    assert set(updated_ids) - set(original_ids) == {
        "mongo",
        "migration",
        "operations",
        "performance",
    }
    assert len(updated_ids) == len(set(updated_ids)) == 34
    assert all(
        item["title"].strip()
        and item["paragraphs"]
        and all(text.strip() for text in item["paragraphs"])
        for item in updated
    )
    print(
        f"PASS: {len(documents)} Markdown documents, {len(diagrams)} SVG roots, "
        "30 original report chapters and 34 for Enterprise 2.1. "
        "PDF compilation/visual QA is a separate gate."
    )


if __name__ == "__main__":
    main()
