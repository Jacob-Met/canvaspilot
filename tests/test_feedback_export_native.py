"""Read actual Canvas HTTP responses through the CLI and inspect the saved HTML."""

import copy
import hashlib
import json
import os
import subprocess
import sys
import threading
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "submission_feedback.json"
ASSIGNMENT = "/api/v1/courses/41/assignments/902"
SUBMISSION = ASSIGNMENT + "/submissions/self"
TOKEN = "feedback-export-synthetic-only"


class Document(HTMLParser):
    """Independent consumer: collect visible text, field values and resource tags."""

    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.fields = {}
        self.parts = []
        self.current_field = None
        self.hidden = 0
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.tags.append((tag, attributes))
        if tag in {"style", "script"}:
            self.hidden += 1
        if "data-field" in attributes:
            self.current_field = attributes["data-field"]
            self.fields.setdefault(self.current_field, [])

    def handle_endtag(self, tag):
        if tag in {"style", "script"}:
            self.hidden -= 1
        if tag == "dd":
            self.current_field = None

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)
            if self.current_field is not None:
                self.fields[self.current_field].append(data)

    @property
    def text(self):
        return " ".join(self.parts)

    def field(self, key):
        return "".join(self.fields[key])


@pytest.fixture
def provider(tmp_path, request):
    state = {
        "source": json.loads(FIXTURE.read_text()),
        "requests": [],
        "submission_status": 200,
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            uri = urlsplit(self.path)
            query = parse_qs(uri.query)
            state["requests"].append({"method": self.command, "path": uri.path, "query": query})
            if self.headers.get("Authorization") != "Bearer " + TOKEN:
                code, body = 401, {"error": "Authored fixture requires its disposable token"}
            elif uri.path == ASSIGNMENT and query == {"per_page": ["50"]}:
                code, body = 200, state["source"]["assignment"]
            elif uri.path == SUBMISSION and query == {
                "per_page": ["50"],
                "include[]": ["submission_comments", "rubric_assessment"],
            }:
                code = state["submission_status"]
                body = state["source"]["submission"] if code == 200 else {"error": "Authored refusal"}
            else:
                code, body = 404, {"error": "Unexpected fixture route"}
            encoded = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_POST(self):
            state["requests"].append({"method": self.command, "path": self.path})
            self.send_error(405)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = dict(os.environ)
    for key in tuple(env):
        if key.lower().endswith("_proxy") or key.startswith("CANVAS_"):
            env.pop(key)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["CANVAS_PROFILE"] = str(tmp_path / "unused-profile")
    # Keep the receiving source path explicit; dependencies may live elsewhere.
    env["PYTHONPATH"] = os.environ.get("CANVASPILOT_TEST_SOURCE", str(ROOT / "src"))
    if os.environ.get("PYTHONPATH"):
        env["PYTHONPATH"] += os.pathsep + os.environ["PYTHONPATH"]
    base = f"http://127.0.0.1:{server.server_port}"
    state["base_url"] = base

    def invoke(output, *extra):
        result = subprocess.run(
            [sys.executable, "-B", "-m", "canvaspilot.cli", "export-feedback", "41", "902",
             "--base-url", base, "--token", TOKEN, "--out", str(output), *extra],
            env=env, cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
        )
        state["last_process"] = {"returncode": result.returncode,
                                 "stdout": result.stdout, "stderr": result.stderr,
                                 "output": str(output)}
        return result

    try:
        yield state, invoke
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not (tmp_path / "unused-profile").exists()
        if os.environ.get("CANVASPILOT_EXPORT_EVIDENCE"):
            evidence = Path(os.environ["CANVASPILOT_EXPORT_EVIDENCE"])
            evidence.mkdir(parents=True, exist_ok=True)
            (evidence / (request.node.name + ".json")).write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n"
            )


def assert_reads(state, calls=1):
    assert [r["path"] for r in state["requests"]] == [ASSIGNMENT, SUBMISSION] * calls
    assert {r["method"] for r in state["requests"]} == {"GET"}
    assert "read_status" not in json.dumps(state["requests"])


def error_report(result):
    # Native HTTPX diagnostics can precede the CLI's final structured error.
    # Keep the whole stderr in the receiving receipt; do not alter logging.
    return json.loads(result.stderr.splitlines()[-1])


def test_cli_saves_readable_feedback_from_real_reader(provider, tmp_path):
    state, invoke = provider
    original = copy.deepcopy(state["source"])
    output = tmp_path / "feedback.html"
    completed = invoke(output)
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    content = output.read_bytes()
    document = Document(content.decode("utf-8"))
    assert report["ok"] is True
    assert report["sha256"] == hashlib.sha256(content).hexdigest()
    assert report["course_id"] == 41 and report["assignment_id"] == 902
    assert document.field("submission.score") == "0"
    assert document.field("submission.attempt") == "2"
    assert document.field("submission.grader_id") == "-19"
    assert document.field("assignment.points_possible") == "20"
    assert document.field("rubric.points_possible") == "12"
    assert "grading preceded the latest resubmission" in document.text
    assert "not used for grading" in document.text
    assert "Explain the source." in document.text
    assert "Earlier rubric criterion." in document.text
    assert "Synthetic student" in document.text and "Synthetic reviewer" in document.text
    assert "notes.txt" in document.text and "synthetic-audio" in document.text
    assert "instructor comments" not in document.text.lower()
    assert not {tag for tag, _ in document.tags} & {"script", "iframe", "img", "audio", "video", "link", "form"}
    assert state["source"] == original
    assert_reads(state)


