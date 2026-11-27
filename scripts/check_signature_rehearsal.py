"""Rehearse the Signature product, circulation and access logs on owned loopback."""

import http.client
import io
import json
import logging
import secrets
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import urlencode, urlsplit

import check_browser_pair as browser_pair
from check_browser_pair import capture, login, reach_by_tab
from playwright.sync_api import expect
from summarize_http_logs import summarize

TITLE = "La Dernière Séance — démonstration"
CONFLICT = "Cet exemplaire ou cette demande n’est plus disponible."


def new_member(browser, base, username, display_name):
    context = browser.new_context(
        viewport={"width": 390, "height": 844}, service_workers="block"
    )
    context.set_default_timeout(10000)
    local_only(context, base)
    page = context.new_page()
    password = secrets.token_urlsafe(24)
    page.goto(base + "/inscription")
    page.get_by_label("Identifiant", exact=True).fill(username)
    page.get_by_label("Nom affiché", exact=True).fill(display_name)
    page.get_by_label("Mot de passe", exact=True).fill(password)
    page.get_by_label("Confirmer le mot de passe", exact=True).fill(password)
    page.get_by_role("button", name="Créer mon compte", exact=True).click()
    page.wait_for_url("**/connexion")
    login(page, base, username, password)
    return page


def local_only(context, base):
    def intercept(route):
        if route.request.url.startswith(base + "/"):
            route.continue_()
        else:
            route.abort()

    context.route("**/*", intercept)


