"""Install reviewed release archives without executing a downloaded installer."""

import argparse
import hashlib
import json
import os
import platform
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from .security import (
    initialize_directory,
    private_path,
    require,
    unlinked_path,
    write_private,
)

LOCK = Path(__file__).with_name("upstream.lock.json")


def extract_verified(archive, spec, destination):
    with Path(archive).open("rb") as stream:
        require(
            hashlib.file_digest(stream, "sha256").hexdigest() == spec["sha256"],
            "upstream_archive_digest_mismatch",
        )
    # Digests are pinned in reviewed source, never obtained from the same request
    # as the executable at installation time. Only named regular files are read.
    destination = initialize_directory(destination)
    is_zip = str(archive).endswith(".zip")
    with (
        zipfile.ZipFile(archive) if is_zip else tarfile.open(archive, "r:gz") as package
    ):
        for filename, entry in spec["binaries"].items():
            require(
                Path(filename).name == filename and filename not in {".", ".."},
                "invalid_locked_filename",
            )
            if is_zip:
                info = package.getinfo(entry["member"])
                require(
                    not info.is_dir() and info.file_size < 128 * 1024 * 1024,
                    "invalid_archive_member",
                )
                data = package.read(info)
            else:
                info = package.getmember(entry["member"])
                require(
                    info.isfile() and info.size < 128 * 1024 * 1024,
                    "invalid_archive_member",
                )
                with package.extractfile(info) as stream:
                    data = stream.read()
            require(
                hashlib.sha256(data).hexdigest() == entry["sha256"],
                "upstream_binary_digest_mismatch",
            )
            target = write_private(destination / filename, data)
            if os.name != "nt":
                target.chmod(0o700)
        # Preserve publisher licenses, SBOMs and analysis reports alongside tools.
        names = (
            package.namelist()
            if is_zip
            else [info.name for info in package.getmembers() if info.isfile()]
        )
        for name in names:
            filename = Path(name).name
            if not (
                filename.lower().startswith(("license", "notice", "third-party"))
                or filename.endswith((".cdx.json", ".sast.json", ".sarif.json"))
            ):
                continue
            if is_zip:
                require(
                    package.getinfo(name).file_size < 32 * 1024 * 1024,
                    "upstream_notice_too_large",
                )
                data = package.read(name)
            else:
                info = package.getmember(name)
                require(
                    info.isfile() and info.size < 32 * 1024 * 1024,
                    "upstream_notice_too_large",
                )
                with package.extractfile(info) as stream:
                    data = stream.read()
            write_private(destination / filename, data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument(
        "--archive-directory", type=Path, help="Optional offline release-archive cache"
    )
    args = parser.parse_args(argv)
    try:
        require(
            platform.machine().lower() in {"amd64", "x86_64"}
            and platform.system() in {"Windows", "Linux"},
            "only_windows_x64_ubuntu2404_x64_qualified",
        )
        system = "windows" if os.name == "nt" else "linux"
        names = {
            "age-" + system,
            "mongo-windows" if os.name == "nt" else "mongo-ubuntu2404",
        }
        entries = [
            entry
            for entry in json.loads(LOCK.read_text())["archives"]
            if entry["label"] in names
        ]
        require(len(entries) == 2, "upstream_lock_incomplete")
        work = private_path(args.work_dir, directory=True)
        require(
            not unlinked_path(args.destination).exists(),
            "new_install_destination_required",
        )
        with tempfile.TemporaryDirectory(prefix="cvmb-install-", dir=work) as directory:
            sources = []
            for entry in entries:
                filename = entry["url"].rsplit("/", 1)[1]
                path = (
                    unlinked_path(args.archive_directory / filename)
                    if args.archive_directory
                    else Path(directory) / filename
                )
                if not args.archive_directory:
                    with (
                        urllib.request.urlopen(entry["url"], timeout=30) as response,
                        path.open("xb") as output,
                    ):
                        count = 0
                        while data := response.read(65536):
                            count += len(data)
                            require(
                                count <= 512 * 1024 * 1024,
                                "upstream_download_too_large",
                            )
                            output.write(data)
                with path.open("rb") as stream:
                    require(
                        hashlib.file_digest(stream, "sha256").hexdigest()
                        == entry["sha256"],
                        "upstream_archive_digest_mismatch",
                    )
                sources.append((entry, path))
            destination = initialize_directory(args.destination)
            for entry, path in sources:
                extract_verified(
                    path,
                    entry,
                    destination
                    / ("age" if entry["label"].startswith("age-") else "mongodb"),
                )
        print(
            json.dumps(
                {
                    "status": "PINNED_RELEASES_INSTALLED",
                    "age": "1.3.2",
                    "mongodb_tools": "100.20.0",
                }
            )
        )
        return 0
    except Exception:  # noqa: BLE001 - do not print upstream paths or tool output.
        print(
            "Installation refused or failed; inspect versions, archive digests and new destination."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
