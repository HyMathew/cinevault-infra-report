"""Authenticated HTTPS staging probe executed from the proxy's network namespace."""

import http.client
import json
import socket
import ssl
import sys
from html.parser import HTMLParser
from http.cookies import SimpleCookie
from urllib.parse import urlencode

HOST = "cinevault-stage.test"
PORT = 8443
MAX_BODY = 1_000_000
STAGING_HSTS = "max-age=300"


class HiddenFields(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.tokens = set()
        self.feed(page.decode("utf-8"))

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if (
            tag == "input"
            and attributes.get("name") == "csrf_token"
            and attributes.get("type") == "hidden"
            and attributes.get("value")
        ):
            self.tokens.add(attributes["value"])


def request(context, path, form=None, cookies=None, server_name=HOST):
    conn = http.client.HTTPSConnection(server_name, PORT, context=context, timeout=8)
    # Keep SNI and Host fixed to the certificate while the probe dials only loopback.
    conn._create_connection = lambda _address, timeout, source_address: (
        socket.create_connection(("127.0.0.1", PORT), timeout, source_address)
    )
    headers = {"Connection": "close"}
    if cookies:
        headers["Cookie"] = "; ".join(
            f"{name}={value}" for name, value in cookies.items()
        )
    body = None
    if form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = urlencode(form).encode("ascii")
    try:
        conn.connect()
        protocol = conn.sock.version()
        conn.request("GET" if form is None else "POST", path, body, headers)
        with conn.getresponse() as response:
            assert response.headers.get_all("Strict-Transport-Security") == [
                STAGING_HSTS
            ], "unexpected_hsts_response"
            data = response.read(MAX_BODY + 1)
            assert len(data) <= MAX_BODY
            parsed = SimpleCookie()
            for value in response.headers.get_all("Set-Cookie", []):
                parsed.load(value)
            return (
                protocol,
                response.status,
                response.headers.get("Location"),
                parsed,
                data,
            )
    finally:
        conn.close()


def verify(payload):
    context = ssl.create_default_context(cadata=payload["ca"])
    context.minimum_version = ssl.TLSVersion.TLSv1_3

    try:
        request(context, "/health", server_name="wrong-stage.test")
    except ssl.SSLError:
        pass
    else:
        raise AssertionError("invalid_tls_name_accepted")

    protocol, status, _, _, _ = request(context, "/health")
    assert protocol == "TLSv1.3" and status == 200
    _, status, _, _, catalogue = request(context, "/films")
    assert status == 200
    assert all(
        str(payload[k]).encode("utf-8") in catalogue for k in ("title", "movie_id")
    )
    _, status, location, _, _ = request(context, "/profil")
    assert status == 303 and location == "/connexion"
    _, status, _, pre, page = request(context, "/connexion")
    assert status == 200 and "session" in pre
    (csrf,) = HiddenFields(page).tokens
    form = {
        "csrf_token": csrf,
        "username": payload["username"],
        "password": payload["password"],
    }
    _, status, location, post, _ = request(
        context, "/connexion", form, {"session": pre["session"].value}
    )
    assert status == 303 and location == "/profil"
    auth = post["cinevault_auth"]
    assert all(
        m["secure"] and m["httponly"] and m["samesite"].lower() == "lax"
        for m in (pre["session"], auth)
    )
    _, status, _, _, profile = request(
        context, "/profil", cookies={"cinevault_auth": auth.value}
    )
    assert status == 200 and b"Mon profil" in profile
    assert payload["username"].encode("utf-8") in profile

    return {
        "passed": True,
        "tls_protocol": protocol,
        "invalid_server_name_rejected": True,
        "catalogue_contains_migrated_movie": True,
        "anonymous_profile_denied": True,
        "login_redirected_to_profile": True,
        "secure_session_and_auth_cookies": True,
        "authenticated_profile_visible": True,
        "strict_transport_security": STAGING_HSTS,
    }


def main():
    try:
        result = verify(json.load(sys.stdin))
    except (AssertionError, KeyError, OSError, ValueError, http.client.HTTPException):
        result = {"passed": False}
    print(json.dumps(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
