"""Verify a public CineVault registry manifest and, optionally, its provenance."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

REGISTRY = "ghcr.io"
REPOSITORY = r"[a-z0-9][a-z0-9-]{0,38}/cinevault-(?:api|web)"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
IMAGE = re.compile(rf"{re.escape(REGISTRY)}/({REPOSITORY})@({DIGEST.pattern})")
INDEX_TYPES = {
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
}
MANIFEST_TYPES = {
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
}
CONFIG_TYPES = {
    "application/vnd.oci.image.config.v1+json",
    "application/vnd.docker.container.image.v1+json",
}
ACCEPT = ", ".join(sorted(INDEX_TYPES | MANIFEST_TYPES))
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
PREDICATE = "https://slsa.dev/provenance/v1"
ISSUER = "https://token.actions.githubusercontent.com"
QUALIFICATION_REF = "refs/heads/quality/cinevault-v2"


class RegistryVerificationError(ValueError):
    """Public, bounded diagnostic that contains no token or remote response body."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def require(condition, message):
    if not condition:
        raise RegistryVerificationError(message)


def is_digest(value):
    return isinstance(value, str) and DIGEST.fullmatch(value) is not None


def unique_object(pairs):
    result = dict(pairs)
    require(len(result) == len(pairs), "registry document contains duplicate keys")
    return result


def read_document(opener, path, headers, limit):
    request = Request("https://" + REGISTRY + path, headers=headers)
    try:
        with opener.open(request, timeout=15) as response:
            raw = response.read(limit + 1)
            metadata = response.headers
    except HTTPError as exc:
        with exc:
            status = exc.code
        raise RegistryVerificationError(f"registry returned HTTP {status}") from None
    except (URLError, OSError):
        raise RegistryVerificationError("registry TLS connection failed") from None
    require(0 < len(raw) <= limit, "registry document exceeds its size limit")
    try:
        document = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise RegistryVerificationError("registry returned invalid JSON") from None
    require(isinstance(document, dict), "unexpected registry document type")
    return raw, metadata, document


def manifest(opener, repository, digest, token):
    raw, headers, document = read_document(
        opener,
        f"/v2/{repository}/manifests/{digest}",
        {
            "Accept": ACCEPT,
            "Accept-Encoding": "identity",
            "Authorization": "Bearer " + token,
        },
        MAX_MANIFEST_BYTES,
    )
    digest_header = headers.get("Docker-Content-Digest")
    require(
        "sha256:" + hashlib.sha256(raw).hexdigest() == digest
        and (digest_header is None or digest_header == digest),
        "manifest bytes do not match the registry digest",
    )
    media = headers.get("Content-Type", "").split(";", 1)[0]
    require(
        media in INDEX_TYPES | MANIFEST_TYPES
        and document.get("mediaType", media) == media
        and document.get("schemaVersion") == 2,
        "unexpected OCI manifest media type or schema",
    )
    return raw, media, document


def well_formed_descriptor(descriptor):
    return (
        isinstance(descriptor, dict)
        and is_digest(descriptor.get("digest"))
        and type(descriptor.get("size")) is int
        and descriptor["size"] > 0
    )


def verify(reference, expected_config, expected_platform_manifest=None, *, opener=None):
    """Fetch only public manifest bytes, resolving Linux amd64 when given an index."""
    match = IMAGE.fullmatch(reference)
    require(
        match and is_digest(expected_config),
        "an immutable GHCR reference and configuration digest are required",
    )
    require(
        expected_platform_manifest is None or is_digest(expected_platform_manifest),
        "invalid expected platform manifest digest",
    )
    repository, requested = match.groups()
    if opener is None:
        opener = build_opener(ProxyHandler({}), NoRedirect())
    query = urlencode({"service": REGISTRY, "scope": f"repository:{repository}:pull"})
    _, _, credentials = read_document(opener, "/token?" + query, {}, 32_768)
    token = credentials.get("token")
    require(
        isinstance(token, str)
        and 1 <= len(token) <= 16_384
        and token.isascii()
        and all(33 <= ord(char) <= 126 for char in token),
        "registry did not return an anonymous pull token",
    )

    _, kind, document = manifest(opener, repository, requested, token)
    selected = requested
    index_platform = None
    if kind in INDEX_TYPES:
        entries = document.get("manifests")
        require(
            isinstance(entries, list) and 1 <= len(entries) <= 64,
            "invalid registry index size",
        )
        linux_amd64 = [
            row
            for row in entries
            if isinstance(row, dict)
            and isinstance(row.get("platform"), dict)
            and row["platform"].get("os") == "linux"
            and row["platform"].get("architecture") == "amd64"
        ]
        require(len(linux_amd64) == 1, "registry index has no unique Linux amd64 image")
        expected = linux_amd64[0]
        require(
            well_formed_descriptor(expected)
            and expected.get("mediaType") in MANIFEST_TYPES,
            "invalid registry platform descriptor",
        )
        selected = expected["digest"]
        raw, child_kind, document = manifest(opener, repository, selected, token)
        require(
            child_kind == expected["mediaType"] and len(raw) == expected["size"],
            "platform manifest disagrees with its registry index",
        )
        index_platform = "linux/amd64"

    require(
        expected_platform_manifest is None or selected == expected_platform_manifest,
        "registry platform manifest differs from the scanned OCI manifest",
    )
    config, layers = document.get("config"), document.get("layers")
    require(
        well_formed_descriptor(config)
        and config.get("mediaType") in CONFIG_TYPES
        and config["digest"] == expected_config,
        "registry image configuration differs from the scanned image",
    )
    require(
        isinstance(layers, list)
        and 1 <= len(layers) <= 256
        and all(map(well_formed_descriptor, layers)),
        "invalid registry layer descriptors",
    )
    return {
        "passed": True,
        "registry_reference": reference,
        "registry_subject_digest": requested,
        "registry_platform_manifest_digest": selected,
        "registry_config_digest": config["digest"],
        "platform_selected_from_index": index_platform,
        "layer_descriptors": len(layers),
        "anonymous_manifest_access": True,
    }


