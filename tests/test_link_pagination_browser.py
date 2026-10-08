"""Optional actual Chromium → broker HTTP → assignment API qualification.

Set CANVASPILOT_TEST_CHROME to an existing Chromium executable. Every browser
request is intercepted in a fresh context; no school or existing profile is used.
"""

from __future__ import annotations

import json
import os
import queue
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

import pytest

from canvaspilot import client as client_mod
from canvaspilot import session_broker as broker_mod
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient

BASE = "https://school.instructure.com"
PATH = "/api/v1/courses/7/assignments"
CHROME = os.environ.get("CANVASPILOT_TEST_CHROME")


@pytest.mark.skipif(not CHROME, reason="set CANVASPILOT_TEST_CHROME for isolated browser qualification")
def test_actual_fetch_preserves_next_links_through_broker_and_api(monkeypatch):
    from playwright.sync_api import sync_playwright

    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                 "http_proxy", "https_proxy", "all_proxy", "no_proxy", "CANVAS_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    state = broker_mod._BrokerState()
    state.base_url = BASE
    monkeypatch.setattr(broker_mod, "STATE", state)
    seen = []
    blocked = []
    versions = []
    stop = threading.Event()
    next_url = BASE + PATH + "?cursor=a,b;c%2Fd&include%5B%5D=one&include%5B%5D=two"
    last_url = BASE + PATH + "?cursor=last%3D3"

    def worker():
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    executable_path=CHROME, headless=True, args=["--no-sandbox"]
                )
                versions.append(browser.version)
                context = browser.new_context(service_workers="block")

                def route_request(route):
                    url = route.request.url
                    parsed = urlsplit(url)
                    if url == BASE + "/":
                        route.fulfill(status=200, content_type="text/html", body="<title>Synthetic Canvas</title>")
                        return
                    if parsed.netloc != "school.instructure.com" or parsed.path != PATH:
                        blocked.append(url)
                        route.abort()
                        return
                    seen.append(url)
                    headers = {"Content-Type": "application/json"}
                    if len(seen) == 1:
                        rows = [{"id": 1}, {"id": 2}]
                        headers["LiNk"] = f'<{next_url}>; title="Page, two"; rel="next"'
                    elif url == next_url:
                        rows = []
                        headers["LINK"] = f'<{last_url}>; rel="next"'
                    elif url == last_url:
                        rows = [{"id": 3, "name": "Last coursework"}]
                    else:
                        route.fulfill(status=400, body="unexpected cursor")
                        return
                    route.fulfill(status=200, headers=headers, body=json.dumps(rows))

                context.route("**/*", route_request)
                context.new_page().goto(BASE + "/")
                state.ready.set()
                while not stop.is_set():
                    try:
                        job, reply = state.jobs.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    try:
                        result = broker_mod._run_job(context, job)
                        reply.put({"ok": True, **result})
                    except Exception as exc:  # noqa: BLE001 — report any worker failure instead of hanging the caller
                        reply.put({"ok": False, "error": str(exc)})
                context.close()
                browser.close()
        except Exception as exc:  # noqa: BLE001 — startup failure must settle the test's wait
            state.error = str(exc)
            state.ready.set()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    assert state.ready.wait(20), "isolated browser did not start"
    assert state.error is None, state.error
    server = ThreadingHTTPServer(("127.0.0.1", 0), broker_mod.Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    monkeypatch.setattr(client_mod, "BROKER_PORT", server.server_address[1])
    try:
        with CanvasClient(base_url=BASE, token="", timeout=10) as client:
            rows = CanvasAPI(client).list_assignments(7)
        assert [row["id"] for row in rows] == [1, 2, 3]
        assert seen[1:] == [next_url, last_url]
        assert not blocked
        assert state.error is None
        print(json.dumps({
            "browser": versions[0], "assignment_ids": [row["id"] for row in rows],
            "canvas_requests": seen, "unhandled_requests": blocked,
            "boundary": "actual in-page fetch, broker Handler/queue, client decoder and CanvasAPI",
            "data": "authored routes in a fresh browser; no network or school session",
        }, indent=2))
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
        thread.join(timeout=5)
        assert not thread.is_alive(), "isolated browser worker did not stop"
