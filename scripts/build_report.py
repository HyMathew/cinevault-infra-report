"""Compile the report with pinned Typst, embedded fonts and a fixed release date."""

import argparse
import hashlib
import json
import os
import platform
import stat
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.15.1"
ASSETS = {
    "Windows": (
        "typst-x86_64-pc-windows-msvc.zip",
        "19ce3551153c2fe7ee9fa2f95208310c8f4d3209fedb699e0333faf8913f6736",
    ),
    "Linux": (
        "typst-x86_64-unknown-linux-musl.tar.xz",
        "a6d077d0a95eed5a2eba715b2dae06be954f624ccbf85758a03f389ded33118c",
    ),
}


def compiler(folder):
    name, digest = ASSETS[platform.system()]
    url = f"https://github.com/typst/typst/releases/download/v{VERSION}/{name}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "CineVaultRT0705-report"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(40 * 1024 * 1024 + 1)
    assert len(data) <= 40 * 1024 * 1024, "Unexpected compiler archive size"
    assert hashlib.sha256(data).hexdigest() == digest, (
        "Compiler archive digest mismatch"
    )
    archive = folder / name
    archive.write_bytes(data)
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive) as source:
            assert sum(item.file_size for item in source.infolist()) < 200 * 1024 * 1024
            for item in source.infolist():
                assert (folder / item.filename).resolve().is_relative_to(folder)
                assert not stat.S_ISLNK(item.external_attr >> 16)
            assert source.testzip() is None, "Compiler ZIP CRC mismatch"
            source.extractall(folder)
        return next(folder.glob("*/typst.exe"))
    with tarfile.open(archive) as source:
        assert sum(item.size for item in source.getmembers()) < 200 * 1024 * 1024
        for item in source.getmembers():
            assert (folder / item.name).resolve().is_relative_to(folder)
            assert item.isfile() or item.isdir(), "Unexpected compiler archive member"
        source.extractall(folder, filter="data")
    return next(folder.glob("*/typst"))


def compile_report(executable):
    version = subprocess.check_output([str(executable), "--version"], text=True).strip()
    assert version.startswith("typst " + VERSION + " "), "Unexpected Typst version"
    config = json.loads((ROOT / "report/build-config.json").read_text(encoding="utf-8"))
    output = ROOT / "report" / config["filename"]
    assert output.parent == ROOT / "report" and output.suffix == ".pdf"
    subprocess.run(
        [
            str(executable),
            "compile",
            "--ignore-system-fonts",
            "--creation-timestamp",
            str(config["source_date_epoch"]),
            "--root",
            str(ROOT),
            "--input",
            "status=" + config["status"],
            str(ROOT / "report/main.typ"),
            str(output),
        ],
        check=True,
        env={**os.environ, "SOURCE_DATE_EPOCH": str(config["source_date_epoch"])},
    )
    data = output.read_bytes()
    assert data.startswith(b"%PDF-") and data.rstrip().endswith(b"%%EOF")
    result = {
        "compiled_at_utc": datetime.now(UTC).isoformat(),
        "compiler": version,
        "system_fonts_ignored": True,
        "creation_timestamp_is_fixed_release_epoch": config["source_date_epoch"],
        "filename": output.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "platform": platform.system(),
        "scope": "Compilation only; visual inspection and final audit are separate gates.",
    }
    (ROOT / "report/build-receipt.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--typst", type=Path, help="Use a previously verified local Typst0.15.1"
    )
    args = parser.parse_args()
    if args.typst:
        compile_report(args.typst.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="cinevault-typst-") as directory:
            compile_report(compiler(Path(directory).resolve()))


if __name__ == "__main__":
    main()
