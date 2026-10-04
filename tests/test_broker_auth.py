"""Auth boundary: broker /fetch, /status, /shutdown require X-Broker-Token.

Spins up a real Handler on an ephemeral loopback port with STATE patched
(no browser needed): a fake worker answers queued jobs with an echo payload.
Proves (i) the hole is closed for callers without the token and
(ii) the legitimate same-user client path (env-or-token-file) still works.
"""

from __future__ import annotations

import queue
import threading
from http.server import ThreadingHTTPServer

import httpx
import pytest

from canvaspilot.client import (
    BROKER_TOKEN_ENV,
    BROKER_TOKEN_HEADER,
    broker_auth_headers,
    issue_broker_token,
    load_broker_token,
)
from canvaspilot.session_broker import STATE, Handler

# Loopback test traffic must not consult proxy env: this sandbox's NO_PROXY
# contains entries httpx 0.28.1 cannot parse as URL patterns.
_HTTP = httpx.Client(trust_env=False)


@pytest.fixture
def live_broker(tmp_path, monkeypatch):
    """Real Handler over loopback; STATE patched; jobs answered by a fake worker."""
    monkeypatch.delenv(BROKER_TOKEN_ENV, raising=False)
    profile = tmp_path / "profile"
    token, created = issue_broker_token(profile)
    assert created

    saved_token, saved_ready, saved_error = STATE.token, STATE.ready.is_set(), STATE.error
    STATE.token = token
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
        yield {"base": base, "token": token, "profile": profile}
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        STATE.token, STATE.error = saved_token, saved_error
        if not saved_ready:
            STATE.ready.clear()
        while True:  # drain any leftover test jobs
            try:
                STATE.jobs.get_nowait()
            except queue.Empty:
                break


def _fetch(base, **kwargs):
    return _HTTP.post(
        f"{base}/fetch",
        json={"op": "fetch", "method": "GET", "path": "/api/v1/courses"},
        timeout=10.0,
        **kwargs,
    )


def test_fetch_rejects_missing_token(live_broker):
    r = _fetch(live_broker["base"])
    assert r.status_code == 401
    assert r.json()["ok"] is False


def test_fetch_rejects_wrong_token(live_broker):
    r = _fetch(live_broker["base"], headers={BROKER_TOKEN_HEADER: "wrong-token"})
    assert r.status_code == 401
    assert r.json()["ok"] is False


def test_fetch_accepts_valid_token(live_broker):
    r = _fetch(live_broker["base"], headers={BROKER_TOKEN_HEADER: live_broker["token"]})
    assert r.status_code == 200
    payload = r.json()
    assert payload["ok"] is True
    assert payload["echo"]["path"] == "/api/v1/courses"


def test_status_requires_token(live_broker):
    base = live_broker["base"]
    assert _HTTP.get(f"{base}/status", timeout=5.0).status_code == 401
    r = _HTTP.get(base + "/status", headers={BROKER_TOKEN_HEADER: live_broker["token"]}, timeout=10.0)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_shutdown_requires_token(live_broker):
    # Never send a valid token to /shutdown in tests — it would os._exit the runner.
    r = _HTTP.post(f"{live_broker['base']}/shutdown", json={}, timeout=5.0)
    assert r.status_code == 401
    assert r.json()["ok"] is False


def test_health_open_but_no_session_leak(live_broker):
    r = _HTTP.get(f"{live_broker['base']}/health", timeout=5.0)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["ready"] is True
    for leaked in ("url", "title", "profile", "base_url", "headless"):
        assert leaked not in body


def test_legitimate_client_path_uses_token_file(live_broker):
    """Same-user client: no env var, token resolved from the profile token file."""
    headers = broker_auth_headers(live_broker["profile"])
    assert headers[BROKER_TOKEN_HEADER] == live_broker["token"]
    r = _fetch(live_broker["base"], headers=headers)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_env_token_overrides_file(tmp_path, monkeypatch):
    profile = tmp_path / "p"
    file_token, _ = issue_broker_token(profile)
    monkeypatch.setenv(BROKER_TOKEN_ENV, "env-secret")
    assert load_broker_token(profile) == "env-secret"
    token, created = issue_broker_token(profile)
    assert (token, created) == ("env-secret", False)
    assert file_token != "env-secret"


def test_token_file_permissions_and_reuse(tmp_path):
    profile = tmp_path / "p"
    t1, c1 = issue_broker_token(profile)
    assert c1 is True
    mode = (profile / ".broker-token").stat().st_mode & 0o777
    assert mode == 0o600
    t2, c2 = issue_broker_token(profile)
    assert (t2, c2) == (t1, False)


def test_session_stop_sends_profile_token(tmp_path, monkeypatch):
    """`session stop --profile DIR` authenticates with that profile's token file."""
    from canvaspilot import cli as cli_mod

    monkeypatch.delenv(BROKER_TOKEN_ENV, raising=False)
    profile = tmp_path / "custom"
    token, _ = issue_broker_token(profile)

    captured: dict = {}

    class FakeResp:
        text = '{"ok": true}'

    def fake_post(url, **kwargs):
        captured.update(kwargs)
        assert url.endswith("/shutdown")
        return FakeResp()

    monkeypatch.setattr("httpx.post", fake_post)
    cli_mod.main(["session", "stop", "--profile", str(profile)])
    assert captured["headers"][BROKER_TOKEN_HEADER] == token


def test_session_status_sends_profile_token(tmp_path, monkeypatch, capsys):
    """`session status --profile DIR` sends the profile token on /status."""
    from canvaspilot import cli as cli_mod
    from canvaspilot import client as client_mod

    monkeypatch.delenv(BROKER_TOKEN_ENV, raising=False)
    profile = tmp_path / "custom"
    token, _ = issue_broker_token(profile)

    captured: dict = {}

    class FakeResp:
        def json(self):
            return {"ok": True}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        assert url.endswith("/status")
        return FakeResp()

    monkeypatch.setattr(client_mod, "broker_health", lambda: {"ok": True})
    monkeypatch.setattr("httpx.get", fake_get)
    cli_mod.main(["session", "status", "--profile", str(profile)])
    assert captured["headers"][BROKER_TOKEN_HEADER] == token
    assert '"ok": true' in capsys.readouterr().out
