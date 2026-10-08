"""Read the installed CLI's exact authored packet in a fresh offline Chrome context."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import traceback
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "evidence/offline-browser"
OUT = INPUT / "browser-first"
OUT.mkdir()
assert shutil.disk_usage(ROOT).free > 128 * 1024 * 1024
packet = INPUT / "reading.html"
original = packet.read_bytes()
fixture = json.loads((INPUT / "authored-fixture.json").read_text())
capture = json.loads((INPUT / "capture.json").read_text())
selection = capture["selection"]
expected = [fixture["pages"][name] for name in selection]
record = {"utc": datetime.datetime.now(datetime.UTC).isoformat(),
          "packet_sha256": hashlib.sha256(original).hexdigest(),
          "capture_sha256": hashlib.sha256((INPUT / "capture.json").read_bytes()).hexdigest(),
          "selection": selection, "checks": [], "requests": [], "blocked_http": [],
          "page_errors": [], "dialogs": [], "console_errors": []}
assert record["packet_sha256"] == capture["output_sha256"]
browser = None


def check(name, condition, detail=None):
    record["checks"].append({"name": name, "passed": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(name)


def screenshot(page, name, **options):
    path = OUT / name
    page.screenshot(path=str(path), **options)
    record.setdefault("screenshots", {})[name] = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}


try:
    with sync_playwright() as driver:
        browser = driver.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=True, args=["--disable-background-networking", "--no-first-run",
                                 "--disable-default-apps", "--disable-component-update"])
        record["browser_version"] = browser.version
        context = browser.new_context(viewport={"width": 1200, "height": 900})
        context.set_offline(True)

        def block(route):
            record["blocked_http"].append(route.request.url)
            route.abort()

        context.route("http://**/*", block)
        context.route("https://**/*", block)
        page = context.new_page()
        page.on("request", lambda request: record["requests"].append({"url": request.url, "method": request.method}))
        page.on("pageerror", lambda error: record["page_errors"].append(str(error)))
        page.on("console", lambda message: record["console_errors"].append(message.text) if message.type == "error" else None)

        def dialog(item):
            record["dialogs"].append(item.message)
            item.dismiss()

        page.on("dialog", dialog)
        page.goto(packet.as_uri(), wait_until="load", timeout=30000)
        check("saved packet opens with the browser offline", page.locator("article.page").count() == 3)
        check("literal course and page titles remain text",
              page.locator("h1").inner_text() == fixture["course"]["name"]
              and page.locator("article.page > h2").all_text_contents() == [row["title"] for row in expected])
        identities = page.locator("article.page").evaluate_all("(nodes) => nodes.map(n => n.getAttribute('data-page-id'))")
        check("selected identities retain exact integers without JavaScript number coercion",
              identities == [str(row["page_id"]) for row in expected], identities)
        originals = page.locator("pre[data-original-html] code").all_text_contents()
        raw_hashes = [hashlib.sha256(text.encode()).hexdigest() for text in originals]
        check("retained HTML preserves exact Unicode entities and CR LF source",
              originals == [row["body"] for row in expected]
              and raw_hashes == [row["body_sha256"] for row in capture["console_report"]["pages"]], raw_hashes)
        fields = ("page_id", "url", "title", "created_at", "updated_at", "published",
                  "front_page", "locked_for_user", "editor")
        # Parse metadata in Python so a browser-side JSON number conversion cannot
        # silently round the large authored page ID before this assertion.
        metadata = [json.loads(text) for text in page.locator("pre[data-page-metadata] code").all_text_contents()]
        check("supplied metadata remains exact including null and draft status",
              metadata == [{key: row[key] for key in fields if key in row} for row in expected])
        readings = page.locator("pre[data-reading] code").all_text_contents()
        check("reading projection retains sentences bullets code indentation and inert link references",
              "Observe the same specimen twice." in readings[0]
              and "• Record the units." in readings[0]
              and "• Retain both readings." in readings[0]
              and "[Image: A phase diagram]" in readings[0]
              and "[Embedded iframe not included]" in readings[0]
              and "[https://unrequested.example/reading?q=1&n=2]" in readings[0]
              and "    first_line()\n    second_line(\"雪\")" in readings[1])
        check("provider markup is absent from the active document",
              page.locator("script,img,iframe,object,embed,svg,math,video,audio,form,[src],[srcset]").count() == 0
              and not page.evaluate("Object.prototype.hasOwnProperty.call(window, '__pagePacketExecuted')"))
        anchors = page.locator("a").evaluate_all("(nodes) => nodes.map(n => n.getAttribute('href'))")
        check("only local contents and deliberate Canvas page links are active",
              len(anchors) == 9 and all(value.startswith("#") or value.startswith(capture["base_url"] + "/courses/42/pages/")
                                         for value in anchors), anchors)
        screenshot(page, "desktop.png", full_page=True)
        page.locator("nav a").nth(2).click()
        on_page = page.evaluate("location.hash") == "#page-3"
        page.locator("#page-3 a[href='#contents']").click()
        check("contents and return navigation work offline",
              on_page and page.evaluate("location.hash") == "#contents")
        page.locator("nav a").first.click()
        original_record = page.locator("#page-1 details").nth(1)
        original_record.locator("summary").click()
        check("original-source disclosure is usable without executing or fetching it",
              original_record.get_attribute("open") is not None
              and original_record.locator("pre").is_visible()
              and original_record.locator("pre code").text_content() == expected[0]["body"])
        page.set_viewport_size({"width": 390, "height": 844})
        open_width = page.evaluate("({width: innerWidth, scroll: document.documentElement.scrollWidth})")
        check("390px reading and expanded source stay within the viewport",
              open_width["scroll"] <= open_width["width"] + 1, open_width)
        original_record.locator("summary").click()
        page.evaluate("window.scrollTo(0, 0)")
        screenshot(page, "phone.png", full_page=True)
        page.emulate_media(media="print")
        closed = page.locator("details:not([open])").evaluate_all("(nodes) => nodes.every(n => getComputedStyle(n).display === 'none')")
        check("closed metadata and source records are excluded from print layout", closed)
        page.emulate_media(media="screen")
        check("offline reading performs no HTTP requests and reports no browser errors",
              not record["blocked_http"]
              and all(row["url"].startswith(packet.as_uri()) for row in record["requests"])
              and not record["page_errors"] and not record["dialogs"] and not record["console_errors"])
        context.close()
        browser.close()
        browser = None
        record["passed"] = True
except BaseException as error:
    record["passed"] = False
    record["error"] = f"{type(error).__name__}: {error}"
    record["traceback"] = traceback.format_exc()
    raise
finally:
    record["packet_unchanged"] = packet.read_bytes() == original
    record["fixture_unchanged"] = hashlib.sha256((INPUT / "authored-fixture.json").read_bytes()).hexdigest() == capture["fixture_sha256"]
    (OUT / "browser.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"passed": record["passed"], "checks": len(record["checks"]),
                  "browser": record["browser_version"], "page_errors": record["page_errors"],
                  "http_requests": record["blocked_http"],
                  "receipt_sha256": hashlib.sha256((OUT / "browser.json").read_bytes()).hexdigest()}))
