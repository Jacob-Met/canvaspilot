"""Calendar identity follows the provider actually serving session reads."""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from datetime import UTC, datetime
from http.server import ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from canvaspilot import calendar_export, session_broker
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient

SCHOOL = "https://school.fixture.invalid"
ROWS = [{"id": 1, "name": "Authored deadline", "due_at": "2026-11-01T08:45:00Z"}]
NOW = datetime(2026, 10, 8, 12, tzinfo=UTC)


def api_for_session(monkeypatch, health):
    monkeypatch.setattr(calendar_export, "broker_health", health)
    calls = []
    client = CanvasClient(token="", base_url="https://canvas.instructure.com")
    def assignments(course, **kwargs):
        calls.append(course)
        return ROWS
    return SimpleNamespace(client=client, list_assignments=assignments), calls


@pytest.mark.parametrize("health", [
    None, {}, {"ok": True}, {"base_url": None}, {"base_url": ""},
    {"base_url": "school.fixture.invalid"}, {"base_url": "https://school.fixture.invalid/?query=1"},
])
def test_unknown_or_invalid_session_provider_refuses_before_course_read(monkeypatch, health):
    api, calls = api_for_session(monkeypatch, lambda: health)
    with pytest.raises(ValueError, match="base URL|HTTP"):
        calendar_export.build_assignment_calendar(api, [42], generated_at=NOW)
    assert calls == []


def test_provider_change_refuses_before_reading_next_course(monkeypatch):
    states = iter([{"base_url": SCHOOL}, {"base_url": "https://other.fixture.invalid"}])
    api, calls = api_for_session(monkeypatch, lambda: next(states))
    with pytest.raises(ValueError, match="provider changed"):
        calendar_export.build_assignment_calendar(api, [42, 77], generated_at=NOW)
    assert calls == ["42"]


def test_equivalent_provider_spelling_keeps_identity(monkeypatch):
    states = iter([{"base_url": "https://SCHOOL.fixture.invalid:443/"},
                   {"base_url": SCHOOL}])
    api, calls = api_for_session(monkeypatch, lambda: next(states))
    _, report = calendar_export.build_assignment_calendar(api, [42], generated_at=NOW)
    assert report["source"] == SCHOOL
    assert calls == ["42"]


@pytest.mark.parametrize("mode", ["fixture", "token"])
def test_token_and_fixture_identity_never_consult_session_broker(monkeypatch, mode):
    def forbidden():
        raise AssertionError("session broker must not be probed for token/fixture export")
    monkeypatch.setattr(calendar_export, "broker_health", forbidden)
    client = CanvasClient(base_url=SCHOOL, token="synthetic-only" if mode == "token" else "",
                          fixture={"routes": {"GET /api/v1/courses/42/assignments": ROWS}}
                          if mode == "fixture" else None)
    if mode == "fixture":
        api = CanvasAPI(client)
    else:
        api = SimpleNamespace(client=client, list_assignments=lambda *args, **kwargs: ROWS)
    _, report = calendar_export.build_assignment_calendar(api, [42], generated_at=NOW)
    assert report["source"] == SCHOOL
    client.close()


@pytest.mark.parametrize("transition", ["unknown-before", "changed-after", "missing-after"])
def test_real_cli_provider_guard_leaves_no_artifact(monkeypatch, tmp_path, transition):
    """Execute unchanged Handler/_call/queue, replacing only browser response work."""
    calls = []
    stop = threading.Event()
    monkeypatch.setattr(session_broker.STATE, "base_url", "" if transition == "unknown-before" else SCHOOL)
    monkeypatch.setattr(session_broker.STATE, "read_only", True)
    monkeypatch.setattr(session_broker.STATE, "error", None)
    monkeypatch.setattr(session_broker.STATE, "jobs", queue.Queue())
    monkeypatch.setattr(session_broker.STATE, "ready", threading.Event())
    session_broker.STATE.ready.set()

    def browser():
        while not stop.is_set():
            try:
                job, reply = session_broker.STATE.jobs.get(timeout=0.03)
            except queue.Empty:
                continue
            calls.append(job)
            assert job["method"] == "GET"
            session_broker.STATE.base_url = (
                "https://other.fixture.invalid" if transition == "changed-after" else ""
            )
            reply.put({"ok": True, "response": {"status": 200, "json": ROWS,
                                                "text": None, "headers": {"link": ""}}})

    server = ThreadingHTTPServer(("127.0.0.1", 0), session_broker.Handler)
    serving = threading.Thread(target=server.serve_forever,
                               kwargs={"poll_interval": 0.02}, daemon=True)
    worker = threading.Thread(target=browser, daemon=True)
    serving.start()
    worker.start()
    output, profile = tmp_path / "refused.ics", tmp_path / "unused-profile"
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("CANVAS") and not key.upper().endswith("_PROXY")}
    env["CANVAS_SESSION_PORT"] = str(server.server_address[1])
    try:
        result = subprocess.run(
            [sys.executable, "-m", "canvaspilot.cli", "export-calendar", "42", "77",
             "--token", "", "--profile", str(profile), "--out", str(output)],
            env=env, capture_output=True, text=True, timeout=10, check=False,
        )
        assert result.returncode == 1
        error = json.loads(result.stderr.strip().splitlines()[-1])
        assert error["ok"] is False and error["error"] == "ValueError"
        assert not result.stdout and "Traceback" not in result.stderr
        assert not output.exists() and not profile.exists()
        assert not list(tmp_path.glob(".*.tmp"))
        assert len(calls) == (0 if transition == "unknown-before" else 1)
    finally:
        server.shutdown()
        server.server_close()
        stop.set()
        serving.join(timeout=3)
        worker.join(timeout=3)
