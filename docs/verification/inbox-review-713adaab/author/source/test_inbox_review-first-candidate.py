"""Native contract fixtures for inbox review; never contacts a Canvas account."""

import copy
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "canvaspilot-synthetic-inbox-713adaab"
CONVERSATION = {
    "id": 901,
    "subject": "Synthetic office hours — 火",
    "workflow_state": "unread",
    "starred": True,
    "message_count": 2,
    "participants": [{"id": 7, "name": "Fictional Student"}, {"id": 9, "name": "Fictional Tutor"}],
    "messages": [
        {
            "id": 51,
            "author_id": 9,
            "created_at": "2026-10-08T08:30:00Z",
            "body": "Révision <em>literal markup</em> & 火\nSecond line",
            "generated": False,
            "attachments": [{"id": 72, "filename": "notes.txt", "url": "https://fixture.invalid/notes"}],
            "media_comment": None,
            "forwarded_messages": [
                {"id": 44, "author_id": 7, "body": "Earlier question", "forwarded_messages": []}
            ],
        },
        {"id": 50, "author_id": 7, "body": "", "attachments": [], "generated": False},
    ],
}


@pytest.fixture
def inbox_http(monkeypatch, tmp_path):
    conversations = [
        copy.deepcopy(CONVERSATION),
        {**copy.deepcopy(CONVERSATION), "id": 902, "workflow_state": "read", "starred": False},
        {**copy.deepcopy(CONVERSATION), "id": 903, "workflow_state": "archived", "starred": False},
    ]
    state = {"conversations": conversations, "requests": [], "status": 200, "fail_next": False}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            request = urlsplit(self.path)
            query = parse_qs(request.query)
            state["requests"].append({"method": self.command, "path": request.path, "query": query})
            status = state["status"]
            link = None
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                status = 401
            if status != 200:
                body = {"error": "Synthetic read refusal"}
            elif request.path == "/api/v1/conversations":
                scope = query.get("scope", ["inbox"])[0]
                rows = state["conversations"]
                if scope == "unread":
                    rows = [row for row in rows if row["workflow_state"] == "unread"]
                elif scope == "archived":
                    rows = [row for row in rows if row["workflow_state"] == "archived"]
                elif scope == "starred":
                    rows = [row for row in rows if row["starred"]]
                elif scope == "sent":
                    rows = [row for row in rows if row["id"] == 902]
                else:
                    rows = [row for row in rows if row["workflow_state"] != "archived"]
                if query.get("cursor") == ["next"]:
                    if state["fail_next"]:
                        status, body = 500, {"error": "Synthetic later-page refusal"}
                    else:
                        body = rows[1:]
                else:
                    body = rows[:1]
                    if len(rows) > 1:
                        following = {"cursor": "next"}
                        if "scope" in query:
                            following["scope"] = scope
                        link = f'<{base}/api/v1/conversations?{urlencode(following)}>; rel="next"'
            elif request.path.startswith("/api/v1/conversations/"):
                identifier = request.path.rsplit("/", 1)[1]
                row = next((row for row in state["conversations"] if str(row["id"]) == identifier), None)
                if row is None:
                    status, body = 404, {"error": "Synthetic missing conversation"}
                else:
                    # Canvas documents this default side effect. This is a
                    # contract fixture, not an observation of a live school.
                    if query.get("auto_mark_as_read") != ["false"] and row["workflow_state"] == "unread":
                        row["workflow_state"] = "read"
                    body = row
            else:
                status, body = 404, {"error": "Unknown fixture route"}
            encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            if link:
                self.send_header("Link", link)
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    base = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("CANVAS_BASE_URL", base)
    monkeypatch.setenv("CANVAS_API_TOKEN", TOKEN)
    monkeypatch.setenv("CANVAS_PROFILE", str(tmp_path / "unused-profile"))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    try:
        yield state, base
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def run_cli(base, *arguments):
    return subprocess.run(
        [sys.executable, "-B", "-m", "canvaspilot.cli", *arguments,
         "--base-url", base, "--token", TOKEN],
        cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, timeout=15,
        check=False,
    )


