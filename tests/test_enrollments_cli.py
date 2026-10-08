"""Exercise the native enrollments command against disposable synthetic HTTP pages."""
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


class EnrollmentsCLITests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="canvaspilot-enrollments-cli-")
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
                self.send_error(405, "Synthetic read-only enrollment receiver")

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
             "--base-url", self.base, "--token", "synthetic-enrollments-token",
             "--profile", str(Path(self.work.name) / "unused-profile")],
            cwd=self.work.name, env=env, capture_output=True, timeout=30, check=False,
        )

    def assert_reads(self, count):
        self.assertEqual(len(self.requests), count)
        self.assertTrue(all(row["method"] == "GET" for row in self.requests))
        self.assertTrue(all(row["authorization"] == "Bearer synthetic-enrollments-token"
                            for row in self.requests))
        self.assertFalse((Path(self.work.name) / "unused-profile").exists())

    def test_state_and_all_reported_fields_survive_native_pagination(self):
        rows = [
            {"id": 92, "course_id": 42, "type": "StudentEnrollment", "enrollment_state": "completed",
             "role": "Student", "grades": {"current_score": 0, "final_score": None},
             "future_field": [False, None, {"title": "Literal <b>読書</b>\nSyllabus"}]},
            {"id": 17, "course_id": 77, "enrollment_state": "completed", "role": None,
             "observed_user": {"id": "001", "name": "Synthetic learner"}},
        ]
        next_path = "/api/v1/users/self/enrollments?cursor=opaque%2Fnext&include%5B%5D=observed_users"
        self.pages = [
            (200, rows[:1], {"Link": f'<{self.base}{next_path}>; rel="next"'}),
            (200, rows[1:], {}),
        ]
        result = self.run_cli("enrollments", "--state", "completed")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout), rows)
        self.assert_reads(2)
        first = urlsplit(self.requests[0]["path"])
        self.assertEqual(first.path, "/api/v1/users/self/enrollments")
        self.assertEqual(parse_qs(first.query), {"state[]": ["completed"], "per_page": ["50"]})
        self.assertEqual(self.requests[1]["path"], next_path)
        self.assertEqual(self.pages, [])

    def test_default_empty_and_raw_state_keep_existing_api_semantics(self):
        for arguments, expected in [
            ((), {"state[]": ["active"], "per_page": ["50"]}),
            (("--state", ""), {"per_page": ["50"]}),
            (("--state=",), {"per_page": ["50"]}),
            (("--state", "custom state"), {"state[]": ["custom state"], "per_page": ["50"]}),
        ]:
            with self.subTest(arguments=arguments):
                self.requests.clear()
                self.pages = [(200, [], {})]
                result = self.run_cli("enrollments", *arguments)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stderr, b"")
                self.assertEqual(json.loads(result.stdout), [])
                self.assert_reads(1)
                self.assertEqual(parse_qs(urlsplit(self.requests[0]["path"]).query), expected)

    def test_native_failures_never_print_a_partial_success_collection(self):
        cases = [
            ([(403, {"error": "synthetic refusal"}, {})], "CanvasAuthError", 1),
            ([(200, [{"id": 4}], {"Link": f'<{self.base}/api/v1/users/self/enrollments?page=2>; rel="next"'}),
              (500, {"error": "synthetic later failure"}, {})], "HTTPStatusError", 2),
        ]
        for pages, error_type, count in cases:
            with self.subTest(error_type=error_type):
                self.requests.clear()
                self.pages = list(pages)
                result = self.run_cli("enrollments")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b"")
                failure = json.loads(result.stderr)
                self.assertEqual(failure["ok"], False)
                self.assertEqual(failure["error"], error_type)
                self.assertIsInstance(failure["message"], str)
                self.assert_reads(count)

    def test_help_and_invalid_options_finish_without_reading_or_opening_a_profile(self):
        result = self.run_cli("enrollments", "--help")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b"--state", result.stdout)
        self.assertIn(b"active", result.stdout)
        self.assertEqual(result.stderr, b"")
        for arguments in [("--state",), ("--accept",)]:
            with self.subTest(arguments=arguments):
                refused = self.run_cli("enrollments", *arguments)
                self.assertEqual(refused.returncode, 2)
                self.assertEqual(refused.stdout, b"")
                self.assertIn(b"error:", refused.stderr)
        self.assertEqual(self.requests, [])
        self.assertFalse((Path(self.work.name) / "unused-profile").exists())

    def test_unrelated_identity_command_keeps_its_existing_route(self):
        profile = {"id": 42, "name": "Synthetic enrollment reader"}
        self.pages = [(200, profile, {})]
        result = self.run_cli("whoami")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(json.loads(result.stdout), {"mode": "token", "base_url": self.base, "profile": profile})
        self.assert_reads(1)
        self.assertEqual(urlsplit(self.requests[0]["path"]).path, "/api/v1/users/self/profile")


if __name__ == "__main__":
    unittest.main()
