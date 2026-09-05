"""Long-lived Canvas session broker (headed login; optional --headless after).

Keeps one Playwright persistent context open and serves in-page fetch over
localhost HTTP so CLI/MCP calls do not tear down SSO every time.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from canvaspilot.client import default_base_url, default_profile

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = int(os.environ.get("CANVAS_SESSION_PORT", "18765"))


class _BrokerState:
    def __init__(self) -> None:
        self.base_url = default_base_url()
        self.profile = default_profile()
        self.headless = False
        self.jobs: queue.Queue[tuple[dict[str, Any], queue.Queue[dict[str, Any]]]] = queue.Queue()
        self.ready = threading.Event()
        self.page_url = ""
        self.page_title = ""
        self.error: str | None = None


STATE = _BrokerState()


def _canvas_page(ctx):  # type: ignore[no-untyped-def]
    for p in ctx.pages:
        if "instructure.com" in (p.url or "") and "login.microsoft" not in (p.url or ""):
            return p
    return ctx.pages[0] if ctx.pages else ctx.new_page()


def _browser_loop() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        STATE.error = f"playwright missing: {exc}"
        return

    STATE.profile.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(STATE.profile),
            headless=STATE.headless,
            viewport={"width": 1400, "height": 900},
            args=["--disable-popup-blocking", "--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(STATE.base_url, wait_until="domcontentloaded")
        STATE.page_url = page.url
        try:
            STATE.page_title = page.title()
        except Exception:
            STATE.page_title = ""
        STATE.ready.set()
        msg = (
            "Headless broker up (reuse logged-in profile). Leave process running."
            if STATE.headless
            else "Log into Canvas in this window. Leave it open. CLI/MCP will use this session."
        )
        print(
            json.dumps(
                {
                    "status": "session_ready",
                    "base_url": STATE.base_url,
                    "profile": str(STATE.profile),
                    "port": DEFAULT_PORT,
                    "headless": STATE.headless,
                    "message": msg,
                    "url": STATE.page_url,
                }
            ),
            flush=True,
        )

        while True:
            try:
                job, reply = STATE.jobs.get(timeout=1.0)
            except queue.Empty:
                # refresh status
                try:
                    p = _canvas_page(ctx)
                    STATE.page_url = p.url
                    STATE.page_title = p.title()
                except Exception:
                    pass
                continue

            if job.get("op") == "shutdown":
                reply.put({"ok": True, "shutdown": True})
                break

            try:
                result = _run_job(ctx, job)
                reply.put({"ok": True, **result})
            except Exception as exc:  # noqa: BLE001
                reply.put({"ok": False, "error": str(exc)})

        ctx.close()


def _run_job(ctx, job: dict[str, Any]) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    op = job.get("op")
    if op == "status":
        p = _canvas_page(ctx)
        return {
            "url": p.url,
            "title": p.title(),
            "headless": STATE.headless,
            "logged_in": "instructure.com" in p.url and "login.microsoft" not in p.url,
        }

    if op == "fetch":
        method = (job.get("method") or "GET").upper()
        path = job["path"]
        body = job.get("body")
        headers = job.get("headers") or {"Accept": "application/json"}
        page = _canvas_page(ctx)
        if "instructure.com" not in page.url:
            page.goto(STATE.base_url, wait_until="domcontentloaded")
            time.sleep(1)
        # Ensure same-origin: relative path on Canvas host
        if path.startswith("http"):
            parsed = urlparse(path)
            if parsed.netloc and parsed.netloc not in page.url:
                page.goto(f"{parsed.scheme}://{parsed.netloc}/", wait_until="domcontentloaded")
            path = parsed.path + (("?" + parsed.query) if parsed.query else "")

        result = page.evaluate(
            """async ({method, path, headers, body}) => {
              const opts = {method, credentials: 'include', headers: headers || {}};
              if (body != null && method !== 'GET' && method !== 'HEAD') {
                if (typeof body === 'string') opts.body = body;
                else {
                  opts.headers = Object.assign({'Content-Type': 'application/json'}, opts.headers);
                  opts.body = JSON.stringify(body);
                }
              }
              const r = await fetch(path, opts);
              const text = await r.text();
              let json = null;
              try { json = JSON.parse(text); } catch (e) {}
              return {status: r.status, json, text: json ? null : text.slice(0, 4000)};
            }""",
            {"method": method, "path": path, "headers": headers, "body": body},
        )
        return {"response": result}

    raise RuntimeError(f"unknown op: {op}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        return

    def _json(self, code: int, obj: dict[str, Any]) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/health"):
            self._json(
                200,
                {
                    "ok": True,
                    "ready": STATE.ready.is_set(),
                    "url": STATE.page_url,
                    "title": STATE.page_title,
                    "headless": STATE.headless,
                    "error": STATE.error,
                    "base_url": STATE.base_url,
                },
            )
            return
        if self.path.startswith("/status"):
            self._json(200, _call({"op": "status"}))
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            job = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "bad json"})
            return
        if self.path.startswith("/shutdown"):
            self._json(200, _call({"op": "shutdown"}))
            threading.Thread(target=lambda: (time.sleep(0.3), os._exit(0)), daemon=True).start()
            return
        if self.path.startswith("/fetch"):
            self._json(200, _call(job if "op" in job else {"op": "fetch", **job}))
            return
        self._json(404, {"ok": False, "error": "not found"})


def _call(job: dict[str, Any], timeout: float = 120.0) -> dict[str, Any]:
    if STATE.error:
        return {"ok": False, "error": STATE.error}
    if not STATE.ready.wait(timeout=60):
        return {"ok": False, "error": "browser not ready"}
    reply: queue.Queue[dict[str, Any]] = queue.Queue()
    STATE.jobs.put((job, reply))
    try:
        return reply.get(timeout=timeout)
    except queue.Empty:
        return {"ok": False, "error": "job timeout"}


def broker_url(port: int | None = None) -> str:
    return f"http://{DEFAULT_HOST}:{port or DEFAULT_PORT}"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Canvas stay-open session broker")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless (use after a headed login into the same profile)",
    )
    args = parser.parse_args(argv)
    if args.base_url:
        STATE.base_url = args.base_url.rstrip("/")
        os.environ["CANVAS_BASE_URL"] = STATE.base_url
    if args.profile:
        STATE.profile = Path(args.profile)
    STATE.headless = bool(args.headless)

    t = threading.Thread(target=_browser_loop, name="canvas-browser", daemon=True)
    t.start()
    if not STATE.ready.wait(timeout=90):
        raise SystemExit(STATE.error or "browser failed to start")

    server = ThreadingHTTPServer((DEFAULT_HOST, args.port), Handler)
    print(json.dumps({"status": "listening", "url": broker_url(args.port)}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _call({"op": "shutdown"})
        server.shutdown()


if __name__ == "__main__":
    main()
