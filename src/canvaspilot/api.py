"""High-level Canvas operations (full REST including quizzes)."""

from __future__ import annotations

import re
from html import unescape
from typing import Any

from canvaspilot.client import CanvasClient

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def strip_html(html: str | None) -> str:
    if not html:
        return ""
    text = TAG_RE.sub(" ", unescape(html))
    return WS_RE.sub(" ", text).strip()


class CanvasAPI:
    def __init__(self, client: CanvasClient | None = None) -> None:
        self.client = client or CanvasClient()

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> CanvasAPI:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def whoami(self) -> dict[str, Any]:
        profile = self.client.request("GET", "/api/v1/users/self/profile")
        return {
            "mode": self.client.mode,
            "base_url": self.client.base_url,
            "profile": profile,
        }

    def get_course(self, course_id: int | str) -> dict[str, Any]:
        return self.client.request(
            "GET",
            f"/api/v1/courses/{course_id}",
            params={"include[]": ["syllabus_body", "term", "total_scores"]},
        )

    def list_courses(self, *, enrollment_state: str = "active") -> list[dict[str, Any]]:
        rows = self.client.get_paginated(
            "/api/v1/courses",
            params=[
                ("enrollment_state", enrollment_state),
                ("include[]", "term"),
                ("include[]", "total_scores"),
            ],
        )
        return [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "course_code": c.get("course_code"),
                "enrollment_term_id": c.get("enrollment_term_id"),
                "term": (c.get("term") or {}).get("name"),
            }
            for c in rows
            if isinstance(c, dict) and c.get("id")
        ]

    def list_assignments(self, course_id: int | str, *, bucket: str | None = "upcoming") -> list[dict[str, Any]]:
        params: list[tuple[str, Any]] = [("order_by", "due_at"), ("include[]", "submission")]
        if bucket:
            params.append(("bucket", bucket))
        rows = self.client.get_paginated(
            f"/api/v1/courses/{course_id}/assignments",
            params=params,
        )
        out = []
        for a in rows:
            if not isinstance(a, dict):
                continue
            out.append(
                {
                    "id": a.get("id"),
                    "course_id": course_id,
                    "name": a.get("name"),
                    "due_at": a.get("due_at"),
                    "points_possible": a.get("points_possible"),
                    "submission_types": a.get("submission_types"),
                    "html_url": a.get("html_url"),
                    "has_submitted_submissions": a.get("has_submitted_submissions"),
                    "description_text": strip_html(a.get("description")),
                }
            )
        return out

    def get_assignment(self, course_id: int | str, assignment_id: int | str) -> dict[str, Any]:
        a = self.client.request(
            "GET",
            f"/api/v1/courses/{course_id}/assignments/{assignment_id}",
            params={"include[]": ["submission"]},
        )
        return {
            "id": a.get("id"),
            "course_id": course_id,
            "name": a.get("name"),
            "due_at": a.get("due_at"),
            "points_possible": a.get("points_possible"),
            "submission_types": a.get("submission_types"),
            "html_url": a.get("html_url"),
            "description_html": a.get("description"),
            "description_text": strip_html(a.get("description")),
            "rubric": a.get("rubric"),
            "submission": a.get("submission"),
        }

    def assignment_brief(self, course_id: int | str, assignment_id: int | str) -> dict[str, Any]:
        a = self.get_assignment(course_id, assignment_id)
        return {
            "title": a.get("name"),
            "due_at": a.get("due_at"),
            "points_possible": a.get("points_possible"),
            "submission_types": a.get("submission_types"),
            "prompt": a.get("description_text"),
            "html_url": a.get("html_url"),
            "course_id": course_id,
            "assignment_id": assignment_id,
        }

    def list_announcements(self, course_ids: list[int | str], *, start_date: str | None = None) -> list[dict[str, Any]]:
        params: list[tuple[str, Any]] = [
            ("active_only", True),
            ("per_page", 50),
        ]
        for cid in course_ids:
            params.append(("context_codes[]", f"course_{cid}"))
        if start_date:
            params.append(("start_date", start_date))
        rows = self.client.request("GET", "/api/v1/announcements", params=params)
        if not isinstance(rows, list):
            rows = [rows] if rows else []
        return [
            {
                "id": a.get("id"),
                "title": a.get("title"),
                "posted_at": a.get("posted_at"),
                "context_code": a.get("context_code"),
                "message_text": strip_html(a.get("message")),
                "html_url": a.get("html_url"),
            }
            for a in rows
            if isinstance(a, dict)
        ]

    def list_modules(self, course_id: int | str) -> list[dict[str, Any]]:
        return self.client.get_paginated(
            f"/api/v1/courses/{course_id}/modules",
            params={"include[]": ["items"]},
        )

    def list_pages(self, course_id: int | str) -> list[dict[str, Any]]:
        rows = self.client.get_paginated(f"/api/v1/courses/{course_id}/pages")
        return [
            {
                "url": p.get("url"),
                "title": p.get("title"),
                "published": p.get("published"),
                "updated_at": p.get("updated_at"),
                "front_page": p.get("front_page"),
            }
            for p in rows
            if isinstance(p, dict)
        ]

    def get_page(self, course_id: int | str, page_url: str) -> dict[str, Any]:
        p = self.client.request("GET", f"/api/v1/courses/{course_id}/pages/{page_url}")
        return {
            "url": p.get("url"),
            "title": p.get("title"),
            "body_html": p.get("body"),
            "body_text": strip_html(p.get("body")),
            "published": p.get("published"),
        }

    def list_discussion_topics(self, course_id: int | str) -> list[dict[str, Any]]:
        rows = self.client.get_paginated(
            f"/api/v1/courses/{course_id}/discussion_topics",
            params={"order_by": "recent_activity", "only_announcements": False},
        )
        return [
            {
                "id": t.get("id"),
                "title": t.get("title"),
                "posted_at": t.get("posted_at"),
                "published": t.get("published"),
                "message_text": strip_html(t.get("message")),
                "html_url": t.get("html_url"),
            }
            for t in rows
            if isinstance(t, dict)
        ]

    def get_discussion(self, course_id: int | str, topic_id: int | str) -> dict[str, Any]:
        topic = self.client.request(
            "GET",
            f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}",
        )
        view = self.client.request(
            "GET",
            f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/view",
        )
        return {"topic": topic, "view": view}

    def post_discussion_reply(
        self,
        course_id: int | str,
        topic_id: int | str,
        message: str,
    ) -> dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/courses/{course_id}/discussion_topics/{topic_id}/entries",
            data={"message": message},
        )

    def list_files(self, course_id: int | str) -> list[dict[str, Any]]:
        try:
            rows = self.client.get_paginated(f"/api/v1/courses/{course_id}/files")
        except Exception:
            folders = self.client.request(
                "GET",
                f"/api/v1/courses/{course_id}/folders/by_path",
            )
            root = folders[0] if isinstance(folders, list) and folders else None
            if not root:
                raise
            rows = self.client.get_paginated(f"/api/v1/folders/{root['id']}/files")
        return [
            {
                "id": f.get("id"),
                "display_name": f.get("display_name"),
                "filename": f.get("filename"),
                "size": f.get("size"),
                "updated_at": f.get("updated_at"),
                "url": f.get("url"),
                "content_type": f.get("content-type") or f.get("content_type"),
            }
            for f in rows
            if isinstance(f, dict)
        ]

    def list_quizzes(self, course_id: int | str) -> list[dict[str, Any]]:
        rows = self.client.get_paginated(f"/api/v1/courses/{course_id}/quizzes")
        return [
            {
                "id": q.get("id"),
                "title": q.get("title"),
                "due_at": q.get("due_at"),
                "lock_at": q.get("lock_at"),
                "question_count": q.get("question_count"),
                "points_possible": q.get("points_possible"),
                "published": q.get("published"),
                "quiz_type": q.get("quiz_type"),
                "html_url": q.get("html_url"),
            }
            for q in rows
            if isinstance(q, dict)
        ]

    def get_quiz(self, course_id: int | str, quiz_id: int | str) -> dict[str, Any]:
        return self.client.request("GET", f"/api/v1/courses/{course_id}/quizzes/{quiz_id}")

    def list_quiz_questions(self, course_id: int | str, quiz_id: int | str) -> list[Any]:
        return self.client.get_paginated(
            f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions"
        )

    def list_quiz_submissions(self, course_id: int | str, quiz_id: int | str) -> Any:
        return self.client.request(
            "GET",
            f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions",
        )

    def start_quiz_submission(
        self,
        course_id: int | str,
        quiz_id: int | str,
        *,
        access_code: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {}
        if access_code:
            body["access_code"] = access_code
        return self.client.request(
            "POST",
            f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions",
            json_body=body if body else {},
        )

    def complete_quiz_submission(
        self,
        course_id: int | str,
        quiz_id: int | str,
        submission_id: int | str,
        *,
        attempt: int | None = None,
        validation_token: str | None = None,
    ) -> Any:
        payload: dict[str, Any] = {}
        if attempt is not None:
            payload["attempt"] = attempt
        if validation_token:
            payload["validation_token"] = validation_token
        return self.client.request(
            "POST",
            f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/{submission_id}/complete",
            json_body=payload,
        )

    def list_conversations(self, *, scope: str = "inbox") -> list[Any]:
        return self.client.get_paginated(
            "/api/v1/conversations",
            params={"scope": scope},
        )

    def get_conversation(self, conversation_id: int | str) -> Any:
        return self.client.request("GET", f"/api/v1/conversations/{conversation_id}")

    def list_calendar_events(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        context_codes: list[str] | None = None,
    ) -> list[Any]:
        params: list[tuple[str, Any]] = []
        if start_date:
            params.append(("start_date", start_date))
        if end_date:
            params.append(("end_date", end_date))
        for code in context_codes or []:
            params.append(("context_codes[]", code))
        return self.client.get_paginated("/api/v1/calendar_events", params=params or None)

    def submission_status(self, course_id: int | str, assignment_id: int | str) -> dict[str, Any]:
        return self.client.request(
            "GET",
            f"/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self",
        )

    def submit_assignment_text(
        self,
        course_id: int | str,
        assignment_id: int | str,
        body: str,
    ) -> dict[str, Any]:
        return self.client.request(
            "POST",
            f"/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions",
            data={
                "submission[submission_type]": "online_text_entry",
                "submission[body]": body,
            },
        )

    def planner_items(self, *, start_date: str | None = None, end_date: str | None = None) -> list[Any]:
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self.client.get_paginated("/api/v1/planner/items", params=params)

    def activity_stream(self) -> Any:
        return self.client.request("GET", "/api/v1/users/self/activity_stream")

    def sync_summary(self, *, limit_courses: int = 10) -> dict[str, Any]:
        courses = self.list_courses()[:limit_courses]
        upcoming: list[dict[str, Any]] = []
        for c in courses:
            try:
                assigns = self.list_assignments(c["id"], bucket="upcoming")
            except Exception as exc:  # noqa: BLE001 — per-course soft fail
                upcoming.append({"course_id": c["id"], "error": str(exc)})
                continue
            for a in assigns[:5]:
                upcoming.append({**a, "course_name": c.get("name")})
        return {
            "mode": self.client.mode,
            "course_count": len(courses),
            "courses": courses,
            "upcoming_assignments": upcoming,
        }
