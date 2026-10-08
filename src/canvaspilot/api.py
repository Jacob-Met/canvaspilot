"""High-level Canvas operations (full REST including quizzes)."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime
from html import unescape
from math import isfinite
from typing import Any

from canvaspilot.assignment_submission import project_assignment_submission
from canvaspilot.client import CanvasClient
from canvaspilot.feedback import build_submission_feedback

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def _validate_sync_limits(limit_courses: int, limit_assignments_per_course: int) -> None:
    for name, value in (
        ("limit_courses", limit_courses),
        ("limit_assignments_per_course", limit_assignments_per_course),
    ):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer")


def _sync_due_key(row: dict[str, Any]) -> tuple[int, datetime | None]:
    """Order aware timestamps by instant, leaving all unknown dates stable at the end."""
    raw = row.get("due_at")
    if isinstance(raw, str):
        try:
            value = datetime.fromisoformat(raw)
            if value.utcoffset() is not None:
                # Direct comparison avoids UTC conversion overflow at years 1/9999.
                return (0, value)
        except ValueError:
            pass
    return (1, None)


def assert_canvas_api_path(path: str) -> str:
    """Allow only relative Canvas REST paths under ``/api/v1`` (no absolute URLs)."""
    p = (path or "").strip()
    if not p.startswith("/api/v1"):
        raise ValueError("path must start with /api/v1 (Canvas REST only)")
    if "://" in p or ".." in p or p.startswith("//"):
        raise ValueError("absolute URLs and path traversal are not allowed")
    return p


def strip_html(html: str | None) -> str:
    if not html:
        return ""
    # Remove literal markup tags BEFORE unescaping entities: text that was
    # escaped (e.g. "&lt;canvas&gt;") must survive as text, not be mistaken
    # for a tag and deleted.
    text = TAG_RE.sub(" ", html)
    return WS_RE.sub(" ", unescape(text)).strip()


def _brief_rubric(rubric: Any, warnings: list[str]) -> list[dict[str, Any]] | None:
    """Project supplied rubric details without inventing missing grading data."""
    if rubric is None:
        return None
    if not isinstance(rubric, list):
        warnings.append("rubric: expected a list; rubric unavailable")
        return None

    def record_fields(value: Any, path: str, *, criterion: bool) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            warnings.append(f"{path}: expected an object; entry omitted")
            return None
        fields = {"id", "description", "long_description", "points"}
        if criterion:
            fields |= {
                "criterion_use_range", "ignore_for_scoring", "learning_outcome_id",
                "outcome_id", "vendor_guid",
            }
        result: dict[str, Any] = {}
        for key, field in value.items():
            if key not in fields:
                continue
            if field is None:
                valid = True
            elif key == "points":
                valid = type(field) is int or (type(field) is float and isfinite(field))
            elif key in {"criterion_use_range", "ignore_for_scoring"}:
                valid = isinstance(field, bool)
            elif key in {"id", "learning_outcome_id", "outcome_id"}:
                valid = type(field) in (str, int)
            else:
                valid = isinstance(field, str)
            if valid:
                result[key] = field
            else:
                warnings.append(f"{path}.{key}: invalid value; field omitted")
        if criterion and "ratings" in value:
            ratings = value["ratings"]
            if ratings is None:
                result["ratings"] = None
            elif isinstance(ratings, list):
                result["ratings"] = []
                for index, rating in enumerate(ratings):
                    item = record_fields(rating, f"{path}.ratings[{index}]", criterion=False)
                    if item is not None:
                        result["ratings"].append(item)
            else:
                warnings.append(f"{path}.ratings: expected a list; ratings unavailable")
                result["ratings"] = None
        if not result:
            warnings.append(f"{path}: no usable rubric fields; entry omitted")
            return None
        return result

    result = []
    for index, criterion in enumerate(rubric):
        item = record_fields(criterion, f"rubric[{index}]", criterion=True)
        if item is not None:
            result.append(item)
    return result


class CanvasAPI:
    def __init__(self, client: CanvasClient | None = None) -> None:
        self.client = client or CanvasClient()

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> CanvasAPI:  # noqa: PYI034 — false positive, returns self (verified by isolated repro)
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

    def grade_review(self, course_id: int | str) -> dict[str, Any]:
        """Review only Canvas-reported current-user grades and group context."""
        from canvaspilot.grade_review import grade_review

        return grade_review(self.client, course_id)

    def list_assignments(
        self,
        course_id: int | str,
        *,
        bucket: str | None = "upcoming",
        detail: str = "compact",
    ) -> list[dict[str, Any]]:
        """List assignments. ``detail=compact`` (default) omits description bodies — use get_assignment for full text."""
        params: list[tuple[str, Any]] = [("order_by", "due_at"), ("include[]", "submission")]
        if bucket:
            params.append(("bucket", bucket))
        rows = self.client.get_paginated(
            f"/api/v1/courses/{course_id}/assignments",
            params=params,
        )
        out = []
        full = str(detail or "compact").lower() in {"full", "verbose", "all"}
        for a in rows:
            if not isinstance(a, dict):
                continue
            row: dict[str, Any] = {
                "id": a.get("id"),
                "course_id": course_id,
                "name": a.get("name"),
                "due_at": a.get("due_at"),
                "points_possible": a.get("points_possible"),
                "submission_types": a.get("submission_types"),
                "html_url": a.get("html_url"),
                "has_submitted_submissions": a.get("has_submitted_submissions"),
            }
            row["submission"], row["submission_warnings"] = project_assignment_submission(
                a.get("submission")
            )
            if full:
                row["description_text"] = strip_html(a.get("description"))
            out.append(row)
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
            "rubric_settings": a.get("rubric_settings"),
            "use_rubric_for_grading": a.get("use_rubric_for_grading"),
            "submission": a.get("submission"),
        }

    def assignment_brief(self, course_id: int | str, assignment_id: int | str) -> dict[str, Any]:
        a = self.get_assignment(course_id, assignment_id)
        warnings: list[str] = []
        rubric = _brief_rubric(a.get("rubric"), warnings)
        settings = a.get("rubric_settings")
        if settings is not None and not isinstance(settings, dict):
            warnings.append("rubric_settings: expected an object; settings unavailable")
            settings = None
        use_for_grading = a.get("use_rubric_for_grading")
        if use_for_grading is not None and not isinstance(use_for_grading, bool):
            warnings.append("use_rubric_for_grading: expected a boolean; grading use unknown")
            use_for_grading = None
        return {
            "title": a.get("name"),
            "due_at": a.get("due_at"),
            "points_possible": a.get("points_possible"),
            "submission_types": a.get("submission_types"),
            "prompt": a.get("description_text"),
            "html_url": a.get("html_url"),
            "course_id": course_id,
            "assignment_id": assignment_id,
            "rubric": rubric,
            "rubric_settings": deepcopy(settings),
            "use_rubric_for_grading": use_for_grading,
            "rubric_warnings": warnings,
        }

    def list_announcements(
        self,
        course_ids: list[int | str],
        *,
        start_date: str | None = None,
        detail: str = "compact",
    ) -> list[dict[str, Any]]:
        params: list[tuple[str, Any]] = [
            ("active_only", True),
            ("per_page", 50),
        ]
        for cid in course_ids:
            params.append(("context_codes[]", f"course_{cid}"))
        if start_date:
            params.append(("start_date", start_date))
        rows = self.client.get_paginated("/api/v1/announcements", params=params)
        if not isinstance(rows, list):
            rows = [rows] if rows else []
        full = str(detail or "compact").lower() in {"full", "verbose", "all"}
        out = []
        for a in rows:
            if not isinstance(a, dict):
                continue
            text = strip_html(a.get("message")) or ""
            if not full and len(text) > 400:
                text = text[:400] + "…"
            out.append(
                {
                    "id": a.get("id"),
                    "title": a.get("title"),
                    "posted_at": a.get("posted_at"),
                    "context_code": a.get("context_code"),
                    "message_text": text,
                    "html_url": a.get("html_url"),
                }
            )
        return out

    def list_modules(self, course_id: int | str, *, detail: str = "compact") -> list[dict[str, Any]]:
        rows = self.client.get_paginated(
            f"/api/v1/courses/{course_id}/modules",
            params={"include[]": ["items"]},
        )

        def valid_items(value: Any) -> bool:
            return isinstance(value, list) and all(
                isinstance(item, dict)
                and isinstance(item.get("id"), (int, str))
                and re.fullmatch(r"[0-9]+", str(item["id"]))
                for item in value
            )

        modules = []
        for module in rows:
            if not isinstance(module, dict):
                modules.append(module)
                continue
            inline = module.get("items")
            count = module.get("items_count")
            if not valid_items(inline) or (type(count) is int and len(inline) < count):
                # Canvas may omit inline items even when include[]=items was
                # requested. Resolve them before projecting either detail mode.
                if inline is None and type(count) is int and count == 0:
                    items = []
                else:
                    module_id = module.get("id")
                    if not isinstance(module_id, (int, str)) or not re.fullmatch(r"[0-9]+", str(module_id)):
                        raise ValueError("Cannot retrieve module items without a valid module ID")
                    items = self.client.get_paginated(
                        f"/api/v1/courses/{course_id}/modules/{module_id}/items"
                    )
                    if not valid_items(items):
                        raise ValueError("Canvas returned malformed module items")
                # Do not mutate fixture data or another caller's response object.
                module = {**module, "items": items}
            modules.append(module)
        full = str(detail or "compact").lower() in {"full", "verbose", "all"}
        if full:
            return modules
        out = []
        for m in modules:
            if not isinstance(m, dict):
                continue
            items = []
            for it in m.get("items") or []:
                if not isinstance(it, dict):
                    continue
                items.append(
                    {
                        "id": it.get("id"),
                        "title": it.get("title"),
                        "type": it.get("type"),
                        "html_url": it.get("html_url"),
                        "content_id": it.get("content_id"),
                        "external_url": it.get("external_url"),
                    }
                )
            out.append(
                {
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "position": m.get("position"),
                    "published": m.get("published"),
                    "items_count": m.get("items_count"),
                    "items": items,
                }
            )
        return out

    def module_progress(
        self, course_id: int | str, *, module_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Read Canvas-declared module progress and a course study checklist."""
        from canvaspilot.module_progress import module_progress

        return module_progress(self, course_id, module_id=module_id)

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

    def browse_files(
        self,
        course_id: int | str,
        folder_id: int | str = "root",
        *,
        folders_page: int = 1,
        files_page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """Browse one course folder and bounded direct-child metadata pages."""
        from canvaspilot.folder_browser import browse_course_folder

        return browse_course_folder(
            self.client, course_id, folder_id,
            folders_page=folders_page, files_page=files_page, per_page=per_page,
        )

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

    def submission_history(self, course_id: int | str, assignment_id: int | str) -> dict[str, Any]:
        """Read the current self submission and exactly the history Canvas returns."""
        from canvaspilot.submission_history import read_submission_history

        return read_submission_history(self.client, course_id, assignment_id)

    def submission_status(self, course_id: int | str, assignment_id: int | str) -> dict[str, Any]:
        return self.client.request(
            "GET",
            f"/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self",
        )

    def submission_feedback(self, course_id: int | str, assignment_id: int | str) -> dict[str, Any]:
        """Read self submission comments and rubric evidence alongside grade/attempt metadata.

        A false grade_matches_current_submission means grading preceded the
        latest resubmission. Rubric points are not used to calculate a grade.
        """
        path = f"/api/v1/courses/{course_id}/assignments/{assignment_id}"
        assignment = self.client.request("GET", path)
        submission = self.client.request(
            "GET",
            f"{path}/submissions/self",
            params={"include[]": ["submission_comments", "rubric_assessment"]},
        )
        return build_submission_feedback(assignment, submission)

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

    def list_todo_items(self) -> list[Any]:
        return self.client.get_paginated("/api/v1/users/self/todo")

    def list_enrollments(self, *, state: str = "active") -> list[Any]:
        return self.client.get_paginated(
            "/api/v1/users/self/enrollments",
            params={"state[]": state} if state else None,
        )

    def reply_conversation(self, conversation_id: int | str, body: str) -> Any:
        return self.client.request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/add_message",
            data={"body": body},
        )

    def api_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | list[tuple[str, Any]] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """Escape hatch: any Canvas REST call under ``/api/v1`` (session or PAT)."""
        return self.client.request(
            method.upper(),
            assert_canvas_api_path(path),
            params=params,
            json_body=json_body,
            data=data,
        )

    def api_paginated(
        self,
        path: str,
        *,
        params: dict[str, Any] | list[tuple[str, Any]] | None = None,
    ) -> list[Any]:
        """Escape hatch: paginated GET under ``/api/v1``."""
        return self.client.get_paginated(assert_canvas_api_path(path), params=params)

    def sync_summary(
        self, *, limit_courses: int = 10, limit_assignments_per_course: int = 5
    ) -> dict[str, Any]:
        """Read upcoming deadlines with explicit selection counts over returned API rows."""
        _validate_sync_limits(limit_courses, limit_assignments_per_course)
        returned_courses = self.list_courses()
        courses = returned_courses[:limit_courses]
        upcoming: list[dict[str, Any]] = []
        course_summaries: list[dict[str, Any]] = []
        for c in courses:
            try:
                assigns = self.list_assignments(c["id"], bucket="upcoming")
            except Exception as exc:  # noqa: BLE001 — per-course soft fail
                upcoming.append({"course_id": c["id"], "error": str(exc)})
                course_summaries.append({
                    "course_id": c["id"],
                    "status": "error",
                    "assignments_returned": None,
                    "assignments_included": None,
                    "assignments_omitted": None,
                    "unknown_due_dates": None,
                })
                continue
            selected = sorted(assigns, key=_sync_due_key)[:limit_assignments_per_course]
            upcoming.extend({**a, "course_name": c.get("name")} for a in selected)
            course_summaries.append({
                "course_id": c["id"],
                "status": "ok",
                "assignments_returned": len(assigns),
                "assignments_included": len(selected),
                "assignments_omitted": len(assigns) - len(selected),
                "unknown_due_dates": sum(1 for a in assigns if _sync_due_key(a)[0]),
            })
        return {
            "mode": self.client.mode,
            "course_count": len(courses),
            "courses": courses,
            "upcoming_assignments": sorted(upcoming, key=_sync_due_key),
            "courses_returned": len(returned_courses),
            "courses_omitted": len(returned_courses) - len(courses),
            "limits": {
                "courses": limit_courses,
                "assignments_per_course": limit_assignments_per_course,
            },
            "course_summaries": course_summaries,
        }