@pytest.mark.parametrize("workflow_state", ["unread", "read", "archived"])
def test_conversation_preserves_state_and_complete_payload(inbox_http, workflow_state):
    state, base = inbox_http
    state["conversations"][0]["workflow_state"] = workflow_state
    before = copy.deepcopy(state["conversations"][0])
    with CanvasAPI(CanvasClient(base_url=base, token=TOKEN)) as api:
        result = api.get_conversation(901)
    assert result == before
    assert state["conversations"][0] == before
    assert state["requests"][0]["query"]["auto_mark_as_read"] == ["false"]
    assert [request["method"] for request in state["requests"]] == ["GET"]


def test_default_inbox_uses_default_scope_and_all_link_pages(inbox_http):
    state, base = inbox_http
    before = copy.deepcopy(state["conversations"])
    with CanvasAPI(CanvasClient(base_url=base, token=TOKEN)) as api:
        result = api.list_conversations()
    assert result == before[:2]
    assert len(state["requests"]) == 2
    assert "scope" not in state["requests"][0]["query"]
    assert state["requests"][1]["query"] == {"cursor": ["next"]}
    assert state["conversations"] == before


@pytest.mark.parametrize("scope,identifiers", [
    ("unread", [901]), ("starred", [901]), ("archived", [903]), ("sent", [902]),
])
def test_explicit_inbox_scopes_remain_server_filters(inbox_http, scope, identifiers):
    state, base = inbox_http
    with CanvasAPI(CanvasClient(base_url=base, token=TOKEN)) as api:
        result = api.list_conversations(scope=scope)
    assert [row["id"] for row in result] == identifiers
    assert state["requests"][0]["query"]["scope"] == [scope]


def test_empty_inbox_remains_empty(inbox_http):
    state, base = inbox_http
    state["conversations"] = []
    with CanvasAPI(CanvasClient(base_url=base, token=TOKEN)) as api:
        assert api.list_conversations() == []


def test_cli_inbox_selects_unread_and_preserves_returned_rows(inbox_http):
    state, base = inbox_http
    before = copy.deepcopy(state["conversations"][0])
    completed = run_cli(base, "inbox", "--scope", "unread")
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == [before]
    assert state["conversations"][0] == before
    assert state["requests"][0]["query"]["scope"] == ["unread"]


def test_cli_conversation_preserves_unread_and_nested_text(inbox_http):
    state, base = inbox_http
    before = copy.deepcopy(state["conversations"][0])
    completed = run_cli(base, "conversation", "901")
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == before
    assert state["conversations"][0] == before
    assert state["requests"][0]["query"]["auto_mark_as_read"] == ["false"]


@pytest.mark.parametrize("identifier", ["0", "-1", "not-an-id", "1.5"])
def test_cli_rejects_invalid_conversation_id_before_requests(inbox_http, identifier):
    state, base = inbox_http
    completed = run_cli(base, "conversation", identifier)
    assert completed.returncode == 2
    assert "must be a positive integer" in completed.stderr
    assert completed.stdout == ""
    assert state["requests"] == []


@pytest.mark.parametrize("status", [401, 404, 500])
def test_cli_read_errors_are_controlled_and_have_no_success_output(inbox_http, status):
    state, base = inbox_http
    state["status"] = status
    completed = run_cli(base, "conversation", "901")
    assert completed.returncode == 1
    assert completed.stdout == ""
    failure = json.loads(completed.stderr)
    assert failure["ok"] is False
    assert failure["error"] in ("CanvasAuthError", "HTTPStatusError")
    assert state["conversations"][0]["workflow_state"] == "unread"


def test_cli_inbox_later_page_error_never_prints_partial_success(inbox_http):
    state, base = inbox_http
    state["fail_next"] = True
    completed = run_cli(base, "inbox")
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert json.loads(completed.stderr)["ok"] is False
    assert len(state["requests"]) == 2
