"""Real Chromium execution of the actual broker fetch and public assignment API.

All browser requests are intercepted and answered with fictional Canvas pages.
Use PYTHONPATH to select an exact source tree; no existing browser profile,
school account, session broker, network provider or write endpoint is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import sync_playwright

from canvaspilot import client as client_module
from canvaspilot import session_broker
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", required=True)
    parser.add_argument("--expect", choices=["baseline", "candidate"], required=True)
    args = parser.parse_args()

    base = "https://pagination-fixture.instructure.com"
    endpoint = "/api/v1/courses/7/assignments"
    cursor_a = "next=a%2Fb%2Bc&include%5B%5D=submission"
    cursor_b = "next=tail%3Dopaque&include%5B%5D=submission"
    rows = [{"id": number, "name": f"Fictional assignment {number}"} for number in range(1, 26)]
    requests, responses, blocked = [], [], []

    def receive(route):
        request = route.request
        parsed = urlsplit(request.url)
        if request.url == base + "/":
            route.fulfill(status=200, content_type="text/html", body="<title>Canvas fixture</title>")
            return
        if request.method != "GET" or parsed.path != endpoint or not request.url.startswith(base + "/"):
            blocked.append({"method": request.method, "url": request.url})
            route.abort()
            return
        requests.append(request.url)
        if parsed.query == cursor_a:
            chunk, following = rows[10:20], f"{base}{endpoint}?{cursor_b}"
        elif parsed.query == cursor_b:
            chunk, following = rows[20:], None
        elif "per_page=50" in parsed.query:
            chunk, following = rows[:10], f"{base}{endpoint}?{cursor_a}"
        else:
            blocked.append({"method": request.method, "url": request.url})
            route.abort()
            return
        headers = {"content-type": "application/json"}
        if following:
            headers["lInK"] = f'<{following}>; rel="next"'
        route.fulfill(status=200, headers=headers, body=json.dumps(chunk))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=args.chromium,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            context = browser.new_context(service_workers="block")
            context.route("**/*", receive)
            page = context.new_page()
            page.goto(base + "/")

            def broker_post(url, *, json, **kwargs):
                assert url == f"{client_module.broker_base()}/fetch"
                result = session_broker._run_job(context, json)
                responses.append(result["response"])
                return httpx.Response(200, json={"ok": True, **result})

            with patch.object(client_module, "broker_health", return_value={"ok": True}), patch.object(
                client_module.httpx, "post", side_effect=broker_post
            ):
                result = CanvasAPI(CanvasClient(base_url=base, token="")).list_assignments(7)
            version = browser.version
        finally:
            browser.close()

    expected = 10 if args.expect == "baseline" else 25
    assert [row["id"] for row in result] == list(range(1, expected + 1))
    assert not blocked
    if args.expect == "candidate":
        assert requests[1:] == [f"{base}{endpoint}?{cursor_a}", f"{base}{endpoint}?{cursor_b}"]
        assert responses[0]["link"] == f'<{base}{endpoint}?{cursor_a}>; rel="next"'
        assert responses[-1]["link"] is None
    else:
        assert len(requests) == 1
        assert "link" not in responses[0]
    source = Path(client_module.__file__).parent
    source_hashes = {
        name: hashlib.sha256((source / name).read_bytes()).hexdigest()
        for name in ("client.py", "session_broker.py", "pagination.py") if (source / name).exists()
    }
    print(json.dumps({
        "expectation": args.expect,
        "chromium": version,
        "public_api": "CanvasAPI.list_assignments(7)",
        "fictional_collection_count": 25,
        "returned_count": len(result),
        "canvas_requests": requests,
        "broker_response_has_link": "link" in responses[0],
        "blocked_requests": blocked,
        "source_sha256": source_hashes,
        "scope": "actual broker JavaScript and public client; local request interception, no live account",
    }, indent=2))


if __name__ == "__main__":
    main()
