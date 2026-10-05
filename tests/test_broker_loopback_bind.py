"""Loopback-bind guard for the session broker (mitigation 3, issue #5 context).

The broker's only network defense is its 127.0.0.1 bind: /fetch and /shutdown
are unauthenticated. These tests pin the invariant that startup refuses any
non-loopback bind host, so a future constant edit or a --host flag cannot
silently expose those endpoints to the network.

On baseline (guard absent) these tests fail — ``session_broker`` has no
``_assert_loopback_bind`` attribute — which is exactly the exposure: nothing
would refuse a non-loopback bind.
"""

from __future__ import annotations

import socket

import pytest

from canvaspilot import session_broker as sb


def test_guard_exists():
    assert callable(sb._assert_loopback_bind)


@pytest.mark.parametrize(
    "host", ["127.0.0.1", "127.0.0.2", "::1", "localhost", " 127.0.0.1 "]
)
def test_loopback_hosts_accepted(host):
    sb._assert_loopback_bind(host)  # must not raise


@pytest.mark.parametrize(
    "host", ["0.0.0.0", "::", "192.168.1.10", "10.0.0.5", "8.8.8.8", ""]
)
def test_non_loopback_hosts_refused(host):
    with pytest.raises(SystemExit):
        sb._assert_loopback_bind(host)


def test_unresolvable_hostname_refused(monkeypatch):
    def boom(*args, **kwargs):
        raise socket.gaierror("name resolution failed")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    with pytest.raises(SystemExit):
        sb._assert_loopback_bind("not-a-real-host.invalid")


def test_hostname_resolving_non_loopback_refused(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
        ],
    )
    with pytest.raises(SystemExit):
        sb._assert_loopback_bind("some-host")


def test_hostname_with_any_non_loopback_resolution_refused(monkeypatch):
    # One non-loopback address among loopback ones fails the whole host.
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", 0)),
        ],
    )
    with pytest.raises(SystemExit):
        sb._assert_loopback_bind("mixed-host")


def test_refusal_message_names_host():
    with pytest.raises(SystemExit) as excinfo:
        sb._assert_loopback_bind("0.0.0.0")
    assert "0.0.0.0" in str(excinfo.value)


class _FakeServer:
    def __init__(self, addr, handler):
        self.addr = addr

    def serve_forever(self):
        pass


def test_main_refuses_non_loopback_bind_before_serving(monkeypatch):
    monkeypatch.setattr(sb, "DEFAULT_HOST", "0.0.0.0")
    monkeypatch.setattr(sb, "_browser_loop", lambda: sb.STATE.ready.set())
    monkeypatch.setattr(sb, "ThreadingHTTPServer", _FakeServer)
    with pytest.raises(SystemExit):
        sb.main([])


def test_main_still_serves_loopback(monkeypatch):
    assert sb.DEFAULT_HOST == "127.0.0.1"  # guard: the constant itself
    servers = []
    monkeypatch.setattr(sb, "_browser_loop", lambda: sb.STATE.ready.set())
    monkeypatch.setattr(
        sb,
        "ThreadingHTTPServer",
        lambda addr, handler: servers.append(addr) or _FakeServer(addr, handler),
    )
    sb.main([])
    assert servers and servers[0][0] == "127.0.0.1"
