"""Verify the image audit, registry digest and signed publication for one staging image."""

import argparse
import base64
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

if __package__:
    from . import verify_registry_image as registry
else:
    import verify_registry_image as registry

LIMIT = 16 * 1024**2
REF = "quality/cinevault-v2"
ARCHIVES = {
    "image-audit": "publish-image",
    "image-verified-provenance": "Verify published image provenance",
}
SEVERITIES = {"Critical", "High", "Medium", "Low", "Negligible", "Unknown"}


def sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise registry.RegistryVerificationError(message)


def gh_api(path):
    result = subprocess.run(
        ["gh", "api", "--hostname", "github.com", path],
        capture_output=True,
        check=True,
        env={**os.environ, "GH_PROMPT_DISABLED": "1", "GH_NO_UPDATE_NOTIFIER": "1"},
        stdin=subprocess.DEVNULL,
        timeout=35,
    )
    require(len(result.stdout) <= LIMIT, "GitHub metadata too large")
    return json.loads(result.stdout)


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    require(parsed.tzinfo is not None, "GitHub timestamp lacks timezone")
    return parsed


def release_metadata(repo, run, attempt, commit):
    base = f"repos/{repo}/actions/runs/{run}"
    result = gh_api(base)
    require(
        result["id"] == run
        and result["run_attempt"] == attempt
        and result["repository"]["full_name"]
        == result["head_repository"]["full_name"]
        == repo
        and result["head_sha"] == commit
        and result["head_branch"] == REF
        and result["path"] == ".github/workflows/tests.yml"
        and result["event"] == "workflow_dispatch",
        "workflow identity or attempt differs",
    )
    require(
        result["status"] == "completed" and result["conclusion"] == "success",
        "publication workflow did not succeed",
    )
    boundary = gh_api(f"{base}/attempts/{attempt}/jobs?per_page=100")
    rows = boundary["jobs"]
    require(len(rows) == boundary["total_count"], "GitHub job inventory is incomplete")
    windows = {}
    for archive, name in ARCHIVES.items():
        jobs = [job for job in rows if job["name"] == name]
        require(len(jobs) == 1, f"missing distinct job for {archive}")
        job = jobs[0]
        require(
            job["run_id"] == run
            and job["run_attempt"] == attempt
            and job["status"] == "completed"
            and job["conclusion"] == "success",
            f"job identity or state differs for {archive}",
        )
        windows[archive] = timestamp(job["started_at"]), timestamp(job["completed_at"])
    listed = gh_api(f"{base}/artifacts?per_page=100")
    artifacts = listed["artifacts"]
    require(
        len(artifacts) == listed["total_count"],
        "GitHub artifact inventory is incomplete",
    )
    verified = {}
    for name, (start, end) in windows.items():
        matches = [
            item
            for item in artifacts
            if item["name"] == name
            and item["expired"] is False
            and start <= timestamp(item["created_at"]) <= end
        ]
        require(
            len(matches) == 1,
            f"missing distinct artifact for {name} in requested attempt",
        )
        entry = matches[0]
        require(
            entry["workflow_run"]["id"] == run
            and entry["workflow_run"]["head_sha"] == commit
            and registry.is_digest(entry["digest"])
            and type(entry["size_in_bytes"]) is int
            and 0 < entry["size_in_bytes"] <= LIMIT,
            f"unverified artifact metadata for {name}",
        )
        verified[name] = entry
    return verified


def read_artifact(path, metadata):
    with path.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    require(
        len(raw) == metadata["size_in_bytes"] and sha(raw) == metadata["digest"],
        "artifact does not match GitHub size and SHA-256",
    )
    return zipfile.ZipFile(io.BytesIO(raw))


def safe_inventory(archive):
    members = archive.infolist()
    names = set()
    require(len(members) <= 256, "too many archive entries")
    for entry in members:
        path = PurePosixPath(entry.filename)
        mode = stat.S_IFMT(entry.external_attr >> 16)
        require(
            path.parts
            and not path.is_absolute()
            and ".." not in path.parts
            and "\\" not in entry.filename
            and ":" not in entry.filename
            and path.as_posix() not in names
            and mode in (0, stat.S_IFREG, stat.S_IFDIR),
            "ambiguous or unsafe audit archive member",
        )
        names.add(path.as_posix())
    require(
        sum(row.file_size for row in members) <= 32 * 1024**2,
        "audit archive expands beyond limit",
    )
    return names


def document(archive, path):
    raw = archive.read(path)
    return raw, json.loads(raw)


