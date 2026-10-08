"""Independent Link metadata controls through actual local broker HTTP.

These synthetic responses isolate the session broker parser boundary. The
broker capability and headers.link envelope match the published PR35 protocol;
no school account, existing profile, token transport, or browser is substituted.
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urljoin

import httpx
import pytest

from canvaspilot import client as client_mod

BASE = "https://school.instructure.com"
PATH = "/api/v1/courses/29/assignments"
NEXT = BASE + PATH + "?cursor=second"


@contextmanager
def collection(monkeypatch, replies):
    calls = []
    queue = list(replies)

    def response_for(request):
        calls.append(request)
        if not queue:
            raise AssertionError("unplanned collection request")
        return queue.pop(0)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_json(self, value):
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path != "/health":
                raise AssertionError(self.path)
            self.send_json({"ok": True, "ready": True, "base_url": BASE, "link_pagination": True})

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            request = httpx.Request(data["method"], urljoin(BASE + "/", data["path"]),
                                    headers=data.get("headers"), json=data.get("body"))
            item = response_for(request)
            envelope = {"status": 200, "json": item.get("json"), "text": None,
                        "link": item.get("link"), "url": str(request.url), **item}
            if envelope.pop("legacy", False):
                envelope.pop("url", None)
                envelope.pop("link", None)
            envelope["headers"] = {"link": envelope.get("link") or ""}
            self.send_json({"ok": True, "response": envelope})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True)
    thread.start()
    monkeypatch.setattr(client_mod, "BROKER_PORT", server.server_address[1])
    client = client_mod.CanvasClient(base_url=BASE, token="", timeout=3)
    try:
        yield client, calls
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()


@pytest.mark.parametrize("suffix", [
    "",
    "; rel=<next>",
    "; rel=next/prev",
    '; rel="<next>"',
    '; rel="next/prev"',
    '; rel="next\talternate"',
    '; rel="next"; title=not=a=token',
])
def test_malformed_relation_metadata_cannot_assert_completion(monkeypatch, suffix):
    replies = [{"json": [{"id": 1}], "link": f"<{NEXT}>{suffix}"},
               {"json": [{"id": 99}], "link": None}]
    with collection(monkeypatch, replies) as (client, calls):
        with pytest.raises(RuntimeError, match="pagination.*Link"):
            client.get_paginated(PATH)
        assert len(calls) == 1


@pytest.mark.parametrize("suffix", [
    '; rel="next"; anchor="https://elsewhere.example/other"',
    '; ANCHOR="/another-collection"; rel="next"',
])
def test_unsupported_link_context_cannot_supply_next_collection(monkeypatch, suffix):
    replies = [{"json": [{"id": 1}], "link": f"<{NEXT}>{suffix}"},
               {"json": [{"id": 99}], "link": None}]
    with collection(monkeypatch, replies) as (client, calls):
        with pytest.raises(RuntimeError, match="pagination.*(context|anchor)"):
            client.get_paginated(PATH)
        assert len(calls) == 1


def test_opaque_query_and_quoted_valid_parameters_survive(monkeypatch):
    cursor = BASE + PATH + "?cursor=%2f%2F,a;b&include%5B%5D=a&include%5B%5D=b&empty=&literal=+"
    header = f'<{cursor}>; title="quoted; words, here"; title*=utf-8\'\'next%20page; rel="alternate NEXT https://relations.example/opaque%2Ftype urn:example:relation"'
    with collection(monkeypatch, [
        {"json": [], "link": header}, {"json": [{"id": 2}], "link": None},
    ]) as (client, calls):
        assert client.get_paginated(PATH) == [{"id": 2}]
        assert str(calls[1].url) == cursor
