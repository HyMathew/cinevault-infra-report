import io
import json
from uuid import UUID

from scripts.summarize_http_logs import summarize

API_ID = UUID("12345678-1234-4000-a123-abcdefabcdef").hex
WEB_ID = UUID("99999999-1234-4000-b234-abcdefabcdef").hex
SECOND_API_ID = UUID("12345678-1234-4000-a123-abcdefabcdee").hex


def api_event(**overrides):
    return {
        "service": "api",
        "method": "GET",
        "route": "/api/v1/movies/<movie_id>",
        "request_id": API_ID,
        "status": 200,
        "duration_ms": 12.2,
        **overrides,
    }


def stream(*contents):
    return io.StringIO(
        "\n".join(
            content if isinstance(content, str) else json.dumps(content)
            for content in contents
        )
        + "\n"
    )


def test_joins_api_events_from_web_id_and_reports_rates_and_percentiles():
    web = api_event(
        service="web",
        request_id=WEB_ID,
        route="/catalogue",
        api_request_ids=[API_ID, SECOND_API_ID],
    )
    second = api_event(request_id=SECOND_API_ID, status=503, duration_ms=22.2)
    result = summarize(stream("delivery notice", api_event(), web, second), WEB_ID)
    assert result["ignored_lines"] == 1
    assert result["services"]["api"] == {
        "requests": 2,
        "status_counts": {200: 1, 503: 1},
        "error_5xx_percent": 50.0,
        "p50_ms": 12.2,
        "p95_ms": 22.2,
        "p99_ms": 22.2,
    }
    assert [entry["request_id"] for entry in result["related_events"]] == [
        API_ID,
        WEB_ID,
        SECOND_API_ID,
    ]
    via_api = summarize(stream(api_event(), web, second), API_ID)
    assert via_api["related_events"] == result["related_events"]


def test_omits_noncanonical_events_without_preserving_their_contents():
    sentinel = "Unexpected private marker"
    result = summarize(
        stream(
            api_event(authorization=sentinel),
            api_event(route="/?secret=" + sentinel),
            api_event(request_id=sentinel),
            api_event(duration_ms=float("nan")),
            api_event(duration_ms=-1),
            api_event(service=["api"]),
            api_event(),
            sentinel * 1000,
        )
    )
    assert result["ignored_lines"] == 7
    assert result["services"]["api"]["requests"] == 1
    assert sentinel not in json.dumps(result)
    assert "related_events" not in result
