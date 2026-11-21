"""Summarize CineVault HTTP events from stdin without printing log payloads."""

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass

SERVICES = {"api", "web"}
METHODS = {
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
    "TRACE",
    "CONNECT",
    "OTHER",
}
IDENTITY = re.compile(r"[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}")
ROUTE = re.compile(r"(?:unmatched|/[a-zA-Z0-9_./<>:-]{0,159})")
EVENT_FIELDS = {"service", "request_id", "method", "route", "status", "duration_ms"}


@dataclass(frozen=True)
class Event:
    service: str
    request_id: str
    method: str
    route: str
    status: int
    duration_ms: float
    upstream_ids: tuple[str, ...]


def valid(value, pattern):
    return type(value) is str and pattern.fullmatch(value) is not None


def event(line):
    try:
        fields = json.loads(line)
    except (ValueError, RecursionError):
        return None
    if type(fields) is not dict or not EVENT_FIELDS <= fields.keys():
        return None
    if fields.keys() - (EVENT_FIELDS | {"api_request_ids"}):
        return None
    service, method = fields["service"], fields["method"]
    if type(service) is not str or service not in SERVICES:
        return None
    if type(method) is not str or method not in METHODS:
        return None
    identity, route = fields["request_id"], fields["route"]
    status, duration = fields["status"], fields["duration_ms"]
    upstream = fields.get("api_request_ids", [])
    if (
        not valid(identity, IDENTITY)
        or not valid(route, ROUTE)
        or type(status) is not int
        or not 100 <= status <= 599
        or type(duration) not in (int, float)
        or duration < 0
        or (type(duration) is float and not math.isfinite(duration))
        or type(upstream) is not list
        or len(upstream) > 8
        or not all(valid(value, IDENTITY) for value in upstream)
        or (service == "api" and upstream)
    ):
        return None
    return Event(service, identity, method, route, status, duration, tuple(upstream))


def read_events(stream):
    for line in iter(lambda: stream.readline(8193), ""):
        if len(line) > 8192:
            while line and not line.endswith("\n"):
                line = stream.readline(8193)
            yield None
        else:
            yield event(line)


@dataclass
class Group:
    statuses: Counter
    durations: list

    def add(self, item):
        self.statuses[item.status] += 1
        self.durations.append(item.duration_ms)

    def summary(self):
        samples = sorted(self.durations)
        total = len(samples)
        failures = sum(
            count for status, count in self.statuses.items() if 500 <= status
        )
        percentiles = {
            f"p{point}_ms": samples[math.ceil(total * point / 100) - 1]
            for point in (50, 95, 99)
        }
        return {
            "requests": total,
            "status_counts": dict(sorted(self.statuses.items())),
            "error_5xx_percent": round(failures * 100 / total, 3),
            **percentiles,
        }


def summarize(stream, request_id=None):
    totals = defaultdict(lambda: Group(Counter(), []))
    by_route = defaultdict(lambda: Group(Counter(), []))
    trace_candidates = []
    trace_ids = {request_id}
    omitted = 0
    for item in read_events(stream):
        if item is None:
            omitted += 1
            continue
        totals[item.service].add(item)
        by_route[(item.service, item.method, item.route)].add(item)
        if request_id:
            trace_candidates.append(item)
            if request_id == item.request_id or request_id in item.upstream_ids:
                trace_ids.add(item.request_id)
                trace_ids.update(item.upstream_ids)
    related = [
        {
            "service": item.service,
            "method": item.method,
            "route": item.route,
            "status": item.status,
            "duration_ms": item.duration_ms,
            "request_id": item.request_id,
            "api_request_ids": list(item.upstream_ids),
        }
        for item in trace_candidates
        if item.request_id in trace_ids
    ]
    return {
        "ignored_lines": omitted,
        "services": {
            service: group.summary() for service, group in sorted(totals.items())
        },
        "routes": [
            {"service": service, "method": method, "route": route, **group.summary()}
            for (service, method, route), group in sorted(by_route.items())
        ],
        **({"related_events": related} if request_id else {}),
    }


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Arguments invalides. Utiliser --help.\n")


def main(argv=None):
    parser = Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--request-id", help="Request ID returned by CineVault")
    args = parser.parse_args(argv)
    if args.request_id is not None and not valid(args.request_id, IDENTITY):
        parser.error("Identifiant invalide.")
    outcome = summarize(sys.stdin, args.request_id)
    print(json.dumps(outcome, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
