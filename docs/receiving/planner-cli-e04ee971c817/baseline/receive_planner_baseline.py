"""Original CLI absence plus the unchanged native planner fixture path.

This standard-library receiver deliberately skips package __init__/bundle/MCP
bootstrap and provides an import-only HTTPX tripwire. It executes the complete,
exact CLI file and the unchanged native API/client fixture implementation.
It does not qualify HTTPX, installed entry points, token/session transport or MCP.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

POSITIVE = r'''
import json, os, sys, types
from pathlib import Path
source = Path(sys.argv[1])
payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
package = types.ModuleType("canvaspilot")
package.__path__ = [str(source / "src/canvaspilot")]
sys.modules["canvaspilot"] = package
blocked = []
httpx = types.ModuleType("httpx")
def forbid_httpx(name):
    blocked.append(name)
    raise AssertionError("HTTPX behavior is outside this native fixture receiver: " + name)
httpx.__getattr__ = forbid_httpx
sys.modules["httpx"] = httpx
def guard(event, args):
    if event.startswith("socket.") or event in ("subprocess.Popen", "os.system"):
        raise AssertionError("Forbidden external effect: " + event)
    if event == "open":
        mode = args[1]
        flags = args[2]
        if (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        ):
            raise AssertionError("Forbidden file write")
sys.addaudithook(guard)
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
calls = []
closed = []
class RecordedClient(CanvasClient):
    def request(self, method, path, **kwargs):
        calls.append({"method": method, "path": path, **kwargs})
        if method != "GET":
            raise AssertionError("Fixture reads must remain GET")
        return super().request(method, path, **kwargs)
    def close(self):
        closed.append(True)
        return super().close()
client = RecordedClient(base_url="https://canvas.synthetic.example",
    token="", profile=source / "unused-profile",
    fixture={"routes": {"GET /api/v1/planner/items": payload["rows"]}})
api = CanvasAPI(client)
try:
    selected = api.planner_items(start_date=payload["start"], end_date=payload["end"])
    defaults = api.planner_items()
finally:
    api.close()
print(json.dumps({"selected": selected, "defaults": defaults, "calls": calls,
    "mode": client.mode, "closed": len(closed), "httpx_behavior": blocked,
    "bootstrap": "namespace package; original __init__/bundle/MCP not exercised"},
    ensure_ascii=True, allow_nan=False))
'''
FIXTURE = {
    "start": "2026-10-08T09:10:11Z",
    "end": "2026-10-12",
    "rows": [
        {"context_type": "Course", "course_id": 42, "plannable_type": "assignment",
         "plannable_id": "700", "plannable_date": "2026-10-08T12:00:00Z",
         "plannable": {"id": 700, "title": "Synthetic zero-point check", "points_possible": 0},
         "submissions": {"submitted": False, "missing": True, "score": None},
         "planner_override": {"marked_complete": True, "dismissed": False},
         "html_url": "/courses/42/assignments/700"},
        {"context_type": "Course", "course_id": 77, "plannable_type": "discussion_topic",
         "plannable_id": 801, "plannable": {"title": "Literal <b>読書</b>\n & conversation"},
         "submissions": False, "planner_override": None, "future_field": {"kept": [0, False, None]}},
        {"plannable_type": "planner_note", "plannable_id": 902,
         "plannable": {"id": 902, "title": "Bring a book", "course_id": None,
                       "todo_date": "2026-10-12T06:00:00Z", "details": "Fictional reminder"},
         "planner_override": None, "submissions": False},
    ],
}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--evidence", required=True, type=Path)
    a = p.parse_args()
    source = a.source.resolve()
    evidence = a.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    paths = [
        "src/canvaspilot/cli.py", "src/canvaspilot/api.py", "src/canvaspilot/client.py",
        "src/canvaspilot/assignment_submission.py", "src/canvaspilot/feedback.py",
    ]
    before = {path: sha((source / path).read_bytes()) for path in paths}
    fixture = evidence / "synthetic-planner.json"
    fixture.write_text(json.dumps(FIXTURE, ensure_ascii=True, indent=2) + "\n",
                       encoding="utf-8", newline="")
    env = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONHASHSEED": "0", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}
    cli = source / "src/canvaspilot/cli.py"
    commands = {
        "original-help": [sys.executable, "-B", "-S", str(cli), "--help"],
        "original-planner": [sys.executable, "-B", "-S", str(cli), "planner",
                             "--start-date", FIXTURE["start"], "--end-date", FIXTURE["end"]],
        "native-fixture": [sys.executable, "-B", "-S", "-c", POSITIVE, str(source), str(fixture)],
    }
    results = {}
    streams = {}
    for name, command in commands.items():
        r = subprocess.run(command, env=env, cwd=source, capture_output=True, timeout=20)
        streams[name] = r
        for suffix, data in (("stdout", r.stdout), ("stderr", r.stderr)):
            (evidence / f"{name}.{suffix}").write_bytes(data)
        results[name] = {"returncode": r.returncode, "stdout_bytes": len(r.stdout),
                         "stdout_sha256": sha(r.stdout), "stderr_bytes": len(r.stderr),
                         "stderr_sha256": sha(r.stderr)}
    control = streams["native-fixture"]
    parsed = json.loads(control.stdout) if control.returncode == 0 else {}
    original = streams["original-planner"]
    help_result = streams["original-help"]
    expected_calls = [
        {"method": "GET", "path": "/api/v1/planner/items",
         "params": {"start_date": FIXTURE["start"], "end_date": FIXTURE["end"]}},
        {"method": "GET", "path": "/api/v1/planner/items", "params": {}},
    ]
    checks = [
        ("original-help-succeeds", help_result.returncode == 0),
        ("existing-agenda-entry-present", b"agenda" in help_result.stdout),
        ("planner-command-absent", b"planner" not in help_result.stdout),
        ("actual-original-planner-refused", original.returncode == 2 and not original.stdout
         and b"invalid choice" in original.stderr and b"'planner'" in original.stderr),
        ("native-api-fixture-succeeds", control.returncode == 0 and not control.stderr),
        ("all-original-values-retained", parsed.get("selected") == FIXTURE["rows"]),
        ("native-default-selection-retained", parsed.get("defaults") == FIXTURE["rows"]),
        ("exact-native-get-and-date-forwarding", parsed.get("calls") == expected_calls),
        ("fixture-mode-and-close-preserved", parsed.get("mode") == "fixture" and parsed.get("closed") == 1),
        ("no-httpx-behavior-needed", parsed.get("httpx_behavior") == []),
        ("source-unchanged", before == {path: sha((source / path).read_bytes()) for path in paths}),
    ]
    receipt = {
        "format": "canvaspilot-planner-original-receiver-v1",
        "source": str(source), "python": sys.version, "source_sha256": before,
        "cases": results,
        "conditions": [{"name": name, "pass": bool(ok)} for name, ok in checks],
        "passed": sum(bool(ok) for _, ok in checks),
        "failed": sum(not bool(ok) for _, ok in checks),
        "limits": [
            "Original CLI file executes native main; package/installed bootstrap is not exercised.",
            "Positive control uses the exact native API and client fixture path with an import-only HTTPX tripwire.",
            "No HTTPX behavior, HTTP/session pagination, MCP, school account, browser or provider is exercised.",
            "Synthetic planner records are authored fixtures; native returned date/field behavior is retained.",
        ],
    }
    data = (json.dumps(receipt, indent=2) + "\n").encode()
    (evidence / "baseline-results.json").write_bytes(data)
    print(json.dumps({"passed": receipt["passed"], "failed": receipt["failed"],
                      "cases": results, "receipt_sha256": sha(data)}))
    return bool(receipt["failed"])

if __name__ == "__main__":
    raise SystemExit(main())
