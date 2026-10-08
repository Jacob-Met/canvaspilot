"""Independent receiving of CanvasPilot feedback through its real API, CLI and MCP.

All responses come from an isolated loopback HTTP fixture. No Canvas account,
browser, broker, submission write, or grading operation is used.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
INPUT_HASH = "7ce2ff38268b7caf0b5eb80620546b6bb24d41c38c95ed767bfe0ff7f4fe6652"
TOKEN = "synthetic-feedback-fixture-token"
ASSIGNMENT = "/api/v1/courses/41/assignments/73"
SUBMISSION = ASSIGNMENT + "/submissions/self"
SUBMISSION_FIELDS = [
    "id", "assignment_id", "user_id", "submission_type", "attempt", "workflow_state",
    "submitted_at", "graded_at", "posted_at", "grader_id", "score", "grade",
    "grade_matches_current_submission", "excused", "late", "missing", "redo_request",
]
ASSIGNMENT_FIELDS = ["id", "course_id", "name", "html_url", "due_at", "points_possible"]


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def verify_semantics(result, case_index, case):
    require(isinstance(result, dict), "feedback result is an object")
    for field in ASSIGNMENT_FIELDS:
        require(result["assignment"][field] == case["assignment"].get(field), ("assignment", field))
    for field in SUBMISSION_FIELDS:
        require(result["submission"][field] == case["submission"].get(field), ("submission", field))
    require(set(result) == {"assignment", "submission", "rubric", "submission_comments"}, "bounded feedback sections")
    require(result["submission_comments"] == case["submission"].get("submission_comments"), "complete comments preserve authors, times, media and missing values")
    rubric = result["rubric"]
    require(rubric["use_rubric_for_grading"] == case["assignment"].get("use_rubric_for_grading"), "advisory versus grading rubric remains explicit")
    require(rubric["settings"] == case["assignment"].get("rubric_settings"), "rubric settings preserved")
    if case_index == 0:
        require(rubric["assessment_returned"] is True, "assessment received")
        rows = rubric["criteria"]
        require([row["criterion"] for row in rows] == case["assignment"]["rubric"], "rubric definitions, order, ratings and non-scoring metadata preserved")
        require([row["assessment"] for row in rows] == [
            {"points": 7, "comments": "The second claim needs support."},
            {"points": 0, "rating_id": "none", "comments": "Add the source details."},
            None,
        ], "assessment joins use exact criterion IDs, including zero and unassessed values")
        require(rubric["unmatched_assessments"] == {"removed": case["submission"]["rubric_assessment"]["removed"]}, "orphaned feedback retained")
        require(result["submission"]["grade_matches_current_submission"] is False, "prior-attempt grade remains explicitly stale")
        require(result["submission"]["grader_id"] == -73, "autograder identifier retained without author-role inference")
        require("total" not in rubric and "score" not in rubric and "grade" not in rubric, "no grade inferred by summing advisory/non-scoring rubric values")
    elif case_index == 1:
        require(rubric["assessment_returned"] is False, "missing assessment not represented as graded")
        require(rubric["criteria"] == [{"criterion": case["assignment"]["rubric"][0], "assessment": None}], "unassessed criterion is not zero")
        require(result["submission"]["grade_matches_current_submission"] is None, "grade applicability remains unknown")
        require(result["submission_comments"] is None, "missing comments remain unknown")
    elif case_index == 2:
        require(rubric["criteria"] is None, "no rubric definitions invented")
        require(rubric["assessment_returned"] is False, "null assessment remains unavailable")
        require(result["submission"]["grade_matches_current_submission"] is True, "current grade retained")
    elif case_index == 3:
        require(rubric["criteria"] is None, "unavailable definitions remain null")
        require(rubric["assessment_returned"] is True, "returned assessment recorded separately from unavailable definitions")
        require(rubric["unmatched_assessments"] == {"unknown": {"points": None, "comments": "Discuss this criterion with the reviewer."}}, "unmatched comments and null points survive")
        require(result["submission_comments"] == [], "explicit empty comments remain an empty list")


def verify_requests(requests):
    require(len(requests) == 2, ("exactly two read requests", requests))
    require([item["path"] for item in requests] == [ASSIGNMENT, SUBMISSION], "assignment then own submission")
    for item in requests:
        require(item["method"] == "GET", "no mutation method")
        require(item["synthetic_authorization_valid"], "only local synthetic token used")
        require(item["query"].get("per_page") == ["50"], "existing client per_page behavior retained")
    require(set(requests[0]["query"]) <= {"per_page"}, "bounded assignment request")
    require(set(requests[1]["query"]) == {"per_page", "include[]"}, "bounded submission request")
    require(sorted(requests[1]["query"]["include[]"]) == ["rubric_assessment", "submission_comments"], "both feedback fields requested")


async def receive_mcp(env, source, cases, state, report, output):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "canvaspilot.cli", "mcp"], env=env, cwd=source)
    with (output / "mcp-stderr.log").open("w") as errors:
        async with stdio_client(params, errlog=errors) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=20) as session:
                initialized = await session.initialize()
                tools = await session.list_tools()
                target = [tool for tool in tools.tools if tool.name == "canvas_submission_feedback"]
                require(len(target) == 1, "feedback tool advertised exactly once")
                advertised = target[0].model_dump(mode="json", by_alias=True)
                schema = advertised["inputSchema"]
                require(set(schema.get("required", [])) == {"course_id", "assignment_id"}, "MCP requires both identifiers")
                require(set(schema["properties"]) == {"course_id", "assignment_id"}, "no user-targeting or write parameters")
                report["mcp_initialization"] = initialized.model_dump(mode="json", by_alias=True)
                report["mcp_feedback_tool"] = advertised
                for index, case in enumerate(cases):
                    state["case"] = case
                    state["requests"] = []
                    result = await session.call_tool("canvas_submission_feedback", {"course_id": "41", "assignment_id": "73"})
                    wire = result.model_dump(mode="json", by_alias=True)
                    require(not wire.get("isError", False), ("MCP returned tool error", wire))
                    text = [block["text"] for block in wire["content"] if block.get("type") == "text"]
                    require(len(text) == 1, "one native JSON result")
                    payload = json.loads(text[0])
                    verify_semantics(payload, index, case)
                    verify_requests(state["requests"])
                    (output / f"mcp-case-{index + 1}.json").write_text(json.dumps(payload, indent=2) + "\n")
                    report["interfaces"].append({"interface": "mcp-stdio", "case": case["name"], "passed": True, "requests": list(state["requests"])})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = (ROOT / "cases.json").read_bytes()
    require(hashlib.sha256(data).hexdigest() == INPUT_HASH, "independent inputs remain frozen")
    cases = json.loads(data)["cases"]
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.source.resolve()
    source_pins = {str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((source / "src/canvaspilot").glob("*.py"))}
    report = {"independent_input_sha256": INPUT_HASH, "source_pins": source_pins, "runtime_started_at": datetime.now(timezone.utc).isoformat(), "interfaces": [], "passed": False}
    state = {"case": cases[0], "requests": []}

    class FixtureHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle_request(self):
            url = urlsplit(self.path)
            state["requests"].append({"method": self.command, "path": url.path, "query": parse_qs(url.query), "synthetic_authorization_valid": self.headers.get("Authorization") == f"Bearer {TOKEN}"})
            if self.command != "GET" or url.path not in {ASSIGNMENT, SUBMISSION}:
                self.send_response(400)
                self.end_headers()
                return
            payload = state["case"]["assignment" if url.path == ASSIGNMENT else "submission"]
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = handle_request

    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    for proxy_key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(proxy_key, None)
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT") if key in os.environ}
    env.update({"PYTHONPATH": f"{source / 'src'}:{args.dependencies.resolve()}", "PYTHONDONTWRITEBYTECODE": "1", "CANVAS_BASE_URL": base, "CANVAS_API_TOKEN": TOKEN, "CANVAS_PROFILE": str(args.output / "unused-profile"), "NO_PROXY": "127.0.0.1,localhost"})
    try:
        sys.path[:0] = [str(source / "src"), str(args.dependencies.resolve())]
        from canvaspilot.api import CanvasAPI
        from canvaspilot.client import CanvasClient
        for index, case in enumerate(cases):
            state["case"] = case
            state["requests"] = []
            with CanvasAPI(CanvasClient(base_url=base, token=TOKEN, profile=args.output / "unused-profile")) as api:
                result = api.submission_feedback(41, 73)
            verify_semantics(result, index, case)
            verify_requests(state["requests"])
            (args.output / f"api-case-{index + 1}.json").write_text(json.dumps(result, indent=2) + "\n")
            report["interfaces"].append({"interface": "python-api", "case": case["name"], "passed": True, "requests": list(state["requests"])})
            state["requests"] = []
            process = subprocess.run([sys.executable, "-m", "canvaspilot.cli", "feedback", "41", "73", "--base-url", base, "--token", TOKEN], cwd=source, env=env, capture_output=True, text=True, timeout=20)
            (args.output / f"cli-case-{index + 1}.stdout.json").write_text(process.stdout)
            (args.output / f"cli-case-{index + 1}.stderr.log").write_text(process.stderr)
            require(process.returncode == 0, ("CLI exit", process.returncode, process.stderr))
            cli_result = json.loads(process.stdout)
            verify_semantics(cli_result, index, case)
            require(cli_result == result, "API and CLI expose the same feedback")
            verify_requests(state["requests"])
            report["interfaces"].append({"interface": "cli-process", "case": case["name"], "passed": True, "requests": list(state["requests"])})
        asyncio.run(receive_mcp(env, source, cases, state, report, args.output))
        for path, expected in source_pins.items():
            require(hashlib.sha256((source / path).read_bytes()).hexdigest() == expected, ("candidate changed during receiving", path))
        require(not (args.output / "unused-profile").exists(), "no browser profile created")
        report["passed"] = True
    except BaseException as error:
        report["error"] = repr(error)
        raise
    finally:
        server.shutdown()
        server.server_close()
        report["runtime_finished_at"] = datetime.now(timezone.utc).isoformat()
        (args.output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"passed": report["passed"], "interfaces_checked": len(report["interfaces"]), "http_requests": sum(len(row["requests"]) for row in report["interfaces"]), "error": report.get("error")}))


if __name__ == "__main__":
    main()