def provenance_source(reference, commit, source_ref, run):
    match = IMAGE.fullmatch(reference)
    require(match, "an immutable GHCR reference is required for provenance")
    owner, image = match[1].split("/")
    require(owner == "hymathew", "provenance requires an official CineVault repository")
    require(
        isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit),
        "provenance requires a full source commit",
    )
    default = "master" if image == "cinevault-api" else "main"
    require(
        source_ref in {QUALIFICATION_REF, "refs/heads/" + default},
        "source ref is not permitted for CineVault image publication",
    )
    require(type(run) is int and run > 0, "provenance requires a workflow run ID")
    return f"HyMathew/{image}"


def attest(release_subject, repository, workflow, commit, source_ref):
    args = [
        "gh",
        "attestation",
        "verify",
        release_subject,
        "--repo",
        repository,
        "--signer-workflow",
        f"{repository}/{workflow}",
        "--signer-digest",
        commit,
        "--source-digest",
        commit,
        "--source-ref",
        source_ref,
        "--cert-oidc-issuer",
        ISSUER,
        "--deny-self-hosted-runners",
        "--predicate-type",
        PREDICATE,
        "--format",
        "json",
    ]
    environment = {
        **os.environ,
        "GH_HOST": "github.com",
        "GH_PROMPT_DISABLED": "1",
        "GH_NO_UPDATE_NOTIFIER": "1",
        "GH_NO_EXTENSION_UPDATE_NOTIFIER": "1",
    }
    try:
        result = subprocess.run(
            args,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=90,
            check=False,
        )
    except FileNotFoundError:
        raise RegistryVerificationError(
            "GitHub CLI is required for provenance"
        ) from None
    except (OSError, subprocess.TimeoutExpired):
        raise RegistryVerificationError(
            "GitHub CLI provenance check did not finish"
        ) from None
    require(result.returncode == 0, "GitHub CLI did not verify the artifact signature")
    require(
        0 < len(result.stdout) <= 8 * MAX_MANIFEST_BYTES,
        "invalid provenance output size",
    )
    try:
        rows = json.loads(result.stdout, object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise RegistryVerificationError(
            "GitHub CLI returned invalid provenance JSON"
        ) from None
    require(
        isinstance(rows, list) and 1 <= len(rows) <= 30, "invalid provenance result"
    )
    return rows


def matching_provenance(
    rows,
    repository,
    workflow,
    commit,
    source_ref,
    run,
    name,
    digest,
    *,
    expected_attempt=None,
):
    uri = "https://github.com/" + repository
    invocation = re.compile(
        re.escape(f"{uri}/actions/runs/{run}/attempts/") + r"([1-9][0-9]*)"
    )
    identity = {
        "sourceRepositoryURI": uri,
        "sourceRepositoryRef": source_ref,
        "sourceRepositoryDigest": commit,
        "buildSignerURI": f"{uri}/{workflow}@{source_ref}",
        "buildSignerDigest": commit,
        "issuer": ISSUER,
        "runnerEnvironment": "github-hosted",
    }
    for row in rows:
        try:
            result = row["verificationResult"]
            cert = result["signature"]["certificate"]
            statement = result["statement"]
            attempt = invocation.fullmatch(cert["runInvocationURI"])
            if (
                attempt
                and (expected_attempt is None or int(attempt[1]) == expected_attempt)
                and all(cert.get(field) == value for field, value in identity.items())
                and result["verifiedTimestamps"]
                and statement["predicateType"] == PREDICATE
                and {"name": name, "digest": {"sha256": digest}} in statement["subject"]
            ):
                return int(attempt[1])
        except (KeyError, TypeError, AttributeError, ValueError):
            continue
    raise RegistryVerificationError(
        "verified provenance does not match the source and workflow run"
    )


def verify_attestation(reference, commit, source_ref, run, *, expected_attempt=None):
    repo = provenance_source(reference, commit, source_ref, run)
    workflow = ".github/workflows/tests.yml"
    name, digest = reference.split("@sha256:")
    rows = attest("oci://" + reference, repo, workflow, commit, source_ref)
    attempt = matching_provenance(
        rows,
        repo,
        workflow,
        commit,
        source_ref,
        run,
        name,
        digest,
        expected_attempt=expected_attempt,
    )
    return {
        "signature_verified": True,
        "source_commit": commit,
        "source_ref": source_ref,
        "workflow": f"{repo}/{workflow}",
        "workflow_run": run,
        "workflow_attempt": attempt,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--config-digest", required=True)
    parser.add_argument("--platform-manifest-digest")
    parser.add_argument("--source-commit")
    parser.add_argument("--source-ref")
    parser.add_argument("--run-id", type=int)
    args = parser.parse_args(argv)
    try:
        source = (args.source_commit, args.source_ref, args.run_id)
        needs_provenance = any(value is not None for value in source)
        if needs_provenance:
            provenance_source(args.reference, *source)
            require(
                is_digest(args.platform_manifest_digest),
                "the scanned platform manifest digest is required for provenance",
            )
        evidence = verify(
            args.reference, args.config_digest, args.platform_manifest_digest
        )
        if needs_provenance:
            evidence["provenance"] = verify_attestation(args.reference, *source)
    except RegistryVerificationError as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
