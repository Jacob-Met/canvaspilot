"""Actual CLI and loopback HTTP controls for announcement text search."""
from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import sys
import threading
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4

import canvaspilot
from canvaspilot.cli import main

TOKEN = "synthetic-announcement-search-token"
FULL_BODY = "Ordinary context " * 40 + "Room change to Ω-204. Read & compare."
SOURCE_ROOT = str(Path(canvaspilot.__file__).parent.parent)
RECEIVING_CALLS = []
ROWS = [
    {
        "id": 7, "title": "Meeting details", "message": "<p>" + FULL_BODY.replace("&", "&amp;") + "</p>",
        "posted_at": "2026-10-08T12:00:00Z", "context_code": "course_42",
        "html_url": "https://canvas.invalid/courses/42/discussion_topics/7",
    },
    {
        "id": 7, "title": "ROOM CHANGE", "message": "<p>Straße meeting.</p>",
        "posted_at": None, "context_code": "course_77", "html_url": None,
    },
    {
        "id": 0, "title": None, "message": None,
        "posted_at": None, "context_code": "course_42", "html_url": None,
    },
]


def expected_rows():
    return [
        {key: value for key, value in ROWS[0].items() if key != "message"}
        | {"message_text": FULL_BODY},
        {key: value for key, value in ROWS[1].items() if key != "message"}
        | {"message_text": "Straße meeting."},
        {key: value for key, value in ROWS[2].items() if key != "message"}
        | {"message_text": ""},
    ]


@contextmanager
def canvas_server(mode="ok", rows=None):
    rows = deepcopy(ROWS if rows is None else rows)
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            parts = urlsplit(self.path)
            query = parse_qsl(parts.query, keep_blank_values=True)
            requests.append({
                "method": "GET", "path": parts.path, "query": query,
                "authorization": self.headers.get("Authorization"),
            })
            if parts.path != "/api/v1/announcements":
                self.send_error(404)
                return
            later = any(key == "cursor" for key, _ in query)
            if mode == "unauthorized":
                self.send_error(401)
                return
            if mode == "unavailable" or (mode == "late-failure" and later):
                self.send_error(503)
                return
            body = rows[1:] if later else rows[:1]
            if mode == "empty":
                body = []
            elif mode == "late-object" and later:
                body = {"id": 999, "title": "room change"}
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            if mode != "empty" and len(rows) > 1 and not later:
                self.send_header(
                    "Link",
                    f'<http://127.0.0.1:{self.server.server_port}'
                    '/api/v1/announcements?cursor=opaque%2Bnext>; rel="next"',
                )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(
        target=lambda: server.serve_forever(poll_interval=0.01), daemon=True,
    )
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def clean_environment():
    env = dict(os.environ)
    for key in list(env):
        if key.lower().endswith("_proxy") or key.startswith("CANVAS_"):
            env.pop(key, None)
    env.update({
        "PYTHONPATH": SOURCE_ROOT,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "CANVAS_SESSION_PORT": "1",
    })
    return env


def invoke(base, *args, ascii_console=False):
    profile = Path("/tmp") / f"canvaspilot-search-test-{uuid4().hex}"
    if os.path.lexists(profile):
        raise RuntimeError("fixture profile must start absent")
    env = clean_environment()
    if ascii_console:
        env["PYTHONIOENCODING"] = "ascii:strict"
    command = [
        sys.executable, "-B", "-m", "canvaspilot.cli", *args,
        "--base-url", base, "--token", TOKEN, "--profile", str(profile),
    ]
    result = subprocess.run(
        command, env=env, capture_output=True, text=True, timeout=15, check=False,
    )
    RECEIVING_CALLS.append({
        "args": list(args), "returncode": result.returncode,
        "stdout": result.stdout, "stderr": result.stderr,
        "profile_absent": not os.path.lexists(profile),
    })
    if os.path.lexists(profile):
        raise AssertionError("read-only search created a profile")
    return result


