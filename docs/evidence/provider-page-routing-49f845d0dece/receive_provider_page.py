"""Receive PR45 configured-provider identity against real broker page selection.
Actual CLI, Handler, _call, queue, _canvas_page and _run_job remain production.
Only the terminal Page object is authored; no Playwright/browser/login or
external HTTP request is used. This is not a real-browser qualification.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
import queue
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urljoin, urlsplit

from icalendar import Calendar

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
source = args.source.resolve()
args.output.mkdir(parents=True, exist_ok=False)
expected = {
 "src/canvaspilot/client.py": "6368329745216f473204995c101c912d9070fdd310def150bdbee927f9872de4",
 "src/canvaspilot/api.py": "546fd973330ffb3c95c81ba670b5ae2add751a23362c83a370254ea702eee1a0",
 "src/canvaspilot/cli.py": "173df7056f7d86084aa2dc00ba129bf8c36aaf109cdbf9497e24ec436d90d47b",
 "src/canvaspilot/calendar_export.py": "d0bfe685bc14375cf202e38a55ee64381a1fd75cd38edb2774091d9610f99d90",
 "src/canvaspilot/session_broker.py": "2a106130c344aefebb23b078cd93b5d3ca3afd7f5325ae5fac2fb8a7251780cc",
}
before = {p: hashlib.sha256((source / p).read_bytes()).hexdigest() for p in expected}
if before != expected:
 raise RuntimeError("Frozen source mismatch; refusing receiving")
sys.path.insert(0, str(source / "src"))
broker = importlib.import_module("canvaspilot.session_broker")
if Path(broker.__file__).resolve() != source / "src/canvaspilot/session_broker.py":
 raise RuntimeError("Unexpected broker import")
SCHOOL_A = "https://school-a.instructure.com"
SCHOOL_B = "https://school-b.instructure.com"
transports = []
errors = []
state = {}
stop = threading.Event()

class AuthoredPage:
 def __init__(self, origin):
  self.url = origin + "/courses"
  self.navigations = []
 def goto(self, url, **kwargs):
  self.navigations.append(url)
  self.url = url
 def title(self):
  return "Synthetic provider routing receiver"
 def evaluate(self, expression, parameters):
  if "const r = await fetch(path, opts);" not in expression:
   raise RuntimeError("Unexpected production page expression")
  if parameters["method"] != "GET":
   raise RuntimeError("Unexpected non-GET operation")
  resolved = urljoin(self.url, parameters["path"])
  parts = urlsplit(resolved)
  origin = parts.scheme + "://" + parts.netloc
  if origin not in (SCHOOL_A, SCHOOL_B) or parts.path != "/api/v1/courses/42/assignments":
   raise RuntimeError("Unexpected terminal path")
  transports.append({
   "page_url": self.url, "relative_path": parameters["path"],
   "resolved_url": resolved, "configured_base_url": broker.STATE.base_url,
   "navigations": list(self.navigations),
   "production_expression_sha256": hashlib.sha256(expression.encode()).hexdigest(),
  })
  return {"status": 200, "json": [{
   "id": 1, "name": "Synthetic deadline from " + parts.netloc,
   "due_at": "2026-11-01T08:45:00Z",
   "html_url": origin + "/courses/42/assignments/1",
  }], "text": None}

def worker():
 while not stop.is_set():
  try:
   job, reply = broker.STATE.jobs.get(timeout=0.03)
  except queue.Empty:
   continue
  try:
   result = broker._run_job(state["context"], job)
   reply.put({"ok": True, **result})
  except Exception as exc:
   errors.append(repr(exc))
   reply.put({"ok": False, "error": str(exc)})

broker.STATE.jobs = queue.Queue()
broker.STATE.ready = threading.Event()
broker.STATE.ready.set()
broker.STATE.read_only = True
broker.STATE.error = None
server = ThreadingHTTPServer(("127.0.0.1", 0), broker.Handler)
serving = threading.Thread(target=server.serve_forever,
                           kwargs={"poll_interval": 0.02}, daemon=True)
working = threading.Thread(target=worker, daemon=True)
serving.start()
working.start()
runs = []
try:
 for label, configured, page_origin in [
   ("configured-a-page-a", SCHOOL_A, SCHOOL_A),
   ("configured-a-page-b", SCHOOL_A, SCHOOL_B),
   ("configured-b-page-b", SCHOOL_B, SCHOOL_B),
 ]:
  page = AuthoredPage(page_origin)
  state["context"] = SimpleNamespace(pages=[page])
  broker.STATE.base_url = configured
  broker.STATE.page_url = page.url
  output = args.output / (label + ".ics")
  profile = args.output / "unused-profile"
  env = {key: value for key, value in os.environ.items()
         if not key.startswith("CANVAS") and not key.upper().endswith("_PROXY")}
  env.update(PYTHONPATH=str(source / "src"), PYTHONDONTWRITEBYTECODE="1",
             CANVAS_SESSION_PORT=str(server.server_address[1]))
  command = [sys.executable, "-m", "canvaspilot.cli", "export-calendar", "42",
             "--token", "", "--profile", str(profile), "--out", str(output)]
  first = len(transports)
  result = subprocess.run(command, cwd=source, env=env, capture_output=True,
                          text=True, timeout=15, check=False)
  (args.output / (label + ".stdout.txt")).write_text(result.stdout)
  (args.output / (label + ".stderr.txt")).write_text(result.stderr)
  if result.returncode != 0 or not output.is_file():
   raise RuntimeError("Counterexample precondition failed: " + label + ": " + result.stderr)
  report = json.loads(result.stdout)
  parsed = Calendar.from_ical(output.read_bytes())
  events = parsed.walk("VEVENT")
  if len(events) != 1 or parsed.errors:
   raise RuntimeError("Expected one independently parsed event")
  runs.append({
   "label": label, "configured_provider": configured, "selected_page_origin": page_origin,
   "exit": result.returncode, "reported_source": report["source"],
   "uid": str(events[0]["UID"]), "assignment_url": str(events[0]["URL"]),
   "transport": transports[first:], "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
   "command": command, "artifact_exists": output.exists(),
  })
 if errors:
  raise RuntimeError("Unexpected terminal errors: " + repr(errors))
 if len(transports) != 3 or any(t["navigations"] for t in transports):
  raise RuntimeError("Expected exactly three relative fetches without navigation")
 a, mismatch, b = runs
 if not (a["reported_source"] == SCHOOL_A and b["reported_source"] == SCHOOL_B):
  raise RuntimeError("Matching-provider controls did not qualify")
 witness = {
  "mismatched_provider_export_succeeded": mismatch["exit"] == 0,
  "reported_a_while_selected_page_b": mismatch["reported_source"] == SCHOOL_A
     and mismatch["selected_page_origin"] == SCHOOL_B,
  "artifact_url_identifies_b": mismatch["assignment_url"].startswith(SCHOOL_B + "/"),
  "different_actual_providers_share_uid": a["uid"] == mismatch["uid"],
  "same_actual_provider_changes_uid_with_configuration": mismatch["uid"] != b["uid"],
  "all_fetches_used_production_relative_routing": len(transports) == 3
     and all(t["relative_path"].startswith("/api/") and not t["navigations"] for t in transports),
  "no_profile_created": not (args.output / "unused-profile").exists(),
 }
 if not all(witness.values()):
  raise RuntimeError("Expected stable-provider counterexample not reproduced")
 after = {p: hashlib.sha256((source / p).read_bytes()).hexdigest() for p in expected}
 if before != after:
  raise RuntimeError("Production bytes changed during receiving")
 receipt = {
  "status": "counterexample_reproduced", "published_head": "1748e52ed1533c102e04525f96c3d76d4141d30c",
  "source": str(source), "native_head": subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=source, text=True).strip(),
  "python": sys.version, "receiver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  "boundary": "Actual CLI, Handler, _call, queue, _canvas_page, _run_job; authored terminal Page object only",
  "actual_browser_or_live_account_used": False, "external_requests": 0,
  "source_sha256_before": before, "source_sha256_after": after,
  "witness": witness, "runs": runs,
 }
 (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
 print(json.dumps({"status": receipt["status"], "receipt": str(args.output / "receipt.json"),
                   "witness": witness, "identities": [{k:r[k] for k in
                     ("label","reported_source","uid","assignment_url")} for r in runs]}))
finally:
 server.shutdown()
 server.server_close()
 stop.set()
 serving.join(timeout=3)
 working.join(timeout=3)
