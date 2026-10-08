"""Native calendar consumer receiving through the production broker Handler and queue.

Only the browser response worker is authored. No browser, Canvas account or
external Canvas request is used. Run the same file against every source pin.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from icalendar import Calendar

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True, type=Path)
parser.add_argument("--out", required=True, type=Path)
args = parser.parse_args()
args.source = args.source.resolve()
args.out.mkdir(parents=True, exist_ok=False)
sys.path.insert(0, str(args.source / "src"))
broker = importlib.import_module("canvaspilot.session_broker")
assert Path(broker.__file__).resolve() == args.source / "src/canvaspilot/session_broker.py"
paths = ["src/canvaspilot/" + name for name in
         ("client.py", "api.py", "cli.py", "calendar_export.py", "session_broker.py")]
hashes = {path: hashlib.sha256((args.source / path).read_bytes()).hexdigest() for path in paths}
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.source, text=True).strip()
checks, runs, calls, errors = [], [], [], []
stop = threading.Event()
scenario = {"name": "", "base": "https://school-a.fixture.invalid"}
OPAQUE = "?cursor=%2f%2F,a;b&empty=&literal=+"
NAME = "Later deadline 科学😀, notes; line\nnext"

def check(name, condition, detail=None):
    checks.append({"name": name, "pass": bool(condition), "detail": detail})

def row(course, ident, due, name=None):
    return {"id": ident, "name": name or f"Assignment {course}/{ident}",
            "due_at": due,
            "html_url": scenario["base"] + f"/courses/{course}/assignments/{ident}"}

def page(rows, link="", status=200):
    return {"ok": True, "response":
            {"status": status, "json": rows, "text": None, "headers": {"link": link}}}

def respond(job):
    assert job["op"] == "fetch" and job["method"] == "GET", job
    parsed = urlsplit(job["path"])
    pieces = parsed.path.split("/")
    assert pieces[:4] == ["", "api", "v1", "courses"] and pieces[5:] == ["assignments"], job
    course = pieces[4]
    assert course in ("42", "77"), job
    later = "cursor=" in job["path"]
    nxt = scenario["base"] + parsed.path + OPAQUE
    if later:
        assert job["path"] == nxt, job
    due = "2026-11-01T01:45:00-07:00"
    mode = scenario["name"]
    if mode.startswith("identity"):
        return page([row(course, 1, due)])
    if course == "42":
        if not later:
            return page([row(course, 1, due)], f'<{nxt}>; rel="NEXT"')
        ident = 1 if mode == "duplicate" else 2
        later_due = "2026-11-01T01:15:00-07:00"
        title = NAME
        if mode == "changed":
            later_due, title = "2026-11-03T09:30:00+05:45", "Changed second page 科学"
        return page([row(course, ident, later_due, title), row(course, 3, None)])
    if mode in ("later-http", "later-metadata"):
        if not later:
            return page([row(course, 1, "2026-11-01T09:00:00Z")], f'<{nxt}>; rel="next"')
        if mode == "later-http":
            return page({"error": "authored unavailable second page"}, status=503)
        return page([row(course, 2, "2026-11-01T10:00:00Z")], f"<{nxt}>")
    return page([row(course, 1, "2026-11-01T08:30:00Z")])

def worker():
    while not stop.is_set():
        try:
            job, reply = broker.STATE.jobs.get(timeout=0.05)
        except queue.Empty:
            continue
        calls.append(copy.deepcopy(job))
        try:
            reply.put(respond(job))
        except Exception as error:
            errors.append(repr(error))
            reply.put({"ok": False, "error": "authored fixture refused unexpected request"})

broker.STATE.read_only = True
broker.STATE.ready.set()
broker.STATE.error = None
server = ThreadingHTTPServer(("127.0.0.1", 0), broker.Handler)
server_thread = threading.Thread(target=server.serve_forever,
                                 kwargs={"poll_interval": 0.02}, daemon=True)
worker_thread = threading.Thread(target=worker, daemon=True)
server_thread.start()
worker_thread.start()

def run(label, courses=("42", "77"), explicit_base=True, source_base=None):
    scenario["name"] = label
    if source_base:
        scenario["base"] = source_base
    broker.STATE.base_url = scenario["base"]
    output = args.out / (label + ".ics")
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("CANVAS") and not key.upper().endswith("_PROXY")}
    env.update(PYTHONPATH=str(args.source / "src"),
               CANVAS_SESSION_PORT=str(server.server_address[1]))
    command = [sys.executable, "-m", "canvaspilot.cli", "export-calendar", *courses,
               "--token", "", "--profile", str(args.out / "unused-profile"),
               "--out", str(output)]
    if explicit_base:
        command += ["--base-url", scenario["base"]]
    before = len(calls)
    result = subprocess.run(command, cwd=args.source, env=env, capture_output=True,
                            text=True, timeout=20, check=False)
    (args.out / (label + ".stdout.txt")).write_text(result.stdout)
    (args.out / (label + ".stderr.txt")).write_text(result.stderr)
    report = None
    error_report = None
    try:
        report = json.loads(result.stdout)
    except ValueError:
        pass
    try:
        error_report = json.loads(result.stderr.strip().splitlines()[-1])
    except (ValueError, IndexError):
        pass
    events = []
    parser_errors = []
    if output.exists():
        parsed = Calendar.from_ical(output.read_bytes())
        parser_errors = parsed.errors
        for event in parsed.walk("VEVENT"):
            events.append({"uid": str(event["UID"]), "summary": str(event["SUMMARY"]),
                           "due": event.decoded("DTSTART").isoformat(),
                           "url": str(event["URL"])})
    record = {"label": label, "command": command, "exit": result.returncode,
              "requests": copy.deepcopy(calls[before:]), "report": report,
              "error_report": error_report, "events": events,
              "artifact_exists": output.exists(), "parser_errors": parser_errors,
              "traceback": "Traceback (most recent call last)" in result.stderr}
    runs.append(record)
    return record

try:
    full = run("complete")
    check("complete CLI succeeds", full["exit"] == 0)
    check("three dated assignments reach independent parser", len(full["events"]) == 3
          and not full["parser_errors"], full["events"])
    expected = [
        datetime(2026, 11, 1, 8, 15, tzinfo=timezone.utc).isoformat(),
        datetime(2026, 11, 1, 8, 30, tzinfo=timezone.utc).isoformat(),
        datetime(2026, 11, 1, 8, 45, tzinfo=timezone.utc).isoformat()]
    check("cross-page events globally sort by UTC", [e["due"] for e in full["events"]] == expected)
    report = full["report"] or {}
    check("receipt accounts for second-page omission and every returned row",
          report.get("course_summaries") == [
              {"course_id": "42", "assignments_returned": 3, "events_exported": 2},
              {"course_id": "77", "assignments_returned": 1, "events_exported": 1}]
          and report.get("assignments_omitted") == [
              {"course_id": "42", "assignment_id": "3", "reason": "no_due_date"}])
    check("first filters stay on first request and opaque cursor arrives unchanged",
          len(full["requests"]) == 3
          and parse_qs(urlsplit(full["requests"][0]["path"]).query).get("bucket") == ["upcoming"]
          and parse_qs(urlsplit(full["requests"][0]["path"]).query).get("include[]") == ["submission"]
          and full["requests"][1]["path"] == scenario["base"] + "/api/v1/courses/42/assignments" + OPAQUE)
    events_by_url = {e["url"]: e for e in full["events"]}
    expected_later = scenario["base"] + "/courses/42/assignments/2"
    check("later Unicode title survives independent parsing",
          events_by_url.get(expected_later, {}).get("summary") == "[Course 42] " + NAME)
    check("equal numeric assignment IDs across courses remain distinct",
          len({e["uid"] for e in full["events"]}) == 3)
    previous_bytes = (args.out / "complete.ics").read_bytes() if full["artifact_exists"] else None

    changed = run("changed")
    changed_by_url = {e["url"]: e for e in changed["events"]}
    check("changing page two preserves every assignment identity", changed["exit"] == 0
          and len(changed_by_url) == 3
          and {k: e["uid"] for k, e in events_by_url.items()} ==
              {k: e["uid"] for k, e in changed_by_url.items()})
    check("changed second-page content reaches next fresh export",
          changed_by_url.get(expected_later, {}).get("summary") == "[Course 42] Changed second page 科学"
          and changed_by_url.get(expected_later, {}).get("due") ==
              datetime(2026, 11, 3, 3, 45, tzinfo=timezone.utc).isoformat())
    check("unchanged page-one/course-two content remains stable",
          all(changed_by_url.get(k) == v for k, v in events_by_url.items() if k != expected_later))

    for label in ("later-http", "later-metadata", "duplicate"):
        refused = run(label)
        check(label + " refuses entire calendar", refused["exit"] != 0
              and not refused["artifact_exists"] and refused["report"] is None)
        check(label + " emits structured error without traceback",
              isinstance(refused["error_report"], dict)
              and refused["error_report"].get("ok") is False and not refused["traceback"])
        check(label + " preserves previous export", previous_bytes is not None
              and (args.out / "complete.ics").read_bytes() == previous_bytes)

    school_a = run("identity-default-a", courses=("42",), explicit_base=False,
                   source_base="https://school-a.fixture.invalid")
    school_b = run("identity-default-b", courses=("42",), explicit_base=False,
                   source_base="https://school-b.fixture.invalid")
    explicit = run("identity-explicit-a", courses=("42",), explicit_base=True,
                   source_base="https://school-a.fixture.invalid")
    check("default-client receipt identifies actual school A",
          (school_a["report"] or {}).get("source") == "https://school-a.fixture.invalid")
    check("default-client receipt identifies actual school B",
          (school_b["report"] or {}).get("source") == "https://school-b.fixture.invalid")
    uid_a = school_a["events"][0]["uid"] if school_a["events"] else None
    uid_b = school_b["events"][0]["uid"] if school_b["events"] else None
    uid_explicit = explicit["events"][0]["uid"] if explicit["events"] else None
    check("different school providers cannot collapse to one calendar UID",
          uid_a is not None and uid_b is not None and uid_a != uid_b)
    check("default and explicit same-school exports preserve identity",
          uid_a is not None and uid_a == uid_explicit)
    check("all browser-worker operations are GET", all(c["method"] == "GET" for c in calls))
    check("no profile or temporary calendar files remain",
          not (args.out / "unused-profile").exists() and not list(args.out.glob(".*.tmp")))
    check("authored fixture handled only planned requests", not errors, errors)
finally:
    server.shutdown()
    server.server_close()
    stop.set()
    server_thread.join(timeout=3)
    worker_thread.join(timeout=3)
    after = {path: hashlib.sha256((args.source / path).read_bytes()).hexdigest() for path in paths}
    check("production bytes unchanged", after == hashes)
    receipt = {"source": str(args.source), "head": head,
               "receiver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "production_sha256_before": hashes, "production_sha256_after": after,
               "broker_import": str(Path(broker.__file__).resolve()), "python": sys.version,
               "runs": runs, "checks": checks, "passed": sum(c["pass"] for c in checks),
               "failed": sum(not c["pass"] for c in checks)}
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"head": head, "passed": receipt["passed"], "failed": receipt["failed"],
                  "failed_checks": [c["name"] for c in checks if not c["pass"]],
                  "receipt": str(args.out / "receipt.json")}), flush=True)
sys.exit(1 if receipt["failed"] else 0)
