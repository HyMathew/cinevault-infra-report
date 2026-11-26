"""Prepare reviewable Alpine OpenSSL lock files for the CineVault API and Web."""

import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, build_opener

REPOSITORY = "https://dl-cdn.alpinelinux.org/alpine/v3.24/main"
LOCK_DIR = "docker/alpine-runtime"
NAMES = ("libcrypto3", "libssl3")
PLATFORMS = {
    "aarch64": "linux/arm64",
    "armhf": "linux/arm/v6",
    "armv7": "linux/arm/v7",
    "ppc64le": "linux/ppc64le",
    "riscv64": "linux/riscv64",
    "s390x": "linux/s390x",
    "x86": "linux/386",
    "x86_64": "linux/amd64",
}
VERSION = r"[0-9]+\.[0-9]+\.[0-9]+-r[0-9]+"
ROW = re.compile(r"([0-9a-f]{64})  ([a-z0-9][a-z0-9_.+~-]+\.apk)")
IMAGE = re.compile(
    rb"^FROM (alpine:3\.24@sha256:[0-9a-f]{64})(?: AS [a-z-]+)?$", re.MULTILINE
)
VERIFY = "set -eu; cd /scratch; tar -xf -; apk verify libcrypto3.apk libssl3.apk"


class PlanError(ValueError):
    """Bounded diagnostic suitable for the operator."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def git(source, *args):
    return subprocess.run(
        ["git", "-C", str(source), *args], check=True, capture_output=True, timeout=20
    ).stdout


def snapshot(source):
    commit = (
        git(source, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
    )
    references = set(IMAGE.findall(git(source, "show", f"{commit}:Dockerfile")))
    if len(references) != 1:
        raise PlanError("expected_one_pinned_alpine_3_24_base")
    paths = git(source, "ls-tree", "-r", "--name-only", commit, "--", LOCK_DIR).decode(
        "ascii"
    )
    locks = {}
    for path in paths.splitlines():
        name = PurePosixPath(path)
        if (
            name.parent.as_posix() != LOCK_DIR
            or name.suffix != ".sha256"
            or name.stem not in PLATFORMS
        ):
            raise PlanError("unexpected_apk_lock_path")
        locks[name.stem] = git(source, "show", f"{commit}:{path}")
    if not locks:
        raise PlanError("apk_locks_missing")
    return commit, references.pop().decode("ascii"), locks


def download(arch, package):
    try:
        with build_opener(NoRedirect).open(
            f"{REPOSITORY}/{arch}/{package}", timeout=20
        ) as response:
            data = response.read(16 * 1024**2 + 1)
    except HTTPError as exc:
        raise PlanError(f"alpine_package_http_{exc.code}: {arch}/{package}") from None
    if not 0 < len(data) <= 16 * 1024**2:
        raise PlanError("invalid_apk_size")
    return data


def verify(docker, image, arch, packages):
    tape = io.BytesIO()
    with tarfile.open(fileobj=tape, mode="w") as archive:
        for name, raw in packages.items():
            entry = tarfile.TarInfo(name + ".apk")
            entry.size = len(raw)
            archive.addfile(entry, io.BytesIO(raw))
    result = subprocess.run(
        [
            *docker,
            "run",
            "--rm",
            "--pull",
            "missing",
            "--platform",
            PLATFORMS[arch],
            "-i",
            "--network",
            "none",
            "--read-only",
            "--user",
            "65534:65534",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--tmpfs",
            "/scratch:rw,noexec,nosuid,nodev,mode=1777,size=40m",
            image,
            "sh",
            "-ec",
            VERIFY,
        ],
        input=tape.getvalue(),
        capture_output=True,
        check=False,
        timeout=60,
    )
    if result.returncode or set(result.stdout.splitlines()) != {
        b"libcrypto3.apk: OK",
        b"libssl3.apk: OK",
    }:
        raise PlanError(f"alpine_signature_verification_failed: {arch}")


def check_metadata(raw, arch, name, version):
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        prefix = stream.read(256 * 1024)
    with tarfile.open(
        fileobj=io.BytesIO(prefix), mode="r|", ignore_zeros=True
    ) as archive:
        for entry in archive:
            if entry.name.removeprefix("./") != ".PKGINFO":
                continue
            if not entry.isfile() or not 0 < entry.size <= 16384:
                break
            fields = archive.extractfile(entry).read().decode("utf-8").splitlines()
            expected = (
                f"pkgname = {name}",
                f"pkgver = {version}",
                f"arch = {arch}",
                "origin = openssl",
            )
            if all(fields.count(item) == 1 for item in expected) and (
                name != "libssl3" or f"depend = libcrypto3={version}" in fields
            ):
                return
            break
    raise PlanError(f"alpine_metadata_mismatch: {arch}/{name}")


def refresh_lock(raw, planned):
    lines = raw.decode("ascii").splitlines()
    seen = set()
    filenames = set()
    for index, line in enumerate(lines):
        match = ROW.fullmatch(line)
        if not match or match[2] in filenames:
            raise PlanError("invalid_apk_lock")
        checksum, filename = match.groups()
        filenames.add(filename)
        for name, (expected_name, expected_hash) in planned.items():
            if not re.fullmatch(rf"{name}-{VERSION}\.apk", filename):
                continue
            if name in seen:
                raise PlanError("duplicate_openssl_version_in_lock")
            seen.add(name)
            if expected_name == filename and expected_hash != checksum:
                raise PlanError("locked_apk_bytes_changed")
            lines[index] = f"{expected_hash}  {expected_name}"
    if seen != set(NAMES):
        raise PlanError("openssl_libraries_missing_in_lock")
    return ("\n".join(lines) + "\n").encode("ascii")


def prepare(sources, version, docker, output):
    if not re.fullmatch(VERSION, version):
        raise PlanError("invalid_alpine_package_version")
    if output.exists() or output.is_symlink():
        raise PlanError("output_directory_already_exists")
    inputs = {role: snapshot(path) for role, path in sources.items()}
    images = {image for _, image, _ in inputs.values()}
    if len(images) != 1:
        raise PlanError("api_and_web_alpine_bases_differ")
    image = images.pop()
    arches = sorted({arch for _, _, locks in inputs.values() for arch in locks})

    def qualify(arch):
        names = {name: f"{name}-{version}.apk" for name in NAMES}
        packages = {name: download(arch, filename) for name, filename in names.items()}
        verify(docker, image, arch, packages)
        for name, raw in packages.items():
            check_metadata(raw, arch, name, version)
        return arch, {
            name: (names[name], hashlib.sha256(raw).hexdigest())
            for name, raw in packages.items()
        }

    with ThreadPoolExecutor(max_workers=3) as workers:
        planned = dict(workers.map(qualify, arches))
    proposed = {
        f"{role}/{LOCK_DIR}/{arch}.sha256": (
            previous,
            refresh_lock(previous, planned[arch]),
        )
        for role, (_, _, locks) in inputs.items()
        for arch, previous in sorted(locks.items())
    }
    result = {
        "status": "verified_lock_proposal",
        "version": version,
        "alpine_base": image,
        "source_repository": REPOSITORY,
        "source_commits": {role: data[0] for role, data in inputs.items()},
        "architectures": planned,
        "locks": {
            path: {"sha256": hashlib.sha256(new).hexdigest(), "changed": old != new}
            for path, (old, new) in proposed.items()
        },
    }
    output.mkdir()
    for path, (_, new) in proposed.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(new)
    with (output / "receipt.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("api", "web", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--docker-context")
    args = parser.parse_args(argv)
    docker = (
        ["docker", "--context", args.docker_context]
        if args.docker_context
        else ["docker"]
    )
    try:
        result = prepare(
            {"api": args.api, "web": args.web}, args.version, docker, args.output
        )
    except PlanError as exc:
        print(f"Lock proposal refused: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError) as exc:
        print(f"Lock proposal failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": result["status"],
                "verified_architectures": len(result["architectures"]),
                "changed_locks": sum(
                    row["changed"] for row in result["locks"].values()
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
