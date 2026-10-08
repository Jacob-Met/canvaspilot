"""Actual CLI, MCP stdio and HTTP receiving for the synthetic discussion reader."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import threading
import unittest
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]
TOPIC_PATH = "/api/v1/courses/63/discussion_topics/81"


class DiscussionThreadNativeTests(unittest.TestCase):
    def setUp(self):
        self.topic = {"id": 81, "title": "Synthetic station design", "message": "<p>Read both options.</p>",
                      "unread_count": 2, "discussion_subentry_count": 70, "user_can_see_posts": True}
        self.view = {
            "unread_entries": [13, 27], "forced_entries": [13],
            "participants": [{"id": 5, "display_name": "Fixture author"}],
            "view": [{"id": 11, "user_id": 5, "parent_id": None, "message": "<p>Platform location?</p>",
                      "replies": [{"id": 13, "user_id": 5, "parent_id": 11, "message": "<p>Near the ramp.</p>"},
                                  {"id": 14, "user_id": 5, "parent_id": 11, "message": "<p>Read neighbor.</p>"}]},
                     {"id": 21, "user_id": 5, "parent_id": None, "message": "<p>Read root.</p>"}]}
        self.requests = []
        self.records = []
        self.view_status = 200
        self.view_raw = None
        self.before = deepcopy((self.topic, self.view))
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                url = urlsplit(self.path)
                owner.requests.append({"method": "GET", "path": url.path, "query": parse_qs(url.query)})
                status = 200
                if url.path == TOPIC_PATH:
                    value = owner.topic
                elif url.path == TOPIC_PATH + "/view":
                    status = owner.view_status
                    value = owner.view if status == 200 else {"error": "Synthetic discussion unavailable"}
                else:
                    status, value = 404, {"error": "Unexpected fixture path"}
                raw = owner.view_raw if url.path.endswith("/view") and owner.view_raw is not None else json.dumps(value).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                owner.requests.append({"method": "POST", "path": self.path})
                self.send_error(405)

            def do_PUT(self):
                owner.requests.append({"method": "PUT", "path": self.path})
                self.send_error(405)

            def do_DELETE(self):
                owner.requests.append({"method": "DELETE", "path": self.path})
                self.send_error(405)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")]),
            "PYTHONDONTWRITEBYTECODE": "1",
            "CANVAS_BASE_URL": self.base,
            "CANVAS_API_TOKEN": "disposable-discussion-fixture",
            "CANVAS_PROFILE": str(ROOT / "unused-discussion-profile"),
            "NO_PROXY": "127.0.0.1",
            "no_proxy": "127.0.0.1",
        }

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.assertFalse((ROOT / "unused-discussion-profile").exists())
        custody = os.environ.get("CANVAS_DISCUSSION_TEST_RECEIPTS")
        if custody:
            destination = Path(custody)
            destination.mkdir(parents=True, exist_ok=True)
            (destination / (self._testMethodName + ".json")).write_text(
                json.dumps({"case": self.id(), "records": self.records,
                            "requests": self.requests, "fixture_before": self.before,
                            "fixture_after": (self.topic, self.view)}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    def cli(self, *extra, course="63", topic="81"):
        result = subprocess.run(
            [sys.executable, "-B", "-m", "canvaspilot.cli", "discussion", course, topic, *extra],
            cwd=ROOT, env=self.env, capture_output=True, text=True, timeout=20, check=False,
        )
        self.records.append({"surface": "cli", "course": course, "topic": topic,
                             "extra": extra, "returncode": result.returncode,
                             "stdout": result.stdout, "stderr": result.stderr})
        return result

    def assert_cli_stderr(self, result, *, error=False):
        # The installed MCP setup enables HTTPX request logging on stderr.
        # Retain and admit those real request logs; inspect the final semantic
        # diagnostic without changing production logging to fit this test.
        lines = result.stderr.splitlines()
        message = None
        if error:
            self.assertTrue(lines, "The failed read needs a visible diagnostic")
            message = json.loads(lines.pop())
            self.assertIs(message["ok"], False)
        for line in lines:
            self.assertTrue(any(
                line.startswith(f"HTTP Request: GET {self.base}{path}?per_page=50 ")
                for path in (TOPIC_PATH, TOPIC_PATH + "/view")
            ), "Unexpected stderr content: " + line)
        return message

    def assert_reads(self, count=1):
        self.assertEqual([x["path"] for x in self.requests], [TOPIC_PATH, TOPIC_PATH + "/view"] * count)
        self.assertTrue(all(x["method"] == "GET" and x["query"] == {"per_page": ["50"]} for x in self.requests))

    def assert_report(self, result, *, focused):
        self.assertEqual(result["topic"], self.topic)
        self.assertEqual(result["view_metadata"]["unread_entries"], [13, 27])
        self.assertEqual(result["unmatched_unread_entries"], [27])
        self.assertEqual([x["entry"]["id"] for x in result["entries"]], [11, 13] if focused else [11, 13, 14, 21])
        self.assertEqual([x["context_only"] for x in result["entries"]], [True, False] if focused else [False] * 4)
        self.assertEqual(result["entries"][1]["parent_path"], [0])
        self.assertEqual(result["entries"][1]["message_text"], "Near the ramp.")
        self.assertIs(result["entries"][1]["forced_read_state"], True)
        self.assertEqual(result["counts"]["observed_entries"], 4)
        self.assertEqual(result["counts"]["known_unread_entries"], 1)
        self.assertEqual(result["source"]["kind"], "canvas_cached_discussion_view")
        self.assertTrue(result["source"]["eventually_consistent"])

    def test_cli_all_and_unread_focus_use_exact_two_read_requests_each(self):
        for focused in (False, True):
            result = self.cli(*(["--unread-only"] if focused else []))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_cli_stderr(result)
            self.assert_report(json.loads(result.stdout), focused=focused)
        self.assert_reads(count=2)
        self.assertEqual((self.topic, self.view), self.before)

    def test_cli_http_refusals_are_errors_without_partial_success_or_retry(self):
        for status in (403, 404, 503):
            with self.subTest(status=status):
                self.requests.clear()
                self.view_status = status
                result = self.cli("--unread-only")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, "")
                error = self.assert_cli_stderr(result, error=True)
                self.assertIs(error["ok"], False)
                self.assertIn(str(status), error["message"])
                self.assert_reads()
        self.assertEqual((self.topic, self.view), self.before)

    def test_cli_malformed_or_unavailable_view_is_not_an_empty_discussion(self):
        for raw in (b"{broken", b"null", b'{"view": null}', b'{"view": [], "unread_entries": null}'):
            with self.subTest(raw=raw):
                self.requests.clear()
                self.view_raw = raw
                result = self.cli("--unread-only")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIs(self.assert_cli_stderr(result, error=True)["ok"], False)
                self.assert_reads()

    def test_cli_invalid_route_and_unknown_flag_make_no_http_requests(self):
        for course, topic, extra in (("../63", "81", ()), ("63", "81?read=true", ()),
                                     ("63", "81", ("--read",)), ("63", "81", ("--unread-only=false",))):
            with self.subTest(course=course, topic=topic, extra=extra):
                result = self.cli(*extra, course=course, topic=topic)
                self.assertIn(result.returncode, (1, 2))
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr)
        self.assertEqual(self.requests, [])

    def test_cli_second_read_reflects_supplied_changes_without_retaining_old_unread_rows(self):
        first = self.cli("--unread-only")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assert_report(json.loads(first.stdout), focused=True)
        self.view["unread_entries"] = []
        self.view["forced_entries"] = []
        second = self.cli("--unread-only")
        self.assertEqual(second.returncode, 0, second.stderr)
        data = json.loads(second.stdout)
        self.assertEqual(data["entries"], [])
        self.assertEqual(data["counts"]["observed_entries"], 4)
        self.assertEqual(data["view_metadata"]["unread_entries"], [])
        self.assert_reads(count=2)

    async def exchange(self, *, errors=False):
        parameters = StdioServerParameters(
            command=sys.executable, args=["-B", "-m", "canvaspilot.cli", "mcp"],
            cwd=ROOT, env=self.env,
        )
        async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            inventory = await session.list_tools()
            tool = next(item for item in inventory.tools if item.name == "canvas_discussion_thread")
            wire = tool.model_dump(by_alias=True)
            self.records.append({"surface": "mcp", "tool": wire})
            self.assertTrue(wire["annotations"]["readOnlyHint"])
            self.assertFalse(wire["annotations"]["destructiveHint"])
            self.assertEqual(wire["inputSchema"]["properties"]["unread_only"]["type"], "boolean")
            if errors:
                for arguments in ({"course_id": "63", "topic_id": "81", "unread_only": "false"},
                                  {"course_id": "63/../2", "topic_id": "81"}):
                    response = await session.call_tool("canvas_discussion_thread", arguments)
                    self.records.append({"surface": "mcp", "arguments": arguments, "response": response.model_dump(by_alias=True)})
                    self.assertTrue(response.model_dump(by_alias=True)["isError"])
                self.assertEqual(self.requests, [])
                self.view_status = 503
                response = await session.call_tool(
                    "canvas_discussion_thread", {"course_id": "63", "topic_id": "81", "unread_only": True}
                )
                self.records.append({"surface": "mcp", "response": response.model_dump(by_alias=True)})
                self.assertTrue(response.model_dump(by_alias=True)["isError"])
                self.assert_reads()
            else:
                for focused in (False, True):
                    response = await session.call_tool(
                        "canvas_discussion_thread", {"course_id": "63", "topic_id": "81", "unread_only": focused}
                    )
                    body = response.model_dump(by_alias=True)
                    self.records.append({"surface": "mcp", "unread_only": focused, "response": body})
                    self.assertFalse(body.get("isError"))
                    result = json.loads("".join(x["text"] for x in body["content"] if x["type"] == "text"))
                    self.assert_report(result, focused=focused)

    def test_mcp_actual_stdio_and_http_share_the_same_reading_contract(self):
        asyncio.run(asyncio.wait_for(self.exchange(), timeout=25))
        self.assert_reads(count=2)
        self.assertEqual((self.topic, self.view), self.before)

    def test_mcp_actual_errors_do_not_dispatch_invalid_inputs_or_retry_refusals(self):
        asyncio.run(asyncio.wait_for(self.exchange(errors=True), timeout=25))
        self.assertEqual((self.topic, self.view), self.before)


if __name__ == "__main__":
    unittest.main()
