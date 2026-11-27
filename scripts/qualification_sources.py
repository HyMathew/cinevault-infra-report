"""Resolve and verify the exact application commits used by the Infra jobs."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

INFRA_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = INFRA_ROOT / ".github" / "qualification-sources.json"
COMMIT = re.compile(r"[0-9a-f]{40}")
ROLES = ("api", "web")


def is_commit(value):
    return isinstance(value, str) and COMMIT.fullmatch(value) is not None


def unique_keys(pairs):
    values = {}
    for key, value in pairs:
        if key in values:
            raise ValueError("Repeated source role in qualification manifest")
        values[key] = value
    return values


def load_sources(path):
    with path.open("rb") as stream:
        raw = stream.read(1025)
    if len(raw) > 1024:
        raise ValueError("Qualification manifest exceeds its size limit")
    sources = json.loads(raw, object_pairs_hook=unique_keys)
    if (
        not isinstance(sources, dict)
        or set(sources) != set(ROLES)
        or not all(is_commit(value) for value in sources.values())
        or len(set(sources.values())) != len(ROLES)
    ):
        raise ValueError(
            "Qualification requires full and distinct API and Web commit fields"
        )
    return sources, hashlib.sha256(raw).hexdigest()


def verify_checkout(role, root, expected):
    if not is_commit(expected):
        raise ValueError(f"{role} requires a full commit")
    root = root.resolve()
    command = ["git", "-C", str(root)]
    identity = subprocess.check_output(
        [*command, "rev-parse", "--show-toplevel", "HEAD"],
        text=True,
        encoding="utf-8",
    ).splitlines()
    if len(identity) != 2 or Path(identity[0]).resolve() != root:
        raise ValueError(f"{role} must point to its checkout root")
    if identity[1] != expected:
        raise ValueError(f"{role} checkout does not match its qualification commit")
    if subprocess.check_output(
        [*command, "status", "--porcelain", "--untracked-files=normal"]
    ):
        raise ValueError(f"{role} checkout must be clean")
    return expected


def verify_sources(manifest, infra_root, infra_commit, roots):
    if not roots or set(roots) - set(ROLES):
        raise ValueError("Provide the application checkouts used by this job")
    sources, digest = load_sources(manifest)
    return {
        "schema": 1,
        "manifest_sha256": digest,
        "infra_commit": verify_checkout("infra", infra_root, infra_commit),
        "applications": {
            role: verify_checkout(role, root, sources[role])
            for role, root in roots.items()
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    resolve = commands.add_parser(
        "resolve", help="Read the pinned commits", allow_abbrev=False
    )
    resolve.add_argument("--github-output", action="store_true")
    verify = commands.add_parser(
        "verify", help="Verify clean Git sources", allow_abbrev=False
    )
    verify.add_argument("--infra-commit", required=True)
    verify.add_argument("--api-root", type=Path)
    verify.add_argument("--web-root", type=Path)
    verify.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "resolve":
            sources, _ = load_sources(MANIFEST)
            if args.github_output:
                with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
                    for role in ROLES:
                        print(f"{role}={sources[role]}", file=stream)
            else:
                print(json.dumps(sources))
            return
        roots = {role: getattr(args, role + "_root") for role in ROLES}
        result = verify_sources(
            MANIFEST,
            INFRA_ROOT,
            args.infra_commit,
            {role: root for role, root in roots.items() if root is not None},
        )
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        with args.receipt.open("x", encoding="utf-8") as stream:
            print(json.dumps(result, indent=2), file=stream)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Qualification sources rejected: {error}\n")


if __name__ == "__main__":
    main()
