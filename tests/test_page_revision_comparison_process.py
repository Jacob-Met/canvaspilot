"""Actual local HTTP/CLI publication tests; no Canvas account or browser."""

import base64
import contextlib
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from canvaspilot.cli import main


@pytest.fixture
def local_api():
    state = {"calls": [], "after_status": 200}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            parsed = urlsplit(self.path)
            state["calls"].append({
                "method": "GET", "path": parsed.path, "query": parse_qs(parsed.query),
            })
            assert self.headers["Authorization"] == "Bearer synthetic-local-fixture"
            identity = int(parsed.path.rsplit("/", 1)[1])
            status = state["after_status"] if identity == 9 else 200
            payload = json.dumps({
                "revision_id": identity, "body": "First\r\n" if identity == 7 else "Second\n",
                "unknown": {"source": "synthetic loopback", "empty": "", "nullable": None},
            }).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()


def command(base, output, before="7", after="9"):
    return [
        sys.executable, "-B", "-m", "canvaspilot.cli", "compare-page-revisions",
        "0042", "Week / Ω?%#", "--before", before, "--after", after,
        "--out", str(output), "--base-url", base, "--token", "synthetic-local-fixture",
    ]


def environment():
    result = dict(os.environ)
    result["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result["PYTHONDONTWRITEBYTECODE"] = "1"
    return result


def invoke(base, output, before="7", after="9"):
    return subprocess.run(
        command(base, output, before, after), env=environment(),
        capture_output=True, timeout=12, check=False,
    )


def assert_two_reads(calls):
    root = "/api/v1/courses/42/pages/Week%20%2F%20%CE%A9%3F%25%23/revisions/"
    assert calls == [
        {"method": "GET", "path": root + identity,
         "query": {"summary": ["false"], "per_page": ["50"]}}
        for identity in ("7", "9")
    ]


def test_actual_cli_two_gets_and_complete_publication(local_api, tmp_path):
    state, base = local_api
    output = tmp_path / "report.html"
    result = invoke(base, output)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    summary = json.loads(result.stdout)
    assert summary == {
        "ok": True, "output": str(output),
        "selection": {
            "course_id": "42", "page_url": "Week / Ω?%#",
            "before_revision": "7", "after_revision": "9",
        },
        "line_diff_status": "computed",
    }
    assert_two_reads(state["calls"])
    content = output.read_bytes()
    encoded = content.split(b"data:application/json;base64,", 1)[1].split(b'"', 1)[0]
    report = json.loads(base64.b64decode(encoded, validate=True))
    assert report["before"]["revision"]["body"] == "First\r\n"
    assert report["after"]["revision"]["body"] == "Second\n"
    assert report["selection"] == summary["selection"]
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize("before,after", [("latest", "9"), ("007", "7"), ("0", "9")])
def test_actual_bad_selector_has_no_get_or_file(local_api, tmp_path, before, after):
    state, base = local_api
    result = invoke(base, tmp_path / "not-created.html", before, after)
    assert result.returncode == 2
    assert result.stdout == b""
    assert state["calls"] == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ["file", "directory", "dangling-symlink"])
def test_actual_existing_output_protected_before_get(local_api, tmp_path, kind):
    state, base = local_api
    output = tmp_path / "protected"
    if kind == "file":
        output.write_bytes(b"exact prior file\x00\xff")
    elif kind == "directory":
        output.mkdir()
    else:
        output.symlink_to("absent-target")
    result = invoke(base, output)
    assert result.returncode == 1
    assert result.stdout == b""
    assert json.loads(result.stderr)["error"] == "FileExistsError"
    assert state["calls"] == []
    assert list(tmp_path.iterdir()) == [output]
    if kind == "file":
        assert output.read_bytes() == b"exact prior file\x00\xff"
    elif kind == "directory":
        assert list(output.iterdir()) == []
    else:
        assert output.is_symlink() and os.readlink(output) == "absent-target"


