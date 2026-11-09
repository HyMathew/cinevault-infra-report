"""Generate/check explicitly fictional examples using the adjacent, unchanged API.

Run with the API development venv, offline. All application state lives in a new
TemporaryDirectory. Only --write writes artifacts, under docs/examples/academic-json.
Neither this script nor its examples are a deployment or account provisioning tool.
"""

import argparse
import copy
import hashlib
import hmac
import importlib.metadata
import ipaddress
import itertools
import json
import re
import socket
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
NOW = 1700000000
PASSWORD = "FICTIF apprentissage uniquement 123"
PUBLISHED_TOKEN = "FICTIVE-NONFUNCTIONAL-EXPIRED-TOKEN-0000"
DUMMY_KEY = b"FICTIVE-LOCAL-ONLY-KEY-00000000000"
HASH_PLACEHOLDER = "$argon2id$FICTIF-INUTILISABLE-NON-CRYPTOGRAPHIQUE"
API_REVISION_EXPECTED = "6a86f2e"
SOURCE_FINGERPRINT_MODE = "sha256:utf8-lf:v1"
BASE = Path(__file__).resolve().parents[1]
DESTINATION = BASE / "docs/examples/academic-json"
ARTIFACT_NAMES = {
    "openapi-components.json",
    "http-exchanges.json",
    "enterprise-store.synthetic.json",
    "lifecycle.json",
    "metadata-cache.synthetic.json",
    "registration-admission.synthetic.json",
    "client-context.synthetic.json",
    "legacy-catalogue.synthetic.json",
    "recovery-report.synthetic.json",
    "recovered-store.synthetic.json",
    "catalogue-export.synthetic.csv",
    "technical-schemas.json",
}

# RFC 3986 syntax, without resolution or a network request. The optional jsonschema
# URI dependency is absent from the API venv, so its default checker skips "uri".
_PCHAR = r"(?:[A-Za-z0-9._~!$&'()*+,;=:@-]|%[0-9A-Fa-f]{2})"
_REGNAME = r"(?:[A-Za-z0-9._~!$&'()*+,;=-]|%[0-9A-Fa-f]{2})*"
_USERINFO = r"(?:[A-Za-z0-9._~!$&'()*+,;=:-]|%[0-9A-Fa-f]{2})*"
_AUTHORITY = rf"(?:{_USERINFO}@)?(?:{_REGNAME}|(?P<literal>\[[^\]]+\]))(?::[0-9]*)?"
_ABSOLUTE = rf"/(?:{_PCHAR}+(?:/{_PCHAR}*)*)?"
_ROOTLESS = rf"{_PCHAR}+(?:/{_PCHAR}*)*"
_URI = re.compile(
    rf"[A-Za-z][A-Za-z0-9+.-]*:(?://{_AUTHORITY}(?:/{_PCHAR}*)*|{_ABSOLUTE}|{_ROOTLESS}|)"
    rf"(?:\?(?:{_PCHAR}|[/?])*)?(?:\#(?:{_PCHAR}|[/?])*)?"
)


def valid_uri(value):
    if not isinstance(value, str):
        return True  # JSON Schema applies format only to strings.
    match = _URI.fullmatch(value)
    if match is None:
        return False
    literal = match.group("literal")
    if literal is None:
        return True
    address = literal[1:-1]
    if re.fullmatch(r"[vV][0-9A-Fa-f]+\.[A-Za-z0-9._~!$&'()*+,;=:-]+", address):
        return True
    try:
        ipaddress.IPv6Address(address)
    except ValueError:
        return False
    return "%" not in address


