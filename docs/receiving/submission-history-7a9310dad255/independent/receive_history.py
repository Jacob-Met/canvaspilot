#!/usr/bin/env python3
"""Independent consumer of the submission-history API, CLI and MCP contract."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

HERE = Path(__file__).resolve().parent
FIXTURE = json.loads((HERE / "fixture.json").read_text())
FIELDS = ("id", "course_id", "name", "html_url", "due_at", "points_possible")
TOKEN = "memory-fixture-token-not-live"
REPORT = {"schema": "canvaspilot.submission-history.independent-memory.receiving.v1", "groups": []}
ASSERTIONS = 0


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1
    if not condition:
        raise AssertionError(message)


def equal(actual, expected, message):
    check(actual == expected, message + "\nactual=" + repr(actual)[:3000] + "\nexpected=" + repr(expected)[:3000])


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def digest(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def source_pins(source):
    return {str(p.relative_to(source)): digest(p)
            for p in sorted((source / "src" / "canvaspilot").glob("*.py"))}


def expected(assignment, submission):
    history = submission.get("submission_history")
    return {
        "assignment": {key: copy.deepcopy(assignment.get(key)) for key in FIELDS},
        "current_submission": {key: copy.deepcopy(value) for key, value in submission.items()
                               if key not in ("submission_history", "submission_comments")},
        "history": {"returned": isinstance(history, list), "records": copy.deepcopy(history)},
        "submission_comments": copy.deepcopy(submission.get("submission_comments")),
    }


def normalized_params(params):
    pairs = []
    source = params.items() if isinstance(params, dict) else (params or [])
    for key, value in source:
        for item in value if isinstance(value, list) else [value]:
            pairs.append((str(key), str(item)))
    return sorted(pairs)


def check_pair(requests, course="7", assignment="92", native_http=False):
    check(len(requests) == 2, "A successful report must perform exactly two requests")
    prefix = "/api/v1/courses/" + course + "/assignments/" + assignment
    equal([r["method"] for r in requests], ["GET", "GET"], "Only GETs are admitted")
    equal([r["path"] for r in requests], [prefix, prefix + "/submissions/self"], "Endpoint paths/order")
    extra = [("per_page", "50")] if native_http else []
    equal(sorted(requests[0]["params"]), sorted(extra), "Assignment query must contain no unsolicited includes")
    equal(sorted(requests[1]["params"]),
          sorted(extra + [("include[]", "submission_history"), ("include[]", "submission_comments")]),
          "Self query must request only the declared history and comments")
    if native_http:
        check(all(r["synthetic_authorization"] for r in requests), "Every HTTP call must use the isolated token")
    else:
        check(all(not r["body"] for r in requests), "No request body is permitted")


class FixtureHTTP:
    def __init__(self):
        self.requests = []
        self.reset()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                owner.respond(self, "GET")

            def do_POST(self):
                owner.respond(self, "POST")

            do_PUT = do_POST
            do_PATCH = do_POST
            do_DELETE = do_POST

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:" + str(self.server.server_address[1])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def reset(self, assignment=None, submission=None, **overrides):
        self.state = {
            "assignment": copy.deepcopy(FIXTURE["assignment"] if assignment is None else assignment),
            "submission": copy.deepcopy(FIXTURE["submission"] if submission is None else submission),
            "assignment_status": 200, "submission_status": 200,
        }
        self.state.update(overrides)

    def respond(self, handler, method):
        parsed = urlsplit(handler.path)
        self.requests.append({
            "method": handler.command, "path": parsed.path, "params": parse_qsl(parsed.query, keep_blank_values=True),
            "synthetic_authorization": handler.headers.get("Authorization") == "Bearer " + TOKEN,
        })
        valid = method == "GET" and re.fullmatch(
            r"/api/v1/courses/[0-9]+/assignments/[0-9]+(?:/submissions/self)?", parsed.path
        )
        which = "submission" if parsed.path.endswith("/submissions/self") else "assignment"
        status = self.state[which + "_status"] if valid else 404
        raw = self.state.get(which + "_raw")
        body = raw.encode() if raw is not None else json.dumps(
            self.state[which] if valid else {"error": "unexpected request"}, ensure_ascii=False
        ).encode()
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Link", "<" + self.url + "/trap>; rel=next")
        handler.end_headers()
        handler.wfile.write(body)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def child_env(source, output, server):
    env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "TMPDIR") if key in os.environ}
    env.update({
        "PYTHONPATH": str(source / "src"), "PYTHONDONTWRITEBYTECODE": "1",
        "CANVAS_BASE_URL": server.url, "CANVAS_API_TOKEN": TOKEN,
        "CANVAS_PROFILE": str(output / "unused-isolated-profile"),
        "CANVAS_SESSION_PORT": "1", "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
    })
    return env


class NativeMCP:
    def __init__(self, source, output, server, label):
        self.transcript = []
        self.output = output
        self.label = label
        self.next_id = 0
        self.lines = queue.Queue()
        self.stderr_file = (output / (label + ".stderr")).open("wb")
        self.process = subprocess.Popen(
            [sys.executable, "-B", "-m", "canvaspilot.mcp_server"], cwd=source,
            env=child_env(source, output, server), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.stderr_file,
        )

        def read_stdout():
            for line in iter(self.process.stdout.readline, b""):
                self.lines.put(line)
            self.lines.put(None)

        self.thread = threading.Thread(target=read_stdout, daemon=True)
        self.thread.start()
        initialized = self.rpc("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "hamon-memory-history-receiver", "version": "1"},
        })
        check("result" in initialized and "error" not in initialized, "MCP initialization must succeed")
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def send(self, message):
        self.transcript.append({"sent": message})
        self.process.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode())
        self.process.stdin.flush()

    def rpc(self, method, params=None):
        self.next_id += 1
        request_id = self.next_id
        self.send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
        deadline = time.monotonic() + 20
        while True:
            raw = self.lines.get(timeout=max(0.01, deadline - time.monotonic()))
            check(raw is not None, "MCP process exited before replying")
            message = json.loads(raw)
            self.transcript.append({"received": message})
            if message.get("id") == request_id:
                return message
            check(time.monotonic() < deadline, "MCP response deadline exceeded")

    def catalog(self):
        response = self.rpc("tools/list")
        check("error" not in response, "tools/list must succeed")
        return response["result"]["tools"]

    def call(self, args):
        return self.rpc("tools/call", {"name": "canvas_submission_history", "arguments": args})

    def close(self):
        self.process.stdin.close()
        try:
            status = self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            status = self.process.wait(timeout=3)
        self.thread.join(timeout=2)
        self.stderr_file.close()
        save(self.output / (self.label + ".json"), {"messages": self.transcript, "exit": status})
        equal(status, 0, "Native MCP server must finish normally after stdin closes")


def tool_report(response):
    check("error" not in response, "Tool call returned a JSON-RPC error")
    result = response["result"]
    check(not result.get("isError", False), "Successful tool call was marked isError")
    texts = [item["text"] for item in result["content"] if item.get("type") == "text"]
    equal(len(texts), 1, "The tool must return one report")
    return json.loads(texts[0])


def require_tool_error(response):
    check("error" not in response, "Valid tools/call requests must expose tool errors through isError")
    check(response["result"].get("isError") is True, "Invalid call must remain isError")
    texts = [item.get("text", "") for item in response["result"].get("content", []) if item.get("type") == "text"]
    check(bool("".join(texts).strip()), "MCP errors must explain the refusal")


def run_group(name, function):
    started = time.monotonic()
    before = ASSERTIONS
    try:
        detail = function()
        item = {"name": name, "passed": True, "detail": detail}
    except Exception as error:
        item = {"name": name, "passed": False, "error": type(error).__name__ + ": " + str(error),
                "traceback": traceback.format_exc()}
    item.update(seconds=round(time.monotonic() - started, 6), assertions=ASSERTIONS - before)
    REPORT["groups"].append(item)
    print(("PASS " if item["passed"] else "FAIL ") + name, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(source / "src"))
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    from canvaspilot.api import CanvasAPI
    from canvaspilot.client import CanvasClient

    check(Path(sys.modules["canvaspilot.api"].__file__).resolve().is_relative_to(source),
          "Import must bind to the explicitly selected source")
    before_pins = source_pins(source)
    server = FixtureHTTP()
    REPORT.update(
        started_at=datetime.now(timezone.utc).isoformat(), source=str(source),
        source_before=before_pins, executable=sys.executable, python=sys.version,
        baseline=args.baseline, loopback=server.url,
        versions={name: importlib.metadata.version(name) for name in ("httpx", "mcp", "pydantic")},
        frozen_inputs={p.name: digest(p) for p in (HERE / "contract.json", HERE / "fixture.json", Path(__file__))},
    )
    cli_index = 0

    class RecordingClient(CanvasClient):
        def __init__(self, assignment, submission, course="7", aid="92"):
            prefix = "/api/v1/courses/" + course + "/assignments/" + aid
            self.calls = []
            fixture = {"routes": {"GET " + prefix: assignment, "GET " + prefix + "/submissions/self": submission}}
            super().__init__(base_url=server.url, token=TOKEN, profile=output / "unused-api-profile", fixture=fixture)

        def request(self, method, path, **kwargs):
            self.calls.append({"method": method, "path": path, "params": normalized_params(kwargs.get("params")),
                               "body": kwargs.get("json_body") or kwargs.get("data")})
            check(method == "GET", "API attempted a non-GET request")
            return super().request(method, path, **kwargs)

        def get_paginated(self, *args, **kwargs):
            raise AssertionError("Submission history must not invent a paginated/roster read")

    def invoke(assignment, submission, course=7, aid=92, normalized_course="7", normalized_aid="92"):
        client = RecordingClient(assignment, submission, normalized_course, normalized_aid)
        with CanvasAPI(client) as api:
            report = api.submission_history(course, aid)
        check_pair(client.calls, normalized_course, normalized_aid)
        return report, client

    def cli(course="7", aid="92", extra=None):
        nonlocal cli_index
        cli_index += 1
        command = [sys.executable, "-B", "-m", "canvaspilot.cli", "submission-history",
                   "--base-url", server.url, "--profile", str(output / "unused-cli-profile"),
                   "--token", TOKEN, *(extra or []), course, aid]
        started = time.monotonic()
        result = subprocess.run(command, cwd=source, env=child_env(source, output, server),
                                capture_output=True, timeout=25)
        label = "cli-" + str(cli_index)
        (output / (label + ".stdout")).write_bytes(result.stdout)
        (output / (label + ".stderr")).write_bytes(result.stderr)
        save(output / (label + ".json"), {
            "argv_without_token": [value if value != TOKEN else "<explicit synthetic token>" for value in command],
            "exit": result.returncode, "seconds": round(time.monotonic() - started, 6),
            "stdout": digest(output / (label + ".stdout")), "stderr": digest(output / (label + ".stderr")),
        })
        return result

    def require_cli_error(result):
        equal(result.returncode, 1, "A known reader/admission error must exit one")
        equal(result.stdout, b"", "Errors must not print a partial success report")
        error = json.loads(result.stderr)
        check(isinstance(error, dict) and error.get("ok") is False, "CLI error must be readable JSON")
        check(bool(error.get("message")), "CLI error needs an explanation")
        check(b"Traceback" not in result.stderr, "Known errors should not expose a traceback")

    try:
        if args.baseline:
            def baseline():
                check(not hasattr(CanvasAPI, "submission_history"), "Baseline unexpectedly exposes the feature")
                result = cli()
                equal(result.returncode, 2, "Actual baseline parser must refuse the new command")
                check(b"invalid choice" in result.stderr, "Baseline refusal must identify the unsupported command")
                equal(result.stdout, b"", "Baseline emits no report")
                mcp = NativeMCP(source, output, server, "baseline-mcp")
                try:
                    tools = mcp.catalog()
                    check(not any(tool["name"] == "canvas_submission_history" for tool in tools),
                          "Baseline MCP unexpectedly advertises the new tool")
                finally:
                    mcp.close()
                equal(server.requests, [], "No baseline capability check may contact fixture endpoints")
                return {"api_absent": True, "cli_exit": result.returncode, "mcp_absent": True}
            run_group("B0 actual native capability absence", baseline)
        else:
            def rich_copy():
                assignment = copy.deepcopy(FIXTURE["assignment"])
                submission = copy.deepcopy(FIXTURE["submission"])
                snapshot = copy.deepcopy((assignment, submission))
                result, _ = invoke(assignment, submission)
                equal(result, expected(assignment, submission), "Rich report must preserve raw provenance")
                equal((assignment, submission), snapshot, "Reading must not mutate native fixture objects")
                save(output / "api-rich-report.json", result)
                result["current_submission"]["extension"]["flags"].append("output-only")
                result["history"]["records"][0]["extension"]["array"][0] = "output-only"
                result["history"]["records"][0]["submission_comments"][0]["comment"] = "output-only"
                result["submission_comments"][0]["extensions"]["published"] = "output-only"
                equal((assignment, submission), snapshot, "Mutating every returned nested branch must leave fixtures intact")
                return {"history_rows": 4, "same_id_duplicates_retained": True, "four_mutation_branches_isolated": True}
            run_group("G1 raw provenance and output mutation isolation", rich_copy)

            def presence():
                variants = [("absent", None), ("null", None), ("empty", [])]
                outputs = []
                for history_name, history in variants:
                    for comments_name, comments in variants:
                        submission = {"attempt": 0, "score": False, "grade": None, "extension": {}}
                        if history_name != "absent":
                            submission["submission_history"] = copy.deepcopy(history)
                        if comments_name != "absent":
                            submission["submission_comments"] = copy.deepcopy(comments)
                        result, _ = invoke({}, submission)
                        equal(result, expected({}, submission), "Absent/null/empty combination " + history_name + "/" + comments_name)
                        equal(set(result["assignment"]), set(FIELDS), "Assignment projection must include six unknown keys")
                        check("submitted_at" not in result["current_submission"], "Do not fill missing current scalar fields")
                        outputs.append(result)
                save(output / "api-presence-reports.json", outputs)
                return {"combinations": len(outputs)}
            run_group("G2 missing null empty and zero distinctions", presence)

            def identifiers():
                rejected = [True, False, 0, -1, 1.0, None, [], {}, b"7", "", "0", "0000", "-7", "+7",
                            "7.0", "7e1", "7_0", " 7", "7 ", "7\n", "\t7", "٧", "７", "²", "7/8", "7?x=1", "7%2f8", "7\x00"]
                attempts = 0
                for value in rejected:
                    for first in (True, False):
                        client = RecordingClient({}, {})
                        try:
                            with CanvasAPI(client) as api:
                                api.submission_history(value if first else 7, 92 if first else value)
                        except ValueError:
                            pass
                        else:
                            raise AssertionError("Invalid identifier was admitted: " + repr(value))
                        equal(client.calls, [], "Both identifier positions must be validated before GET")
                        attempts += 1
                huge = "1" + "0" * 4999 + "7"
                valid = [(1, 2, "1", "2"), ("0007", "0092", "7", "92"),
                         (2 ** 256, "0092", str(2 ** 256), "92"),
                         ("000" + huge, "00092", huge, "92"),
                         ("0007", "000" + huge, "7", huge)]
                for course, aid, norm_course, norm_aid in valid:
                    result, _ = invoke({}, {}, course, aid, norm_course, norm_aid)
                    equal(result, expected({}, {}), "Admitted identifiers must not affect raw report metadata")
                return {"pre_request_refusals": attempts, "valid_pairs": len(valid), "long_ascii_digits": len(huge)}
            run_group("G3 complete identifier admission before I/O", identifiers)

            def malformed():
                cases = []
                for invalid in (None, [], False, 0, "object"):
                    cases.extend([(invalid, {}, "assignment-envelope"), ({}, invalid, "submission-envelope")])
                for key in ("submission_history", "submission_comments"):
                    for invalid in ({}, "list", 0, False, [{} , None], [{}, []], [{}, False]):
                        cases.append(({}, {key: invalid, "attempt": 9}, key))
                for assignment, submission, label in cases:
                    snapshot = copy.deepcopy((assignment, submission))
                    client = RecordingClient(assignment, submission)
                    try:
                        with CanvasAPI(client) as api:
                            api.submission_history(7, 92)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("Malformed " + label + " admitted")
                    check(len(client.calls) <= 2 and all(call["method"] == "GET" for call in client.calls),
                          "Malformed data may not cause extra reads/writes")
                    equal((assignment, submission), snapshot, "Refusal must preserve original input")
                return {"whole_report_refusals": len(cases)}
            run_group("G4 malformed envelopes and late rows refuse whole report", malformed)

            def cli_rich():
                server.reset()
                start = len(server.requests)
                result = cli("0007", "00092")
                equal(result.returncode, 0, "Actual CLI rich read")
                equal(result.stderr, b"", "Successful CLI stderr")
                equal(json.loads(result.stdout), expected(FIXTURE["assignment"], FIXTURE["submission"]), "CLI raw JSON report")
                check_pair(server.requests[start:], native_http=True)
                return {"requests": 2, "redirect_or_attachment_fetches": 0}
            run_group("G5 actual CLI preserves rich metadata through HTTP", cli_rich)

            def cli_changed():
                server.reset()
                start = len(server.requests)
                first = cli()
                equal(first.returncode, 0, "First CLI read")
                changed = {"attempt": 99, "score": None, "grade": False, "body": "new state without returned history"}
                server.reset(assignment={"id": 92, "name": "Changed title"}, submission=changed)
                second = cli()
                equal(second.returncode, 0, "Changed CLI read")
                equal(json.loads(second.stdout), expected({"id": 92, "name": "Changed title"}, changed), "Second read must reflect changed source")
                check(first.stdout != second.stdout, "Changed history input must change the actual report")
                check_pair(server.requests[start:start + 2], native_http=True)
                check_pair(server.requests[start + 2:], native_http=True)
                return {"independent_processes": 2, "fresh_unknown_history": True}
            run_group("G6 actual CLI reads changed input without stale history", cli_changed)

            def cli_refusals():
                server.reset()
                for bad in ("７", "000", "-7"):
                    start = len(server.requests)
                    require_cli_error(cli(bad, "92", ["--"] if bad.startswith("-") else None))
                    equal(server.requests[start:], [], "Invalid CLI IDs may not issue HTTP")
                for state in (
                    {"submission": {"submission_history": [{}, False]}},
                    {"submission_status": 403},
                    {"submission_raw": "{invalid json"},
                ):
                    server.reset(**state)
                    start = len(server.requests)
                    require_cli_error(cli())
                    check_pair(server.requests[start:], native_http=True)
                return {"native_refusals": 6, "partial_reports": 0}
            run_group("G7 actual CLI refusal boundaries", cli_refusals)

            def mcp_fresh():
                server.reset()
                mcp = NativeMCP(source, output, server, "mcp-fresh")
                try:
                    tools = [tool for tool in mcp.catalog() if tool["name"] == "canvas_submission_history"]
                    equal(len(tools), 1, "Exactly one history tool is advertised")
                    schema = tools[0]["inputSchema"]
                    equal(schema["properties"]["course_id"]["type"], "string", "MCP course ID schema")
                    equal(schema["properties"]["assignment_id"]["type"], "string", "MCP assignment ID schema")
                    equal(set(schema["required"]), {"course_id", "assignment_id"}, "MCP required arguments")
                    start = len(server.requests)
                    first = tool_report(mcp.call({"course_id": "0007", "assignment_id": "00092"}))
                    equal(first, expected(FIXTURE["assignment"], FIXTURE["submission"]), "MCP first raw report")
                    check_pair(server.requests[start:], native_http=True)
                    changed = {"attempt": 0, "submission_history": [], "submission_comments": [], "custom": {"same_process": True}}
                    server.reset(assignment={"id": 92, "points_possible": False}, submission=changed)
                    start = len(server.requests)
                    second = tool_report(mcp.call({"course_id": "7", "assignment_id": "92"}))
                    equal(second, expected({"id": 92, "points_possible": False}, changed), "Cached API object must still read fresh submission data")
                    check(first != second, "Changed backend must change the same-process MCP result")
                    check_pair(server.requests[start:], native_http=True)
                finally:
                    mcp.close()
                return {"same_process_successful_calls": 2}
            run_group("G8 actual MCP schema and repeated fresh reads", mcp_fresh)

            def mcp_errors():
                server.reset()
                mcp = NativeMCP(source, output, server, "mcp-errors")
                try:
                    for bad in (True, 7, "٧", "0", "7/8"):
                        start = len(server.requests)
                        require_tool_error(mcp.call({"course_id": bad, "assignment_id": "92"}))
                        equal(server.requests[start:], [], "Invalid MCP IDs must not issue HTTP")
                    server.reset(submission={"submission_comments": [{}, False]})
                    start = len(server.requests)
                    require_tool_error(mcp.call({"course_id": "7", "assignment_id": "92"}))
                    check_pair(server.requests[start:], native_http=True)
                    server.reset(submission={"submission_history": None, "score": 0})
                    start = len(server.requests)
                    result = tool_report(mcp.call({"course_id": "7", "assignment_id": "92"}))
                    equal(result, expected(FIXTURE["assignment"], {"submission_history": None, "score": 0}),
                          "A valid subsequent MCP call must recover without stale partial data")
                    check_pair(server.requests[start:], native_http=True)
                finally:
                    mcp.close()
                return {"invalid_calls": 6, "same_process_recovery": True}
            run_group("G9 actual MCP errors stay errors and do not poison the next call", mcp_errors)
    finally:
        server.close()
        save(output / "http-requests.json", server.requests)
        REPORT["source_after"] = source_pins(source)
        REPORT["source_unchanged"] = REPORT["source_after"] == before_pins
        REPORT["passed"] = sum(group["passed"] for group in REPORT["groups"])
        REPORT["failed"] = sum(not group["passed"] for group in REPORT["groups"])
        REPORT["assertions"] = ASSERTIONS
        REPORT["finished_at"] = datetime.now(timezone.utc).isoformat()
        REPORT["owned_profiles_created"] = any((output / name).exists()
                                               for name in ("unused-isolated-profile", "unused-api-profile", "unused-cli-profile"))
        REPORT["artifacts"] = {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()}
        save(output / "receipt.json", REPORT)
    print(json.dumps({"passed": REPORT["passed"], "failed": REPORT["failed"], "assertions": ASSERTIONS,
                      "source_unchanged": REPORT["source_unchanged"], "receipt": str(output / "receipt.json")}))
    return 0 if REPORT["failed"] == 0 and REPORT["source_unchanged"] and not REPORT["owned_profiles_created"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