class AnnouncementSearchCLITests(unittest.TestCase):
    def report(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_complete_body_matching_and_exact_pagination_filters(self):
        with canvas_server() as (base, requests):
            result = invoke(
                base, "find-announcements", "77", "42", "--text", "room change",
                "--start-date", "2026-10-01T00:00:00Z", ascii_console=True,
            )
        report = self.report(result)
        normalized = expected_rows()
        self.assertEqual(report, {
            "query": "room change", "match_mode": "literal_casefold",
            "course_ids": [77, 42], "start_date": "2026-10-01T00:00:00Z",
            "announcements_returned": 3, "announcements_matched": 2,
            "matches": [
                {"matched_fields": ["message_text"], "announcement": normalized[0]},
                {"matched_fields": ["title"], "announcement": normalized[1]},
            ],
        })
        self.assertGreater(normalized[0]["message_text"].index("Room change"), 400)
        self.assertEqual(requests[0]["query"], [
            ("active_only", "true"), ("per_page", "50"),
            ("context_codes[]", "course_77"), ("context_codes[]", "course_42"),
            ("start_date", "2026-10-01T00:00:00Z"),
        ])
        self.assertEqual(requests[1]["query"], [("cursor", "opaque+next")])
        self.assertEqual(len(requests), 2)
        self.assertTrue(all(r["authorization"] == f"Bearer {TOKEN}" for r in requests))

    def test_unicode_expansion_and_both_fields_preserve_row_values(self):
        rows = [
            {"id": 0, "title": "Straße", "message": "<p>STRASSE &amp; ος.</p>",
             "context_code": "course_42", "posted_at": None, "html_url": None},
            {"id": 0, "title": 0, "message": "<p>strasse</p>",
             "context_code": "course_77", "posted_at": 0, "html_url": ""},
        ]
        with canvas_server(rows=rows) as (base, requests):
            report = self.report(invoke(
                base, "find-announcements", "42", "42", "--text", "STRASSE",
                ascii_console=True,
            ))
        self.assertEqual(report["course_ids"], [42, 42])
        self.assertIsNone(report["start_date"])
        self.assertEqual(report["announcements_returned"], 2)
        self.assertEqual(report["announcements_matched"], 2)
        self.assertEqual(report["matches"], [
            {"matched_fields": ["title", "message_text"], "announcement": {
                "id": 0, "title": "Straße", "message_text": "STRASSE & ος.",
                "context_code": "course_42", "posted_at": None, "html_url": None,
            }},
            {"matched_fields": ["message_text"], "announcement": {
                "id": 0, "title": 0, "message_text": "strasse",
                "context_code": "course_77", "posted_at": 0, "html_url": "",
            }},
        ])
        self.assertEqual(
            [value for key, value in requests[0]["query"] if key == "context_codes[]"],
            ["course_42", "course_42"],
        )
        self.assertFalse(any(key == "start_date" for key, _ in requests[0]["query"]))

    def test_literal_and_whitespace_queries_use_existing_cleaned_message(self):
        rows = [
            {"id": 1, "title": "xxxx", "message": "No phrase"},
            {"id": 2, "title": None, "message": "<p>Use  [x]+.*  in this room today.</p>"},
        ]
        for query in ["[x]+.*", " room "]:
            with self.subTest(query=query):
                with canvas_server(rows=rows) as (base, _):
                    report = self.report(invoke(
                        base, "find-announcements", "42", "--text", query,
                    ))
                self.assertEqual(report["query"], query)
                self.assertEqual(report["announcements_matched"], 1)
                match = report["matches"][0]
                self.assertEqual(match["matched_fields"], ["message_text"])
                self.assertEqual(match["announcement"]["id"], 2)
                self.assertEqual(
                    match["announcement"]["message_text"], "Use [x]+.* in this room today.",
                )

    def test_cross_field_and_unicode_normalization_are_not_invented(self):
        rows = [{"id": 1, "title": "Room", "message": "change Cafe\u0301"}]
        for query in ["room change", "café"]:
            with self.subTest(query=query):
                with canvas_server(rows=rows) as (base, _):
                    report = self.report(invoke(
                        base, "find-announcements", "42", "--text", query,
                    ))
                self.assertEqual(report["announcements_returned"], 1)
                self.assertEqual(report["announcements_matched"], 0)
                self.assertEqual(report["matches"], [])

    def test_empty_collection_and_no_matches_have_distinct_counts(self):
        for mode, returned in [("empty", 0), ("ok", 3)]:
            with self.subTest(mode=mode):
                with canvas_server(mode) as (base, requests):
                    report = self.report(invoke(
                        base, "find-announcements", "42", "--text", "absent phrase",
                    ))
                self.assertEqual(report["announcements_returned"], returned)
                self.assertEqual(report["announcements_matched"], 0)
                self.assertEqual(report["matches"], [])
                self.assertEqual(len(requests), 1 if mode == "empty" else 2)

    def test_argument_refusal_precedes_any_http_request(self):
        cases = [
            (["42"], "--text"),
            (["--text", "query"], "course_ids"),
            (["42", "--text"], "expected one argument"),
            (["42", "--text", ""], "non-whitespace"),
            (["42", "--text", " \t\n"], "non-whitespace"),
            (["42", "--text", "\u2003"], "non-whitespace"),
            (["0", "--text", "query"], "positive integer"),
            (["42", "-1", "--text", "query"], "positive integer"),
            (["1.5", "--text", "query"], "positive integer"),
        ]
        with canvas_server() as (base, requests):
            for args, message in cases:
                with self.subTest(args=args):
                    result = invoke(base, "find-announcements", *args)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(message, result.stderr)
                    self.assertEqual(requests, [])

    def test_blank_query_refusal_precedes_default_profile_and_client_setup(self):
        with (
            patch(
                "canvaspilot.client.default_profile",
                side_effect=AssertionError("default profile must not be consulted"),
            ) as profile,
            patch(
                "canvaspilot.client.CanvasClient",
                side_effect=AssertionError("client must not be constructed"),
            ) as client,
            redirect_stdout(io.StringIO()) as out,
            redirect_stderr(io.StringIO()) as err,
            self.assertRaises(SystemExit) as refused,
        ):
            main(["find-announcements", "42", "--text", " \t "])
        self.assertEqual(refused.exception.code, 2)
        self.assertIn("non-whitespace", err.getvalue())
        self.assertEqual(out.getvalue(), "")
        profile.assert_not_called()
        client.assert_not_called()

    def test_native_read_errors_never_emit_partial_search_results(self):
        cases = [
            ("unauthorized", 1, "CanvasAuthError"),
            ("unavailable", 1, "HTTPStatusError"),
            ("late-failure", 2, "HTTPStatusError"),
            ("late-object", 2, "CanvasPaginationError"),
        ]
        for mode, count, error_name in cases:
            with self.subTest(mode=mode):
                with canvas_server(mode) as (base, requests):
                    result = invoke(base, "find-announcements", "42", "77", "--text", "room change")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                error = json.loads(result.stderr)
                self.assertIs(error["ok"], False)
                self.assertEqual(error["error"], error_name)
                self.assertTrue(error["message"])
                self.assertEqual(len(requests), count)

    def test_httpx_logger_level_is_restored_after_success_and_failure(self):
        logger = logging.getLogger("httpx")
        original_level = logger.level
        try:
            for mode, status in [("ok", 0), ("late-failure", 1)]:
                for level in [logging.NOTSET, logging.DEBUG, logging.ERROR]:
                    with self.subTest(mode=mode, level=level):
                        logger.setLevel(level)
                        with canvas_server(mode) as (base, requests), patch.dict(
                            os.environ, clean_environment(), clear=True,
                        ), redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
                            args = [
                                "find-announcements", "42", "--text", "room change",
                                "--base-url", base, "--token", TOKEN,
                                "--profile", f"/tmp/canvaspilot-search-test-{uuid4().hex}",
                            ]
                            if status:
                                with self.assertRaises(SystemExit) as refused:
                                    main(args)
                                self.assertEqual(refused.exception.code, status)
                                self.assertEqual(out.getvalue(), "")
                                self.assertEqual(json.loads(err.getvalue())["error"], "HTTPStatusError")
                            else:
                                main(args)
                                self.assertEqual(json.loads(out.getvalue())["announcements_matched"], 2)
                                self.assertEqual(err.getvalue(), "")
                        self.assertEqual(logger.level, level)
                        self.assertEqual(len(requests), 2)
        finally:
            logger.setLevel(original_level)


if __name__ == "__main__":
    unittest.main()