def simultaneous_approvals(admin, base):
    origin = urlsplit(base)
    admin.goto(base + "/emprunts?scope=all")
    actions = admin.get_by_role("link", name="Attribuer un exemplaire", exact=True)
    expect(actions).to_have_count(2)
    paths = [link.get_attribute("href") for link in actions.all()]
    drafts = []
    for path in paths:
        assert path.startswith("/emprunts/") and path.endswith("/valider")
        assert admin.goto(base + path).status == 200
        admin.locator("#copy_id").select_option(index=1)
        fields = (
            admin.locator("form")
            .filter(has=admin.locator("#copy_id"))
            .evaluate("form => Object.fromEntries(new FormData(form))")
        )
        assert {"csrf_token", "copy_id", "due_date", "version"} <= fields.keys()
        drafts.append((path, fields))
    assert len(set(paths)) == 2
    assert drafts[0][1]["copy_id"] == drafts[1][1]["copy_id"]
    cookies = "; ".join(
        f"{item['name']}={item['value']}" for item in admin.context.cookies(base)
    )
    ready = Barrier(2, timeout=10)

    def approve(draft):
        path, fields = draft
        connection = http.client.HTTPConnection(
            origin.hostname, origin.port, timeout=15
        )
        try:
            ready.wait()
            connection.request(
                "POST",
                path,
                urlencode(fields).encode(),
                headers={
                    "Cookie": cookies,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            response = connection.getresponse()
            content = response.read().decode("utf-8")
            return (
                response.status,
                response.getheader("X-Request-ID"),
                CONFLICT in content,
            )
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = sorted(workers.map(approve, drafts))
    assert [(status, conflict) for status, _, conflict in outcomes] == [
        (303, False),
        (409, True),
    ]
    return outcomes, drafts[0][1]["copy_id"]


def check_traces(events, api_log, identities):
    combined = events + api_log.read_text(encoding="utf-8")
    details = {
        label: summarize(io.StringIO(combined), identity)["related_events"]
        for label, identity in identities.items()
    }

    def has(label, service, method, route, status):
        return any(
            (event["service"], event["method"], event["route"], event["status"])
            == (service, method, route, status)
            for event in details[label]
        )

    assert has("catalogue", "web", "GET", "/films", 200)
    assert has("catalogue", "api", "GET", "/api/v1/movies", 200)
    assert has("member_denied", "web", "GET", "/administration", 403)
    assert has("member_denied", "api", "GET", "/api/v1/me", 200)
    for label, web_status, api_status in (
        ("approval_accepted", 303, 200),
        ("approval_declined", 409, 409),
    ):
        assert has(label, "web", "POST", "/emprunts/<loan_id>/valider", web_status)
        assert has(label, "api", "POST", "/api/v1/loans/<loan_id>/approve", api_status)
    return details


def exercise(browser, base, config, folder, args, report, _proxy):
    from app.telemetry import _ACCESS_LOG

    report["limits"] = [
        "Owned loopback Flask pair with synthetic users and disposable JSON",
        "Exactly two approvals for one copy; no performance or production inference",
        "RemoteLabz segmentation, alert delivery, recovery and signed images require separate evidence",
    ]
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    _ACCESS_LOG.addHandler(handler)
    try:
        admin_context = browser.new_context(
            viewport={"width": 1280, "height": 900}, service_workers="block"
        )
        admin_context.set_default_timeout(10000)
        local_only(admin_context, base)
        admin = admin_context.new_page()
        report["stage"] = "film_seed"
        login(admin, base, "pair-admin", config["password"])
        admin.goto(base + "/films/nouveau")
        admin.locator("#titre").fill(TITLE)
        admin.locator("#realisateur").fill("Réalisation fictive")
        admin.locator("#annee").fill("2026")
        admin.locator("#support").select_option("dvd")
        admin.locator("#synopsis").fill(
            "Une projectionniste retrouve un film oublié et organise une dernière "
            "projection pour les habitants du quartier."
        )
        admin.get_by_role("button", name="Créer le film", exact=True).click()
        admin.wait_for_url("**/films/*")
        expect(admin.get_by_role("heading", name=TITLE, exact=True)).to_be_visible()
        film_path = urlsplit(admin.url).path

        report["stage"] = "discovery"
        first = new_member(browser, base, "rehearsal-first", "Membre fictif A")
        assert first.goto(base + "/").status == 200
        catalogue = first.goto(base + "/films")
        catalogue_id = catalogue.header_value("x-request-id")
        assert catalogue.status == 200 and catalogue_id
        first.keyboard.press("Control+k")
        dialog = first.get_by_role("dialog", name="Recherche rapide")
        expect(dialog).to_be_visible()
        dialog.get_by_role("searchbox").fill("Dernière Séance")
        suggestion = dialog.get_by_role("link", name=TITLE, exact=False)
        expect(suggestion).to_be_visible()
        assert reach_by_tab(first, suggestion)
        first.keyboard.press("Enter")
        first.wait_for_url(lambda url: urlsplit(url).path == film_path)
        expect(first.get_by_role("heading", name=TITLE, exact=True)).to_be_visible()
        capture(first, "fiche-390.png", args, report)
        report["stage"] = "private_collection"
        first.get_by_role("link", name="Ajouter à ma collection", exact=True).click()
        first.get_by_label("Dans ma collection", exact=True).select_option("favorite")
        first.get_by_role("button", name="Ajouter à ma collection", exact=True).click()
        expect(first.get_by_role("heading", name=TITLE, exact=True)).to_be_visible()
        report["checks"].append(
            "Accueil, catalogue, recherche au clavier, fiche et collection"
        )

        report["stage"] = "circulation"
        second = new_member(browser, base, "rehearsal-second", "Membre fictif B")
        for member in (first, second):
            member.goto(base + film_path)
            member.get_by_role("button", name="Demander un prêt", exact=True).click()
            member.wait_for_url("**/emprunts?scope=mine")
        report["stage"] = "concurrent_approvals"
        outcomes, copy_id = simultaneous_approvals(admin, base)
        admin.goto(base + "/emprunts?scope=all")
        expect(admin.locator("form[action$='/retour']")).to_have_count(1)
        expect(
            admin.get_by_role("link", name="Attribuer un exemplaire", exact=True)
        ).to_have_count(1)
        capture(admin, "circulation-1280.png", args, report)

        report["stage"] = "reservation"
        reader = new_member(browser, base, "rehearsal-waiting", "Membre fictif C")
        reader.goto(base + film_path)
        reader.get_by_role("button", name="Réserver ce film", exact=True).click()
        reader.wait_for_url("**/reservations?scope=mine")
        expect(reader.get_by_text(TITLE, exact=True)).to_be_visible()
        capture(reader, "reservation-390.png", args, report)

        report["stage"] = "storage_invariants"
        document = json.loads((folder / "enterprise.json").read_text(encoding="utf-8"))
        movie = [row for row in document["movies"] if row["title"] == TITLE]
        assert len(movie) == 1 and movie[0]["id"] == film_path.rsplit("/", 1)[-1]
        assert len(document["copies"]) == 1 and document["copies"][0]["id"] == copy_id
        assert sorted(row["status"] for row in document["loans"]) == [
            "active",
            "pending",
        ]
        assert sum(row["copy_id"] == copy_id for row in document["loans"]) == 1
        assert (
            len(document["reservations"]) == 1
            and document["reservations"][0]["status"] == "waiting"
        )
        report["checks"].append(
            "Deux demandes, décision HTTP 303/409, un prêt actif et une réservation"
        )
        report["checks"].append(
            "Le film rendu correspond au film conservé dans le seul fichier JSON"
        )
        report["circulation"] = {
            "copies": 1,
            "approval_http": [303, 409],
            "active": 1,
            "pending": 1,
            "waiting_reservations": 1,
        }

        report["stage"] = "correlation"
        denied = reader.goto(base + "/administration")
        denied_id = denied.header_value("x-request-id")
        assert denied.status == 403 and denied_id
        report["traces"] = check_traces(
            buffer.getvalue(),
            folder / "api.log",
            {
                "catalogue": catalogue_id,
                "member_denied": denied_id,
                "approval_accepted": outcomes[0][1],
                "approval_declined": outcomes[1][1],
            },
        )
        report["checks"].append(
            "Corrélation Web/API des lectures, du refus de rôle et des deux décisions"
        )
        report["stage"] = "complete"
    finally:
        _ACCESS_LOG.removeHandler(handler)
        handler.close()
        buffer.close()


if __name__ == "__main__":
    raise SystemExit(browser_pair.main(exercise=exercise))