def technical_schemas():
    """General technical contracts derived from the API readers, not fixture values."""

    def strict(properties, **annotations):
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
            **annotations,
        }

    integer = {"type": "integer", "minimum": 0}
    digest = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    identity = {
        "type": "string",
        "format": "uuid",
        "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    }
    text = {"type": "string", "pattern": r"^[^\ud800-\udfff]*$"}

    def canonical_text(limit):
        return {
            "type": "string",
            "minLength": 1,
            "maxLength": limit,
            "pattern": r"^\S(?:[\s\S]*\S)?$",
            "allOf": [text, {"not": {"pattern": r"^\s|\s$"}}],
        }

    legacy_film = strict(
        {
            "id": identity,
            "titre": canonical_text(200),
            "annee": {"type": "integer", "minimum": 1888, "maximum": 2100},
            "realisateur": canonical_text(120),
            "acteurs": {"type": "array", "maxItems": 30, "items": canonical_text(120)},
            "support": {"enum": ["numerique", "dvd", "blu-ray", "vhs", "autre"]},
            "synopsis": {**text, "maxLength": 4000},
        }
    )
    cache_entry = strict(
        {
            "stored_at": integer,
            "expires_at": integer,
            "stale_until": integer,
            "value": {
                "type": "object",
                "not": {"required": ["cache"]},
                "additionalProperties": True,
                "$comment": "MetadataCache.check_value permits arbitrary JSON object values except cache; UTF-8 size <=32768 bytes is checked by code.",
            },
        }
    )
    headers = {
        "type": "object",
        "required": [
            "Content-Type",
            "X-CineVault-Client-IP",
            "X-CineVault-Client-Time",
            "X-CineVault-Client-Signature",
        ],
        "properties": {
            "Content-Type": {"const": "application/json"},
            "X-CineVault-Client-IP": {
                "type": "string",
                "maxLength": 45,
                "not": {"pattern": "%"},
                "anyOf": [{"format": "ipv4"}, {"format": "ipv6"}],
            },
            "X-CineVault-Client-Time": {
                "type": "string",
                "pattern": "^(?:0|[1-9][0-9]{0,9})$",
            },
            "X-CineVault-Client-Signature": digest,
        },
        "additionalProperties": text,
        "$comment": "The native HTTP boundary permits other headers; only the selected JSON carrier fields are described here.",
    }
    definitions = {
        "LegacyCatalogue": strict(
            {"films": {"type": "array", "items": legacy_film}},
            description="Persistent legacy catalogue; Repository._read and validation.validate. Distinct film IDs remain checked by Repository.",
        ),
        "Health": strict(
            {"status": {"type": "string", "const": "ok"}},
            description="Successful /health carrier emitted by create_app; actual storage availability is checked by the handler.",
        ),
        "RecoveryReport": strict(
            {
                "operation_id": identity,
                "source_sha256": digest,
                "target_sha256": digest,
                "disabled_users": integer,
                "revoked_sessions": integer,
                "closed_reservations": integer,
            },
            description="Report emitted by recovery.recover. File digests, source counts and quarantine effects require executable checks.",
        ),
        "MetadataCache": strict(
            {
                "version": {"type": "integer", "const": 1},
                "window_start": integer,
                "count": {"type": "integer", "minimum": 0, "maximum": 20},
                "blocked_until": integer,
                "entries": {
                    "type": "object",
                    "maxProperties": 100,
                    "propertyNames": digest,
                    "additionalProperties": cache_entry,
                },
            },
            description="MetadataCache.read/check_value. TTL=86400, grace=604800, relative clocks and byte limits are checked by code.",
        ),
        "ClientContext": strict(
            {
                "fictional_key_hex": {
                    "type": "string",
                    "pattern": "^(?:[0-9a-f]{2}){32,}$",
                },
                "body_utf8": text,
                "headers": headers,
                "signed_message": {
                    "type": "string",
                    "pattern": r"^cinevault-client-v1\n(?:0|[1-9][0-9]{0,9})\n[^\n]+\nPOST\n/api/v1/auth/(?:login|register)\n[0-9a-f]{64}$",
                },
                "accepted_only_at_fictional_clock": integer,
                "rejected_at": integer,
            },
            description="Serialized synthetic context carrier generated by this tool, with native header constraints from client_context.client_address. HMAC, canonical IP, exact body binding and freshness require executable checks.",
        ),
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:cinevault:academic:technical:1",
        "title": "CineVault technical academic contracts",
        "$defs": definitions,
    }


def encoded(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def source_sha256(path):
    """Fingerprint UTF-8 source text with LF line endings, retaining all other text."""
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return sha256(text.encode("utf-8"))


def verify_source_fingerprints(api_root, manifest):
    assert manifest["source_fingerprint_mode"] == SOURCE_FINGERPRINT_MODE
    for name, digest in manifest["api_source_sha256"].items():
        source = (api_root / name).resolve()
        assert source.is_relative_to(api_root)
        assert source_sha256(source) == digest, "API source differs: " + name


def load_artifacts(destination, *, allow_previous=False):
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    names = set(manifest["artifact_sha256"])
    previous = ARTIFACT_NAMES - {"technical-schemas.json"}
    migration = allow_previous and names == previous
    if migration:
        assert not (destination / "technical-schemas.json").exists(), (
            "Unowned technical schema file would be overwritten"
        )
    assert names == ARTIFACT_NAMES or migration, (
        "Unexpected fixture path or incomplete manifest"
    )
    artifacts = {}
    for name, digest in manifest["artifact_sha256"].items():
        content = (destination / name).read_bytes()
        assert sha256(content) == digest, "Artifact checksum differs: " + name
        artifacts[name] = (
            content.decode("utf-8") if name.endswith(".csv") else json.loads(content)
        )
    return artifacts, manifest


def pointer_part(value):
    return value.replace("~", "~0").replace("/", "~1")


def resolve(document, pointer):
    value = document
    for key in pointer.removeprefix("#/").split("/"):
        value = value[key.replace("~1", "/").replace("~0", "~")]
    return value


def expand(document, value):
    return resolve(document, value["$ref"]) if "$ref" in value else value


def schema_validate(specification, schema, value):
    from jsonschema import Draft202012Validator, FormatChecker

    schema = {
        **schema,
        "components": specification.get("components", {}),
        "$defs": specification.get("$defs", {}),
    }
    checker = FormatChecker()
    checker.checks("uri")(valid_uri)
    Draft202012Validator(schema, format_checker=checker).validate(value)


def neutralize(value):
    """Published bearer and password hashes can never authenticate in the examples."""
    if isinstance(value, list):
        return [neutralize(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: neutralize(item) for key, item in value.items()}
    if "token" in result:
        result["token"] = PUBLISHED_TOKEN
    if "password_hash" in result:
        result["password_hash"] = HASH_PLACEHOLDER
    if "token_hash" in result:
        # Distinct from the published token; all sessions also use a historical clock.
        result["token_hash"] = sha256(
            ("FICTIVE-UNPUBLISHED-SESSION:" + result["id"]).encode()
        )
    return result


class Evidence:
    def __init__(self, specification):
        self.spec = specification
        self.components = {}
        self.exchanges = []
        self.checks = []

    def component(self, name, value):
        self.components.setdefault(name, neutralize(copy.deepcopy(value)))

    def call(
        self,
        client,
        name,
        method,
        path,
        *,
        body=None,
        headers=None,
        status=200,
        component=None,
    ):
        kwargs = {"headers": headers or {}}
        if body is not None:
            kwargs["json"] = body
        response = client.open(path, method=method, **kwargs)
        if response.status_code != status:
            raise AssertionError(
                f"{name}: expected {status}, received {response.status_code}: {response.get_json()}"
            )
        value = response.get_json(silent=True)
        record = {
            "name": name,
            "method": method,
            "path": path,
            "request_body": body,
            "status": status,
            "response_body": value,
            "response_headers": {
                key: response.headers[key]
                for key in ("ETag", "Location", "Retry-After", "Idempotency-Replayed")
                if key in response.headers
            },
        }
        self.exchanges.append(neutralize(record))
        if component:
            self.component(component, value)
        if value and isinstance(value, dict) and "_etag" in value:
            from app.enterprise_catalogue import etag

            assert value["_etag"] == etag(
                {key: item for key, item in value.items() if key != "_etag"}
            )
        return value


class FictionalProvider:
    """No transport: synthetic values through the actual shared MetadataCache."""

    def __init__(self, path):
        from app.metadata import MetadataCache

        self.clock = NOW
        self.fail = False
        self.cache = MetadataCache(path, lambda: self.clock)
        self.poster = {
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/FICTIF_INEXISTANT.jpg",
            "source_url": "https://commons.wikimedia.org/wiki/File:FICTIF_INEXISTANT.jpg",
            "artist": "Artiste entièrement fictif — aucun média consulté",
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "attribution_required": True,
        }

    def fetch(self, key, value):
        from app.metadata import MetadataUnavailable

        def obtain(reserve):
            reserve()
            if self.fail:
                raise MetadataUnavailable()
            return copy.deepcopy(value)

        return self.cache.fetch(key, obtain)

    def film(self, identity):
        return {
            "id": identity,
            "title": "Le Voyage de papier — FICTIF",
            "year": 2001 if identity == "Q123" else None,
            "director": "A. Martin FICTIF",
            "actors": ["B. Durand FICTIF"],
            "genres": ["Aventure"],
            "description": "Proposition synthétique, aucune source externe interrogée.",
            "poster_filename": "FICTIF_INEXISTANT.jpg" if identity == "Q123" else None,
            "poster": self.poster if identity == "Q123" else None,
            "revision": 123,
            "retrieved_at": NOW,
            "source_url": "https://www.wikidata.org/wiki/" + identity,
            "warnings": [
                "Données et attribution fictives ; aucun droit de média vérifié."
            ],
        }

    def detail(self, identity):
        return self.fetch("detail:" + identity, {"film": self.film(identity)})

    def search(self, query):
        return self.fetch(
            "search:" + query,
            {
                "items": [
                    {
                        "id": "Q123",
                        "title": "Le Voyage de papier — FICTIF",
                        "description": "Résultat entièrement synthétique.",
                        "source_url": "https://www.wikidata.org/wiki/Q123",
                    }
                ]
            },
        )


def application(root, clock, filename="enterprise.json"):
    from app import create_app
    from app.storage_v2 import V2Store

    path = root / filename
    V2Store(path).initialize()
    app = create_app(
        {
            "TESTING": True,
            "DATA_FILE": str(root / (filename + ".legacy.json")),
            "ENTERPRISE_ENABLED": True,
            "ENTERPRISE_DATA_FILE": str(path),
            "AUTH_THROTTLE_KEY": DUMMY_KEY,
            "CLIENT_CONTEXT_KEY": DUMMY_KEY,
            "CLIENT_CONTEXT_REQUIRED": False,
            "METADATA_ENABLED": False,
            "AUTH_CLOCK": lambda: clock[0],
        }
    )
    return app.test_client(), path


def build(api_root):
    from app.metadata import TTL
    from app.storage_v2 import V2Store, validate_document

    specification = json.loads(
        (api_root / "docs/openapi-v1.json").read_text(encoding="utf-8")
    )
    evidence = Evidence(specification)
    clock = [NOW]
    with tempfile.TemporaryDirectory(
        prefix="cinevault-fictional-examples-"
    ) as temporary:
        root = Path(temporary)
        client, path = application(root, clock)
        store = V2Store(path)
        call = lambda *args, **kwargs: evidence.call(client, *args, **kwargs)
        provider = FictionalProvider(root / "metadata-cache.json")
        client.application.extensions["metadata_client"] = provider

        accounts, auth = {}, {}
        for username, role in [
            ("fictif-admin", "admin"),
            ("fictif-alice", "member"),
            ("fictif-bob", "member"),
            ("fictif-carol", "member"),
            ("fictif-dave", "member"),
            ("fictif-aux", "member"),
        ]:
            profile = call(
                "register-" + username,
                "POST",
                "/api/v1/auth/register",
                body={
                    "username": username,
                    "display_name": username + " — FICTIF",
                    "password": PASSWORD,
                },
                status=201,
                component="Profile",
            )
            accounts[username] = profile
            if role == "admin":
                store.transact(
                    lambda document, profile=profile: next(
                        user
                        for user in document["users"]
                        if user["id"] == profile["id"]
                    ).update(role="admin")
                )
            login = call(
                "login-" + username,
                "POST",
                "/api/v1/auth/login",
                body={"username": username, "password": PASSWORD},
                component="Token",
            )
            auth[username] = {"Authorization": "Bearer " + login["token"]}
        admin, alice, bob, carol, dave, auxiliary = [
            auth["fictif-" + name]
            for name in ("admin", "alice", "bob", "carol", "dave", "aux")
        ]
        admission = client.application.extensions["registration_admission"].read(NOW)
        assert admission["total"] == 6 == sum(admission["sources"].values())
        evidence.checks.append(
            "admission: schema plus actual reader, total equals source counters"
        )

        call(
            "anonymous-profile-error",
            "GET",
            "/api/v1/me",
            status=401,
            component="Error",
        )
        call(
            "invalid-registration",
            "POST",
            "/api/v1/auth/register",
            body={"username": "bad", "display_name": "FICTIF", "password": "short"},
            status=422,
        )
        call(
            "profile-update",
            "PATCH",
            "/api/v1/me",
            headers=alice,
            body={"display_name": "Alice fictive — mise à jour"},
        )
        call(
            "metadata-search",
            "GET",
            "/api/v1/metadata/search?q=papier",
            headers=admin,
            component="MetadataSearch",
        )
        call(
            "metadata-detail",
            "GET",
            "/api/v1/metadata/Q123",
            headers=admin,
            component="MetadataDetail",
        )
        call(
            "metadata-without-year-poster",
            "GET",
            "/api/v1/metadata/Q124",
            headers=admin,
        )
        evidence.component("Poster", provider.poster)
        copy_input = {
            "support": "dvd",
            "location": "Rayon FICTIF A",
            "condition": "good",
        }
        movie_input = {
            "title": "Le Voyage de papier — FICTIF",
            "year": 2001,
            "director": "A. Martin FICTIF",
            "actors": ["B. Durand FICTIF"],
            "synopsis": "Une ville de papier entièrement inventée.",
            "genres": ["Aventure"],
        }
        create_body = {**movie_input, "external_id": "Q123", "initial_copy": copy_input}
        movie_a = call(
            "movie-create-with-copy",
            "POST",
            "/api/v1/movies",
            headers=admin,
            body=create_body,
            status=201,
            component="Movie",
        )
        evidence.component("MovieCreate", create_body)
        evidence.component("MovieInput", movie_input)
        evidence.component("CopyInput", copy_input)
        copies = call(
            "copy-list",
            "GET",
            "/api/v1/copies?movie_id=" + movie_a["id"],
            component="CopyList",
        )["copies"]
        copy_a = copies[0]
        evidence.component("Copy", copy_a)
        call(
            "public-posters",
            "GET",
            "/api/v1/posters?movie_id=" + movie_a["id"],
            component="Posters",
        )
        movie_b = call(
            "second-movie",
            "POST",
            "/api/v1/movies",
            headers=admin,
            body={**movie_input, "title": "Les Archives du vent — FICTIF"},
            status=201,
        )
        movie_c = call(
            "recommendation-candidate",
            "POST",
            "/api/v1/movies",
            headers=admin,
            body={**movie_input, "title": "Échos d’encre — FICTIF"},
            status=201,
        )
        copy_create = {"movie_id": movie_b["id"], **copy_input}
        evidence.component("CopyCreate", copy_create)
        copy_b = call(
            "idempotent-copy-create",
            "POST",
            "/api/v1/copies",
            headers={**admin, "Idempotency-Key": "FICTIVE-copy-operation-0001"},
            body=copy_create,
            status=201,
        )
        replay = call(
            "idempotent-copy-replay",
            "POST",
            "/api/v1/copies",
            headers={**admin, "Idempotency-Key": "FICTIVE-copy-operation-0001"},
            body=copy_create,
            status=201,
        )
        assert replay == copy_b
        call(
            "movie-update",
            "PUT",
            "/api/v1/movies/" + movie_b["id"],
            headers={**admin, "If-Match": movie_b["_etag"]},
            body={**movie_input, "title": movie_b["title"]},
        )
        call(
            "copy-update",
            "PUT",
            "/api/v1/copies/" + copy_b["id"],
            headers={**admin, "If-Match": copy_b["_etag"]},
            body=copy_input,
        )
        call("movie-list", "GET", "/api/v1/movies", component="MovieList")
        call("movie-get", "GET", "/api/v1/movies/" + movie_a["id"])
        call("copy-get", "GET", "/api/v1/copies/" + copy_a["id"])
        entries = []
        for kind, movie in [
            ("favorite", movie_a),
            ("watched", movie_a),
            ("owned", movie_b),
            ("custom", movie_c),
            ("watchlist", movie_c),
        ]:
            body = {
                "movie_id": movie["id"],
                "kind": kind,
                "list_name": "Mes films FICTIFS" if kind == "custom" else "",
                "supports": ["dvd"] if kind == "owned" else [],
            }
            entries.append(
                call(
                    "collection-" + kind,
                    "POST",
                    "/api/v1/collections",
                    headers=alice,
                    body=body,
                    status=201,
                    component="CollectionEntry",
                )
            )
            evidence.component("CollectionCreate", body)
        update = {"list_name": "Mes récits FICTIFS", "supports": []}
        evidence.component("CollectionUpdate", update)
        call(
            "collection-update",
            "PUT",
            "/api/v1/collections/" + entries[3]["id"],
            headers={**alice, "If-Match": entries[3]["_etag"]},
            body=update,
        )
        call(
            "collection-get",
            "GET",
            "/api/v1/collections/" + entries[0]["id"],
            headers=alice,
        )
        call(
            "collection-list",
            "GET",
            "/api/v1/collections",
            headers=alice,
            component="CollectionList",
        )

        loan = call(
            "loan-pending",
            "POST",
            "/api/v1/loans",
            headers=alice,
            body={"movie_id": movie_a["id"]},
            status=201,
            component="Loan",
        )
        loan_endpoint = "/api/v1/loans/" + loan["id"]
        call("loan-get", "GET", loan_endpoint, headers=alice)
        call(
            "loan-options",
            "GET",
            loan_endpoint + "/options",
            headers=admin,
            component="LoanOptions",
        )
        active = call(
            "loan-active",
            "POST",
            loan_endpoint + "/approve",
            headers={**admin, "If-Match": loan["_etag"]},
            body={"copy_id": copy_a["id"], "due_at": NOW + 86400},
        )
        reservations = []
        for name, headers in [("bob", bob), ("carol", carol), ("dave", dave)]:
            reservations.append(
                call(
                    "reservation-waiting-" + name,
                    "POST",
                    "/api/v1/reservations",
                    headers=headers,
                    body={"movie_id": movie_a["id"]},
                    status=201,
                    component="Reservation",
                )
            )
        cancelled_reservation = call(
            "reservation-cancelled",
            "POST",
            "/api/v1/reservations/" + reservations[1]["id"] + "/cancel",
            headers={**carol, "If-Match": reservations[1]["_etag"]},
        )
        returned = call(
            "loan-returned",
            "POST",
            loan_endpoint + "/return",
            headers={**admin, "If-Match": active["_etag"]},
        )
        bob_loan = call(
            "reserved-loan-pending",
            "POST",
            "/api/v1/loans",
            headers=bob,
            body={"movie_id": movie_a["id"]},
            status=201,
        )
        bob_active = call(
            "reserved-loan-active",
            "POST",
            "/api/v1/loans/" + bob_loan["id"] + "/approve",
            headers={**admin, "If-Match": bob_loan["_etag"]},
            body={"copy_id": copy_a["id"], "due_at": NOW + 86400},
        )
        fulfilled = call(
            "reservation-fulfilled",
            "GET",
            "/api/v1/reservations/" + reservations[0]["id"],
            headers=bob,
        )
        to_cancel = call(
            "cancel-request-pending",
            "POST",
            "/api/v1/loans",
            headers=carol,
            body={"movie_id": movie_b["id"]},
            status=201,
        )
        cancelled = call(
            "loan-cancelled",
            "POST",
            "/api/v1/loans/" + to_cancel["id"] + "/cancel",
            headers={**carol, "If-Match": to_cancel["_etag"]},
        )
        pending = call(
            "retained-pending-loan",
            "POST",
            "/api/v1/loans",
            headers=alice,
            body={"movie_id": movie_b["id"]},
            status=201,
        )
        clock[0] = reservations[2]["expires_at"] + 1
        for username in accounts:
            login = call(
                "renew-" + username,
                "POST",
                "/api/v1/auth/login",
                body={"username": username, "password": PASSWORD},
            )
            auth[username] = {"Authorization": "Bearer " + login["token"]}
        admin, alice, bob, carol, dave, auxiliary = [
            auth["fictif-" + name]
            for name in ("admin", "alice", "bob", "carol", "dave", "aux")
        ]
        expired = call(
            "reservation-expired",
            "GET",
            "/api/v1/reservations/" + reservations[2]["id"],
            headers=dave,
        )
        waiting = call(
            "retained-waiting-reservation",
            "POST",
            "/api/v1/reservations",
            headers=carol,
            body={"movie_id": movie_a["id"]},
            status=201,
        )
        # The first receipt expired during the 14-day jump; retain a fresh copy receipt.
        call(
            "retained-copy-receipt",
            "POST",
            "/api/v1/copies",
            headers={**admin, "Idempotency-Key": "FICTIVE-copy-operation-0002"},
            body={"movie_id": movie_c["id"], **copy_input},
            status=201,
        )
        call("loan-list", "GET", "/api/v1/loans", headers=admin, component="LoanList")
        call(
            "reservation-list",
            "GET",
            "/api/v1/reservations",
            headers=admin,
            component="ReservationList",
        )
        call(
            "availability",
            "GET",
            "/api/v1/availability?movie_id=" + movie_a["id"],
            component="Availability",
        )
        lifecycle = {
            "loans": {
                "pending": pending,
                "active": bob_active,
                "returned": returned,
                "cancelled": cancelled,
            },
            "reservations": {
                "waiting": waiting,
                "fulfilled": fulfilled,
                "cancelled": cancelled_reservation,
                "expired": expired,
            },
        }

        transfer = {
            "format_version": 1,
            "movies": [
                {**movie_input, "title": "Import JSON — FICTIF", "copies": [copy_input]}
            ],
        }
        request = {"format": "json", "content": transfer, "duplicate_policy": "reject"}
        evidence.component("ImportRequest", request)
        imported = call(
            "json-import",
            "POST",
            "/api/v1/catalogue/import",
            headers={**admin, "Idempotency-Key": "FICTIVE-import-json-0001"},
            body=request,
            component="ImportSummary",
        )
        assert imported["created_movies"] == imported["created_copies"] == 1
        call(
            "json-import-replay",
            "POST",
            "/api/v1/catalogue/import",
            headers={**admin, "Idempotency-Key": "FICTIVE-import-json-0001"},
            body=request,
        )
        for policy, status in [("reject", 409), ("skip", 200), ("append_copies", 200)]:
            call(
                "duplicate-policy-" + policy,
                "POST",
                "/api/v1/catalogue/import",
                headers={**admin, "Idempotency-Key": "FICTIVE-import-policy-" + policy},
                body={**request, "duplicate_policy": policy},
                status=status,
            )
        exported = call(
            "json-export",
            "GET",
            "/api/v1/catalogue/export?format=json",
            headers=admin,
            component="CatalogueExport",
        )
        evidence.component("CatalogueTransfer", exported["content"])
        csv_export = call(
            "csv-export", "GET", "/api/v1/catalogue/export?format=csv", headers=admin
        )
        csv_request = {
            "format": "csv",
            "content": csv_export["content"],
            "duplicate_policy": "skip",
        }
        call(
            "csv-import",
            "POST",
            "/api/v1/catalogue/import",
            headers={**admin, "Idempotency-Key": "FICTIVE-import-csv-0001"},
            body=csv_request,
        )
        call(
            "statistics-mine",
            "GET",
            "/api/v1/statistics",
            headers=alice,
            component="Statistics",
        )
        call("statistics-all", "GET", "/api/v1/statistics?scope=all", headers=admin)
        recommendations = call(
            "recommendations",
            "GET",
            "/api/v1/recommendations?genre=Aventure",
            headers=alice,
            component="Recommendations",
        )
        assert recommendations["recommendations"]
        assert all(
            item["score"] == sum(reason["points"] for reason in item["reasons"])
            for item in recommendations["recommendations"]
        )
        call("users-list", "GET", "/api/v1/users", headers=admin)
        call(
            "user-get",
            "GET",
            "/api/v1/users/" + accounts["fictif-alice"]["id"],
            headers=alice,
        )
        call(
            "user-admin-update",
            "PATCH",
            "/api/v1/users/" + accounts["fictif-dave"]["id"],
            headers=admin,
            body={"role": "member", "enabled": False},
        )
        call(
            "password-change",
            "PUT",
            "/api/v1/me/password",
            headers=auxiliary,
            body={"current_password": PASSWORD, "new_password": PASSWORD + " neuf"},
            status=204,
        )
        call("logout", "POST", "/api/v1/auth/logout", headers=bob, status=204)
        call(
            "audit-list",
            "GET",
            "/api/v1/audit-events",
            headers=admin,
            component="AuditList",
        )
        # Dedicated objects keep the four retained lifecycle states and their links intact.
        disposable_movie = call(
            "disposable-movie-create",
            "POST",
            "/api/v1/movies",
            headers=admin,
            body={**movie_input, "title": "Démonstration effacée — FICTIF"},
            status=201,
        )
        disposable_copy = call(
            "disposable-copy-create",
            "POST",
            "/api/v1/copies",
            headers=admin,
            body={"movie_id": disposable_movie["id"], **copy_input},
            status=201,
        )
        disposable_entry = call(
            "disposable-collection-create",
            "POST",
            "/api/v1/collections",
            headers=alice,
            body={"movie_id": disposable_movie["id"], "kind": "favorite"},
            status=201,
        )
        call(
            "collection-delete",
            "DELETE",
            "/api/v1/collections/" + disposable_entry["id"],
            headers={**alice, "If-Match": disposable_entry["_etag"]},
            status=204,
        )
        call(
            "copy-delete",
            "DELETE",
            "/api/v1/copies/" + disposable_copy["id"],
            headers={**admin, "If-Match": disposable_copy["_etag"]},
            status=204,
        )
        call(
            "movie-delete",
            "DELETE",
            "/api/v1/movies/" + disposable_movie["id"],
            headers={**admin, "If-Match": disposable_movie["_etag"]},
            status=204,
        )
        call(
            "failed-login-for-attempt",
            "POST",
            "/api/v1/auth/login",
            body={"username": "fictif-absent", "password": PASSWORD},
            status=401,
        )
        call("health", "GET", "/health")

        provider.clock = NOW + TTL + 1
        provider.fail = True
        stale = call(
            "metadata-stale-fallback", "GET", "/api/v1/metadata/Q123", headers=admin
        )
        assert stale["cache"]["status"] == "stale"
        cache_state = provider.cache.read(provider.clock)
        assert cache_state["entries"]
        evidence.checks.extend(
            [
                "metadata: real cache reader, TTL and grace, fresh/stale, public poster validator",
                "HTTP entity ETags recomputed for every captured versioned resource",
                "recommendation scores equal the sum of reason points",
                "copy creation and catalogue import replay receipts exercised",
                "loan and reservation state machines exercised by real handlers",
            ]
        )

        document = store.read()
        for collection, deleted in (
            ("movies", disposable_movie),
            ("copies", disposable_copy),
            ("collections", disposable_entry),
        ):
            assert all(item["id"] != deleted["id"] for item in document[collection])
        evidence.checks.append(
            "dedicated deleted movie, copy and collection entry are absent from the final snapshot"
        )
        validate_document(document)
        assert all(
            document[name]
            for name in (
                "users",
                "sessions",
                "auth_attempts",
                "idempotency_records",
                "movies",
                "copies",
                "collections",
                "loans",
                "reservations",
                "audit_events",
            )
        )
        assert {item["status"] for item in document["loans"]} == set(lifecycle["loans"])
        assert {item["status"] for item in document["reservations"]} == set(
            lifecycle["reservations"]
        )
        published_store = neutralize(document)
        validate_document(published_store)
        evidence.component("Stored_id", document["movies"][0]["id"])
        evidence.component("Stored_shortText", document["movies"][0]["director"])
        evidence.component("Stored_timestamp", NOW)
        for name, collection in [
            ("Stored_movie", "movies"),
            ("Stored_copy", "copies"),
            ("Stored_collection", "collections"),
            ("Stored_loan", "loans"),
            ("Stored_reservation", "reservations"),
            ("Stored_audit_event", "audit_events"),
        ]:
            evidence.component(name, document[collection][0])
        evidence.component("ExternalSource", movie_a["external_source"])
        # The fake prefix passes the storage shape but is deliberately not a password hash.
        store_file = root / "published-store.json"
        store_file.write_bytes(encoded(published_store))
        verifier_client = client.application.test_client()
        client.application.extensions["enterprise_store"] = V2Store(store_file)
        assert (
            verifier_client.get(
                "/api/v1/me", headers={"Authorization": "Bearer " + PUBLISHED_TOKEN}
            ).status_code
            == 401
        )
        assert (
            verifier_client.post(
                "/api/v1/auth/login",
                json={"username": "fictif-alice", "password": PASSWORD},
            ).status_code
            == 401
        )
        evidence.checks.append(
            "published token and published credentials both rejected at the fictional snapshot clock"
        )

        from app.recovery import recover

        # The rejected login changed attempt counters in its disposable copy only.
        store_file.write_bytes(encoded(published_store))
        recovered_path = root / "recovered.json"
        recovery_report = recover(
            store_file,
            recovered_path,
            sha256(store_file.read_bytes()),
            "fictif-recovery-admin",
            "Administrateur de reprise FICTIF",
            PASSWORD,
            timestamp=clock[0] + 1,
        )
        recovered_store = neutralize(
            json.loads(recovered_path.read_text(encoding="utf-8"))
        )
        validate_document(recovered_store)
        assert recovery_report["disabled_users"] == len(published_store["users"])
        assert recovery_report["revoked_sessions"] == len(published_store["sessions"])
        assert recovery_report["closed_reservations"] == 1
        assert recovered_store["sessions"] == []
        # Published recovery files are sanitized too: the carrier hash must describe
        # the published bytes, not the discarded temporary file with real Argon2 hashes.
        recovery_report["target_sha256"] = sha256(encoded(recovered_store))
        evidence.checks.append(
            "offline recover executed, quarantine/session revocation/queue closure checked; published target hash recomputed after neutralization"
        )

        from app import create_app

        legacy_client = create_app(
            {
                "TESTING": True,
                "DATA_FILE": str(root / "legacy-only.json"),
                "ENTERPRISE_ENABLED": False,
            }
        ).test_client()
        legacy_input = {
            "titre": "Le Voyage de papier — FICTIF",
            "annee": 2001,
            "realisateur": "A. Martin FICTIF",
            "acteurs": ["B. Durand FICTIF"],
            "support": "dvd",
            "synopsis": "Un récit fictif.",
        }
        evidence.call(
            legacy_client,
            "legacy-create",
            "POST",
            "/api/films",
            body=legacy_input,
            status=201,
        )
        legacy_document = evidence.call(
            legacy_client, "legacy-list", "GET", "/api/films"
        )

        login_body = {"username": "fictif-alice", "password": PASSWORD}
        raw = json.dumps(login_body, ensure_ascii=False, separators=(",", ":")).encode()
        message = "\n".join(
            (
                "cinevault-client-v1",
                str(clock[0]),
                "192.0.2.10",
                "POST",
                "/api/v1/auth/login",
                sha256(raw),
            )
        )
        signed_headers = {
            "Content-Type": "application/json",
            "X-CineVault-Client-IP": "192.0.2.10",
            "X-CineVault-Client-Time": str(clock[0]),
            "X-CineVault-Client-Signature": hmac.new(
                DUMMY_KEY, message.encode("ascii"), hashlib.sha256
            ).hexdigest(),
        }
        from app.client_context import InvalidClientContext, client_address

        with client.application.test_request_context(
            "/api/v1/auth/login", method="POST", data=raw, headers=signed_headers
        ):
            assert client_address(client.application, clock[0]) == "192.0.2.10"
            try:
                client_address(client.application, clock[0] + 31)
            except InvalidClientContext:
                pass
            else:
                raise AssertionError("Expired fictional context was accepted")
        context = {
            "fictional_key_hex": DUMMY_KEY.hex(),
            "body_utf8": raw.decode(),
            "headers": signed_headers,
            "signed_message": message,
            "accepted_only_at_fictional_clock": clock[0],
            "rejected_at": clock[0] + 31,
        }
        evidence.checks.append(
            "signed client context accepted at fixture clock, rejected after 31 seconds"
        )

    return {
        "openapi-components.json": evidence.components,
        "http-exchanges.json": evidence.exchanges,
        "enterprise-store.synthetic.json": published_store,
        "lifecycle.json": lifecycle,
        "metadata-cache.synthetic.json": cache_state,
        "registration-admission.synthetic.json": admission,
        "client-context.synthetic.json": context,
        "legacy-catalogue.synthetic.json": legacy_document,
        "recovery-report.synthetic.json": recovery_report,
        "recovered-store.synthetic.json": recovered_store,
        "catalogue-export.synthetic.csv": csv_export["content"],
        "technical-schemas.json": technical_schemas(),
    }, evidence.checks


def validate_artifacts(api_root, artifacts):
    from app.catalogue_transfer import normalize, parse_csv
    from app.enterprise_catalogue import etag
    from app.metadata import MetadataCache
    from app.registration_admission import RegistrationAdmission
    from app.storage_v2 import validate_document

    spec = json.loads((api_root / "docs/openapi-v1.json").read_text(encoding="utf-8"))
    components = artifacts["openapi-components.json"]
    assert set(components) == set(spec["components"]["schemas"]), (
        "OpenAPI component coverage differs"
    )
    for name, value in components.items():
        schema_validate(spec, {"$ref": "#/components/schemas/" + name}, value)
        if isinstance(value, dict) and "_etag" in value:
            assert value["_etag"] == etag(
                {key: item for key, item in value.items() if key != "_etag"}
            )
    document = artifacts["enterprise-store.synthetic.json"]
    store_schema = json.loads(
        (api_root / "schemas/catalogue-v2.schema.json").read_text(encoding="utf-8")
    )
    schema_validate(store_schema, store_schema, document)
    validate_document(document)
    defs = {
        "digest": document["sessions"][0]["token_hash"],
        "timestamp": NOW,
        "user": document["users"][0],
        "session": document["sessions"][0],
        "attempt": document["auth_attempts"][0],
        "reserved": [],
        "id": document["movies"][0]["id"],
        "shortText": "FICTIF",
        "movie": document["movies"][0],
        "copy": document["copies"][0],
        "collection": document["collections"][0],
        "audit_event": document["audit_events"][0],
        "loan": document["loans"][0],
        "reservation": document["reservations"][0],
        "cached_copy": next(
            record["response"]
            for record in document["idempotency_records"]
            if record["operation"] == "copy.create"
        ),
        "receipt": document["idempotency_records"][0],
        "import_summary": components["ImportSummary"],
        "external_source": components["ExternalSource"],
    }
    assert set(defs) == set(store_schema["$defs"])
    for name, value in defs.items():
        schema_validate(store_schema, {"$ref": "#/$defs/" + name}, value)
    lifecycle = artifacts["lifecycle.json"]
    assert set(lifecycle["loans"]) == {"pending", "active", "returned", "cancelled"}
    assert set(lifecycle["reservations"]) == {
        "waiting",
        "fulfilled",
        "cancelled",
        "expired",
    }
    for plural, name in [("loans", "Loan"), ("reservations", "Reservation")]:
        for state, value in lifecycle[plural].items():
            assert state == value["status"]
            schema_validate(spec, {"$ref": "#/components/schemas/" + name}, value)
            assert value["_etag"] == etag(
                {key: item for key, item in value.items() if key != "_etag"}
            )
    schema_locations = set()
    observed_operations = set()
    for exchange in artifacts["http-exchanges.json"]:
        actual_path = exchange["path"].split("?")[0]
        matches = [
            path
            for path in spec["paths"]
            if re.fullmatch(re.sub(r"\{[^}]+\}", "[^/]+", path), actual_path)
        ]
        if not matches:
            assert actual_path == "/health" or actual_path.startswith("/api/films")
            continue
        template = min(matches, key=lambda value: value.count("{"))
        observed_operations.add((exchange["method"], template))
        operation = spec["paths"][template][exchange["method"].lower()]
        prefix = "#/paths/" + pointer_part(template) + "/" + exchange["method"].lower()
        if "requestBody" in operation and exchange["request_body"] is not None:
            request_body = expand(spec, operation["requestBody"])
            schema = request_body["content"]["application/json"]["schema"]
            schema_validate(spec, schema, exchange["request_body"])
            location = (
                operation["requestBody"].get("$ref", prefix + "/requestBody")
                + "/content/application~1json/schema"
            )
            schema_locations.add(location)
        declaration = operation["responses"][str(exchange["status"])]
        response = expand(spec, declaration)
        if exchange["response_body"] is not None:
            schema = response["content"]["application/json"]["schema"]
            schema_validate(spec, schema, exchange["response_body"])
            value = exchange["response_body"]
            if isinstance(value, dict) and "_etag" in value:
                assert value["_etag"] == etag(
                    {key: item for key, item in value.items() if key != "_etag"}
                )
            schema_locations.add(
                declaration.get(
                    "$ref", prefix + "/responses/" + str(exchange["status"])
                )
                + "/content/application~1json/schema"
            )
        else:
            assert exchange["status"] == 204
    for name in spec["components"]["requestBodies"]:
        assert (
            "#/components/requestBodies/" + name + "/content/application~1json/schema"
            in schema_locations
        )
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if not isinstance(operation, dict):
                continue
            body = operation.get("requestBody", {})
            if "content" in body:
                assert (
                    "#/paths/"
                    + pointer_part(path)
                    + "/"
                    + method
                    + "/requestBody/content/application~1json/schema"
                    in schema_locations
                )
            for status, response in operation.get("responses", {}).items():
                schema = (
                    response.get("content", {})
                    .get("application/json", {})
                    .get("schema")
                )
                if schema and "$ref" not in schema:
                    assert (
                        "#/paths/"
                        + pointer_part(path)
                        + "/"
                        + method
                        + "/responses/"
                        + status
                        + "/content/application~1json/schema"
                        in schema_locations
                    )
    for location in schema_locations:
        assert isinstance(resolve(spec, location), dict)
    declared_operations = {
        (method.upper(), path)
        for path, item in spec["paths"].items()
        for method in item
        if method
        in {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
    }
    missing_operations = declared_operations - observed_operations
    assert not missing_operations, "Missing OpenAPI operations: " + repr(
        sorted(missing_operations)
    )
    transfer_schema = json.loads(
        (api_root / "schemas/catalogue-transfer-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    schema_validate(transfer_schema, transfer_schema, components["CatalogueTransfer"])
    normalize(components["CatalogueTransfer"])
    parsed_csv = parse_csv(artifacts["catalogue-export.synthetic.csv"])
    normalize(parsed_csv)
    with tempfile.TemporaryDirectory(
        prefix="cinevault-fixture-validation-"
    ) as temporary:
        root = Path(temporary)
        cache_path = root / "cache.json"
        cache_path.write_bytes(encoded(artifacts["metadata-cache.synthetic.json"]))
        cache = MetadataCache(cache_path)
        assert cache.read(NOW + 86401)["entries"]
        admission = RegistrationAdmission(root / "store.json")
        admission.path.write_bytes(
            encoded(artifacts["registration-admission.synthetic.json"])
        )
        assert admission.read(NOW)["total"] == 6
        from app.repository import Repository

        legacy_path = root / "legacy.json"
        legacy_path.write_bytes(encoded(artifacts["legacy-catalogue.synthetic.json"]))
        Repository(legacy_path).execute(lambda films: (len(films), False))
        from app.client_context import InvalidClientContext, client_address

        context = artifacts["client-context.synthetic.json"]
        fixture_clock = context["accepted_only_at_fictional_clock"]
        fresh_client, _ = application(root, [fixture_clock], "context-validation.json")
        assert bytes.fromhex(context["fictional_key_hex"]) == DUMMY_KEY
        raw = context["body_utf8"].encode("utf-8")
        headers = context["headers"]
        expected_message = "\n".join(
            (
                "cinevault-client-v1",
                str(fixture_clock),
                headers["X-CineVault-Client-IP"],
                "POST",
                "/api/v1/auth/login",
                sha256(raw),
            )
        )
        assert context["signed_message"] == expected_message
        assert (
            headers["X-CineVault-Client-Signature"]
            == hmac.new(
                DUMMY_KEY, expected_message.encode("ascii"), hashlib.sha256
            ).hexdigest()
        )
        with fresh_client.application.test_request_context(
            "/api/v1/auth/login", method="POST", data=raw, headers=headers
        ):
            assert (
                client_address(fresh_client.application, fixture_clock) == "192.0.2.10"
            )
            try:
                client_address(fresh_client.application, context["rejected_at"])
            except InvalidClientContext:
                pass
            else:
                raise AssertionError("Expired context accepted")
    recovered = artifacts["recovered-store.synthetic.json"]
    validate_document(recovered)
    schema_validate(store_schema, store_schema, recovered)
    report = artifacts["recovery-report.synthetic.json"]
    assert set(report) == {
        "operation_id",
        "source_sha256",
        "target_sha256",
        "disabled_users",
        "revoked_sessions",
        "closed_reservations",
    }
    uuid.UUID(report["operation_id"])
    assert report["source_sha256"] == sha256(encoded(document))
    assert report["target_sha256"] == sha256(encoded(recovered))
    assert report["disabled_users"] == len(document["users"])
    assert report["revoked_sessions"] == len(document["sessions"])
    assert report["closed_reservations"] == len(
        [item for item in document["reservations"] if item["status"] == "waiting"]
    )
    assert recovered["sessions"] == []
    assert sum(user["enabled"] for user in recovered["users"]) == 1
    assert all(
        user["password_hash"] == HASH_PLACEHOLDER
        for user in document["users"] + recovered["users"]
    )
    assert all(
        session["token_hash"] != sha256(PUBLISHED_TOKEN.encode())
        for session in document["sessions"]
    )
    admission_schema = json.loads(
        (api_root / "schemas/registration-admission.schema.json").read_text(
            encoding="utf-8"
        )
    )
    schema_validate(
        admission_schema,
        admission_schema,
        artifacts["registration-admission.synthetic.json"],
    )
    technical = artifacts["technical-schemas.json"]
    from jsonschema import Draft202012Validator

    Draft202012Validator.check_schema(technical)
    health_index = next(
        index
        for index, exchange in enumerate(artifacts["http-exchanges.json"])
        if exchange["name"] == "health"
    )
    technical_examples = {
        "LegacyCatalogue": (
            "legacy-catalogue.synthetic.json",
            artifacts["legacy-catalogue.synthetic.json"],
        ),
        "Health": (
            "http-exchanges.json#/" + str(health_index) + "/response_body",
            artifacts["http-exchanges.json"][health_index]["response_body"],
        ),
        "RecoveryReport": (
            "recovery-report.synthetic.json",
            artifacts["recovery-report.synthetic.json"],
        ),
        "MetadataCache": (
            "metadata-cache.synthetic.json",
            artifacts["metadata-cache.synthetic.json"],
        ),
        "ClientContext": (
            "client-context.synthetic.json",
            artifacts["client-context.synthetic.json"],
        ),
    }
    assert set(technical["$defs"]) == set(technical_examples)
    for name, (_, value) in technical_examples.items():
        schema_validate(technical, {"$ref": "#/$defs/" + name}, value)
    return {
        "openapi_components": sorted(components),
        "storage_defs": sorted(defs),
        "http_schema_locations": sorted(schema_locations),
        "http_exchange_count": len(artifacts["http-exchanges.json"]),
        "openapi_operations": [
            method + " " + path for method, path in sorted(observed_operations)
        ],
        "openapi_operation_count": len(observed_operations),
        "technical_schema_count": len(technical_examples),
        "technical_schema_examples": {
            name: location for name, (location, _) in technical_examples.items()
        },
    }


def main():
    if not __debug__:
        raise RuntimeError(
            "Run this validation tool without Python -O: assertions are required"
        )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-root", type=Path, default=BASE.parent / "cinevault-api")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Generate fixtures after all offline checks pass",
    )
    args = parser.parse_args()
    api_root = args.api_root.resolve()
    sys.path.insert(0, str(api_root))
    specification = json.loads(
        (api_root / "docs/openapi-v1.json").read_text(encoding="utf-8")
    )
    from jsonschema import Draft202012Validator

    for schema in specification["components"]["schemas"].values():
        Draft202012Validator.check_schema(schema)

    # Fail closed if any dependency attempts outbound transport.
    def no_network(*args, **kwargs):
        raise AssertionError(
            "Network access is forbidden in fictional example generation"
        )

    ids, tokens = itertools.count(1), itertools.count(1)
    with (
        patch.object(socket.socket, "connect", no_network),
        patch("socket.create_connection", no_network),
        patch("uuid.uuid4", side_effect=lambda: uuid.UUID(int=next(ids), version=4)),
        patch(
            "secrets.token_urlsafe",
            side_effect=lambda size=32: (
                "FICTIVE-TEMPORARY-TOKEN-" + str(next(tokens)).zfill(20)
            ),
        ),
    ):
        if args.write:
            artifacts, checks = build(api_root)
        else:
            artifacts, manifest = load_artifacts(DESTINATION)
            verify_source_fingerprints(api_root, manifest)
            checks = manifest["runtime_checks_executed_when_generated"]
        coverage = validate_artifacts(api_root, artifacts)
    if args.write:
        output = {
            name: value.encode("utf-8") if name.endswith(".csv") else encoded(value)
            for name, value in artifacts.items()
        }
        source_paths = sorted(
            list((api_root / "app").glob("*.py"))
            + list((api_root / "schemas").glob("*.schema.json"))
            + [api_root / "docs/openapi-v1.json"]
        )
        manifest = {
            "fictional": True,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "source_fingerprint_mode": SOURCE_FINGERPRINT_MODE,
            "generator_sha256": source_sha256(Path(__file__)),
            "regression_tests_sha256": source_sha256(
                BASE / "scripts/test_academic_json_examples.py"
            ),
            "regression_test_command": "python -B scripts/test_academic_json_examples.py -v",
            "api_revision_expected_from_task_not_git_verified": API_REVISION_EXPECTED,
            "clock_is_fictional_unix_seconds": NOW,
            "coverage": coverage,
            "artifact_sha256": {
                name: sha256(content) for name, content in sorted(output.items())
            },
            "api_source_sha256": {
                str(path.relative_to(api_root)).replace("\\", "/"): source_sha256(path)
                for path in source_paths
            },
            "runtime_checks_executed_when_generated": checks,
            "runtime_versions": {
                name: importlib.metadata.version(name)
                for name in ("Flask", "jsonschema", "argon2-cffi", "portalocker")
            },
            "formats": {
                "checked": ["uuid", "uri", "ipv4", "ipv6"],
                "annotation_only": ["password"],
            },
            "limitations": [
                "No network, server, VM, real account, live credential or external provider consulted.",
                "Wikidata IDs, URLs, media attribution and licences are illustrative only, not checked against real content or rights.",
                "Real Argon2 register/login ran only in temporary storage; published password hashes are invalid placeholders, tokens replaced, session digests unrelated and timestamps historical.",
                "All users and credentials are fictitious. Never import these snapshots into a real service.",
                "OpenAPI format password is an annotation; actual password rules were exercised by handlers. UUID/URI formats are checked by jsonschema FormatChecker.",
                "JSON Schema validates shape, not authorization, reference consistency or business chronology; validate_document and scenario assertions supplement it.",
                "The reserved storage definition is covered by [], not presented as an eleventh collection.",
                "Five additional academic technical JSON Schemas describe legacy, health, recovery report, metadata cache and serialized signed-context carrier. Native executable checks still enforce cross-field semantics, HMAC, freshness, byte lengths and sums.",
                "Offline recovery was executed only in the temporary scenario. Published recovered hashes were neutralized and the report target_sha256 recomputed for those published bytes; this is not a live restore receipt.",
                "Local execution is not a CI or deployment result. No security audit completeness claim.",
            ],
        }
        output["manifest.json"] = encoded(manifest)
        if (DESTINATION / "manifest.json").exists():
            load_artifacts(
                DESTINATION, allow_previous=True
            )  # Preserve any previously edited fixture by failing closed.
        DESTINATION.mkdir(parents=True, exist_ok=True)
        for name, content in output.items():
            (DESTINATION / name).write_bytes(content)
    print(
        json.dumps(
            {
                "result": "PASS",
                "mode": "generate" if args.write else "validate",
                "components": len(coverage["openapi_components"]),
                "storage_defs": len(coverage["storage_defs"]),
                "http_exchanges": coverage["http_exchange_count"],
                "http_schema_locations": len(coverage["http_schema_locations"]),
                "openapi_operations": coverage["openapi_operation_count"],
                "technical_schemas": coverage["technical_schema_count"],
                "output": str(DESTINATION.relative_to(BASE)),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
