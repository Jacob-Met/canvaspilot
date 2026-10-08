"""Current-source discussion capability witness; only synthetic fixture requests."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PINS = json.loads((ROOT / "source-pins.json").read_text())
SOURCE = ROOT / "baseline" / "src"
sys.path.insert(0, str(SOURCE))
def snapshot():
    rows = {}
    for rec in PINS["files"]:
        raw = (ROOT / "baseline" / rec["path"]).read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != rec["sha256"]:
            raise RuntimeError("source mismatch: " + rec["path"])
        rows[rec["path"]] = actual
    return rows
before = snapshot()
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.bundle import tool_inventory

topic = {"id": 71, "title": "Synthetic creek restoration discussion",
         "message": "<p>Compare the two fictional restoration plans.</p>",
         "read_state": "unread", "unread_count": 1, "user_can_see_posts": True}
view = {"participants": [{"id": 10, "display_name": "Fixture student A"},
                         {"id": 11, "display_name": "Fixture student B"}],
        "unread_entries": [103], "forced_entries": [103],
        "view": [{"id": 101, "user_id": 10, "parent_id": None,
                  "message": "<p>Option A leaves more open water.</p>",
                  "replies": [{"id": 103, "user_id": 11, "parent_id": 101,
                               "message": "<p>How does that affect summer shade?</p>"}]},
                 {"id": 102, "user_id": 11, "parent_id": None,
                  "message": "<p>Option B retains mature trees.</p>"}]}
fixture = {"routes": {"GET /api/v1/courses/42/discussion_topics/71": topic,
                      "GET /api/v1/courses/42/discussion_topics/71/view": view}}
class ReadOnlyFixture(CanvasClient):
    def __init__(self):
        super().__init__(fixture=fixture, token="", base_url="https://synthetic.example")
        self.requests = []
    def request(self, method, path, **kwargs):
        if method != "GET" or "GET " + path not in fixture["routes"]:
            raise RuntimeError("unexpected request")
        self.requests.append({"method": method, "path": path, "kwargs": kwargs})
        return super().request(method, path, **kwargs)
client = ReadOnlyFixture()
with CanvasAPI(client) as api:
    result = api.get_discussion(42, 71)
    if result != {"topic": topic, "view": view}:
        raise RuntimeError("existing raw discussion behavior changed")
    method_present = hasattr(api, "discussion_thread")
env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(SOURCE),
       "PYTHONDONTWRITEBYTECODE": "1"}
command = [sys.executable, "-B", "-m", "canvaspilot.cli", "discussion", "42", "71"]
run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
if run.returncode != 2 or "invalid choice: 'discussion'" not in run.stderr or run.stdout:
    raise RuntimeError("unexpected original CLI boundary")
after = snapshot()
if before != after:
    raise RuntimeError("source mutated")
receipt = {
    "base": PINS["base"], "tree": PINS["tree"], "python": sys.version,
    "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "source_before": before, "source_after": after,
    "raw_get_discussion_positive_control": result,
    "requests": client.requests,
    "discussion_thread_method_present": method_present,
    "discussion_thread_tool_present": "canvas_discussion_thread" in tool_inventory()["curated"],
    "cli": {"command": command, "returncode": run.returncode,
            "stdout": run.stdout, "stderr": run.stderr},
    "assessment": "The existing raw topic/view API works; the terminal reader and curated unread-context report are absent. This is an additive capability boundary, not an assertion that raw discussion reads fail.",
    "limits": ["Synthetic fixture only", "No live Canvas, account, token, browser, post or mark-read request"]
}
text = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
(ROOT / "baseline-receipt.json").write_text(text)
print(text, end="")
