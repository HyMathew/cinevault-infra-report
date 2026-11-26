"""Keep Alpine refresh bounded to verified OpenSSL package pairs."""

import gzip
import io
import tarfile
from pathlib import Path

import pytest

from scripts import prepare_openssl_locks as refresh

OLD = "3.5.9-r1"
NEW = "3.5.10-r0"
FROZEN = (
    f"{'a' * 64}  libcrypto3-{OLD}.apk\n"
    f"{'b' * 64}  libssl3-{OLD}.apk\n"
    f"{'c' * 64}  libffi-3.8.1-r0.apk\n"
).encode()
PROPOSED = {name: (f"{name}-{NEW}.apk", "d" * 64) for name in refresh.NAMES}


def test_only_the_two_libraries_change():
    planned = refresh.refresh_lock(FROZEN, PROPOSED)
    assert planned.splitlines()[-1] == FROZEN.splitlines()[-1]
    assert planned.splitlines()[:2] == [
        f"{checksum}  {filename}".encode() for filename, checksum in PROPOSED.values()
    ]


def test_refuses_different_bytes_for_a_locked_filename():
    planned = {name: (f"{name}-{OLD}.apk", "e" * 64) for name in refresh.NAMES}
    with pytest.raises(refresh.PlanError, match="locked_apk_bytes_changed"):
        refresh.refresh_lock(FROZEN, planned)


def test_requires_both_libraries():
    incomplete = b"\n".join(FROZEN.splitlines()[1:]) + b"\n"
    with pytest.raises(refresh.PlanError, match="openssl_libraries_missing_in_lock"):
        refresh.refresh_lock(incomplete, PROPOSED)


def metadata(arch, dependency):
    body = (
        "pkgname = libssl3\n"
        f"pkgver = {NEW}\narch = {arch}\norigin = openssl\ndepend = libcrypto3={dependency}\n"
    ).encode()
    tape = io.BytesIO()
    with tarfile.open(fileobj=tape, mode="w") as archive:
        entry = tarfile.TarInfo(".PKGINFO")
        entry.size = len(body)
        archive.addfile(entry, io.BytesIO(body))
    return gzip.compress(tape.getvalue())


def test_metadata_requires_exact_architecture_and_openssl_pair():
    refresh.check_metadata(metadata("x86_64", NEW), "x86_64", "libssl3", NEW)
    for raw in (metadata("aarch64", NEW), metadata("x86_64", OLD)):
        with pytest.raises(refresh.PlanError, match="alpine_metadata_mismatch"):
            refresh.check_metadata(raw, "x86_64", "libssl3", NEW)


def test_refuses_partial_proposal_when_one_architecture_fails(monkeypatch, tmp_path):
    def snapshot(_):
        return "a" * 40, "alpine", {"x86_64": FROZEN, "armhf": FROZEN}

    def verify(_docker, _image, arch, _packages):
        if arch == "armhf":
            raise refresh.PlanError("alpine_signature_verification_failed")

    monkeypatch.setattr(refresh, "snapshot", snapshot)
    monkeypatch.setattr(refresh, "download", lambda *_: b"test")
    monkeypatch.setattr(refresh, "verify", verify)
    monkeypatch.setattr(refresh, "check_metadata", lambda *args: None)
    destination = tmp_path / "proposal"
    with pytest.raises(refresh.PlanError, match="alpine_signature_verification_failed"):
        refresh.prepare(
            {"api": tmp_path, "web": tmp_path}, NEW, ["docker"], destination
        )
    assert not destination.exists()


def test_incomplete_receipt_does_not_publish_any_files(monkeypatch, tmp_path):
    monkeypatch.setattr(
        refresh, "snapshot", lambda _: ("a" * 40, "alpine", {"x86_64": FROZEN})
    )
    monkeypatch.setattr(refresh, "download", lambda *_: b"valid fixture")
    monkeypatch.setattr(refresh, "verify", lambda *_: None)
    monkeypatch.setattr(refresh, "check_metadata", lambda *_: None)
    original_open = Path.open

    def fail_receipt(path, *args, **kwargs):
        if path.name == "receipt.json":
            with original_open(path, "xb") as partial:
                partial.write(b"{")
            raise OSError("simulated failure after a partial receipt write")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_receipt)
    destination = tmp_path / "proposal"
    with pytest.raises(OSError, match="partial receipt write"):
        refresh.prepare(
            {"api": tmp_path, "web": tmp_path}, NEW, ["docker"], destination
        )
    assert list(tmp_path.iterdir()) == []
