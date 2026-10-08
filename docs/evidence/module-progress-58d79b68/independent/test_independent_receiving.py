"""Independent CanvasPilot receiving controls and preserved normalization counterexamples.

The three original-contract counterexamples deliberately assert upstream-shape
refusal. Their failures characterize information lost by the existing reader;
the reviewer does not alter that reader or repair these assertions retrospectively.
"""
from __future__ import annotations
import asyncio
from copy import deepcopy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "candidate"
EVIDENCE = []
SYNTHETIC_TOKEN = "independent-module-progress-fixture"
SOURCE_COMMIT = "51609ba3f93d20f69616b357c3c6bee19732dfd4"

def module(identity=77, **fields):
    return {"id": identity, "name": "Independent synthetic module", "items_count": 0,
            "items": [], "state": "started", "requirement_type": "all",
            "require_sequential_progress": False, "prerequisite_module_ids": [], **fields}

def item(identity=771, **fields):
    return {"id": identity, "module_id": 77, "title": "Independent synthetic item",
            "type": "Page", **fields}

class WireFixture:
    def __init__(self):
        self.requests = []
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)
                owner.requests.append({"method": "GET", "path": parsed.path, "query": query})
                status, body, headers = owner.response(parsed.path, query)
                raw = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(raw)
            def refuse_write(self):
                owner.requests.append({"method": self.command, "path": self.path})
                self.send_error(405)
            do_POST = refuse_write
            do_PUT = refuse_write
            do_PATCH = refuse_write
            do_DELETE = refuse_write
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = "http://127.0.0.1:" + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.02}, daemon=True)
        self.thread.start()

    def response(self, path, query):
        parts = path.strip("/").split("/")
        if len(parts) < 5 or parts[:3] != ["api", "v1", "courses"]:
            return 404, {"fixture_error": "unexpected route"}, {}
        course = parts[3]
        if parts[4:] == ["modules"]:
            if course == "201":
                # Invalid upstream collection shape, but a valid single module.
                return 200, module(), {}
            if course == "202":
                return 200, [module(items_count=1, items=None)], {}
            if course == "203":
                page = int(query.get("cursor", ["1"])[0])
                return 200, [module(identity=10000+page)], {
                    "Link": "<" + self.base + path + "?cursor=" + str(page+1) + '&opaque=retained>; rel="next"'
                }
            if course == "204":
                if "cursor" in query:
                    return 503, {"fixture_error": "later page unavailable"}, {}
                return 200, [module()], {
                    "Link": "<" + self.base + path + '?cursor=denied>; rel="next"'
                }
            if course == "206":
                return 200, [
                    module(state="completed", requirement_type="one", items_count=2, items=[
                        item(completion_requirement={"type": "must_view", "completed": False}),
                        item(772, completion_requirement={"type": "future_requirement", "completed": True}),
                    ]),
                    module(identity=88, state="locked", unlock_at="2000-01-01T00:00:00Z",
                           items_count=1, items=[item(881, module_id=88,
                               completion_requirement={"type": "must_submit", "completed": True})]),
                    module(identity=99, state=None, workflow_state="active", items_count=1,
                           items=[item(991, module_id=99,
                               completion_requirement={"type": "must_mark_done", "completed": True})]),
                ], {}
            if course == "207":
                return 200, [module(), module(identity=88, course_id=999)], {}
        if course == "202" and parts[4:] == ["modules", "77", "items"]:
            # Invalid upstream collection shape, wrapped by the existing reader.
            return 200, item(completion_requirement={"type": "must_view", "completed": False}), {}
        return 404, {"fixture_error": "unknown synthetic route"}, {}

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

