"""Real CLI/HTTP controls at the inherited announcement pagination boundary."""
from __future__ import annotations

import io
import json
import os
import threading
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from canvaspilot.cli import main


@contextmanager
def forty_page_server(*, has_more: bool):
    """Serve 40 matching rows, optionally advertising one unread final page."""
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            page = int(query.get("page", ["1"])[0])
            requests.append({"path": parsed.path, "query": query, "page": page})
            if parsed.path != "/api/v1/announcements" or not 1 <= page <= 40:
                self.send_error(404)
                return
            # Retain deliberate duplicate IDs across pages: completion is not
            # equivalent to finding one matching ID or de-duplicating results.
            row = {
                "id": 0,
                "title": f"Needle page {page}",
                "message": f"<p>Complete body {page}</p>",
                "context_code": "course_42" if page % 2 else "course_77",
                "posted_at": None,
                "html_url": None,
            }
            body = json.dumps([row]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            if page < 40 or has_more:
                self.send_header(
                    "Link",
                    f'<http://127.0.0.1:{self.server.server_port}'
                    f'/api/v1/announcements?page={page + 1}>; rel="next"',
                )
            self.end_headers()
            self.wfile.write(body)

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


class AnnouncementSearchPageBoundaryTests(unittest.TestCase):
    def receive(self, *, has_more):
        env = {
            key: value for key, value in os.environ.items()
            if not key.lower().endswith("_proxy") and not key.startswith("CANVAS_")
        }
        with (
            TemporaryDirectory(prefix="announcement-page-boundary-") as temporary,
            forty_page_server(has_more=has_more) as (base, requests),
            patch.dict(os.environ, env, clear=True),
            redirect_stdout(io.StringIO()) as out,
            redirect_stderr(io.StringIO()) as err,
        ):
            profile = Path(temporary) / "unused-profile"
            status = 0
            try:
                main([
                    "find-announcements", "42", "77", "--text", "needle",
                    "--base-url", base, "--token", "synthetic-boundary-token",
                    "--profile", str(profile),
                ])
            except SystemExit as exit_:
                status = exit_.code
            self.assertFalse(profile.exists())
        return status, out.getvalue(), err.getvalue(), requests

    def assert_complete_traversal(self, requests):
        self.assertEqual([row["page"] for row in requests], list(range(1, 41)))
        self.assertTrue(all(row["path"] == "/api/v1/announcements" for row in requests))
        self.assertEqual(requests[0]["query"], {
            "active_only": ["true"],
            "per_page": ["50"],
            "context_codes[]": ["course_42", "course_77"],
        })
        self.assertEqual(requests[-1]["query"], {"page": ["40"]})

    def test_exactly_forty_complete_pages_preserve_all_matching_rows(self):
        status, stdout, stderr, requests = self.receive(has_more=False)
        self.assertEqual(status, 0, stderr)
        self.assertEqual(stderr, "")
        self.assert_complete_traversal(requests)
        self.assertEqual(json.loads(stdout), {
            "course_ids": [42, 77],
            "start_date": None,
            "query": "needle",
            "match_mode": "literal_casefold",
            "announcements_returned": 40,
            "announcements_matched": 40,
            "matches": [{
                "matched_fields": ["title"],
                "announcement": {
                    "id": 0,
                    "title": f"Needle page {page}",
                    "message_text": f"Complete body {page}",
                    "context_code": "course_42" if page % 2 else "course_77",
                    "posted_at": None,
                    "html_url": None,
                },
            } for page in range(1, 41)],
        })

    def test_forty_matching_pages_with_a_continuation_refuse_partial_success(self):
        status, stdout, stderr, requests = self.receive(has_more=True)
        self.assertEqual(status, 1, stderr)
        self.assertEqual(stdout, "")
        self.assert_complete_traversal(requests)
        failure = json.loads(stderr)
        self.assertEqual(set(failure), {"ok", "error", "message"})
        self.assertIs(failure["ok"], False)
        self.assertEqual(failure["error"], "CanvasPaginationError")
        self.assertIsInstance(failure["message"], str)
        self.assertTrue(failure["message"])
