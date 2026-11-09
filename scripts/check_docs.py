"""Offline checks of published document structure and local links, not runtime QA."""

import json
import re
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def main():
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
    for path in diagrams:
        assert ElementTree.parse(path).getroot().tag.endswith("svg"), path.name
    chapters = json.loads((ROOT / "report/chapters.json").read_text(encoding="utf-8"))
    assert len(chapters) == len({item["id"] for item in chapters}) == 30
    assert all(item["title"] and all(item["paragraphs"]) for item in chapters)
    print(
        f"PASS: {len(documents)} Markdown documents, {len(diagrams)} SVG roots, "
        "30 nonempty report chapters. PDF compilation/visual QA is a separate gate."
    )


if __name__ == "__main__":
    main()
