"""Tests for the session broker's shared-secret auth (X-Broker-Token).

Covers the mitigation for the broker's unauthenticated localhost trust boundary:
every broker endpoint rejects requests without a matching token, and the client
sends the token (never leaking it into the in-page Canvas request).
"""

from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer

import httpx
import pytest

from canvaspilot import client, session_broker

TEST_TOKEN = "test-broker-token-abc123"
WRONG_TOKEN = "wrong-token-xyz"


_PROXY_ENV_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)


@pytest.fixture()
def broker_server(monkeypatch: pytest.MonkeyPatch):
    """Live Handler on an ephemeral port with a known token; no browser needed.

    Auth is enforced before any job is queued, and /health answers from STATE,
    so none of these tests need Playwright. Proxy env vars are scrubbed so the
    localhost calls are never routed through an egress proxy.
    """
    monkeypatch.setattr(session_broker, "_BROKER_TOKEN", TEST_TOKEN)
    for var in _PROXY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    while not session_broker.STATE.jobs.empty():
        session_broker.STATE.jobs.get_nowait()
    server = ThreadingHTTPServer(("127.0.0.1", 0), session_broker.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


def _authed() -> dict[str, str]:
    return {session_broker.BROKER_TOKEN_HEADER: TEST_TOKEN}


def test_health_rejects_missing_token(broker_server: str) -> None:
    r = httpx.get(f"{broker_server}/health", timeout=5.0)
    assert r.status_code == 403
    assert "unauthorized" in r.json()["error"]


def test_health_rejects_wrong_token(broker_server: str) -> None:
    r = httpx.get(
        f"{broker_server}/health",
        headers={session_broker.BROKER_TOKEN_HEADER: WRONG_TOKEN},
        timeout=5.0,
    )
    assert r.status_code == 403


def test_health_accepts_correct_token(broker_server: str) -> None:
    r = httpx.get(f"{broker_server}/health", headers=_authed(), timeout=5.0)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_status_requires_token(broker_server: str) -> None:
    r = httpx.get(f"{broker_server}/status", timeout=5.0)
    assert r.status_code == 403


def test_fetch_rejects_unauthenticated_without_queueing(broker_server: str) -> None:
    r = httpx.post(f"{broker_server}/fetch", json={"op": "fetch"}, timeout=5.0)
    assert r.status_code == 403
    # The request must be rejected before it can reach the browser job queue.
    assert session_broker.STATE.jobs.qsize() == 0


def test_auth_checked_before_body_parsing(broker_server: str) -> None:
    r = httpx.post(
        f"{broker_server}/fetch",
        content=b"this is not json",
        headers={"Content-Type": "application/json"},
        timeout=5.0,
    )
    assert r.status_code == 403  # not 400: auth gate runs before body parsing


def test_shutdown_rejects_unauthenticated_and_survives(broker_server: str) -> None:
    r = httpx.post(f"{broker_server}/shutdown", json={}, timeout=5.0)
    assert r.status_code == 403
    # The broker must still be alive (an unauthenticated kill must not land).
    r2 = httpx.get(f"{broker_server}/health", headers=_authed(), timeout=5.0)
    assert r2.status_code == 200


def test_resolve_token_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(session_broker.BROKER_TOKEN_ENV, "from-env")
    token, generated = session_broker._resolve_broker_token()
    assert (token, generated) == ("from-env", False)


def test_resolve_token_generates_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(session_broker.BROKER_TOKEN_ENV, raising=False)
    token, generated = session_broker._resolve_broker_token()
    assert generated is True
    assert len(token) >= 32
    token2, _ = session_broker._resolve_broker_token()
    assert token2 != token


def test_broker_token_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(client.BROKER_TOKEN_ENV, "env-secret")
    assert client.broker_token() == "env-secret"
    assert client.broker_auth_headers() == {client.BROKER_TOKEN_HEADER: "env-secret"}


def test_broker_auth_headers_empty_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(client.BROKER_TOKEN_ENV, raising=False)
    assert client.broker_auth_headers() == {}


def test_client_sends_broker_token_not_to_canvas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """broker_fetch authenticates the broker request and keeps the token out of
    the in-page Canvas request (no credential leak to Canvas servers)."""
    monkeypatch.setenv(client.BROKER_TOKEN_ENV, TEST_TOKEN)
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        captured.update(kwargs)
        return httpx.Response(
            200, json={"ok": True, "response": {"status": 200, "json": {"x": 1}}}
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    assert client.broker_fetch("GET", "/api/v1/courses") == {"x": 1}

    http_headers = captured["headers"]
    assert isinstance(http_headers, dict)
    assert http_headers[client.BROKER_TOKEN_HEADER] == TEST_TOKEN
    # The JSON body forwarded to the in-page fetch must not carry the token.
    body = captured["json"]
    assert isinstance(body, dict)
    assert client.BROKER_TOKEN_HEADER not in body["headers"]


def test_client_403_unauthorized_raises_helpful_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(client.BROKER_TOKEN_ENV, raising=False)

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(
            403,
            json={"ok": False, "error": "unauthorized: missing or invalid X-Broker-Token header"},
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(client.CanvasAuthError, match="CANVAS_BROKER_TOKEN"):
        client.broker_fetch("GET", "/api/v1/courses")


def test_client_health_403_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(client.BROKER_TOKEN_ENV, raising=False)

    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(403, json={"ok": False, "error": "unauthorized"})

    monkeypatch.setattr(httpx, "get", fake_get)
    # Fail closed: without the token the broker is treated as unusable.
    assert client.broker_health() is None
