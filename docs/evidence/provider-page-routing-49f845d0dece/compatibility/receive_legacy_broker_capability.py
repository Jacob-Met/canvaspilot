"""Receive a new calendar CLI against the exact legacy broker health protocol.
Production CLI/client/calendar and legacy Handler/_call/queue are used.
Only observation wrappers and a fail-fast responder for forbidden fetches are
authored. No browser, profile, credential or external request is used.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
import queue
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True, type=Path)
parser.add_argument("--source-pins", required=True, type=Path)
parser.add_argument("--legacy-source", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--expect", required=True, choices=("baseline", "candidate"))
args = parser.parse_args()
source = args.source.resolve()
legacy = args.legacy_source.resolve()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=False)
paths = {
    "src/canvaspilot/client.py", "src/canvaspilot/api.py",
    "src/canvaspilot/cli.py", "src/canvaspilot/calendar_export.py",
    "src/canvaspilot/session_broker.py",
}
pins = json.loads(args.source_pins.read_bytes())
if not isinstance(pins, dict) or set(pins) != paths:
    raise RuntimeError("Expected exactly five frozen production source pins")
if any(not isinstance(v, str) or len(v) != 64
       or any(c not in "0123456789abcdef" for c in v) for v in pins.values()):
    raise RuntimeError("Expected lowercase SHA-256 pins")
before = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in pins}
if before != pins:
    raise RuntimeError("Frozen current source mismatch")
legacy_path = legacy / "src/canvaspilot/session_broker.py"
legacy_sha = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
if legacy_sha != "2a106130c344aefebb23b078cd93b5d3ca3afd7f5325ae5fac2fb8a7251780cc":
    raise RuntimeError("Expected exact original legacy broker")
profile = output / "unused-profile"
for key in list(os.environ):
    if key.startswith("CANVAS") or key.upper().endswith("_PROXY"):
        del os.environ[key]
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path.insert(0, str(source / "src"))
spec = importlib.util.spec_from_file_location("legacy_broker_receiving", legacy_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load the pinned legacy broker")
broker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = broker
spec.loader.exec_module(broker)

health = []
requests = []
jobs = []
stop = threading.Event()
sentinel = "Independent receiver observed forbidden legacy broker fetch"

class ObservedHandler(broker.Handler):
    def _json(self, code, obj):
        if self.path.startswith("/health"):
            health.append(json.loads(json.dumps(obj)))
        return super()._json(code, obj)

    def do_POST(self):
        requests.append({"method": "POST", "path": self.path})
        return super().do_POST()

def worker():
    while not stop.is_set():
        try:
            job, reply = broker.STATE.jobs.get(timeout=0.03)
        except queue.Empty:
            continue
        jobs.append(job)
        reply.put({"ok": False, "error": sentinel})

broker.STATE.jobs = queue.Queue()
broker.STATE.ready = threading.Event()
broker.STATE.ready.set()
broker.STATE.base_url = "https://school-a.instructure.com"
broker.STATE.page_url = "https://school-b.instructure.com/courses"
broker.STATE.read_only = True
broker.STATE.error = None
server = ThreadingHTTPServer(("127.0.0.1", 0), ObservedHandler)
serving = threading.Thread(target=server.serve_forever,
                           kwargs={"poll_interval": 0.02}, daemon=True)
working = threading.Thread(target=worker, daemon=True)
serving.start()
working.start()
try:
    env = dict(os.environ, PYTHONPATH=str(source / "src"),
               CANVAS_SESSION_PORT=str(server.server_address[1]))
    calendar = output / "legacy-broker.ics"
    command = [sys.executable, "-m", "canvaspilot.cli", "export-calendar", "42",
               "--token", "", "--profile", str(profile), "--out", str(calendar)]
    completed = subprocess.run(command, cwd=source, env=env, capture_output=True,
                               text=True, timeout=15, check=False)
    (output / "cli.stdout.txt").write_text(completed.stdout)
    (output / "cli.stderr.txt").write_text(completed.stderr)
    if not health or any(h.get("base_url") != broker.STATE.base_url
                         or h.get("ready") is not True
                         or "provider_origin_checks" in h for h in health):
        raise RuntimeError("Legacy Handler health protocol was not observed intact")
    if completed.returncode != 1 or completed.stdout or calendar.exists():
        raise RuntimeError("Expected explicit CLI refusal and no artifact")
    if "Traceback" in completed.stderr:
        raise RuntimeError("CLI error must remain structured")
    error = json.loads(completed.stderr.strip().splitlines()[-1])
    if error.get("ok") is not False:
        raise RuntimeError("Expected explicit error report")
    if args.expect == "baseline":
        if requests != [{"method": "POST", "path": "/fetch"}] or len(jobs) != 1:
            raise RuntimeError("Baseline must reach the real legacy broker fetch path")
        if error.get("error") != "CanvasAuthError" or error.get("message") != sentinel:
            raise RuntimeError("Baseline must reach the deliberate forbidden-fetch responder")
        status = "legacy_broker_fetch_reached"
    else:
        message = str(error.get("message", "")).lower()
        if requests or jobs:
            raise RuntimeError("Updated CLI must refuse before legacy fetch or queue dispatch")
        if error.get("error") != "ValueError" or "restart" not in message or "before export" not in message:
            raise RuntimeError("Updated CLI must give the explicit broker restart instruction")
        status = "legacy_broker_restart_refusal_passed"
    if profile.exists() or list(output.glob("*.ics*")):
        raise RuntimeError("Refusal must leave no profile, calendar or temporary calendar")
    after = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in pins}
    if before != after or hashlib.sha256(legacy_path.read_bytes()).hexdigest() != legacy_sha:
        raise RuntimeError("Frozen source changed during receiving")
    receipt = {
        "status": status, "expected_contract": args.expect,
        "source": str(source), "source_pins": str(args.source_pins.resolve()),
        "source_pins_sha256": hashlib.sha256(args.source_pins.read_bytes()).hexdigest(),
        "source_native_head": subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip(),
        "source_sha256_before": before, "source_sha256_after": after,
        "legacy_source": str(legacy), "legacy_broker_sha256": legacy_sha,
        "legacy_native_head": subprocess.check_output(["git", "-C", str(legacy), "rev-parse", "HEAD"], text=True).strip(),
        "receiver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": sys.version,
        "boundary": "Actual CLI/client/calendar plus exact legacy Handler/_call/queue; observation-only Handler wrapper and fail-fast responder for forbidden fetches",
        "actual_browser_or_live_account_used": False, "external_requests": 0,
        "legacy_health_responses": health, "post_requests": requests, "queued_jobs": jobs,
        "command": command, "cli_exit": completed.returncode, "error_report": error,
        "artifact_exists": calendar.exists(), "profile_exists": profile.exists(),
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": status, "receipt": str(output / "receipt.json"),
                      "health_responses": len(health), "post_requests": requests,
                      "queued_jobs": len(jobs), "error": error}))
finally:
    stop.set()
    server.shutdown()
    server.server_close()
    working.join(timeout=2)
    serving.join(timeout=2)
