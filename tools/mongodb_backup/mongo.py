"""Canonical coordinator freeze and isolated, insert-only restoration gates."""

import hashlib
import re
import time
from contextlib import contextmanager

from bson import BSON, Int64, json_util
from pymongo import MongoClient, ReturnDocument, timeout
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from .security import BackupError, database_name, require
from .streams import MONGO_RESTORE_TARGETS, deadline_check

MARKER = "_cinevault_restore_claim"


def canonical(value):
    return json_util.dumps(
        value,
        json_options=json_util.CANONICAL_JSON_OPTIONS,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def connect(config):
    return MongoClient(
        config["uri"],
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
        timeoutMS=5000,
        appname="cinevault-portable-backup",
    )


def primary(client):
    value = client.admin.command("hello")
    require(
        value.get("isWritablePrimary") is True
        and value.get("setName")
        and value.get("topologyVersion", {}).get("processId"),
        "replica_primary_required",
    )
    return {
        "replica_set": value["setName"],
        "process_id": str(value["topologyVersion"]["processId"]),
    }


def instance_digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def version(client):
    value = client.server_info()["version"]
    require(
        isinstance(value, str) and value in MONGO_RESTORE_TARGETS,
        "mongo_server_version_not_qualified",
    )
    return value


def fingerprint(database, deadline, *, ignore_marker=False):
    """O(one BSON document) memory; BSON preserves Int64 and embedded field order."""
    result = {}
    for item in sorted(database.list_collections(), key=lambda item: item["name"]):
        deadline_check(deadline)
        name = item["name"]
        if name == MARKER and ignore_marker:
            continue
        require(
            re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name)
            and item.get("type") == "collection",
            "unsupported_collection_type",
        )
        options = item.get("options", {})
        require(
            not any(
                key in options for key in ("timeseries", "capped", "encryptedFields")
            ),
            "unsupported_collection_options",
        )
        indexes = []
        for index in database[name].list_indexes():
            index = dict(index)
            require(
                "expireAfterSeconds" not in index,
                "ttl_writers_must_be_disabled_explicitly",
            )
            index["key"] = list(index["key"].items())
            index.pop("ns", None)
            indexes.append(index)
        indexes.sort(key=lambda index: index["name"])
        digest = hashlib.sha256()
        count = 0
        with database[name].find({}).sort("_id", 1).batch_size(128) as cursor:
            for document in cursor:
                deadline_check(deadline)
                digest.update(BSON.encode(document))
                count += 1
        result[name] = {
            "count": count,
            "documents_sha256": digest.hexdigest(),
            "options_sha256": hashlib.sha256(canonical(options)).hexdigest(),
            "indexes_sha256": hashlib.sha256(canonical(indexes)).hexdigest(),
            "index_count": len(indexes),
        }
    coordinate = database.coordination.find_one({"_id": "business"})
    require(
        coordinate
        and type(coordinate.get("revision")) is Int64
        and 0 <= coordinate["revision"] < 2**63 - 1,
        "canonical_coordinator_required",
    )
    return {"revision": int(coordinate["revision"]), "collections": result}


