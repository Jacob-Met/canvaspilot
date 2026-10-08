"""Independent course-folder receiving controls on actual public/native paths.

The source copy and every HTTP listener are private. The real broker Handler is
used with a local authored worker queue; no browser, account, or provider runs.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "candidate"
for _name in list(os.environ):
    if "TOKEN" in _name.upper() or "PROXY" in _name.upper():
        os.environ.pop(_name, None)
os.environ["CANVAS_BASE_URL"] = "https://canvas.fixture.invalid"
os.environ["CANVAS_PROFILE"] = str(ROOT / "unused-profile")
os.environ["CANVAS_SESSION_PORT"] = "0"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONPATH"] = str(SOURCE / "src")
sys.path.insert(0, str(SOURCE / "src"))

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient
from canvaspilot.folder_browser import FolderBrowseError

EVENTS = []


def folder(identity=110, course=42, parent=100, **extra):
    return {"id": identity, "context_type": "Course", "context_id": course,
            "parent_folder_id": parent, "name": "Unit 雪",
            "full_name": "course files/Unit 雪", "folders_count": 99, "files_count": 99,
            "files_url": "https://invalid.invalid/never-follow",
            "folders_url": "https://invalid.invalid/never-follow", **extra}


def file(identity=501, parent=110, **extra):
    return {"id": identity, "folder_id": parent, "display_name": "Report 雪.pdf",
            "filename": "Report 雪.pdf", "size": 9, "content-type": "application/pdf",
            "url": "https://invalid.invalid/never-download",
            "preview_url": "https://invalid.invalid/never-preview",
            "body": "PRIVATE_BODY_NOT_METADATA", **extra}


class Wire:
    def __init__(self):
        self.calls = []
        self.overrides = {}
        self.page_size_cap = None
        self.root = folder(100, parent=None)
        self.selected = folder()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)
                owner.calls.append({"method": "GET", "path": parsed.path, "query": query})
                status, value = owner.route(parsed.path, query)
                raw = json.dumps(value, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Link", '<https://invalid.invalid/opaque-cursor>; rel="next"')
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                owner.calls.append({"method": "POST", "path": self.path})
                self.send_error(405)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_port)

    def route(self, path, query):
        if path in self.overrides:
            return copy.deepcopy(self.overrides[path])
        if path == "/api/v1/courses/42/folders/root":
            return 200, copy.deepcopy(self.root)
        if path == "/api/v1/courses/42/folders/110":
            return 200, copy.deepcopy(self.selected)
        if path == "/api/v1/folders/110/folders":
            values = [folder(120, parent=110), folder(121, parent=110), folder(122, parent=110)]
        elif path == "/api/v1/folders/110/files":
            values = [file(501), file(502), file(503)]
        elif path in ("/api/v1/folders/100/folders", "/api/v1/folders/100/files"):
            values = []
        else:
            return 404, {"private_error_detail": "PRIVATE_ERROR_BODY"}
        size = int(query.get("per_page", ["50"])[0])
        if self.page_size_cap is not None:
            size = min(size, self.page_size_cap)
        page = int(query.get("page", ["1"])[0])
        return 200, values[(page - 1) * size:page * size]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


@contextmanager
def actual_readonly_broker(wire):
    import canvaspilot.client as client_module
    from canvaspilot.session_broker import Handler, STATE
    names = ("base_url", "profile", "headless", "read_only", "jobs", "page_url", "page_title", "error")
    before = {key: getattr(STATE, key) for key in names}
    was_ready = STATE.ready.is_set()
    old_port = client_module.BROKER_PORT
    STATE.base_url = "https://canvas.fixture.invalid"
    STATE.profile = ROOT / "unused-profile"
    STATE.headless = False
    STATE.read_only = True
    STATE.jobs = queue.Queue()
    STATE.page_url = "https://canvas.fixture.invalid/courses"
    STATE.page_title = "Independent receiving"
    STATE.error = None
    STATE.ready.set()
    stopped = threading.Event()
    jobs = []

    def respond():
        while not stopped.is_set():
            try:
                job, reply = STATE.jobs.get(timeout=0.02)
            except queue.Empty:
                continue
            jobs.append(copy.deepcopy(job))
            if job.get("op") != "fetch" or job.get("method") != "GET" or job.get("body") is not None:
                reply.put({"ok": False, "error": "unexpected independent fixture operation"})
                continue
            parsed = urlsplit(job["path"])
            status, value = wire.route(parsed.path, parse_qs(parsed.query))
            reply.put({"ok": True, "response": {"status": status, "json": value, "text": None}})

    worker = threading.Thread(target=respond, daemon=True)
    worker.start()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    serving = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    serving.start()
    client_module.BROKER_PORT = server.server_port
    os.environ["CANVAS_SESSION_PORT"] = str(server.server_port)
    os.environ.pop("CANVAS_API_TOKEN", None)
    try:
        yield jobs
    finally:
        server.shutdown()
        server.server_close()
        stopped.set()
        worker.join(timeout=3)
        serving.join(timeout=3)
        client_module.BROKER_PORT = old_port
        for key, value in before.items():
            setattr(STATE, key, value)
        if not was_ready:
            STATE.ready.clear()


class IndependentFolders(unittest.TestCase):
    def setUp(self):
        self.wire = Wire()
        self.addCleanup(self.wire.close)
        os.environ["CANVAS_BASE_URL"] = self.wire.url
        os.environ["CANVAS_API_TOKEN"] = "synthetic-review-value"
        os.environ["CANVAS_SESSION_PORT"] = "0"
        self.api = CanvasAPI(CanvasClient())
        self.addCleanup(self.api.close)

    def tearDown(self):
        self.assertFalse((ROOT / "unused-profile").exists())
        self.assertTrue(all(row["method"] == "GET" for row in self.wire.calls))
        EVENTS.append({"test": self.id().split(".")[-1], "http_requests": self.wire.calls})

    def cli(self, *args):
        return subprocess.run([sys.executable, *(["-O"] if sys.flags.optimize else []), "-m", "canvaspilot.cli", "browse-files", *args],
                              capture_output=True, text=True, env=dict(os.environ), timeout=15)

    def test_normalized_ids_and_independent_pages_reach_exact_native_requests(self):
        self.wire.selected = folder("00110", course="00042", parent="00100")
        result = self.api.browse_files("00042", "00110", folders_page=2, files_page=1, per_page=2)
        self.assertEqual(result["folder"]["id"], "00110")
        self.assertEqual([r["id"] for r in result["folders"]["items"]], [122])
        self.assertEqual([r["id"] for r in result["files"]["items"]], [501, 502])
        self.assertEqual([r["path"] for r in self.wire.calls],
                         ["/api/v1/courses/42/folders/110",
                          "/api/v1/folders/110/folders", "/api/v1/folders/110/files"])
        self.assertEqual(self.wire.calls[1]["query"], {"page": ["2"], "per_page": ["2"]})
        self.assertEqual(self.wire.calls[2]["query"], {"page": ["1"], "per_page": ["2"]})
        self.assertNotIn("never-", json.dumps(result))
        self.assertNotIn("PRIVATE_BODY", json.dumps(result))

    def test_same_numeric_context_in_another_context_type_never_reaches_children(self):
        for item in (folder(context_type="Group"), folder(context_type="User"),
                     folder(context_id=True), folder(context_id=None)):
            with self.subTest(item=item):
                self.wire.selected = item
                before = len(self.wire.calls)
                with self.assertRaises(FolderBrowseError):
                    self.api.browse_files(42, 110)
                self.assertEqual(len(self.wire.calls) - before, 1)

    def test_duplicate_numeric_aliases_and_self_parent_child_stop_before_file_reads(self):
        for values in ([folder(120, parent=110), folder("00120", parent="00110")],
                       [folder(110, parent=110)]):
            with self.subTest(values=values):
                self.wire.overrides["/api/v1/folders/110/folders"] = (200, values)
                before = len(self.wire.calls)
                with self.assertRaises(FolderBrowseError):
                    self.api.browse_files(42, 110)
                self.assertEqual(len(self.wire.calls) - before, 2)
                self.assertNotEqual(self.wire.calls[-1]["path"], "/api/v1/folders/110/files")

    def test_mixed_foreign_file_page_never_returns_a_valid_prefix_through_cli(self):
        self.wire.overrides["/api/v1/folders/110/files"] = (
            200, [file(), file(502, parent=999, display_name="FOREIGN_PRIVATE_NAME")])
        with self.assertRaises(FolderBrowseError):
            self.api.browse_files(42, 110)
        result = self.cli("42", "--folder-id", "110")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("FOREIGN_PRIVATE_NAME", result.stderr)
        self.assertNotIn("Report", result.stderr)
        error = json.loads(result.stderr.strip().splitlines()[-1])
        self.assertEqual(error["error"], "FolderBrowseError")
        self.assertFalse(error["ok"])

    def test_permission_change_empty_and_server_page_cap_preserve_unknown_completeness(self):
        self.wire.page_size_cap = 1
        first = self.api.browse_files(42, 110, per_page=100)
        second = self.api.browse_files(42, 110, folders_page=2, files_page=2, per_page=100)
        empty = self.api.browse_files(42, 110, files_page=10000, per_page=100)
        self.assertEqual([r["id"] for r in first["files"]["items"]], [501])
        self.assertEqual([r["id"] for r in second["files"]["items"]], [502])
        self.assertEqual(empty["files"]["items"], [])
        self.assertIsNone(empty["files"]["next_page_to_try"])
        self.assertTrue(empty["files"]["page_limit_reached"])
        for result in (first, second, empty):
            for kind in ("folders", "files"):
                self.assertIsNone(result[kind]["has_more"])
        self.wire.overrides["/api/v1/folders/110/files"] = (403, {"name": "PRIVATE_ERROR_BODY"})
        failed = self.cli("42", "--folder-id", "110")
        self.assertEqual(failed.returncode, 1)
        self.assertEqual(failed.stdout, "")
        self.assertNotIn("PRIVATE_ERROR_BODY", failed.stderr)

    def test_real_readonly_broker_keeps_course_binding_and_independent_pages(self):
        with actual_readonly_broker(self.wire) as jobs:
            with CanvasAPI(CanvasClient()) as api:
                result = api.browse_files(42, 110, folders_page=2, files_page=1, per_page=2)
            self.assertEqual([r["id"] for r in result["folders"]["items"]], [122])
            good = self.cli("42", "--folder-id", "110", "--files-page", "2", "--per-page", "2")
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertEqual([r["id"] for r in json.loads(good.stdout)["files"]["items"]], [503])
            self.wire.selected = folder(course=77, name="FOREIGN_PRIVATE_NAME")
            before = len(jobs)
            failed = self.cli("42", "--folder-id", "110")
            self.assertEqual(failed.returncode, 1)
            self.assertEqual(failed.stdout, "")
            self.assertNotIn("FOREIGN_PRIVATE_NAME", failed.stderr)
            self.assertEqual(len(jobs) - before, 1)
            self.assertEqual(jobs[1]["path"], "/api/v1/folders/110/folders?page=2&per_page=2")
            self.assertEqual(jobs[2]["path"], "/api/v1/folders/110/files?page=1&per_page=2")
            self.assertTrue(all(j["method"] == "GET" and j["body"] is None for j in jobs))
            self.assertEqual(self.wire.calls, [])
            EVENTS.append({"test": self.id().split(".")[-1], "broker_jobs": copy.deepcopy(jobs)})

    def test_real_mcp_stdio_rejects_foreign_metadata_and_strictly_typed_pages(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def run():
            params = StdioServerParameters(command=sys.executable,
                args=[*(["-O"] if sys.flags.optimize else []), "-m", "canvaspilot.mcp_server"], env=dict(os.environ))
            with (ROOT / ("mcp-review-" + str(sys.flags.optimize) + ".log")).open("w") as errlog:
                async with (
                    stdio_client(params, errlog=errlog) as (read, write),
                    ClientSession(read, write, read_timeout_seconds=10) as session,
                ):
                    await session.initialize()
                    catalog = await session.list_tools()
                    item = next(t for t in catalog.tools if t.name == "canvas_browse_files")
                    wire_item = item.model_dump(by_alias=True)
                    self.assertTrue(wire_item["annotations"]["readOnlyHint"])
                    self.assertFalse(wire_item["annotations"]["destructiveHint"])

                    async def call(arguments):
                        result = await session.call_tool("canvas_browse_files", arguments)
                        wire_result = result.model_dump(by_alias=True)
                        text = "".join(c["text"] for c in wire_result["content"] if c["type"] == "text")
                        return wire_result.get("isError", False), text

                    failed, text = await call({"course_id": "42", "folder_id": "110", "per_page": 2})
                    self.assertFalse(failed, text)
                    self.assertEqual([r["id"] for r in json.loads(text)["files"]["items"]], [501, 502])
                    before = len(self.wire.calls)
                    for value in (True, 1.0, "1", None, 10001):
                        failed, text = await call({"course_id": "42", "folder_id": "110", "files_page": value})
                        self.assertTrue(failed, str(value))
                    self.assertEqual(len(self.wire.calls), before)
                    self.wire.overrides["/api/v1/folders/110/files"] = (
                        200, [file(), file(502, parent=999, display_name="FOREIGN_PRIVATE_NAME")])
                    failed, text = await call({"course_id": "42", "folder_id": "110"})
                    self.assertTrue(failed)
                    self.assertNotIn("FOREIGN_PRIVATE_NAME", text)
                    self.assertNotIn('"items"', text)
                    EVENTS.append({"test": self.id().split(".")[-1], "mcp_catalog": wire_item,
                                   "foreign_file_error": text})
        asyncio.run(run())


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    receipt = {
        "schema": "canvaspilot.independent-folder-receiving.v1",
        "candidate_tree": "fbc99e88b46328072ab8eaab23023b9b17dd1898",
        "python": sys.version, "optimization": sys.flags.optimize,
        "dependencies": {name: importlib.metadata.version(name)
                         for name in ("httpx", "mcp", "pydantic")},
        "tests": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skips": len(result.skipped),
        "successful": result.wasSuccessful(), "events": EVENTS,
        "boundary": "native public API/CLI/MCP and actual Handler with authored loopback responses",
        "live_provider_or_browser_calls": 0,
    }
    (ROOT / ("review-" + str(sys.flags.optimize) + ".json")).write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    raise SystemExit(not result.wasSuccessful())
