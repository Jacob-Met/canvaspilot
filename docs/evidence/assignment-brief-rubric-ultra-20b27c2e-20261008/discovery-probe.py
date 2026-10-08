"""Read-only product witness against an exact CanvasPilot source checkout."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--checkout", type=Path, default=ROOT / "baseline")
parser.add_argument("--output", type=Path, default=ROOT / "missing-rubric-before.json")
args = parser.parse_args()
sys.path.insert(0, str(args.checkout / "src"))

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.cli import main
from canvaspilot import mcp_server

RUBRIC = [
    {"id": "evidence", "description": "Use primary evidence", "long_description": "Cite two sources and explain how they support the argument.",
     "points": 12, "criterion_use_range": False,
     "ratings": [{"id": "full-evidence", "description": "Meets all requirements", "points": 12},
                 {"id": "no-evidence", "description": "No supporting sources", "points": 0}]},
    {"id": "reasoning", "description": "Address a counterargument", "long_description": "Explain one limitation in the proposed interpretation.",
     "points": 8, "criterion_use_range": False,
     "ratings": [{"id": "full-reasoning", "description": "Meets all requirements", "points": 8},
                 {"id": "no-reasoning", "description": "No counterargument", "points": 0}]},
]
ASSIGNMENT = {
    "id": 311, "name": "Synthetic source analysis", "due_at": "2026-10-15T17:00:00Z",
    "points_possible": 20, "submission_types": ["online_upload"],
    "html_url": "https://canvas.example.invalid/courses/17/assignments/311",
    "description": "<p>Write a short analysis. Follow the attached grading rubric.</p>",
    "rubric": RUBRIC,
}
fixture = {"routes": {"GET /api/v1/courses/17/assignments/311": ASSIGNMENT}}
calls = []


class RecordedFixtureClient(CanvasClient):
    def request(self, method, path, **kwargs):
        calls.append({"method": method, "path": path})
        return super().request(method, path, **kwargs)


with tempfile.TemporaryDirectory() as temp:
    with patch("httpx.Client", side_effect=AssertionError("No HTTP client is allowed in this fixture witness")):
        with CanvasAPI(RecordedFixtureClient(fixture=fixture, token="", profile=Path(temp),
                                            base_url="https://canvas.example.invalid")) as api:
            full = api.get_assignment("17", "311")
            brief = api.assignment_brief("17", "311")

        def fixture_client(**kwargs):
            return RecordedFixtureClient(fixture=fixture, **kwargs)

        output = io.StringIO()
        with patch("canvaspilot.client.CanvasClient", side_effect=fixture_client), contextlib.redirect_stdout(output):
            main(["brief", "17", "311", "--token", "", "--profile", temp,
                  "--base-url", "https://canvas.example.invalid"])
        cli = json.loads(output.getvalue())

        with CanvasAPI(RecordedFixtureClient(fixture=fixture, token="", profile=Path(temp),
                                            base_url="https://canvas.example.invalid")) as api:
            with patch.object(mcp_server, "_api", api):
                mcp_result = asyncio.run(mcp_server.mcp.call_tool(
                    "canvas_assignment_brief", {"course_id": "17", "assignment_id": "311"}
                ))
        mcp_payload = json.loads(mcp_result.content[0].text)

result = {
    "repository": "Jacob-Met/canvaspilot",
    "baseline_commit": "874ad9c073fc5bab625e583849dbbe4eaf7fc6af",
    "checkout": str(args.checkout.resolve()),
    "api_source_sha256": hashlib.sha256((args.checkout / "src/canvaspilot/api.py").read_bytes()).hexdigest(),
    "full_assignment_preserves_supplied_rubric": full.get("rubric") == RUBRIC,
    "supplied_criteria": len(RUBRIC),
    "supplied_criterion_points": sum(row["points"] for row in RUBRIC),
    "brief_rubric_present": "rubric" in brief,
    "cli_brief_rubric_present": "rubric" in cli,
    "registered_mcp_brief_rubric_present": "rubric" in mcp_payload,
    "registered_mcp_is_error": mcp_result.is_error,
    "prompt_preserved": brief["prompt"] == "Write a short analysis. Follow the attached grading rubric.",
    "cli_equals_api_brief": cli == brief,
    "registered_mcp_equals_api_brief": mcp_payload == brief,
    "observed_native_calls": calls,
    "native_brief_output": brief,
    "finding": "The getter retains the supplied rubric; compare the API, CLI and registered MCP brief outputs against it.",
    "limits": "Explicit synthetic fixture backend and actual registered MCP call_tool dispatcher; no school account, browser session, token, HTTP transport, stdio client, submission, model or external state is used.",
}
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
