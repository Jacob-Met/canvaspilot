"""Read-only broker mode: --read-only rejects non-GET/HEAD /fetch ops (403).

Spins up a real Handler on an ephemeral loopback port with STATE patched
(no browser needed): a fake worker answers queued jobs with an echo payload.
Proves (i) write methods are rejected in read-only mode, (ii) reads still pass,
and (iii) default behavior (flag off) is unchanged.
"""

from __future__ import annotations

import queue
import threading
from http.server import ThreadingHTTPServer

import httpx
import pytest

from canvaspilot.session_broker import STATE, Handler


@pytest.fixture
def live_broker_readonly(monkeypatch):
    """Real Handler over loopback; STATE patched; jobs answered by a fake worker."""
    for var in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    ):
        monkeypatch.delenv(var, raising=False)

    saved_read_only, saved_ready, saved_error = STATE.read_only, STATE.ready.is_set(), STATE.error
    STATE.read_only = True
    STATE.ready.set()

    stop = threading.Event()

    def worker() -> None:
        while not stop.is_set():
            try:
                job, reply = STATE.jobs.get(timeout=0.1)
            except queue.Empty:
                continue
            reply.put({"ok": True, "echo": job})

    threading.Thread(target=worker, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        STATE.read_only, STATE.error = saved_read_only, saved_error
        if not saved_ready:
            STATE.ready.clear()
        while True:  # drain any leftover test jobs
            try:
                STATE.jobs.get_nowait()
            except queue.Empty:
                break


def _fetch(base, method, path="/api/v1/courses"):
    return httpx.post(
        f"{base}/fetch",
        json={"op": "fetch", "method": method, "path": path},
        timeout=10.0,
    )


def test_read_only_allows_get(live_broker_readonly):
    r = _fetch(live_broker_readonly, "GET")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["echo"]["path"] == "/api/v1/courses"


def test_read_only_allows_head(live_broker_readonly):
    r = _fetch(live_broker_readonly, "HEAD")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_read_only_defaults_missing_method_to_get(live_broker_readonly):
    r = httpx.post(
        f"{live_broker_readonly}/fetch",
        json={"op": "fetch", "path": "/api/v1/courses"},
        timeout=10.0,
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH", "post"])
def test_read_only_rejects_write_methods(live_broker_readonly, method):
    r = _fetch(live_broker_readonly, method)
    assert r.status_code == 403
    body = r.json()
    assert body["ok"] is False
    assert "read-only" in body["error"]


def test_read_only_rejects_write_without_explicit_op(live_broker_readonly):
    # /fetch fills op="fetch" when missing; the gate still applies.
    r = httpx.post(
        f"{live_broker_readonly}/fetch",
        json={"method": "POST", "path": "/api/v1/courses/1"},
        timeout=10.0,
    )
    assert r.status_code == 403


def test_default_mode_unchanged_allows_post(live_broker_readonly, monkeypatch):
    # Flip read_only back off mid-fixture: default posture must be unchanged.
    STATE.read_only = False
    r = _fetch(live_broker_readonly, "POST", path="/api/v1/courses/1/discussion_topics")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["echo"]["method"] == "POST"


def test_read_only_defaults_off():
    assert STATE.read_only is False
