"""Exercise the native calendar-events command against disposable synthetic HTTP pages."""
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


class CalendarEventsCLITests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="canvaspilot-calendar-events-cli-")
        self.addCleanup(self.work.cleanup)
        self.requests = []
        self.pages = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                owner.requests.append({"method": self.command, "path": self.path,
                                       "authorization": self.headers.get("Authorization")})
                status, body, headers = (
                    owner.pages.pop(0) if owner.pages else (500, {"error": "unexpected read"}, {})
                )
                data = json.dumps(body, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                owner.requests.append({"method": self.command, "path": self.path})
                self.send_error(405, "Synthetic read-only calendar-event receiver")

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
        env = {"PATH": os.defpath, "PYTHONPATH": str(ROOT / "src"),
               "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "LANG": "C.UTF-8"}
        return subprocess.run(
            [sys.executable, "-B", "-m", "canvaspilot.cli", *arguments,
             "--base-url", self.base, "--token", "synthetic-calendar-events-token",
             "--profile", str(Path(self.work.name) / "unused-profile")],
            cwd=self.work.name, env=env, capture_output=True, timeout=30, check=False,
        )

    def assert_reads(self, count):
        self.assertEqual(len(self.requests), count)
        self.assertTrue(all(row["method"] == "GET" for row in self.requests))
        self.assertTrue(all(row["authorization"] == "Bearer synthetic-calendar-events-token"
                            for row in self.requests))
        self.assertFalse((Path(self.work.name) / "unused-profile").exists())

    def first_query(self):
        path = urlsplit(self.requests[0]["path"])
        self.assertEqual(path.path, "/api/v1/calendar_events")
        return parse_qs(path.query, keep_blank_values=True)

    def test_filters_and_original_records_survive_native_pagination(self):
        rows = [
            {"id": 7, "title": "Office hours <em>質問</em>", "start_at": None,
             "description": "Literal notes\r\nSecond line", "all_day": False,
             "unknown_field": [None, 0, {"original": "not normalized"}]},
            {"id": 2, "context_code": "user_42", "location_name": "Room A & B"},
        ]
        next_path = "/api/v1/calendar_events?page=2&opaque=a%2Bb%2Fc%26d%3De"
        self.pages = [(200, rows[:1], {"Link": f'<{self.base}{next_path}>; rel="next"'}),
                      (200, rows[1:], {})]
        result = self.run_cli(
            "calendar-events", "--start-date", "2026-10-08T11:20:00+09:00",
            "--end-date", "2026-10-15", "--context-code", "course_7",
            "--context-code", "user_42", "--context-code", "course_7",
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout), rows)
        self.assert_reads(2)
        self.assertEqual(self.first_query(), {
            "start_date": ["2026-10-08T11:20:00+09:00"], "end_date": ["2026-10-15"],
            "context_codes[]": ["course_7", "user_42", "course_7"], "per_page": ["50"],
        })
        self.assertEqual(self.requests[1]["path"], next_path)
        self.assertEqual(self.pages, [])

    def test_defaults_empty_dates_and_literal_context_keep_reader_semantics(self):
        cases = [
            ((), {"per_page": ["50"]}),
            (("--start-date=", "--end-date="), {"per_page": ["50"]}),
            (("--context-code=",), {"context_codes[]": [""], "per_page": ["50"]}),
            (("--context-code", "custom context+value"),
             {"context_codes[]": ["custom context+value"], "per_page": ["50"]}),
        ]
        for args, query in cases:
            with self.subTest(args=args):
                self.requests.clear()
                self.pages = [(200, [], {})]
                result = self.run_cli("calendar-events", *args)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stderr, b"")
                self.assertEqual(json.loads(result.stdout), [])
                self.assert_reads(1)
                self.assertEqual(self.first_query(), query)

    def test_native_failures_never_publish_a_partial_collection(self):
        cases = [
            ([(403, {"error": "synthetic refusal"}, {})], "CanvasAuthError", 1),
            ([(200, [{"id": 4}], {"Link": f'<{self.base}/api/v1/calendar_events?page=2>; rel="next"'}),
              (500, {"error": "synthetic later failure"}, {})], "HTTPStatusError", 2),
        ]
        for pages, error_type, count in cases:
            with self.subTest(error_type=error_type):
                self.requests.clear()
                self.pages = list(pages)
                result = self.run_cli("calendar-events")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b"")
                failure = json.loads(result.stderr)
                self.assertIs(failure["ok"], False)
                self.assertEqual(failure["error"], error_type)
                self.assertIsInstance(failure["message"], str)
                self.assertNotIn(b"synthetic-calendar-events-token", result.stderr)
                self.assert_reads(count)

    def test_help_and_missing_values_do_not_open_a_profile_or_read(self):
        result = self.run_cli("calendar-events", "--help")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        for flag in [b"--start-date", b"--end-date", b"--context-code"]:
            self.assertIn(flag, result.stdout)
        self.assertEqual(result.stderr, b"")
        for arguments in [("--start-date",), ("--end-date",), ("--context-code",), ("--accept",)]:
            with self.subTest(arguments=arguments):
                refused = self.run_cli("calendar-events", *arguments)
                self.assertEqual(refused.returncode, 2)
                self.assertEqual(refused.stdout, b"")
                self.assertIn(b"error:", refused.stderr)
        self.assertEqual(self.requests, [])
        self.assertFalse((Path(self.work.name) / "unused-profile").exists())

    def test_existing_enrollments_command_keeps_its_route_and_default(self):
        rows = [{"id": 5, "enrollment_state": "active"}]
        self.pages = [(200, rows, {})]
        result = self.run_cli("enrollments")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(json.loads(result.stdout), rows)
        self.assert_reads(1)
        path = urlsplit(self.requests[0]["path"])
        self.assertEqual(path.path, "/api/v1/users/self/enrollments")
        self.assertEqual(parse_qs(path.query), {"state[]": ["active"], "per_page": ["50"]})


if __name__ == "__main__":
    unittest.main()