@contextmanager
def frozen(source, freezer, name, seconds):
    """The uncommitted coordinator write conflicts with every canonical writer."""
    database_name(name)
    require(type(seconds) is int and 1 <= seconds <= 45, "freeze_bound_1_to_45_seconds")
    require(primary(source) == primary(freezer), "source_and_freezer_primary_mismatch")
    identity = primary(source)
    deadline = time.monotonic() + seconds
    started = time.monotonic()
    with freezer.start_session() as session:
        session.start_transaction(
            read_concern=ReadConcern("snapshot"),
            write_concern=WriteConcern("majority", wtimeout=5000),
        )
        try:
            held = freezer[name].coordination.find_one_and_update(
                {
                    "_id": "business",
                    "revision": {"$gte": Int64(0), "$lt": Int64(2**63 - 1)},
                },
                {"$inc": {"revision": Int64(1)}},
                return_document=ReturnDocument.AFTER,
                session=session,
            )
            require(
                held and type(held.get("revision")) is Int64,
                "canonical_coordinator_required",
            )
            before = fingerprint(source[name], deadline)
            require(
                before["revision"] + 1 == held["revision"],
                "coordinator_freeze_mismatch",
            )
            state = {"inventory": before, "instance": identity, "deadline": deadline}
            yield state
            deadline_check(deadline)
            require(
                freezer[name].coordination.find_one(
                    {"_id": "business"}, session=session
                )
                == held
                and session.in_transaction,
                "freeze_not_alive_after_dump",
            )
            require(
                primary(source) == identity == primary(freezer),
                "primary_changed_during_dump",
            )
            require(
                fingerprint(source[name], deadline) == before,
                "source_changed_during_dump",
            )
            session.abort_transaction()
            require(
                source[name].coordination.find_one({"_id": "business"})["revision"]
                == before["revision"],
                "coordinator_abort_not_verified",
            )
            state["freeze_seconds"] = round(time.monotonic() - started, 3)
        finally:
            if session.in_transaction:
                session.abort_transaction()


def claim_target(client, name, manifest, operation_id):
    database_name(name)
    require(
        name != manifest["source_database"], "source_database_name_refused_as_target"
    )
    require(
        instance_digest(primary(client)) != manifest["source_instance_sha256"],
        "same_source_process_refused_as_target",
    )
    require(
        version(client) in MONGO_RESTORE_TARGETS.get(manifest["mongo_version"], ()),
        "source_target_version_mismatch",
    )
    database = client[name]
    require(not database.list_collection_names(), "target_database_not_empty")
    # create, never upsert: concurrent invocations cannot both own this target.
    database.create_collection(MARKER)
    database[MARKER].insert_one(
        {"_id": operation_id, "state": "QUARANTINED_UNTIL_VERIFIED"}
    )
    require(database.list_collection_names() == [MARKER], "target_changed_during_claim")
    return database


def finish_target(database, expected, operation_id, deadline):
    deadline_check(deadline)
    require(
        database[MARKER].find_one({"_id": operation_id})
        == {"_id": operation_id, "state": "QUARANTINED_UNTIL_VERIFIED"},
        "target_claim_lost",
    )
    require(
        fingerprint(database, deadline, ignore_marker=True) == expected,
        "restored_inventory_mismatch_target_quarantined",
    )
    identity = primary(database.client)
    remaining = deadline - time.monotonic()
    require(remaining > 0, "operation_deadline_exceeded")
    try:
        with timeout(min(5, remaining)):
            database[MARKER].drop()
            deadline_check(deadline)
            require(primary(database.client) == identity, "finalization_unknown")
            require(
                MARKER not in database.list_collection_names(), "finalization_unknown"
            )
            deadline_check(deadline)
        return
    except Exception:  # noqa: BLE001, S110 - uncertain ACK: reconcile without leaking driver secrets.
        # The server may have removed the marker before its ACK was lost. Never
        # replay this write, recreate the marker, drop the DB or rerun restore.
        pass

    # An unconfirmed outcome gets one read-only reconciliation, with its own
    # <=5s budget inside the original deadline. Recheck the whole inventory only
    # on this uncertain path; an ordinary acknowledged drop needs no rescan.
    reconciliation_deadline = min(deadline, time.monotonic() + 5)
    try:
        deadline_check(reconciliation_deadline)
        with timeout(reconciliation_deadline - time.monotonic()):
            require(primary(database.client) == identity, "finalization_unknown")
            require(
                MARKER not in database.list_collection_names(), "finalization_unknown"
            )
            require(
                fingerprint(database, reconciliation_deadline, ignore_marker=True)
                == expected,
                "finalization_unknown",
            )
            require(primary(database.client) == identity, "finalization_unknown")
            deadline_check(reconciliation_deadline)
    except Exception:  # noqa: BLE001 - every unconfirmed outcome stays fail-closed.
        raise BackupError("finalization_unknown") from None
