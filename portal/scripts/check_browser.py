"""Browser checks of the actual public static build; no external dispatch."""

import argparse
import functools
import hashlib
import http.server
import json
import re
import threading
from pathlib import Path
from urllib.parse import quote, urlsplit

from playwright.sync_api import sync_playwright

PROJECT = Path(__file__).resolve().parents[1]
DIST = PROJECT / "dist"
AXE = PROJECT / "node_modules/axe-core/axe.min.js"
BASE = ""
OUTPUT = None


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if not self.path.startswith(BASE + "/"):
            self.send_error(404)
            return
        self.path = self.path[len(BASE) :]
        super().do_GET()


def main():
    global BASE, OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--browser-channel", choices=("chrome", "chromium"))
    args = parser.parse_args()
    OUTPUT = args.report_dir.resolve()
    if OUTPUT.exists() or OUTPUT.is_relative_to(DIST.resolve()):
        parser.error("Report directory must be new and outside the static output")
    BASE = json.loads((DIST / "source-manifest.json").read_text(encoding="utf-8"))[
        "base"
    ]
    OUTPUT.mkdir(parents=True, exist_ok=False)
    (OUTPUT / "executed-qa.py").write_bytes(Path(__file__).read_bytes())
    report = {
        "scope": "Actual static documentation build, not an application or publication gate",
        "checks": [],
        "screens": [],
        "axe": [],
        "page_errors": [],
        "blocked_external_requests": [],
    }
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Handler, directory=str(DIST))
    )
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    home = origin + BASE + "/"

    def check(name, value):
        report["checks"].append({"name": name, "passed": bool(value)})
        assert value, name

    def screen(page, name):
        destination = OUTPUT / (name + ".png")
        page.screenshot(path=str(destination))
        report["screens"].append(
            {
                "file": destination.name,
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            }
        )

    def axe(page, name):
        page.add_script_tag(path=str(AXE))
        result = page.evaluate("""async () => {
          const value = await axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}});
          return {violations:value.violations,incomplete:value.incomplete,passes:value.passes.length};
        }""")
        report["axe"].append({"state": name, **result})
        check("axe automatic WCAG violations: " + name, not result["violations"])

    try:
        manifest = json.loads(
            (DIST / "source-manifest.json").read_text(encoding="utf-8")
        )
        report["build_receipt"] = json.loads(
            (DIST / "build-receipt.json").read_text(encoding="utf-8")
        )
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                **({"channel": args.browser_channel} if args.browser_channel else {})
            )
            report["browser"] = browser.version
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                service_workers="block",
                reduced_motion="reduce",
            )

            def route(request):
                if request.request.url.startswith(origin + "/"):
                    request.continue_()
                else:
                    report["blocked_external_requests"].append(
                        urlsplit(request.request.url).netloc
                    )
                    request.abort()

            context.route("**/*", route)
            page = context.new_page()
            page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
            for entry in manifest["pages"]:
                response = page.goto(
                    home
                    + (quote(entry["route"], safe="/") + "/" if entry["route"] else "")
                )
                check("page responds: " + entry["route"], response.status == 200)
                check(
                    "one main heading: " + entry["route"],
                    page.locator("main h1").count() == 1,
                )
                check(
                    "French language: " + entry["route"],
                    page.locator("html").get_attribute("lang") == "fr",
                )
            page.goto(home)
            report["controls"] = page.locator("button,select,input").evaluate_all(
                "els => els.map(el => ({tag:el.tagName,text:el.innerText,label:el.getAttribute('aria-label'),placeholder:el.getAttribute('placeholder'),title:el.getAttribute('title'),type:el.getAttribute('type')}))"
            )
            for width, height in (
                (320, 812),
                (390, 844),
                (768, 1024),
                (840, 900),
                (1024, 900),
                (1280, 900),
            ):
                page.set_viewport_size({"width": width, "height": height})
                page.goto(home)
                check(
                    f"no home horizontal overflow {width}",
                    page.evaluate("document.documentElement.scrollWidth <= innerWidth"),
                )
                check(
                    f"full brand visible {width}",
                    page.locator(".site-title span").evaluate("""el => {
                  const range = document.createRange(); range.selectNodeContents(el);
                  return range.getBoundingClientRect().right <= document.querySelector('site-search button').getBoundingClientRect().left - 2;
                }"""),
                )
                screen(page, f"home-{width}")
            page.goto(home)
            page.keyboard.press("Tab")
            check(
                "first Tab reaches skip link",
                page.evaluate(
                    "document.activeElement.classList.contains('sl-skip-link')"
                ),
            )
            page.keyboard.press("Enter")
            report["skip_link_after_enter"] = page.evaluate(
                "({tag:document.activeElement.tagName,id:document.activeElement.id,hash:location.hash})"
            )
            check(
                "skip link navigates to main heading anchor",
                urlsplit(page.url).fragment == "_top",
            )
            page.keyboard.press("Tab")
            check(
                "next Tab after skip enters main content",
                page.evaluate(
                    "document.querySelector('main').contains(document.activeElement)"
                ),
            )
            page.goto(home)
            for step in range(20):
                page.keyboard.press("Tab")
                if page.evaluate(
                    "document.activeElement.getAttribute('aria-label') === 'Rechercher'"
                ):
                    report["search_tab_steps"] = step + 1
                    break
            else:
                raise AssertionError("Search button was not reached with Tab")
            page.keyboard.press("Enter")
            page.get_by_role("dialog").wait_for(state="visible")
            page.keyboard.press("Escape")
            check(
                "Escape restores search button focus",
                page.evaluate(
                    "document.activeElement.getAttribute('aria-label') === 'Rechercher'"
                ),
            )
            for theme in ("light", "dark"):
                page.locator("starlight-theme-select select:visible").select_option(
                    theme
                )
                check(
                    "theme selection: " + theme,
                    page.locator("html").get_attribute("data-theme") == theme,
                )
                check(
                    "full French theme label: " + theme,
                    page.locator(
                        "starlight-theme-select select:visible"
                    ).evaluate("""el => {
                      const style = getComputedStyle(el);
                      const canvas = document.createElement('canvas');
                      const context = canvas.getContext('2d');
                      context.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
                      const available = el.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
                      return available >= context.measureText(el.selectedOptions[0].text).width;
                    }"""),
                )
                axe(page, "home-1280-" + theme)
                screen(page, "home-1280-" + theme)
            page.keyboard.press("Control+k")
            search = page.get_by_placeholder("Rechercher", exact=True)
            search.wait_for(state="visible")
            search.fill("ordinal")
            result = page.get_by_role("dialog").get_by_role(
                "link", name=re.compile("Services communs|C3|MongoDB")
            )
            result.first.wait_for(state="visible", timeout=15000)
            check("French Pagefind finds scoped MongoDB result", result.count() > 0)
            axe(page, "search-1280-dark")
            screen(page, "search-1280")
            destination = result.first.get_attribute("href")
            result.first.click()
            page.wait_for_url(origin + destination)
            check("search navigates to result", urlsplit(page.url).path != BASE + "/")
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(home)
            for step in range(20):
                page.keyboard.press("Tab")
                if page.evaluate(
                    "document.activeElement.matches('button.sl-menu-button')"
                ):
                    report["menu_tab_steps"] = step + 1
                    break
            else:
                raise AssertionError("Mobile menu button was not reached with Tab")
            page.keyboard.press("Enter")
            check(
                "keyboard opens mobile menu",
                page.locator("#starlight__sidebar").evaluate(
                    "el => el.matches(':popover-open')"
                ),
            )
            axe(page, "mobile-menu-390-dark")
            screen(page, "menu-390-dark")
            page.keyboard.press("Escape")
            check(
                "Escape closes mobile menu",
                not page.locator("#starlight__sidebar").evaluate(
                    "el => el.matches(':popover-open')"
                ),
            )
            axe(page, "home-390-dark")
            page.goto(home + "guides/data-dictionary/")
            check(
                "table guide reflows at390",
                page.evaluate("document.documentElement.scrollWidth <= innerWidth"),
            )
            for kind in ("table", "pre"):
                for step in range(160):
                    page.keyboard.press("Tab")
                    if page.evaluate(
                        """kind => {
                      const el = document.activeElement;
                      return el.tagName.toLowerCase() === kind && el.scrollWidth > el.clientWidth;
                    }""",
                        kind,
                    ):
                        report["scroll_tab_steps_" + kind] = step + 1
                        break
                else:
                    raise AssertionError(
                        "Overflowing " + kind + " was not reached with Tab"
                    )
                before = page.evaluate("document.activeElement.scrollLeft")
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(200)
                check(
                    "keyboard scrolls " + kind,
                    page.evaluate("document.activeElement.scrollLeft") > before,
                )
            axe(page, "data-dictionary-390-dark")
            page.goto(home + "404.html")
            check(
                "French404 heading",
                page.get_by_role(
                    "heading", name="Page introuvable", exact=True
                ).is_visible(),
            )
            check("no script errors", not report["page_errors"])
            check(
                "no external requests needed", not report["blocked_external_requests"]
            )
            context.close()
            browser.close()
        report["passed"] = True
    finally:
        server.shutdown()
        worker.join(10)
        server.server_close()
        report["owned_server_stopped"] = not worker.is_alive()
        (OUTPUT / "receipt.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "passed": report.get("passed", False),
                    "checks": len(report["checks"]),
                    "screens": len(report["screens"]),
                    "owned_server_stopped": report["owned_server_stopped"],
                }
            )
        )


if __name__ == "__main__":
    main()
