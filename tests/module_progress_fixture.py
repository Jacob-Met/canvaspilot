"""Disposable authored Canvas responses for module-progress receiving."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


def course_fixture():
    return {"routes": {
        "GET /api/v1/courses/42/modules": [
            {"id": 7, "name": "Foundations", "position": 1, "state": "started",
             "requirement_type": "all", "require_sequential_progress": True,
             "prerequisite_module_ids": [], "items_count": 3},
            {"id": 8, "name": "Choose one topic", "position": 2, "state": "completed",
             "requirement_type": "one", "require_sequential_progress": False,
             "prerequisite_module_ids": [], "items_count": 2, "items": [
                 {"id": 81, "module_id": 8, "title": "Topic A", "type": "Page",
                  "completion_requirement": {"type": "must_view", "completed": True}},
                 {"id": 82, "module_id": 8, "title": "Topic B", "type": "Page",
                  "completion_requirement": {"type": "must_view", "completed": False}},
             ]},
            {"id": 9, "name": "Later work", "position": 3, "state": "locked",
             "requirement_type": "all", "require_sequential_progress": False,
             "prerequisite_module_ids": [7], "unlock_at": "2026-10-10T10:00:00Z",
             "items_count": 1, "items": [
                 {"id": 91, "module_id": 9, "title": "Final draft", "type": "Assignment",
                  "completion_requirement": {"type": "must_submit", "completed": False}},
             ]},
            {"id": 10, "name": "Progress unavailable", "position": 4, "items_count": 2, "items": [
                {"id": 101, "module_id": 10, "title": "Readiness check", "type": "Quiz",
                 "completion_requirement": {"type": "min_percentage", "min_percentage": 70}},
                {"id": 102, "module_id": 10, "title": "Future requirement", "type": "Page",
                 "completion_requirement": {"type": "future_rule", "completed": True}},
            ]},
        ],
        "GET /api/v1/courses/42/modules/7/items": [
            {"id": 71, "module_id": 7, "title": "Read Café notes", "type": "Page", "position": 1,
             "html_url": "https://canvas.invalid/courses/42/modules/items/71",
             "completion_requirement": {"type": "must_view", "completed": True}},
            {"id": 72, "module_id": 7, "title": "Preparation quiz", "type": "Quiz", "position": 2,
             "html_url": "https://canvas.invalid/courses/42/modules/items/72",
             "completion_requirement": {"type": "min_score", "min_score": 8, "completed": False}},
            {"id": 73, "module_id": 7, "title": "Additional material", "type": "ExternalUrl",
             "position": 3},
        ],
    }}


class ModuleProgressHTTPFixture:
    """Real loopback HTTP with a short first page and explicit Link continuation."""

    def __init__(self):
        self.fixture = course_fixture()
        self.requests = []
        self.overrides = {}
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)
                owner.requests.append({"method": "GET", "path": parsed.path, "query": query})
                status, body, headers = owner.response(parsed.path, query)
                encoded = json.dumps(body, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(encoded)

            def do_POST(self):
                owner.requests.append({"method": "POST", "path": self.path})
                self.send_error(405)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def response(self, path, query):
        page = query.get("page", ["1"])[0]
        if (path, page) in self.overrides:
            return deepcopy(self.overrides[(path, page)])
        if "GET " + path not in self.fixture["routes"]:
            return 404, {"error": "unknown synthetic route"}, {}
        rows = self.fixture["routes"]["GET " + path]
        boundary = 2
        if not isinstance(rows, list) or len(rows) <= boundary:
            return 200, deepcopy(rows), {}
        if page == "2":
            return 200, deepcopy(rows[boundary:]), {}
        return 200, deepcopy(rows[:boundary]), {
            "Link": f'<{self.base_url}{path}?page=2>; rel="next"',
        }

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
