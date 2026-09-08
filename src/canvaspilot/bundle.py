"""Canvas MCP + API bundle surface.

Curated helpers for common workflows; ``CanvasAPI.api_request`` /
``api_paginated`` cover the rest of Canvas REST under ``/api/v1``.
"""

from __future__ import annotations

from canvaspilot.api import CanvasAPI, assert_canvas_api_path, strip_html
from canvaspilot.client import CanvasAuthError, CanvasClient, broker_health
from canvaspilot.mcp_server import mcp

# Named MCP tools (plus canvas_api_request / canvas_api_paginated escape hatches).
CURATED_MCP_TOOLS: tuple[str, ...] = (
    "canvas_whoami",
    "canvas_list_courses",
    "canvas_get_course",
    "canvas_list_assignments",
    "canvas_get_assignment",
    "canvas_assignment_brief",
    "canvas_list_announcements",
    "canvas_list_modules",
    "canvas_list_pages",
    "canvas_get_page",
    "canvas_list_discussion_topics",
    "canvas_get_discussion",
    "canvas_post_discussion_reply",
    "canvas_list_files",
    "canvas_list_quizzes",
    "canvas_get_quiz",
    "canvas_list_quiz_questions",
    "canvas_list_quiz_submissions",
    "canvas_start_quiz_submission",
    "canvas_complete_quiz_submission",
    "canvas_list_conversations",
    "canvas_get_conversation",
    "canvas_reply_conversation",
    "canvas_list_calendar_events",
    "canvas_planner_items",
    "canvas_activity_stream",
    "canvas_list_todo_items",
    "canvas_list_enrollments",
    "canvas_sync_summary",
    "canvas_submission_status",
    "canvas_submit_assignment_text",
    "canvas_api_request",
    "canvas_api_paginated",
)

ESCAPE_HATCH_TOOLS: tuple[str, ...] = (
    "canvas_api_request",
    "canvas_api_paginated",
)


def make_api(*, token: str | None = None, fixture: dict | None = None) -> CanvasAPI:
    """Programmatic API bundle (same auth modes as MCP)."""
    return CanvasAPI(CanvasClient(token=token, fixture=fixture))


def tool_inventory() -> dict[str, object]:
    return {
        "server": "canvaspilot",
        "curated": list(CURATED_MCP_TOOLS),
        "escape_hatches": list(ESCAPE_HATCH_TOOLS),
        "coverage": "curated student/ops workflows + full /api/v1 via escape hatch",
        "limits": [
            "New Quizzes / LTI tools are not first-class; classic quizzes are",
            "writes (submit, reply, quiz start) require live auth and human judgment",
        ],
    }


__all__ = [
    "CURATED_MCP_TOOLS",
    "ESCAPE_HATCH_TOOLS",
    "CanvasAPI",
    "CanvasAuthError",
    "CanvasClient",
    "assert_canvas_api_path",
    "broker_health",
    "make_api",
    "mcp",
    "strip_html",
    "tool_inventory",
]