class IndependentReceiving(unittest.TestCase):
    def setUp(self):
        self.fixture = WireFixture()
        self.addCleanup(self.fixture.close)
        self.tmp = tempfile.TemporaryDirectory(prefix="canvaspilot-independent-review-")
        self.addCleanup(self.tmp.cleanup)
        self.env = {k: v for k, v in os.environ.items()
                    if not k.lower().endswith("_proxy")}
        self.env.update({
            "CANVAS_BASE_URL": self.fixture.base,
            "CANVAS_API_TOKEN": SYNTHETIC_TOKEN,
            "CANVAS_PROFILE": str(Path(self.tmp.name) / "unused-profile"),
            "PYTHONPATH": str(PACKAGE / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        self.before_sources = {
            str(p.relative_to(PACKAGE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (PACKAGE / "src").rglob("*.py")
        }

    def tearDown(self):
        after = {str(p.relative_to(PACKAGE)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (PACKAGE / "src").rglob("*.py")}
        self.assertEqual(self.before_sources, after)
        self.assertTrue(all(r["method"] == "GET" for r in self.fixture.requests))
        self.assertTrue(all("student_id" not in r.get("query", {}) for r in self.fixture.requests))
        self.assertFalse((Path(self.tmp.name) / "unused-profile").exists())
        EVIDENCE.append({"control": self.id(), "requests": deepcopy(self.fixture.requests),
                         "source_preserved": self.before_sources == after,
                         "only_get": all(r["method"] == "GET" for r in self.fixture.requests)})

    def cli(self, *args):
        r = subprocess.run([sys.executable, "-B", "-m", "canvaspilot.cli", "module-progress", *args],
                           cwd=PACKAGE, env=self.env, capture_output=True, text=True, timeout=12)
        EVIDENCE.append({"control": self.id(), "surface": "cli", "arguments": args,
                         "exit": r.returncode, "stdout": r.stdout, "stderr": r.stderr})
        return r

    async def mcp_calls(self, calls):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        params = StdioServerParameters(command=sys.executable,
                                       args=["-B", "-m", "canvaspilot.mcp_server"], env=self.env)
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errors:
            async with asyncio.timeout(20):
                async with stdio_client(params, errlog=errors) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        listed = await session.list_tools()
                        names = [t.name for t in listed.tools]
                        self.assertEqual(len(names), 36)
                        self.assertIn("canvas_submission_feedback", names)
                        self.assertIn("canvas_assignment_brief", names)
                        progress = next(t for t in listed.tools if t.name == "canvas_module_progress")
                        self.assertTrue(progress.annotations.readOnlyHint)
                        self.assertFalse(progress.annotations.destructiveHint)
                        EVIDENCE.append({"control": self.id(), "surface": "mcp-registration",
                                         "tools_count": len(names), "tools": names,
                                         "progress_annotations": progress.annotations.model_dump()})
                        results = []
                        for arguments in calls:
                            result = await session.call_tool("canvas_module_progress", arguments)
                            text = "\n".join(c.text for c in result.content if c.type == "text")
                            observation = {"arguments": arguments, "isError": bool(result.isError),
                                           "content": text}
                            results.append(observation)
                            EVIDENCE.append({"control": self.id(), "surface": "mcp", **observation})
            errors.seek(0)
            EVIDENCE.append({"control": self.id(), "surface": "mcp-stderr", "stderr": errors.read()})
        return results

    def test_original_contract_singleton_module_should_refuse(self):
        r = self.cli("201")
        EVIDENCE.append({"control": self.id(), "original_expectation": "upstream collection shape refused",
                         "observed_normalization": "singleton module accepted" if r.returncode == 0 else "refused"})
        self.assertEqual(r.returncode, 1, "existing reader wraps a singleton module before the digest sees it")
        self.assertEqual(r.stdout, "")

    def test_original_contract_singleton_item_fallback_should_refuse(self):
        r = self.cli("202")
        EVIDENCE.append({"control": self.id(), "original_expectation": "upstream item collection shape refused",
                         "observed_normalization": "singleton item accepted" if r.returncode == 0 else "refused"})
        self.assertEqual(r.returncode, 1, "existing reader wraps a singleton item before the digest sees it")
        self.assertEqual(r.stdout, "")

    def test_original_contract_mcp_singletons_should_be_tool_errors(self):
        results = asyncio.run(self.mcp_calls([{"course_id": "201"}, {"course_id": "202"}]))
        self.assertTrue(all(r["isError"] for r in results),
                        "both registered MCP calls return successful normalized digests")

    def test_page_cap_is_observed_without_complete_collection_claim(self):
        r = self.cli("203")
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["modules_returned"], 40)
        self.assertEqual(report["modules_included"], 40)
        self.assertIsNone(report["collection_complete"])
        self.assertEqual(report["count_scope"], "returned_modules_and_items")
        self.assertEqual(len(self.fixture.requests), 40)
        self.assertEqual(self.fixture.requests[0]["query"]["include[]"], ["items"])
        self.assertEqual(self.fixture.requests[-1]["query"]["cursor"], ["40"])
        self.assertEqual(self.fixture.requests[-1]["query"]["opaque"], ["retained"])
        self.assertFalse(any("41" in r.get("query", {}).get("cursor", []) for r in self.fixture.requests))

    def test_later_read_failure_is_not_masked_by_module_selection(self):
        r = self.cli("204", "--module-id", "77")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertFalse(json.loads(r.stderr.splitlines()[-1])["ok"])
        self.assertEqual(len(self.fixture.requests), 2)

    def test_mcp_selected_later_failure_keeps_protocol_and_tool_error(self):
        result = asyncio.run(self.mcp_calls([{"course_id": "204", "module_id": "77"}]))[0]
        self.assertTrue(result["isError"])
        self.assertEqual(len(self.fixture.requests), 2)
        self.assertNotIn('"modules":', result["content"])

    def test_explicit_module_state_outweighs_local_counts_and_dates(self):
        r = self.cli("206")
        self.assertEqual(r.returncode, 0, r.stderr)
        completed, locked, unknown = json.loads(r.stdout)["modules"]
        self.assertEqual(completed["state"], "completed")
        self.assertEqual(completed["requirement_type"], "one")
        self.assertEqual(completed["requirement_counts"]["incomplete"], 1)
        self.assertEqual(completed["requirement_counts"]["unknown"], 1)
        self.assertEqual(completed["remaining_work"]["incomplete_item_ids"], [])
        self.assertEqual(completed["remaining_work"]["unknown_completion_item_ids"], [])
        self.assertEqual(completed["items"][1]["completion_requirement"],
                         {"type": "future_requirement", "completed": True})
        self.assertEqual(locked["state"], "locked")
        self.assertTrue(locked["remaining_work"]["module_locked"])
        self.assertEqual(locked["requirement_counts"]["completed"], 1)
        self.assertEqual(locked["remaining_work"]["item_access"], "not_assessed")
        self.assertEqual(unknown["state"], "unknown")
        self.assertIsNone(unknown["remaining_work"]["module_locked"])
        self.assertEqual(unknown["requirement_counts"]["completed"], 1)

    def test_selection_does_not_hide_an_explicit_foreign_module(self):
        r = self.cli("207", "--module-id", "77")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        error = json.loads(r.stderr.splitlines()[-1])
        self.assertEqual(error["error"], "ModuleProgressError")
        self.assertIn("different course", error["message"])

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentReceiving)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    packet = {"schema": "canvaspilot.independent_receiving.v1", "source_commit": SOURCE_COMMIT,
              "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "evidence": EVIDENCE}
    print("CANVAS_REVIEW_JSON=" + json.dumps(packet, ensure_ascii=False))
    sys.exit(not result.wasSuccessful())
