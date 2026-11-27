"""Verify both staging publications before emitting their deployment references."""

import argparse
import json
import re
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

if __package__:
    from . import check_staging_image_release as release
    from .qualification_sources import load_sources
else:
    import check_staging_image_release as release
    from qualification_sources import load_sources


ROLES = ("api", "web")
MANIFEST_FIELDS = {"commit", "run", "attempt", "audit_zip", "provenance_zip"}
MAX_MANIFEST_BYTES = 16 * 1024


def inputs(path):
    with path.open("rb") as source:
        raw = source.read(MAX_MANIFEST_BYTES + 1)
    release.require(len(raw) <= MAX_MANIFEST_BYTES, "pair manifest is too large")
    value = json.loads(raw, object_pairs_hook=release.registry.unique_object)
    release.require(
        isinstance(value, dict) and set(value) == set(ROLES),
        "pair manifest must contain exactly api and web",
    )
    result = {}
    for role in ROLES:
        entry = value[role]
        release.require(
            isinstance(entry, dict) and set(entry) == MANIFEST_FIELDS,
            f"{role} manifest is incomplete or has unexpected fields",
        )
        commit, run, attempt = entry["commit"], entry["run"], entry["attempt"]
        release.require(
            isinstance(commit, str)
            and re.fullmatch("[0-9a-f]{40}", commit) is not None
            and type(run) is int
            and run > 0
            and type(attempt) is int
            and attempt > 0,
            f"{role} requires a full commit, a run and an attempt",
        )
        paths = (entry["audit_zip"], entry["provenance_zip"])
        release.require(
            all(
                isinstance(value, str) and value.strip() and "\0" not in value
                for value in paths
            ),
            f"{role} requires two artifact paths",
        )
        result[role] = (commit, run, attempt, *(path.parent / value for value in paths))
    return result


def verify_pair(manifest, qualification_sources=None):
    plan = inputs(manifest)
    qualification_digest = None
    if qualification_sources is not None:
        sources, qualification_digest = load_sources(qualification_sources)
        release.require(
            sources == {role: entry[0] for role, entry in plan.items()},
            "publication commits differ from the qualification manifest",
        )
    verified, errors = {}, {}
    for role, parameters in plan.items():
        try:
            evidence = release.check(role, *parameters)
            reference = evidence["registry_reference"]
            source = evidence["provenance"]
            match = release.registry.IMAGE.fullmatch(reference)
            commit, run, attempt, *_ = parameters
            release.require(
                evidence["passed"] is True
                and match is not None
                and match[1] == f"hymathew/cinevault-{role}"
                and source["signature_verified"] is True
                and source["source_ref"] == release.registry.QUALIFICATION_REF
                and (
                    source["source_commit"],
                    source["workflow_run"],
                    source["workflow_attempt"],
                )
                == (commit, run, attempt),
                "returned evidence does not match the requested publication",
            )
            verified[role] = evidence
        except release.registry.RegistryVerificationError as error:
            errors[role] = str(error)
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            RecursionError,
            subprocess.SubprocessError,
            zipfile.BadZipFile,
        ):
            errors[role] = "release evidence unavailable or invalid"
    if errors:
        return {"passed": False, "errors": errors}
    return {
        "passed": True,
        "verified_at_utc": datetime.now(UTC).isoformat(),
        **(
            {"qualification_sources_sha256": qualification_digest}
            if qualification_digest is not None
            else {}
        ),
        "images": verified,
        "compose_environment": {
            f"CINEVAULT_STAGE_{role.upper()}_IMAGE": verified[role][
                "registry_reference"
            ]
            for role in ROLES
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--qualification-sources",
        type=Path,
        help="Require commits to match the Infra qualification sources before registry checks",
    )
    args = parser.parse_args(argv)
    try:
        result = verify_pair(args.manifest, args.qualification_sources)
    except release.registry.RegistryVerificationError as error:
        result = {"passed": False, "error": str(error)}
    except (OSError, ValueError, RecursionError):
        result = {"passed": False, "error": "pair manifest unavailable or invalid"}
    print(json.dumps(result, sort_keys=True))
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