@pytest.mark.parametrize("state_kind", ["missing", "null", "empty"])
def test_cli_distinguishes_unreturned_and_empty_feedback(provider, tmp_path, state_kind):
    state, invoke = provider
    source = state["source"]
    if state_kind == "missing":
        source["assignment"].pop("rubric")
        source["submission"].pop("rubric_assessment")
        source["submission"].pop("submission_comments")
    else:
        source["assignment"]["rubric"] = [] if state_kind == "empty" else None
        source["submission"]["rubric_assessment"] = {} if state_kind == "empty" else None
        source["submission"]["submission_comments"] = [] if state_kind == "empty" else None
    source["submission"]["score"] = None
    source["submission"]["grade_matches_current_submission"] = None
    output = tmp_path / "unknown.html"
    result = invoke(output)
    assert result.returncode == 0, result.stderr
    document = Document(output.read_text())
    assert document.field("submission.score") == "Not returned"
    assert "did not establish whether the grade matches" in document.text
    if state_kind == "empty":
        assert "empty comment list" in document.text
        assert "empty criterion list" in document.text
    else:
        assert "Submission comments were not returned" in document.text
        assert "Rubric criteria were not returned" in document.text
        assert "empty comment list" not in document.text
    assert_reads(state)


@pytest.mark.parametrize("flag", ["hide_points", "hide_score_total", "hide_outcome_results"])
def test_cli_keeps_rubric_display_flags_distinct(provider, tmp_path, flag):
    state, invoke = provider
    state["source"]["assignment"]["rubric_settings"][flag] = True
    output = tmp_path / "display.html"
    result = invoke(output)
    assert result.returncode == 0, result.stderr
    doc = Document(output.read_text())
    # Rubric flags never hide or reassign the separately reported submission score.
    assert doc.field("submission.score") == "0"
    assert doc.field("assignment.points_possible") == "20"
    if flag == "hide_points":
        assert "rubric.points_possible" not in doc.fields
        assert not any(key.endswith(".points") for key in doc.fields)
        assert "Explain the source." in doc.text
        assert "Developing" in doc.text
    elif flag == "hide_score_total":
        assert "rubric.points_possible" not in doc.fields
        assert doc.field("criterion.1.assessment.points") == "3"
        assert doc.field("criterion.2.assessment.points") == "0"
    else:
        # This flag concerns posting outcomes to Learning Mastery Gradebook.
        # It does not mean the returned criterion feedback should disappear.
        assert doc.field("rubric.points_possible") == "12"
        assert doc.field("criterion.1.assessment.points") == "3"
        assert "Explain the source." in doc.text
    assert_reads(state)


def test_cli_literal_unicode_markup_and_media_only_comment(provider, tmp_path):
    state, invoke = provider
    text = '<img src="https://invalid.example/pixel" onerror="alert(1)">\nλ < 2 & café 🪷'
    state["source"]["submission"]["submission_comments"][0]["comment"] = text
    state["source"]["assignment"]["name"] = '</title><script>alert("title")</script>'
    output = tmp_path / "literal.html"
    result = invoke(output)
    assert result.returncode == 0, result.stderr
    doc = Document(output.read_text())
    assert doc.field("comment.1.comment") == text
    assert doc.field("comment.2.comment") == "Returned empty text"
    assert "synthetic-audio" in doc.text and "notes.txt" in doc.text
    assert not {tag for tag, _ in doc.tags} & {"script", "img", "audio", "video", "iframe"}
    assert_reads(state)


@pytest.mark.parametrize("status", [403, 404, 500])
def test_cli_failed_read_creates_no_file_or_success(provider, tmp_path, status):
    state, invoke = provider
    state["submission_status"] = status
    output = tmp_path / "refused.html"
    result = invoke(output)
    assert result.returncode == 1
    assert result.stdout == ""
    error = error_report(result)
    assert error["ok"] is False
    assert not output.exists()
    assert_reads(state)


@pytest.mark.parametrize("kind", ["ordinary", "dangling-symlink", "directory"])
def test_cli_existing_destination_is_preserved_before_read(provider, tmp_path, kind):
    state, invoke = provider
    output = tmp_path / "keep.html"
    if kind == "ordinary":
        output.write_bytes(b"User's earlier feedback")
    elif kind == "dangling-symlink":
        output.symlink_to(tmp_path / "absent-target")
    else:
        output.mkdir()
    result = invoke(output)
    assert result.returncode == 1 and result.stdout == ""
    assert error_report(result)["error"] == "FileExistsError"
    assert state["requests"] == []
    if kind == "ordinary":
        assert output.read_bytes() == b"User's earlier feedback"
    elif kind == "dangling-symlink":
        assert output.is_symlink() and not (tmp_path / "absent-target").exists()
    else:
        assert output.is_dir() and list(output.iterdir()) == []


@pytest.mark.parametrize("part,field,value", [
    ("assignment", "id", 903),
    ("assignment", "course_id", 42),
    ("submission", "assignment_id", 904),
    ("submission", "rubric_assessment", []),
    ("submission", "score", float("nan")),
    ("assignment", "rubric_settings", {"hide_points": "false"}),
])
def test_cli_mismatched_or_unrenderable_feedback_is_not_saved(provider, tmp_path, part, field, value):
    state, invoke = provider
    state["source"][part][field] = value
    output = tmp_path / "invalid.html"
    result = invoke(output)
    assert result.returncode == 1 and result.stdout == ""
    assert error_report(result)["ok"] is False
    assert not output.exists()
    assert_reads(state)