def inspect_audit(archive, repo, commit):
    safe_inventory(archive)
    _, audit = document(archive, "image-check.json")
    require(
        audit["scan_passed"] is True
        and audit["scanner_exit_code"] == 0
        and audit["health_passed"] is True
        and audit["cleanup_passed"] is True
        and audit["runtime_uid"] == 10001,
        "image audit did not pass",
    )
    require(
        audit["image"] == repo.split("/")[1] + ":ci-" + commit,
        "image audit source differs",
    )
    folder = audit["attempt_directory"]
    require(re.fullmatch(r"image-[a-f0-9]{32}", folder), "invalid audit directory")
    proof = audit["scan_provenance"]
    build = audit["build_provenance"]
    config, platform = (
        proof["archive_config_digest"],
        proof["archive_oci_manifest_digest"],
    )
    built_platform = build["manifest_digest"]
    image = audit["image_id"]
    require(
        all(
            registry.is_digest(item)
            for item in (
                config,
                built_platform,
                image,
                proof["archive_sha256"],
                build["source_tar_digest"],
            )
        ),
        "invalid scanner or build digest",
    )
    kind = proof["archive_identity_kind"]
    require(
        (kind == "docker-config" and platform is None and image == config)
        or (
            kind in {"oci-manifest", "oci-index"}
            and platform == built_platform
            and image != config
            and (image == platform) == (kind == "oci-manifest")
        ),
        "invalid image archive identity",
    )
    require(
        build["source_commit"] == commit
        and build["config_digest"] == config
        and proof["docker_image_id"] == image,
        "scan and build identities differ",
    )
    _, buildkit = document(archive, folder + "/build-metadata.json")
    require(
        buildkit["containerimage.digest"] == built_platform, "BuildKit manifest differs"
    )
    scan_raw, scan = document(archive, folder + "/image-vulnerabilities.json")
    sbom_raw, sbom = document(archive, folder + "/image-sbom.json")
    require(
        sha(scan_raw) == proof["scan_report_sha256"]
        and sha(sbom_raw) == proof["sbom_sha256"],
        "scan or SBOM checksum differs",
    )
    counts = {}
    for match in scan["matches"]:
        name = match["vulnerability"]["severity"]
        require(name in SEVERITIES, "unknown finding severity")
        counts[name] = counts.get(name, 0) + 1
    require(
        counts == audit["severity_counts"]
        and not ({"High", "Critical"} & counts.keys()),
        "vulnerability gate refused",
    )
    catalog = sbom["source"]["metadata"]
    target = scan["source"]["target"]
    for entry, key in (
        (target, "grype_manifest_digest"),
        (catalog, "sbom_manifest_digest"),
    ):
        encoded_config = base64.b64decode(entry["config"], validate=True)
        manifest = base64.b64decode(entry["manifest"], validate=True)
        require(
            sha(encoded_config) == entry["imageID"] == config
            and sha(manifest) == proof[key]
            and json.loads(manifest)["config"]["digest"] == config,
            "scan or SBOM does not refer to the audited image",
        )
    require(
        proof["grype_config_digest"] == proof["sbom_config_digest"] == config
        and len(sbom["artifacts"]) == proof["sbom_components"] > 0,
        "scan or SBOM inventory differs",
    )
    _, release = document(archive, "registry-publication.json")
    registry_name = "ghcr.io/" + repo.lower()
    reference = registry_name + "@" + release["digest"]
    require(
        release["published"] is True
        and release["repository"] == repo
        and release["source_commit"] == commit
        and release["image_id"] == image
        and release["publication_channel"] == "candidate"
        and release["tag"] == registry_name + ":sha-" + commit
        and release["registry_ref"] == reference
        and release["scan_provenance"] == proof
        and registry.is_digest(release["digest"]),
        "publication and scan identities differ",
    )
    return reference, config, platform, built_platform


def check(role, commit, run, attempt, audit_path, provenance_path):
    require(
        re.fullmatch(r"[0-9a-f]{40}", commit) and run > 0 and attempt > 0,
        "expected full commit, run and attempt",
    )
    repo = f"HyMathew/cinevault-{role}"
    artifacts = release_metadata(repo, run, attempt, commit)
    with read_artifact(audit_path, artifacts["image-audit"]) as archive:
        reference, config, platform, built_platform = inspect_audit(
            archive, repo, commit
        )
    with read_artifact(
        provenance_path, artifacts["image-verified-provenance"]
    ) as archive:
        safe_inventory(archive)
        _, rows = document(archive, "image-attestation-verification.json")
    name, digest = reference.split("@sha256:")
    source_ref = "refs/heads/" + REF
    registry.matching_provenance(
        rows,
        repo,
        ".github/workflows/tests.yml",
        commit,
        source_ref,
        run,
        name,
        digest,
        expected_attempt=attempt,
    )
    result = registry.verify(reference, config, platform)
    signature = registry.verify_attestation(
        reference, commit, source_ref, run, expected_attempt=attempt
    )
    return {
        **result,
        "provenance": signature,
        "build_manifest_digest": built_platform,
        "audited_archive_platform_manifest_digest": platform,
        "artifacts": {
            name: {"id": row["id"], "sha256": row["digest"]}
            for name, row in artifacts.items()
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--role", choices=("api", "web"), required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--attempt", type=int, required=True)
    parser.add_argument("--audit-zip", type=Path, required=True)
    parser.add_argument("--provenance-zip", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        evidence = check(
            args.role,
            args.commit,
            args.run,
            args.attempt,
            args.audit_zip,
            args.provenance_zip,
        )
    except registry.RegistryVerificationError as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        return 1
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        subprocess.SubprocessError,
        zipfile.BadZipFile,
    ):
        print(
            json.dumps(
                {"passed": False, "error": "release evidence unavailable or invalid"}
            )
        )
        return 1
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
