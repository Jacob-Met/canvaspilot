"""Authored current-user grade data and a bounded loopback Canvas response fixture."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


def grade_fixture():
    return {
        "profile": {"id": 7, "name": "Synthetic Learner"},
        "course": {
            "id": 42, "name": "Synthetic Linear Algebra", "course_code": "FIX-MATH",
            "hide_final_grades": False, "apply_assignment_group_weights": True,
            "has_grading_periods": True, "has_weighted_grading_periods": False,
            "enrollments": [{
                "type": "student", "role": "StudentEnrollment", "user_id": 7,
                "enrollment_state": "active", "computed_current_score": 0,
                "computed_final_score": 0, "computed_current_grade": None,
                "computed_final_grade": None, "unposted_current_score": 99,
                "current_grading_period_id": 5, "current_grading_period_title": "Autumn",
                "current_period_computed_current_score": 12.5,
                "current_period_computed_final_score": None,
                "totals_for_all_grading_periods_option": False,
            }],
            "grading_periods": [{"id": 5, "title": "Autumn", "start_date": "2026-09-01"}],
        },
        "groups": [
            {
                "id": 3, "name": "Problem sets", "position": 1, "group_weight": 40,
                "rules": {"drop_lowest": 1, "drop_highest": 0, "never_drop": [102]},
                "assignments": [
                    {
                        "id": 101, "course_id": 42, "assignment_group_id": 3,
                        "name": "Vector spaces", "points_possible": 20, "due_at": None,
                        "grading_type": "points", "submission_types": ["online_upload"],
                        "html_url": "https://school.invalid/courses/42/assignments/101",
                        "submission": {
                            "id": 801, "assignment_id": 101, "user_id": 7,
                            "grade": "0", "score": 0, "entered_score": 1,
                            "points_deducted": 1, "posted_at": "2026-10-01T09:00:00Z",
                            "workflow_state": "graded", "attempt": 1, "excused": False,
                            "missing": False, "late": True, "assignment_visible": True,
                            "grade_matches_current_submission": True,
                        },
                    },
                    {
                        "id": 102, "course_id": 42, "assignment_group_id": 3,
                        "name": "Excused lab", "points_possible": 0,
                        "submission": {
                            "assignment_id": 102, "user_id": 7, "excused": True,
                            "score": None, "grade": None, "posted_at": None,
                        },
                    },
                    {
                        "id": 103, "course_id": 42, "assignment_group_id": 3,
                        "name": "Revised proof", "points_possible": 100,
                        "submission": {
                            "assignment_id": 103, "user_id": 7, "attempt": 2,
                            "grade": "B", "score": 85, "posted_at": "2026-10-02T09:00:00Z",
                            "workflow_state": "submitted", "grade_matches_current_submission": False,
                        },
                    },
                ],
            },
            {
                "id": 4, "name": "Exams", "position": 2, "group_weight": 60,
                "rules": None,
                "assignments": [{
                    "id": 201, "course_id": 42, "assignment_group_id": 4,
                    "name": "Future exam", "points_possible": 100,
                    "due_at": "2026-12-01T12:00:00Z",
                }],
            },
        ],
    }


class GradeReviewHTTPFixture:
    """Actual HTTP; only terminal provider responses are synthetic."""

    def __init__(self):
        self.data = grade_fixture()
        self.requests = []
        self.overrides = {}
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parts = urlsplit(self.path)
                query = parse_qs(parts.query)
                owner.requests.append({"method": "GET", "path": parts.path, "query": query})
                if self.headers.get("Authorization") != "Bearer grade-review-synthetic-token":
                    status, body, headers = 401, {"error": "fixture token required"}, {}
                elif (parts.path, query.get("cursor", [""])[0]) in owner.overrides:
                    status, body, headers = owner.overrides[(parts.path, query.get("cursor", [""])[0])]
                elif parts.path == "/api/v1/users/self/profile":
                    status, body, headers = 200, owner.data["profile"], {}
                elif parts.path == "/api/v1/courses/42":
                    status, body, headers = 200, owner.data["course"], {}
                elif parts.path == "/api/v1/courses/42/assignment_groups":
                    status = 200
                    if query.get("cursor") == ["last-page"]:
                        body, headers = owner.data["groups"][1:], {}
                    else:
                        body = owner.data["groups"][:1]
                        headers = {"Link": f'<{owner.base_url}{parts.path}?cursor=last-page>; rel="next"'}
                else:
                    status, body, headers = 404, {"error": "unmapped synthetic route"}, {}
                raw = json.dumps(deepcopy(body), allow_nan=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

