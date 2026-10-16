"""Classic-quiz discovery through retained source and the actual terminal path."""

from __future__ import annotations

import copy
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from canvaspilot import cli
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.quiz_search import (
    search_quizzes,
    serialize_quiz_search,
    validate_selection,
)


class Collection:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get_paginated(self, path):
        self.calls.append(path)
        value = self.routes[path]
        if isinstance(value, Exception):
            raise value
        return value


@contextmanager
def endpoint(respond):
    requests = []
    errors = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append({
                "method": "GET", "path": self.path,
                "authorization": self.headers.get("Authorization"),
            })
            try:
                status, body, headers = respond(self.path)
                data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)
            except Exception as error:  # noqa: BLE001 - relay server-thread failures to the test.
                errors.append(error)
                self.send_error(500)

        def do_POST(self):
            requests.append({"method": "POST", "path": self.path})
            self.send_error(405)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        if errors:
            raise errors[0]


class QuizSearchTests(unittest.TestCase):
    def test_occurrences_remain_distinct_across_repeated_courses_and_ids(self):
        rows = [
            {"id": 11, "title": "Practice", "description": "<p>Die Straße</p>"},
            {"id": 11, "title": "STRASSE check", "description": None},
        ]
        other = [{"id": 11, "title": "Other", "description": "Straße", "course_id": "0007"}]
        client = Collection({
            "/api/v1/courses/42/quizzes": rows,
            "/api/v1/courses/7/quizzes": other,
        })
        original = copy.deepcopy(client.routes)
        result = search_quizzes(client, ["0042", 7, "42"], "strasse")
        self.assertEqual(result["quiz_count"], 5)
        self.assertEqual(result["matched_count"], 5)
        self.assertEqual([
            (item["selection_number"], item["course_id"], item["quiz_position"])
            for item in result["matches"]
        ], [(1, "42", 1), (1, "42", 2), (2, "7", 1), (3, "42", 1), (3, "42", 2)])
        self.assertEqual(result["matches"][0]["matched_fields"], ["description_text"])
        self.assertEqual(result["matches"][1]["matched_fields"], ["title"])
        self.assertEqual(client.calls, [
            "/api/v1/courses/42/quizzes", "/api/v1/courses/7/quizzes", "/api/v1/courses/42/quizzes",
        ])
        self.assertEqual(client.routes, original)

    def test_full_descriptions_and_literal_field_matching(self):
        raw = "<p>" + "context " * 100 + "日本語 &amp; evidence <b>alpha</b></p>"
        rows = [{"id": 9, "title": "<C++> notes", "description": raw}]
        client = Collection({"/api/v1/courses/42/quizzes": rows})
        result = search_quizzes(client, [42], "日本語 & evidence")
        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["matches"][0]["description_html"], raw)
        self.assertTrue(result["matches"][0]["description_text"].endswith("日本語 & evidence alpha"))
        self.assertGreater(len(result["matches"][0]["description_text"]), 800)
        self.assertEqual(search_quizzes(client, [42], "<c++>")["matched_count"], 1)
        self.assertEqual(search_quizzes(client, [42], ".*")["matched_count"], 0)
        self.assertEqual(search_quizzes(client, [42], "notes context")["matched_count"], 0)
        self.assertEqual(search_quizzes(client, [42], " 日本語 ")["query"], " 日本語 ")

    def test_missing_null_empty_and_markup_only_are_observed_separately(self):
        rows = [{"id": index, "title": "match"} for index in range(1, 6)]
        for row, raw in zip(rows[1:], [None, "", "<p> \n </p>", "Text"], strict=True):
            row["description"] = raw
        result = search_quizzes(Collection({"/api/v1/courses/42/quizzes": rows}), [42], "match")
        self.assertEqual(result["description_counts"], {
            "missing": 1, "null": 1, "empty": 1, "no_text": 1, "text": 1,
        })
        self.assertEqual([m["description_state"] for m in result["matches"]],
                         ["missing", "null", "empty", "no_text", "text"])
        self.assertEqual([m["description_text"] for m in result["matches"]],
                         [None, None, "", "", "Text"])

    def test_metadata_is_detached_and_unselected_fields_are_not_published(self):
        row = {
            "id": "009", "title": "match", "description": "Match", "published": False,
            "question_count": 0, "points_possible": 0, "due_at": None,
            "unlock_at": "2026-11-01T01:30:00-04:00", "locked_for_user": True,
            "access_code": "fictional-not-for-output", "unknown_future_field": {"x": [1]},
        }
        client = Collection({"/api/v1/courses/42/quizzes": [row]})
        result = search_quizzes(client, [42], "match")
        match = result["matches"][0]
        self.assertEqual(match["matched_fields"], ["title", "description_text"])
        self.assertEqual(match["quiz"]["id"], "009")
        self.assertIs(match["quiz"]["published"], False)
        self.assertEqual(match["quiz"]["points_possible"], 0)
        self.assertIsNone(match["quiz"]["due_at"])
        self.assertTrue(match["quiz"]["locked_for_user"])
        self.assertNotIn("fictional-not-for-output", serialize_quiz_search(result))
        self.assertNotIn("unknown_future_field", match["quiz"])
        row["title"] = "changed later"
        self.assertEqual(match["quiz"]["title"], "match")

    def test_all_rows_are_admitted_even_when_they_do_not_match(self):
        invalid = [None, {}, {"id": False}, {"id": 0}, {"id": 2, "title": []},
                   {"id": 2, "description": 3}, {"id": 2, "course_id": 7}]
        for bad in invalid:
            with self.subTest(bad=bad):
                rows = [{"id": 1, "title": "needle"}, bad]
                with self.assertRaises(ValueError):
                    search_quizzes(Collection({"/api/v1/courses/42/quizzes": rows}), [42], "needle")

    def test_empty_collection_and_native_list_projection_are_preserved(self):
        client = CanvasClient(fixture={"routes": {"GET /api/v1/courses/42/quizzes": []}})
        result = search_quizzes(client, [42], "nothing")
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["quiz_count"], 0)
        self.assertEqual(result["selections"], [{
            "selection_number": 1, "course_id": "42", "quiz_count": 0, "matched_count": 0,
        }])
        row = {"id": 8, "title": "Practice", "description": "full text"}
        client.fixture["routes"]["GET /api/v1/courses/42/quizzes"] = [row]
        self.assertEqual(set(CanvasAPI(client).list_quizzes(42)[0]), {
            "id", "title", "due_at", "lock_at", "question_count", "points_possible",
            "published", "quiz_type", "html_url",
        })
        client.close()

    def test_selection_and_query_fail_before_client_construction(self):
        invalid = [([], "x"), ([42] * 11, "x"), ([True], "x"), (["٤٢"], "x"),
                   (["+42"], "x"), (["0"], "x"), (["1" * 21], "x"),
                   ([42], " \t"), ([42], "日" * 171), ([42], None)]
        for courses, query in invalid:
            with self.subTest(courses=courses, query=query):
                client = Collection({})
                with self.assertRaises(ValueError):
                    search_quizzes(client, courses, query)
                self.assertEqual(client.calls, [])
        self.assertEqual(validate_selection(["0" * 19 + "1"], "x" * 512), (["1"], "x" * 512))
        with patch("canvaspilot.client.CanvasClient") as constructor:
            stderr = io.StringIO()
            with redirect_stderr(stderr), self.assertRaises(SystemExit) as stopped:
                cli.main(["find-quizzes", "42", "--text", " "])
            self.assertEqual(stopped.exception.code, 2)
            self.assertFalse(json.loads(stderr.getvalue())["ok"])
            constructor.assert_not_called()

    def test_record_decoded_byte_and_output_bounds(self):
        rows = [{"id": index, "title": "none"} for index in range(1, 1001)]
        client = Collection({"/api/v1/courses/42/quizzes": rows})
        self.assertEqual(search_quizzes(client, [42], "match")["quiz_count"], 1000)
        rows.append({"id": 1001})
        with self.assertRaisesRegex(ValueError, "1000"):
            search_quizzes(client, [42], "match")
        small = [{"id": 1, "title": "match", "description": "日本語"}]
        client.routes["/api/v1/courses/42/quizzes"] = small
        with (patch("canvaspilot.quiz_search.MAX_INPUT_BYTES", 1),
              self.assertRaisesRegex(ValueError, "decoded JSON")):
            search_quizzes(client, [42], "match")
        report = search_quizzes(client, [42], "match")
        with (patch("canvaspilot.quiz_search.MAX_OUTPUT_BYTES", 1),
              self.assertRaisesRegex(ValueError, "output JSON")):
            serialize_quiz_search(report)
        small[0]["points_possible"] = float("nan")
        with self.assertRaises(ValueError):
            search_quizzes(client, [42], "match")

    def test_client_close_and_logger_restore_after_later_failure(self):
        logger = logging.getLogger("httpx")
        previous = logger.level
        client = Collection({
            "/api/v1/courses/42/quizzes": [{"id": 1, "title": "needle"}],
            "/api/v1/courses/7/quizzes": ValueError("later read failed"),
        })
        with patch("canvaspilot.client.CanvasClient", return_value=client), patch.object(
            client, "close", create=True,
        ) as close:
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as stopped:
                cli.main(["find-quizzes", "42", "7", "--text", "needle"])
            self.assertEqual(stopped.exception.code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(json.loads(stderr.getvalue())["message"], "later read failed")
            close.assert_called_once_with()
        self.assertEqual(logger.level, previous)


class QuizSearchCliTests(unittest.TestCase):
    def run_cli(self, base, *args):
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("CANVAS_")
            and key.lower() not in {"http_proxy", "https_proxy", "all_proxy"}
        }
        env.update({
            "PYTHONPATH": os.pathsep.join(filter(None, [
                str(Path(cli.__file__).resolve().parents[1]), os.environ.get("PYTHONPATH", ""),
            ])),
            "PYTHONDONTWRITEBYTECODE": "1",
            "CANVAS_API_TOKEN": "synthetic-quiz-search-only",
            "NO_PROXY": "127.0.0.1,localhost",
        })
        with tempfile.TemporaryDirectory(prefix="canvas-quiz-search-") as scratch:
            profile = Path(scratch) / "unused-profile"
            completed = subprocess.run(
                [sys.executable, "-B", "-m", "canvaspilot.cli", *args,
                 "--base-url", base, "--profile", str(profile)],
                cwd=scratch, env=env, capture_output=True, text=True, timeout=20, check=False,
            )
            self.assertFalse(profile.exists())
        return completed

    def test_real_cli_reads_later_descriptions_without_a_title_filter(self):
        def respond(path):
            route = urlsplit(path)
            self.assertEqual(route.path, "/api/v1/courses/42/quizzes")
            if parse_qs(route.query).get("page") == ["2"]:
                self.assertEqual(route.query, "page=2&cursor=A%2BB")
                return 200, [{"id": 8, "title": "Later", "description": "<p>日本語 &amp; evidence</p>"}], {}
            self.assertEqual(parse_qs(route.query), {"per_page": ["50"]})
            return 200, [{"id": 7, "title": "Other", "description": None}], {
                "Link": '</api/v1/courses/42/quizzes?page=2&cursor=A%2BB>; rel="next"',
            }

        with endpoint(respond) as (base, requests):
            result = self.run_cli(base, "find-quizzes", "0042", "--text", "日本語 & EVIDENCE")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(report["quiz_count"], 2)
        self.assertEqual(report["matched_count"], 1)
        self.assertEqual(report["matches"][0]["quiz"]["id"], 8)
        self.assertEqual(report["matches"][0]["quiz_position"], 2)
        self.assertEqual([item["method"] for item in requests], ["GET", "GET"])
        self.assertEqual({item["authorization"] for item in requests}, {"Bearer synthetic-quiz-search-only"})

    def test_later_page_failure_has_no_partial_success(self):
        def respond(path):
            if parse_qs(urlsplit(path).query).get("page") == ["2"]:
                return 200, {"error": "not a list"}, {}
            return 200, [{"id": 7, "title": "match"}], {
                "Link": '</api/v1/courses/42/quizzes?page=2>; rel="next"',
            }

        with endpoint(respond) as (base, requests):
            result = self.run_cli(base, "find-quizzes", "42", "--text", "match")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(result.stderr)["error"], "CanvasPaginationError")
        self.assertEqual(len(requests), 2)

    def test_auth_failure_and_invalid_selection_do_not_publish_a_report(self):
        with endpoint(lambda _path: (403, {"error": "forbidden"}, {})) as (base, requests):
            result = self.run_cli(base, "find-quizzes", "42", "--text", "match")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertEqual(json.loads(result.stderr)["error"], "CanvasAuthError")
            self.assertEqual(len(requests), 1)
            result = self.run_cli(base, "find-quizzes", "0", "--text", "match")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertEqual(len(requests), 1)

    def test_deep_selected_metadata_has_a_json_error_and_unselected_metadata_succeeds(self):
        nested = b"[" * 600 + b"0" + b"]" * 600
        for field in ("points_possible", "unknown_future_field"):
            with self.subTest(field=field):
                body = (b'[{"id":1,"title":"needle","' + field.encode("ascii")
                        + b'":' + nested + b"}]")
                with endpoint(lambda _path, body=body: (200, body, {})) as (base, requests):
                    result = self.run_cli(base, "find-quizzes", "42", "--text", "needle")
                self.assertEqual(len(requests), 1)
                self.assertEqual(requests[0]["method"], "GET")
                if field == "points_possible":
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    error = json.loads(result.stderr)
                    self.assertFalse(error["ok"])
                    self.assertEqual(error["error"], "RecursionError")
                    self.assertLess(len(result.stderr), 2048)
                    self.assertNotIn("Traceback", result.stderr)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    report = json.loads(result.stdout)
                    self.assertEqual(report["matched_count"], 1)
                    self.assertNotIn(field, report["matches"][0]["quiz"])


if __name__ == "__main__":
    unittest.main()