def test_actual_second_get_permission_failure_creates_nothing(local_api, tmp_path):
    state, base = local_api
    state["after_status"] = 403
    result = invoke(base, tmp_path / "not-created.html")
    assert result.returncode == 1
    assert result.stdout == b""
    assert json.loads(result.stderr)["error"] == "CanvasAuthError"
    assert_two_reads(state["calls"])
    assert list(tmp_path.iterdir()) == []


def test_actual_missing_parent_preserves_neighbour(local_api, tmp_path):
    state, base = local_api
    neighbour = tmp_path / "keep"
    neighbour.write_bytes(b"unchanged")
    result = invoke(base, tmp_path / "missing" / "report.html")
    assert result.returncode == 1 and result.stdout == b""
    assert json.loads(result.stderr)["error"] == "FileNotFoundError"
    assert_two_reads(state["calls"])
    assert list(tmp_path.iterdir()) == [neighbour]
    assert neighbour.read_bytes() == b"unchanged"


def test_actual_competing_publishers_only_one_new_output(local_api, tmp_path):
    state, base = local_api
    output = tmp_path / "single.html"
    children = [
        subprocess.Popen(command(base, output), env=environment(),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for _ in range(2)
    ]
    try:
        results = [child.communicate(timeout=12) for child in children]
        assert sorted(child.returncode for child in children) == [0, 1]
        for child, (stdout, stderr) in zip(children, results):
            if child.returncode == 0:
                assert json.loads(stdout)["ok"] is True and stderr == b""
            else:
                assert stdout == b"" and json.loads(stderr)["error"] == "FileExistsError"
        assert output.read_bytes().startswith(b"<!doctype html>")
        assert list(tmp_path.iterdir()) == [output]
        assert len(state["calls"]) in (2, 4)
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=3)


def test_client_closes_and_cleanup_warning_is_success(monkeypatch, tmp_path, capsys):
    import canvaspilot.client
    import canvaspilot.page_export

    clients = []

    class Client:
        def __init__(self, **kwargs):
            self.calls = []
            self.closed = False
            clients.append(self)

        def request(self, method, path, **kwargs):
            self.calls.append((method, path, kwargs))
            return {"revision_id": int(path.rsplit("/", 1)[1]), "body": "same"}

        def close(self):
            self.closed = True

    monkeypatch.setattr(canvaspilot.client, "CanvasClient", Client)
    output = tmp_path / "published.html"
    original_unlink = os.unlink

    def fail_published_cleanup(path, *args, **kwargs):
        if Path(path).name.startswith(".canvaspilot-pages-") and output.exists():
            raise OSError("synthetic post-publication cleanup refusal")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(canvaspilot.page_export.os, "unlink", fail_published_cleanup)
    try:
        main(["compare-page-revisions", "42", "p", "--before", "7", "--after", "9",
              "--out", str(output)])
        captured = capsys.readouterr()
        summary = json.loads(captured.out)
        assert summary["ok"] is True and summary["cleanup_warning"]
        assert captured.err == ""
        assert clients[0].closed and len(clients[0].calls) == 2
        assert output.read_bytes().startswith(b"<!doctype html>")
    finally:
        monkeypatch.setattr(canvaspilot.page_export.os, "unlink", original_unlink)
        for path in tmp_path.glob(".canvaspilot-pages-*"):
            with contextlib.suppress(FileNotFoundError):
                path.unlink()


def test_invalid_selector_precedes_client_construction(monkeypatch, tmp_path):
    import canvaspilot.client

    def forbidden(**kwargs):
        raise AssertionError("client construction must not occur")

    monkeypatch.setattr(canvaspilot.client, "CanvasClient", forbidden)
    with pytest.raises(SystemExit) as failure:
        main(["compare-page-revisions", "42", "p", "--before", "0007", "--after", "7",
              "--out", str(tmp_path / "absent.html")])
    assert failure.value.code == 2
    assert not list(tmp_path.iterdir())
