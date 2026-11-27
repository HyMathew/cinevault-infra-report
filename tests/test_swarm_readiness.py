"""Protect the read-only staging preflight decisions."""

from datetime import UTC, datetime, timedelta

import pytest

from scripts import check_swarm_readiness as probe


def test_docker_uses_the_local_engine_despite_an_active_context(monkeypatch):
    monkeypatch.setenv("DOCKER_CONTEXT", "unrelated")

    def run(command, **options):
        assert command == [
            "docker",
            "--host",
            "unix:///var/run/docker.sock",
            "node",
            "ls",
        ]
        assert "DOCKER_CONTEXT" not in options["env"]
        return probe.subprocess.CompletedProcess(command, 0, stdout="node\n")

    monkeypatch.setattr(probe.subprocess, "run", run)
    assert probe.docker("node", "ls") == ["node"]


@pytest.fixture
def snapshots():
    now = datetime(2026, 11, 26, tzinfo=UTC)
    keys = {role: str(index) * 64 for index, role in enumerate(probe.ROLES, 1)}
    nodes = {
        role: {
            "role": role,
            "node_sha256": key,
            "active_swarm": True,
            "control": role == "manager",
            "timestamp_utc": (now - timedelta(seconds=5)).isoformat(),
            "logical_cpus": 2,
            "available_ram_bytes": 1300 * probe.MIB,
            "docker_available_disk_bytes": 6000 * probe.MIB,
            "conflicting_volumes": 0,
        }
        for role, key in keys.items()
    }
    service = {"replicas": 1, "image_digest": "sha256:" + "a" * 64}
    for role in probe.SERVICES:
        nodes[role]["observed"] = {
            "task_count": 1,
            "healthy": True,
            "image_digest": service["image_digest"],
        }
    members = {
        key: {
            "ready": True,
            "active": role != "manager",
            "drain": role == "manager",
            "leader": role == "manager",
            "manager": role == "manager",
            "label": role if role in probe.SERVICES else None,
        }
        for role, key in keys.items()
    }
    nodes["manager"]["observed"] = {
        "members": members,
        "services": {role: service.copy() for role in probe.SERVICES},
        "conflicts": {kind: 0 for kind in probe.MANAGER_OBJECTS},
    }
    return nodes, now


def test_assess_preserves_capacity_snapshot_shape(snapshots):
    nodes, now = snapshots
    result = probe.assess(nodes, now)
    assert result["passed"]
    assert result["nodes"] == nodes
    assert result["checked_at_utc"] == now.isoformat()
    assert "minimum_docker_free_mib" not in result


def test_assess_enforces_the_supplied_disk_budget(snapshots):
    nodes, now = snapshots
    limited = nodes["api"]
    limited["docker_available_disk_bytes"] = 3000 * probe.MIB - 1
    result = probe.assess(nodes, now, min_docker_free_mib=3000)
    assert result["minimum_docker_free_mib"] == 3000
    assert result["checks"]["resources_measured"]
    assert result["checks"]["web_disk"] and result["checks"]["manager_disk"]
    assert not result["checks"]["api_disk"] and not result["passed"]
    limited["docker_available_disk_bytes"] += 1
    assert probe.assess(nodes, now, min_docker_free_mib=3000)["passed"]


@pytest.mark.parametrize("minimum", [0, -1, True])
def test_assess_refuses_invalid_disk_budget(snapshots, minimum):
    nodes, now = snapshots
    with pytest.raises(ValueError, match="positive integer"):
        probe.assess(nodes, now, min_docker_free_mib=minimum)


@pytest.mark.parametrize(
    ("path", "value", "failed"),
    [
        (("api", "available_ram_bytes"), 1152 * probe.MIB - 1, "api_memory"),
        (("web", "observed", "task_count"), 2, "web_stable_healthy"),
        (
            ("api", "observed", "image_digest"),
            "sha256:" + "b" * 64,
            "api_stable_healthy",
        ),
        (("manager", "observed", "conflicts"), {}, "stage_names_available"),
        (("manager", "observed", "conflicts", "secret"), 1, "stage_names_available"),
        (("api", "conflicting_volumes"), 1, "stage_names_available"),
        (("api", "node_sha256"), "1" * 64, "distinct_ready_nodes"),
        (
            ("manager", "observed", "members", "3" * 64, "drain"),
            False,
            "manager_drained_leader",
        ),
        (("manager", "observed", "members", "2" * 64, "label"), "web", "api_placement"),
        (
            ("web", "timestamp_utc"),
            "2026-11-25T23:44:59+00:00",
            "contemporaneous_snapshots",
        ),
        (
            ("web", "timestamp_utc"),
            "2026-11-26T00:00:01+00:00",
            "contemporaneous_snapshots",
        ),
    ],
)
def test_assess_refuses_out_of_policy_input(snapshots, path, value, failed):
    nodes, now = snapshots
    destination = nodes
    for key in path[:-1]:
        destination = destination[key]
    destination[path[-1]] = value
    result = probe.assess(nodes, now)
    assert result["checks"][failed] is False
    assert not result["passed"]
