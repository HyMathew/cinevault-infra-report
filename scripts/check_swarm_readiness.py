"""Collect and compare read-only Swarm preflight snapshots for CineVault staging."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROLES = ("web", "api", "manager")
SERVICES = {role: "cinevault_cinevault-" + role for role in ROLES[:2]}
MANAGER_OBJECTS = ("stack", "service", "network", "secret", "config")
MIB = 1024**2
MIN_MEMORY_MIB = {"web": 384, "api": 1152}
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
NODE_ID = re.compile(r"[a-z0-9]{25}")
SNAPSHOT_ID = re.compile(r"[0-9a-f]{64}")


def docker(*args):
    environment = {
        key: value for key, value in os.environ.items() if key != "DOCKER_CONTEXT"
    }
    result = subprocess.run(
        ["docker", "--host", "unix:///var/run/docker.sock", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=12,
        env=environment,
    )
    return result.stdout.splitlines()


def objects(*args):
    return [json.loads(row) for row in docker(*args)]


def one(*args):
    (row,) = objects(*args)
    return row


def node_key(value):
    if not NODE_ID.fullmatch(value):
        raise ValueError("Invalid node ID")
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def image_digest(value):
    digest = value.rsplit("@", 1)[-1]
    return digest if "@" in value and DIGEST.fullmatch(digest) else None


def stage_names(kind):
    rows = docker(kind, "ls", "--format", "{{.Name}}")
    return sum(value == "cvstage" or value.startswith("cvstage_") for value in rows)


def worker(role):
    tasks = docker(
        "ps",
        "--filter",
        "label=com.docker.swarm.service.name=" + SERVICES[role],
        "--format",
        "{{.ID}}",
    )
    if len(tasks) != 1:
        return {"task_count": len(tasks), "healthy": False, "image_digest": None}
    if not re.fullmatch(r"[0-9a-f]{12}", tasks[0]):
        raise ValueError("Invalid container ID")
    status, image = one(
        "container",
        "inspect",
        "--format",
        "[{{json .State.Health.Status}},{{json .Config.Image}}]",
        tasks[0],
    )
    return {
        "task_count": 1,
        "healthy": status == "healthy",
        "image_digest": image_digest(image),
    }


def manager():
    nodes = objects(
        "node",
        "ls",
        "--format",
        "[{{json .ID}},{{json .Status}},{{json .Availability}},{{json .ManagerStatus}}]",
    )
    members = {}
    for identity, state, availability, manager_state in nodes:
        key = node_key(identity)
        label = one(
            "node",
            "inspect",
            "--format",
            '{{json (index .Spec.Labels "cinevault")}}',
            identity,
        )
        members[key] = {
            "ready": state == "Ready",
            "active": availability == "Active",
            "drain": availability == "Drain",
            "leader": manager_state == "Leader",
            "manager": bool(manager_state),
            "label": label if label in ROLES[:2] else None,
        }
    services = {}
    for role, name in SERVICES.items():
        image, replicas = one(
            "service",
            "inspect",
            "--format",
            "[{{json .Spec.TaskTemplate.ContainerSpec.Image}},{{json .Spec.Mode.Replicated.Replicas}}]",
            name,
        )
        services[role] = {"replicas": replicas, "image_digest": image_digest(image)}
    conflicts = {kind: stage_names(kind) for kind in MANAGER_OBJECTS}
    return {"members": members, "services": services, "conflicts": conflicts}


def collect(role):
    if sys.platform != "linux":
        raise ValueError("Collect on the Linux Swarm node")
    identity, state, control, root, cpu = one(
        "info",
        "--format",
        "[{{json .Swarm.NodeID}},{{json .Swarm.LocalNodeState}},{{json .Swarm.ControlAvailable}},"
        "{{json .DockerRootDir}},{{json .NCPU}}]",
    )
    if not Path(root).is_absolute() or type(cpu) is not int or cpu < 1:
        raise ValueError("Unexpected Docker info")
    with Path("/proc/meminfo").open(encoding="ascii") as stream:
        match = re.search(r"^MemAvailable:\s+(\d+) kB$", stream.read(), re.MULTILINE)
    if not match:
        raise ValueError("MemAvailable not found")
    disk = os.statvfs(root)
    result = {
        "role": role,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "node_sha256": node_key(identity),
        "active_swarm": state == "active",
        "control": control is True,
        "logical_cpus": cpu,
        "available_ram_bytes": int(match[1]) * 1024,
        "docker_available_disk_bytes": disk.f_bavail * disk.f_frsize,
        "conflicting_volumes": stage_names("volume"),
    }
    result["observed"] = manager() if role == "manager" else worker(role)
    return result


def assess(nodes, now, *, min_docker_free_mib=None):
    if min_docker_free_mib is not None and (
        type(min_docker_free_mib) is not int or min_docker_free_mib < 1
    ):
        raise ValueError("Requested minimum free space must be a positive integer")
    keys = {role: node["node_sha256"] for role, node in nodes.items()}
    topology = nodes["manager"]["observed"]
    rows = topology["members"]
    conflicts = topology["conflicts"]
    checks = {
        "distinct_ready_nodes": (
            all(SNAPSHOT_ID.fullmatch(key) for key in keys.values())
            and len(set(keys.values())) == 3
            and set(rows) == set(keys.values())
            and all(row["ready"] is True for row in rows.values())
            and all(node["active_swarm"] is True for node in nodes.values())
        ),
        "manager_drained_leader": (
            nodes["manager"]["control"] is True
            and rows.get(keys["manager"], {}).get("leader") is True
            and rows[keys["manager"]]["drain"] is True
        ),
        "stage_names_available": (
            set(conflicts) == set(MANAGER_OBJECTS)
            and all(type(count) is int and count == 0 for count in conflicts.values())
            and all(
                type(node["conflicting_volumes"]) is int
                and node["conflicting_volumes"] == 0
                for node in nodes.values()
            )
        ),
        "resources_measured": all(
            type(node[field]) is int and node[field] >= 0
            for node in nodes.values()
            for field in (
                "logical_cpus",
                "available_ram_bytes",
                "docker_available_disk_bytes",
            )
        )
        and all(node["logical_cpus"] > 0 for node in nodes.values()),
    }
    for role, required_mb in MIN_MEMORY_MIB.items():
        node = nodes[role]
        placement = rows.get(keys[role], {})
        running, service = node["observed"], topology["services"][role]
        checks[role + "_placement"] = (
            node["control"] is False
            and placement.get("manager") is False
            and placement["active"] is True
            and placement["label"] == role
            and sum(row["label"] == role for row in rows.values()) == 1
        )
        checks[role + "_stable_healthy"] = (
            type(service["replicas"]) is int
            and service["replicas"] == 1
            and type(running["task_count"]) is int
            and running["task_count"] == 1
            and running["healthy"] is True
            and DIGEST.fullmatch(service["image_digest"] or "") is not None
            and running["image_digest"] == service["image_digest"]
        )
        checks[role + "_memory"] = node["available_ram_bytes"] >= required_mb * MIB
    checks["contemporaneous_snapshots"] = all(
        timedelta(0)
        <= now - datetime.fromisoformat(node["timestamp_utc"])
        <= timedelta(minutes=15)
        for node in nodes.values()
    )
    budget = {}
    if min_docker_free_mib is not None:
        budget["minimum_docker_free_mib"] = min_docker_free_mib
        for role, node in nodes.items():
            free = node["docker_available_disk_bytes"]
            checks[role + "_disk"] = type(free) is int and free >= min_docker_free_mib * MIB
    return {
        "passed": all(checks.values()),
        "checked_at_utc": now.isoformat(),
        "checks": checks,
        "nodes": nodes,
        **budget,
    }


def read_node(path, role):
    with path.open("rb") as source:
        raw = source.read(32769)
    if len(raw) > 32768:
        raise ValueError("Snapshot too big")
    node = json.loads(raw)
    if node["role"] != role:
        raise ValueError("Snapshot role differs")
    return node


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("collect").add_argument("role", choices=ROLES)
    assess_parser = commands.add_parser("assess")
    for role in ROLES:
        assess_parser.add_argument("--" + role, required=True, type=Path)
    assess_parser.add_argument(
        "--min-docker-free-mib",
        type=int,
        help="Require this much free space on the Docker filesystem of each node",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            output = collect(args.role)
        else:
            nodes = {role: read_node(getattr(args, role), role) for role in ROLES}
            output = assess(nodes, datetime.now(UTC), min_docker_free_mib=args.min_docker_free_mib)
    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        OSError,
        subprocess.SubprocessError,
    ):
        print("Swarm readiness evidence unavailable or invalid.", file=sys.stderr)
        return 2
    print(json.dumps(output, indent=2, sort_keys=True))
    return int(args.command == "assess" and not output["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
