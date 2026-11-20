"""Fail-closed local file and argument boundaries; never format secret values."""

import json
import os
import re
import stat
import subprocess
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit


class BackupError(ValueError):
    """Messages are fixed operator-facing codes, never upstream exceptions."""


def require(condition, code):
    if not condition:
        raise BackupError(code)


def strict_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def no_constant(_):
        raise BackupError("non_finite_json_number")

    return json.loads(data, object_pairs_hook=unique, parse_constant=no_constant)


def database_name(value):
    require(
        isinstance(value, str)
        and re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value)
        and value not in {"admin", "config", "local"},
        "invalid_database_name",
    )
    return value


def unlinked_path(path):
    original = Path(path).absolute()
    normalized = Path(os.path.abspath(original))
    # Inspect the original spelling first: collapsing link/.. must never hide a
    # link. abspath normalizes lexically; unlike resolve it does not follow links.
    for spelling in (original, normalized):
        for item in reversed((spelling, *spelling.parents)):
            if item.exists() or item.is_symlink():
                info = item.lstat()
                require(
                    not stat.S_ISLNK(info.st_mode)
                    and not getattr(info, "st_file_attributes", 0)
                    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024),
                    "linked_path_refused",
                )
    return normalized


def windows_acl(path, *, initialize=False):
    # Windows PowerShell is part of supported Windows hosts. Import explicitly:
    # a caller's PowerShell 7 PSModulePath must not change module resolution.
    executable = (
        Path(os.environ["SystemRoot"])
        / "System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    script = r"""
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security') -ErrorAction Stop
$d = [Console]::In.ReadToEnd() | ConvertFrom-Json
$current = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$allowed = @($current, 'S-1-5-18', 'S-1-5-32-544', 'S-1-3-4')
if ($d.initialize) {
    $acl = Get-Acl -LiteralPath $d.path
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier]))) {
        $acl.RemoveAccessRuleSpecific($rule)
    }
    foreach ($sid in @($current, 'S-1-5-18', 'S-1-5-32-544')) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new(
            [Security.Principal.SecurityIdentifier]::new($sid), 'FullControl',
            'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $acl.AddAccessRule($rule)
    }
    [IO.Directory]::SetAccessControl($d.path, $acl)
}
$acl = Get-Acl -LiteralPath $d.path
$owner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
$ok = ($allowed -contains $owner)
foreach ($rule in $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
    if ($rule.AccessControlType -eq 'Allow' -and $allowed -notcontains $rule.IdentityReference.Value) { $ok = $false }
}
@{ private = $ok } | ConvertTo-Json -Compress
"""
    result = subprocess.run(
        [
            str(executable),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ],
        input=json.dumps({"path": str(path), "initialize": initialize}).encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    require(result.returncode == 0, "acl_inspection_failed")
    require(json.loads(result.stdout)["private"] is True, "private_acl_required")


def private_path(path, *, directory=False):
    path = unlinked_path(path)
    info = path.stat()
    require(
        stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
        "regular_private_path_required",
    )
    if os.name == "nt":
        windows_acl(path)
    else:
        require(
            info.st_uid in {os.getuid(), 0} and info.st_mode & 0o077 == 0,
            "private_mode_required",
        )
    return path


def initialize_directory(path):
    path = unlinked_path(path)
    path.mkdir(mode=0o700, exist_ok=False)
    if os.name == "nt":
        windows_acl(path, initialize=True)
    return private_path(path, directory=True)


def read_private(path, limit=65536):
    path = unlinked_path(path)
    expected = path.stat()
    private_path(path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        info = os.fstat(stream.fileno())
        require(
            (info.st_dev, info.st_ino)
            == (expected.st_dev, expected.st_ino)
            == (path.stat().st_dev, path.stat().st_ino),
            "private_file_changed",
        )
        data = stream.read(limit + 1)
    require(0 < len(data) <= limit, "private_file_size_invalid")
    return data


def key_lines(data, *, identity):
    lines = [
        line.strip()
        for line in data.decode("ascii").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    pattern = (
        r"AGE-SECRET-KEY-(?:PQ-)?1[A-Z0-9]{58}"
        if identity
        else r"(?:age1[ac-hj-np-z02-9]{58}|age1pq1[ac-hj-np-z02-9]{50,4096})"
    )
    require(
        1 <= len(lines) <= 16 and all(re.fullmatch(pattern, line) for line in lines),
        "native_age_keys_only",
    )
    return ("\n".join(lines) + "\n").encode("ascii")


def write_private(path, data):
    with os.fdopen(
        os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        ),
        "wb",
    ) as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    private_path(path)
    return path


def connection_config(data):
    from pymongo.uri_parser import parse_uri

    value = strict_json(data)
    require(
        isinstance(value, dict)
        and set(value) == {"uri"}
        and isinstance(value["uri"], str),
        "config_uri_only_required",
    )
    require(value["uri"].startswith("mongodb://"), "standard_mongodb_uri_required")
    allowed = {
        "authsource",
        "replicaset",
        "directconnection",
        "tls",
        "tlscafile",
        "authmechanism",
    }
    query = parse_qsl(urlsplit(value["uri"]).query, keep_blank_values=True)
    require(
        len({key.lower() for key, _ in query}) == len(query)
        and all(key.lower() in allowed for key, _ in query),
        "uri_options_refused",
    )
    parsed = parse_uri(value["uri"])
    options = {str(k).lower(): v for k, v in parsed["options"].items()}
    require(
        set(options) <= allowed
        and options.get("replicaset")
        and options.get("authsource"),
        "uri_options_refused",
    )
    require(
        parsed["username"] and parsed["password"] and not parsed["database"],
        "authenticated_uri_without_database_required",
    )
    require(options.get("authmechanism") == "SCRAM-SHA-256", "scram_sha256_required")
    require(
        options.get("tls") is True
        or all(
            host in {"127.0.0.1", "::1", "localhost"} for host, _ in parsed["nodelist"]
        ),
        "tls_required_off_loopback",
    )
    return value, (sorted(parsed["nodelist"]), options)
