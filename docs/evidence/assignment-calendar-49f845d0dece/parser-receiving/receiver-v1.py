"""Receive the real calendar CLI with an independent parser and local fixture only."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from icalendar import Calendar

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True, type=Path)
parser.add_argument("--baseline", required=True, type=Path)
parser.add_argument("--out", required=True, type=Path)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=False)
spec = importlib.util.spec_from_file_location("calendar_fixture", args.source / "tests/test_calendar_export.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
server = module.DeadlineServer()
name = "細胞と宇宙😀" * 16 + ", review; notes\\source\r\nEND:VEVENT"
server.rows["42"][0]["name"] = name
server.rows["42"][0]["html_url"] = "https://canvas.fixture.invalid/courses/42/assignments/1"
server.rows["77"][0]["html_url"] = "https://canvas.fixture.invalid/courses/77/assignments/3"
records = []
checks = []


def check(label, condition):
    checks.append({"name": label, "pass": bool(condition)})
    if not condition:
        raise AssertionError(label)


def run(label, source, path, expectation):
    env = {k: v for k, v in os.environ.items()
           if not k.upper().endswith("_PROXY") and not k.startswith("CANVAS")}
    env["PYTHONPATH"] = str(source / "src")
    cmd = [sys.executable, "-m", "canvaspilot.cli", "export-calendar", "42", "77",
           "--base-url", server.url, "--token", "synthetic-receiving-only",
           "--profile", str(args.out / "unused-profile"), "--out", str(path)]
    result = subprocess.run(cmd, env=env, cwd=source, capture_output=True, text=True,
                            check=False, timeout=15)
    (args.out / (label + ".stdout.txt")).write_text(result.stdout)
    (args.out / (label + ".stderr.txt")).write_text(result.stderr)
    record = {"label": label, "source": str(source), "command": cmd,
              "exit_code": result.returncode, "expected_exit": expectation}
    records.append(record)
    check(label + " exit", result.returncode == expectation)
    return result


try:
    absent = args.out / "baseline.ics"
    result = run("baseline", args.baseline, absent, 2)
    check("baseline is actual missing command", "invalid choice: 'export-calendar'" in result.stderr)
    check("baseline no file or HTTP", not absent.exists() and not server.requests)

    initial = args.out / "candidate.ics"
    result = run("candidate", args.source, initial, 0)
    report = json.loads(result.stdout)
    content = initial.read_bytes()
    calendar = Calendar.from_ical(content)
    events = calendar.walk("VEVENT")
    check("independent parser sees exactly two events", len(events) == 2 and not calendar.errors)
    check("independent parser restores escaped Unicode title", str(events[0]["SUMMARY"]) == "[Course 42] " + name)
    check("clock rollback keeps absolute due instants", [
        e.decoded("DTSTART") for e in events
    ] == [datetime(2026, 11, 1, 8, 45, tzinfo=timezone.utc),
          datetime(2026, 11, 1, 9, 15, tzinfo=timezone.utc)])
    check("no invented duration, invitation or alarm", all(
        not any(key in e for key in ("DTEND", "DURATION", "ORGANIZER", "ATTENDEE"))
        and not e.walk("VALARM") for e in events
    ))
    check("new-file receipt matches artifact and omissions", report["events_exported"] == 2
          and report["sha256"] == hashlib.sha256(content).hexdigest()
          and report["assignments_omitted"] == [
              {"course_id": "42", "assignment_id": "2", "reason": "no_due_date"}
          ])
    check("physical lines are valid folded UTF-8", all(
        len(line) <= 75 and line.decode("utf-8") is not None for line in content.split(b"\r\n")
    ))
    identity = {str(e["URL"]): str(e["UID"]) for e in events}

    server.rows["42"][0]["due_at"] = "2026-11-03T09:30:00+02:00"
    server.rows["42"][0]["name"] = "Revised deadline"
    revised = args.out / "revised.ics"
    run("revised", args.source, revised, 0)
    changed = Calendar.from_ical(revised.read_bytes()).walk("VEVENT")
    check("re-export preserves source assignment identities", identity == {
        str(e["URL"]): str(e["UID"]) for e in changed
    })
    target = next(e for e in changed if str(e["URL"]).endswith("/1"))
    check("changed source deadline reaches calendar", target.decoded("DTSTART") ==
          datetime(2026, 11, 3, 7, 30, tzinfo=timezone.utc))

    request_count = len(server.requests)
    run("existing-file", args.source, initial, 1)
    check("existing artifact and requests untouched", initial.read_bytes() == content
          and len(server.requests) == request_count)

    server.fail_course = "77"
    refused = args.out / "failed-course.ics"
    run("failed-course", args.source, refused, 1)
    check("later failure leaves no partial calendar", not refused.exists())
    server.fail_course = None
    server.rows["77"][0]["due_at"] = "2026-11-01"
    malformed = args.out / "malformed.ics"
    run("malformed", args.source, malformed, 1)
    check("unknown timezone is never guessed", not malformed.exists())
    check("all received transport requests are GET", all(r["method"] == "GET" for r in server.requests))
    check("no profile or temporary output remains", not (args.out / "unused-profile").exists()
          and not list(args.out.glob(".*.tmp")))
finally:
    server.close()
    receipt = {
        "base": "72357053a1629c349f700030013559fa6d8130f2",
        "parser": "icalendar " + __import__("importlib.metadata", fromlist=["version"]).version("icalendar"),
        "records": records, "checks": checks, "requests": server.requests,
        "passed": sum(c["pass"] for c in checks), "failed": sum(not c["pass"] for c in checks),
        "source_sha256": {p: hashlib.sha256((args.source / p).read_bytes()).hexdigest()
                          for p in ("src/canvaspilot/calendar_export.py", "src/canvaspilot/cli.py",
                                    "tests/test_calendar_export.py")},
        "limits": "Author receiving with independent parser; no school account or calendar-app import.",
    }
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
