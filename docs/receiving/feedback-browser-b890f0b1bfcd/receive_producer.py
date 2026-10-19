"""Generate real candidate CLI feedback exports from authored loopback responses."""
from __future__ import annotations
import copy
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from urllib.parse import urlsplit, parse_qs

root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=False)

def save(name, value):
    (out / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def pins():
    names = subprocess.check_output(["git", "ls-files", "src/canvaspilot", "pyproject.toml"], cwd=root, text=True).splitlines()
    return {name: {"sha256": hashlib.sha256((root/name).read_bytes()).hexdigest(), "bytes": (root/name).stat().st_size} for name in names}

before = pins()
save("source-before.json", before)
source_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
source_tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True).strip()
long_criterion = "CRITERION_" + "Q" * 240 + "_END"
long_unmatched = "UNMATCHED_" + "R" * 180 + "_END"
literal = 'Receiving only: <img src="https://receiving.invalid/image" onerror="window.injected=true"> <script>window.injected=true</script> & "quotes" — Δ café 東京.'
paragraph = "Printed review body: preserve this exact comment and its original author. " * 40 + "PRINTED_COMMENT_END"
assignment = {
    "id": 902, "course_id": 61, "name": "Independent feedback: café & <Research>",
    "html_url": "https://receiving.invalid/courses/61/assignments/902?view=feedback&literal=%3Cvalue%3E",
    "due_at": "2026-10-04T16:00:00-07:00", "points_possible": 100,
    "use_rubric_for_grading": False,
    "rubric_settings": {"title": "Original analytic rubric", "points_possible": 15, "hide_points": False, "hide_score_total": False, "hide_outcome_results": True},
    "rubric": [
        {"id": "criterion-A", "description": "Reasoning & exact evidence", "points": 10, "long_description": literal, "criterion_use_range": False, "ignore_for_scoring": False,
         "ratings": [{"id": "rating-1", "description": "Develop the evidence", "points": 0, "long_description": "Zero is a supplied value."}]},
        {"id": "criterion-B", "description": "Connection to sources", "points": 5, "ratings": []}
    ]
}
submission = {
    "id": 341, "assignment_id": 902, "user_id": 17, "submission_type": "online_text_entry", "attempt": 3,
    "workflow_state": "submitted", "submitted_at": "2026-10-05T01:00:00Z", "graded_at": "2026-10-04T23:30:00Z", "posted_at": None,
    "grader_id": -7, "score": 0, "grade": "", "grade_matches_current_submission": False,
    "excused": False, "late": True, "missing": False, "redo_request": True,
    "rubric_assessment": {
        "criterion-A": {"points": 0, "rating_id": "rating-1", "comments": "Keep the exact zero and clarify the evidence."},
        "orphan": {"points": 2, "rating_id": None, "comments": "Unmatched feedback remains separate."}
    },
    "submission_comments": [
        {"id": 91, "author_name": "Peer <reviewer>", "author_id": 27, "author": {"display_name": "Different recorded display", "id": 28}, "created_at": "2026-10-04T23:35:00Z", "edited_at": None,
         "comment": literal + "\n" + paragraph, "attachments": [{"id": 121, "display_name": "notes<one>.txt", "content-type": "text/plain", "url": "https://receiving.invalid/never-fetch"}]},
        {"id": 92, "author_name": "Audio peer", "author_id": 29, "comment": "", "media_comment": {"media_type": "audio", "media_id": "audio-91", "display_name": "Audio note"}, "attachments": []}
    ]
}
active = {}
requests = []
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlsplit(self.path)
        requests.append({"case": active["case"], "method": "GET", "path": self.path})
        if parsed.path == "/api/v1/courses/61/assignments/902":
            value = active["assignment"]
        elif parsed.path == "/api/v1/courses/61/assignments/902/submissions/self":
            assert set(parse_qs(parsed.query).get("include[]", [])) == {"submission_comments", "rubric_assessment"}
            value = active["submission"]
        else:
            self.send_error(404); return
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *_):
        pass
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = f"http://127.0.0.1:{server.server_port}"
env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ}
env.update({"PYTHONPATH": str(root/"src"), "PYTHONDONTWRITEBYTECODE": "1", "NO_PROXY": "127.0.0.1,localhost"})
commands = []
expectations = {}
try:
    for case in ("ordinary", "long-headings", "points-hidden", "total-hidden", "both-hidden"):
        a, s = copy.deepcopy(assignment), copy.deepcopy(submission)
        if case == "long-headings":
            a["rubric"][0]["description"] = long_criterion
            s["rubric_assessment"][long_unmatched] = s["rubric_assessment"].pop("orphan")
        a["rubric_settings"]["hide_points"] = case in ("points-hidden", "both-hidden")
        a["rubric_settings"]["hide_score_total"] = case in ("total-hidden", "both-hidden")
        active.update({"case": case, "assignment": a, "submission": s})
        save(case + "-input.json", {"assignment": a, "submission": s})
        input_before = json.dumps(active, sort_keys=True, ensure_ascii=False)
        for command in ("feedback", "export-feedback"):
            argv = [sys.executable, "-m", "canvaspilot.cli", command, "61", "902", "--base-url", base, "--token", "independent-loopback-fixture"]
            if command == "export-feedback":
                argv += ["--out", str(out/(case + ".html"))]
            result = subprocess.run(argv, cwd=root, env=env, text=True, capture_output=True, timeout=30)
            commands.append({"case": case, "command": command, "argv": argv, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
            save("commands.json", commands)
            assert result.returncode == 0, commands[-1]
            payload = json.loads(result.stdout)
            if command == "feedback":
                save(case + "-feedback.json", payload)
                assert payload["assignment"] == {key: a.get(key) for key in ("id", "course_id", "name", "html_url", "due_at", "points_possible")}
                assert payload["submission_comments"] == s["submission_comments"]
                assert payload["rubric"]["criteria"][0]["assessment"] == s["rubric_assessment"]["criterion-A"]
                assert payload["rubric"]["criteria"][1]["assessment"] is None
                assert payload["submission"]["score"] == 0 and payload["submission"]["grade"] == ""
            else:
                content = (out/(case+".html")).read_bytes()
                assert payload["ok"] is True and payload["sha256"] == hashlib.sha256(content).hexdigest()
        assert json.dumps(active, sort_keys=True, ensure_ascii=False) == input_before
        expectations[case] = {"title": a["name"], "criterion": a["rubric"][0]["description"], "unmatched": next(key for key in s["rubric_assessment"] if key != "criterion-A"), "literal": literal, "full_comment": s["submission_comments"][0]["comment"], "hide_points": a["rubric_settings"]["hide_points"], "hide_total": a["rubric_settings"]["hide_score_total"], "html_sha256": hashlib.sha256((out/(case+".html")).read_bytes()).hexdigest()}
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=3)
    save("requests.json", requests)
after = pins()
save("source-after.json", after)
assert before == after
assert len(commands) == 10 and len(requests) == 20
assert all(row["method"] == "GET" for row in requests)
save("expectations.json", expectations)
save("producer-result.json", {"status": "pass", "source_head": source_head, "source_tree": source_tree, "python": sys.version, "httpx": __import__("httpx").__version__, "commands": len(commands), "loopback_gets": len(requests), "source_pins": len(before), "server_closed": True, "receiver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
print(json.dumps({"status": "pass", "commands": len(commands), "loopback_gets": len(requests), "source_pins": len(before), "source_head": source_head}))
