"""Planner CLI receiving through the real package and a disposable HTTP server.

These tests need the project's declared dependencies. They do not replace
HTTPX, the native pagination implementation, or package/MCP bootstrap.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class PlannerCLITests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="canvaspilot-planner-cli-")
        self.addCleanup(self.work.cleanup)
        self.requests = []
        self.pages = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                owner.requests.append({
                    "method": self.command,
                    "path": self.path,
                    "authorization": self.headers.get("Authorization"),
                })
                status, payload, headers = (
                    owner.pages.pop(0) if owner.pages else (500, {"error": "unexpected read"}, {})
                )
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                owner.requests.append({"method": self.command, "path": self.path})
                self.send_error(405, "Read-only planner test")

            do_PUT = do_POST
            do_PATCH = do_POST
            do_DELETE = do_POST

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True,
        )
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.assertFalse(self.thread.is_alive())

    def run_cli(self, *arguments):
        # Start from explicit synthetic configuration; no inherited Canvas
        # token, broker, profile, proxy or package-path configuration is used.
        env = {
            "PATH": os.defpath,
            "PYTHONPATH": str(ROOT / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "LANG": "C.UTF-8",
        }
        return subprocess.run(
            [sys.executable, "-B", "-m", "canvaspilot.cli", *arguments,
             "--base-url", self.base, "--token", "synthetic-planner-token",
             "--profile", str(Path(self.work.name) / "unused-profile")],
            cwd=self.work.name, env=env, capture_output=True, timeout=20, check=False,
        )

    def assert_reads(self, count):
        self.assertEqual(len(self.requests), count)
        self.assertTrue(all(row["method"] == "GET" for row in self.requests))
        self.assertTrue(all(row["authorization"] == "Bearer synthetic-planner-token"
                            for row in self.requests))
        self.assertFalse((Path(self.work.name) / "unused-profile").exists())

    def test_dates_and_all_native_fields_survive_complete_pagination(self):
        rows = [
            {"plannable_type": "assignment", "plannable_id": "700", "course_id": 42,
             "plannable_date": "2026-10-08T12:00:00Z",
             "plannable": {"title": "Synthetic zero-point task", "points_possible": 0},
             "submissions": {"submitted": False, "score": None},
             "planner_override": {"marked_complete": True, "dismissed": False}},
            {"plannable_type": "discussion_topic", "plannable_id": 801,
             "plannable": {"title": "Literal <b>読書</b>\n & conversation"},
             "planner_override": None, "future_field": [0, False, None]},
            {"plannable_type": "planner_note", "plannable_id": 902,
             "plannable": {"title": "Bring a book", "course_id": None},
             "submissions": False},
        ]
        continuation = "/api/v1/planner/items?cursor=opaque%2Fsecond&include%5B%5D=planner_override"
        self.pages = [
            (200, rows[:1], {"Link": f'<{self.base}{continuation}>; rel="next"'}),
            (200, rows[1:], {}),
        ]
        result = self.run_cli(
            "planner", "--start-date", "2026-10-08T09:10:11Z", "--end-date", "2026-10-12",
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout), rows)
        self.assert_reads(2)
        first = urlsplit(self.requests[0]["path"])
        self.assertEqual(first.path, "/api/v1/planner/items")
        self.assertEqual(parse_qs(first.query), {
            "start_date": ["2026-10-08T09:10:11Z"],
            "end_date": ["2026-10-12"], "per_page": ["50"],
        })
        self.assertEqual(self.requests[1]["path"], continuation)
        self.assertEqual(self.pages, [])

    def test_omitted_filters_keep_the_native_empty_result(self):
        self.pages = [(200, [], {})]
        result = self.run_cli("planner")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout), [])
        self.assert_reads(1)
        self.assertEqual(parse_qs(urlsplit(self.requests[0]["path"]).query), {"per_page": ["50"]})

    def test_first_terminal_object_keeps_the_existing_client_convention(self):
        row = {"future_shape": {"unknown": None, "value": False}}
        self.pages = [(200, row, {})]
        result = self.run_cli("planner")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout), [row])
        self.assert_reads(1)

    def test_native_errors_refuse_a_partial_success_document(self):
        cases = [
            ("initial-auth", [(403, {"error": "synthetic auth refusal"}, {})],
             "CanvasAuthError", 1),
            ("later-http", [
                (200, [{"id": "early"}], {"Link": f'<{self.base}/api/v1/planner/items?page=2>; rel="next"'}),
                (500, {"error": "synthetic later page failure"}, {}),
            ], "HTTPStatusError", 2),
            ("later-shape", [
                (200, [{"id": "early"}], {"Link": f'<{self.base}/api/v1/planner/items?page=2>; rel="next"'}),
                (200, {"unexpected": "continuing object"}, {}),
            ], "CanvasPaginationError", 2),
        ]
        for label, pages, error, count in cases:
            with self.subTest(label=label):
                self.requests.clear()
                self.pages = list(pages)
                result = self.run_cli("planner")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b"")
                failure = json.loads(result.stderr)
                self.assertEqual(failure["ok"], False)
                self.assertEqual(failure["error"], error)
                self.assertIsInstance(failure["message"], str)
                self.assert_reads(count)

    def test_missing_date_value_refuses_before_a_request(self):
        result = self.run_cli("planner", "--start-date")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"expected one argument", result.stderr)
        self.assertEqual(self.requests, [])
        self.assertFalse((Path(self.work.name) / "unused-profile").exists())

    def test_existing_identity_command_still_uses_its_native_route(self):
        profile = {"id": 123, "name": "Synthetic planner reader"}
        self.pages = [(200, profile, {})]
        result = self.run_cli("whoami")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(json.loads(result.stdout), {
            "mode": "token", "base_url": self.base, "profile": profile,
        })
        self.assert_reads(1)
        self.assertEqual(urlsplit(self.requests[0]["path"]).path, "/api/v1/users/self/profile")


if __name__ == "__main__":
    unittest.main()
