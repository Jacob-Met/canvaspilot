"""Independent native CLI receiving; synthetic loopback Canvas responses only."""
from __future__ import annotations
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from datetime import datetime, UTC
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from icalendar import Calendar

ROOT = Path("/Users/me/workspace/estate/production-evidence-49f845d0dece/calendar-independent")
REPO = ROOT.parent / "canvaspilot-calendar"
FILES = ("src/canvaspilot/calendar_export.py", "src/canvaspilot/cli.py", "tests/test_calendar_export.py")
EXPECTED = {
    FILES[0]: "5e2196dba90b1a787c8b51e84c6d5695f49edff0e47c9f9eb30a8313f442e4aa",
    FILES[1]: "28d278a60ee0b5b036948071c0965f42ea3f36cc1892940406577491e2c3ef38",
    FILES[2]: "d239fcb95c05892bc72b8b77d1ae20328436646987a36bd0fa428db05af31635",
}
RUN = ROOT / "run-initial"
RUN.mkdir(exist_ok=False)
checks, processes, requests = [], [], []

def check(label, condition, details=None):
    checks.append({"check": label, "pass": bool(condition), "details": details})
    print(("PASS " if condition else "FAIL ") + label, flush=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fingerprint():
    return {name: sha(REPO / name) for name in FILES}

TITLE = "研究🪐é" * 35 + ", draft; path\\item\r\nBEGIN:VEVENT\rnext\nfinal"
NORM_TITLE = TITLE.replace("\r\n", "\n").replace("\r", "\n")
ROWS = {
    "42": [
        {"id": 901, "name": TITLE, "due_at": "2026-11-01T01:50:00-07:00",
         "html_url": "https://canvas.fixture.invalid/courses/42/assignments/901?a=1,2;b=3"},
        {"id": 902, "name": "Date unknown", "due_at": None},
    ],
    "77": [
        {"id": 901, "name": "Same numeric ID, other course", "due_at": "2026-11-01T01:10:00-08:00"},
        {"id": 903, "name": "Quarter-hour offset", "due_at": "2026-12-31T23:40:00+05:45"},
    ],
}

class Endpoint:
    def __init__(self, label):
        self.label, self.rows, self.fail_course, self.phase = label, copy.deepcopy(ROWS), None, "initial"
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass
            def do_GET(self):
                parsed = urlsplit(self.path)
                expected = "/api/v1/courses/"
                course = parsed.path.split("/")[-2] if parsed.path.startswith(expected) else None
                status = 503 if course == owner.fail_course else 200 if course in owner.rows else 404
                requests.append({"server": owner.label, "phase": owner.phase, "method": "GET",
                                 "path": parsed.path, "query": parse_qs(parsed.query), "status": status})
                data = owner.rows.get(course, {"fixture_error": "unexpected route"})
                body = json.dumps(data).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def do_POST(self):
                requests.append({"server": owner.label, "phase": owner.phase, "method": "POST", "path": self.path})
                self.send_error(405)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://localhost:{self.server.server_port}"
    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

def cli(endpoint, name, *, base=None, out=None, bucket=None):
    endpoint.phase = name
    target = out if out is not None else RUN / (name + ".ics")
    env = {k: v for k, v in os.environ.items()
           if not k.upper().endswith("_PROXY") and not k.upper().startswith("CANVAS")}
    env["PYTHONPATH"] = str(REPO / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    args = [sys.executable, "-B", "-m", "canvaspilot.cli", "export-calendar", "042", "77", "42",
            "--base-url", base or endpoint.url,
            "--profile", str(RUN / "unused-profile"), "--token", "synthetic-loopback-fixture",
            "--out", str(target)]
    if bucket:
        args += ["--bucket", bucket]
    before = len(requests)
    p = subprocess.run(args, cwd=RUN, env=env, capture_output=True, text=True, timeout=20)
    (RUN / (name + ".stdout.txt")).write_text(p.stdout)
    (RUN / (name + ".stderr.txt")).write_text(p.stderr)
    error = None
    if p.stderr:
        try:
            error = json.loads(p.stderr.splitlines()[-1])
        except ValueError:
            pass
    receipt = json.loads(p.stdout) if p.returncode == 0 and p.stdout else None
    processes.append({"name": name, "argv": args, "exit": p.returncode,
                      "output": str(target), "request_count": len(requests) - before,
                      "receipt": receipt, "error": error})
    return p, target, receipt, error, requests[before:]

def parsed(path):
    data = path.read_bytes()
    cal = Calendar.from_ical(data)
    return data, cal, cal.walk("VEVENT")

def by_course(events):
    return {str(e["SUMMARY"]).split("] ", 1)[0][8:]: e for e in events
            if str(e["SUMMARY"]).startswith("[Course ") and "Quarter-hour" not in str(e["SUMMARY"])}

def no_publish(name, result, expected_error):
    p, target, _, error, _ = result
    check(name + ": whole output refused", p.returncode == 1 and not p.stdout and not os.path.lexists(target)
          and error is not None and error.get("error") == expected_error, {"exit": p.returncode, "error": error})

first, other = Endpoint("source-a"), Endpoint("source-b")
try:
    check("Source hashes match frozen implementation", fingerprint() == EXPECTED, fingerprint())
    base = "HTTP://LOCALHOST:" + str(first.server.server_port) + "/"
    p, original, report, _, seen = cli(first, "unicode-and-offsets", base=base)
    check("Native CLI produces complete new calendar", p.returncode == 0 and original.exists(), {"exit": p.returncode})
    data, cal, events = parsed(original)
    check("Independent parser accepts exactly three deadline events", len(events) == 3 and not cal.errors,
          {"parser": importlib.metadata.version("icalendar"), "event_count": len(events), "errors": cal.errors})
    check("Unicode, delimiters and literal content lines round-trip", str(events[0]["SUMMARY"]) == "[Course 42] " + NORM_TITLE)
    check("UTF-8 physical lines are intact and at most 75 octets",
          all(len(line) <= 75 and line.decode("utf-8") is not None for line in data.split(b"\r\n"))
          and b"\n" not in data.replace(b"\r\n", b"") and data.endswith(b"\r\n"))
    starts = [e.decoded("DTSTART").isoformat() for e in events]
    check("Aware offsets convert exactly and sort by UTC instant", starts == [
        "2026-11-01T08:50:00+00:00", "2026-11-01T09:10:00+00:00", "2026-12-31T17:55:00+00:00"], starts)
    check("Unknown date is explicitly omitted", report["assignments_omitted"] == [
        {"course_id": "42", "assignment_id": "902", "reason": "no_due_date"}])
    check("Duplicate selected course is read once and upcoming bucket retained",
          len(seen) == 2 and [r["path"] for r in seen] == [
              "/api/v1/courses/42/assignments", "/api/v1/courses/77/assignments"]
          and all(r["query"].get("bucket") == ["upcoming"] for r in seen))
    check("Same assignment ID in different courses remains distinct",
          str(events[0]["UID"]) != str(events[1]["UID"]) and len({str(e["UID"]) for e in events}) == 3)
    check("No duration, invitation, busy block or alarm is invented",
          "METHOD" not in cal and not cal.walk("VALARM")
          and all(str(e["TRANSP"]) == "TRANSPARENT" and
                  not any(key in e for key in ("DTEND", "DURATION", "ORGANIZER", "ATTENDEE")) for e in events))
    check("URL punctuation and reported bytes remain exact", str(events[0]["URL"]) == ROWS["42"][0]["html_url"]
          and report["sha256"] == hashlib.sha256(data).hexdigest())
    old_ids = {str(e["UID"]) for e in events}
    old_course = by_course(events)
    first.rows["42"][0]["due_at"] = "2027-01-02T09:35:00+09:00"
    first.rows["42"][0]["name"] = "Renamed after deadline change"
    p, revised, _, _, _ = cli(first, "revised-normalized-source")
    _, _, revised_events = parsed(revised)
    check("Name and deadline edit plus normalized source retain UIDs",
          p.returncode == 0 and {str(e["UID"]) for e in revised_events} == old_ids)
    revised_course = by_course(revised_events)
    check("Changed deadline reaches parser without changing identity",
          revised_course["42"].decoded("DTSTART") == datetime(2027, 1, 2, 0, 35, tzinfo=UTC)
          and revised_course["42"].decoded("DTSTART") != old_course["42"].decoded("DTSTART"))
    p, separate, _, _, _ = cli(other, "different-source")
    _, _, separate_events = parsed(separate)
    check("Same course and assignment IDs from a different source do not collide",
          p.returncode == 0 and old_ids.isdisjoint({str(e["UID"]) for e in separate_events}))

    first.rows = copy.deepcopy(ROWS)
    first.rows["77"][0]["due_at"] = "2026-11-01T01:10:00"
    no_publish("Naive date in later course", cli(first, "naive-later-course"), "ValueError")

    first.rows = copy.deepcopy(ROWS)
    first.rows["77"][0]["due_at"] = "2026-11-01T01:10:00+00:60"
    no_publish("Malformed timezone minute in later course", cli(first, "invalid-offset-later-course"), "ValueError")

    first.rows = copy.deepcopy(ROWS)
    first.fail_course = "77"
    failure = cli(first, "late-course-failure")
    no_publish("Later course read failure", failure, "HTTPStatusError")
    check("Late failure occurs after one good course", [r["status"] for r in failure[4]] == [200, 503])
    first.fail_course = None

    existing = cli(first, "existing-file", out=original)
    check("Existing calendar bytes protected without further reads",
          existing[0].returncode == 1 and existing[3]["error"] == "FileExistsError"
          and original.read_bytes() == data and len(existing[4]) == 0)
    dangling = RUN / "dangling.ics"
    missing = RUN / "no-target"
    dangling.symlink_to(missing)
    protected = cli(first, "existing-dangling-symlink", out=dangling)
    check("Dangling destination symlink preserved without creating its target",
          protected[0].returncode == 1 and protected[3]["error"] == "FileExistsError"
          and dangling.is_symlink() and not missing.exists() and len(protected[4]) == 0)
    first.rows = {"42": [{"id": 901, "name": "Undated", "due_at": None}], "77": []}
    no_publish("All dates unknown", cli(first, "all-undated", bucket="all"), "ValueError")
    check("All bucket omits transport bucket parameter",
          all("bucket" not in r["query"] for r in requests if r["phase"] == "all-undated"))
    check("Only selected loopback GET reads occurred", all(r["method"] == "GET"
          and r["path"] in ("/api/v1/courses/42/assignments", "/api/v1/courses/77/assignments") for r in requests))
    check("No profile or temporary publication residue", not (RUN / "unused-profile").exists()
          and not list(RUN.glob(".*.tmp")))
finally:
    first.close()
    other.close()
    after = fingerprint()
    check("All three handed-off source hashes remain unchanged", after == EXPECTED, after)
    receipt = {"source_head": "7ff3518e9025c6d54899b01da21b378aebd01f3d",
               "source_before": EXPECTED, "source_after": after,
               "receiver_sha256": sha(Path(__file__)), "python": sys.version,
               "parser": {"name": "icalendar", "version": importlib.metadata.version("icalendar")},
               "boundary": "Independent native subprocess CLI with authored loopback HTTP fixture; no real account or calendar import.",
               "checks": checks, "processes": processes, "requests": requests,
               "passed": sum(c["pass"] for c in checks), "failed": sum(not c["pass"] for c in checks)}
    (RUN / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"passed": receipt["passed"], "failed": receipt["failed"], "receipt": str(RUN / "receipt.json")}))
sys.exit(bool(receipt["failed"]))
