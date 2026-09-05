"""MCP stdio server for Canvas (session/PAT; full REST including quizzes)."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver import MCPServer

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient

mcp = MCPServer(
    "canvaspilot",
    instructions=(
        "Canvas LMS tools for courses, assignments, quizzes, pages, modules, files, "
        "discussions, announcements, planner, inbox, calendar, and submissions via "
        "session broker or PAT. Prefer these over raw browser clicking when available."
    ),
)

_api: CanvasAPI | None = None


def _get_api() -> CanvasAPI:
    global _api
    if _api is None:
        _api = CanvasAPI(CanvasClient())
    return _api


def _dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)


@mcp.tool(description="Confirm Canvas auth and return self profile.", structured_output=False)
async def canvas_whoami() -> str:
    return _dump(_get_api().whoami())


@mcp.tool(description="List active Canvas courses.", structured_output=False)
async def canvas_list_courses() -> str:
    return _dump(_get_api().list_courses())


@mcp.tool(description="Get one course including syllabus body when available.", structured_output=False)
async def canvas_get_course(course_id: str) -> str:
    return _dump(_get_api().get_course(course_id))


@mcp.tool(description="List assignments for a course (default upcoming bucket).", structured_output=False)
async def canvas_list_assignments(course_id: str, bucket: str = "upcoming") -> str:
    return _dump(_get_api().list_assignments(course_id, bucket=bucket or None))


@mcp.tool(description="Get one assignment with cleaned prompt text.", structured_output=False)
async def canvas_get_assignment(course_id: str, assignment_id: str) -> str:
    return _dump(_get_api().get_assignment(course_id, assignment_id))


@mcp.tool(description="Digested assignment brief: prompt, due date, submission types.", structured_output=False)
async def canvas_assignment_brief(course_id: str, assignment_id: str) -> str:
    return _dump(_get_api().assignment_brief(course_id, assignment_id))


@mcp.tool(description="List announcements for one or more courses (comma-separated ids).", structured_output=False)
async def canvas_list_announcements(course_ids: str) -> str:
    ids = [c.strip() for c in course_ids.split(",") if c.strip()]
    return _dump(_get_api().list_announcements(ids))


@mcp.tool(description="List modules (with items) for a course.", structured_output=False)
async def canvas_list_modules(course_id: str) -> str:
    return _dump(_get_api().list_modules(course_id))


@mcp.tool(description="List wiki pages for a course.", structured_output=False)
async def canvas_list_pages(course_id: str) -> str:
    return _dump(_get_api().list_pages(course_id))


@mcp.tool(description="Get a wiki page body by URL slug.", structured_output=False)
async def canvas_get_page(course_id: str, page_url: str) -> str:
    return _dump(_get_api().get_page(course_id, page_url))


@mcp.tool(description="List discussion topics for a course.", structured_output=False)
async def canvas_list_discussion_topics(course_id: str) -> str:
    return _dump(_get_api().list_discussion_topics(course_id))


@mcp.tool(description="Get a discussion topic + view/entries.", structured_output=False)
async def canvas_get_discussion(course_id: str, topic_id: str) -> str:
    return _dump(_get_api().get_discussion(course_id, topic_id))


@mcp.tool(description="Post a reply to a discussion topic.", structured_output=False)
async def canvas_post_discussion_reply(course_id: str, topic_id: str, message: str) -> str:
    return _dump(_get_api().post_discussion_reply(course_id, topic_id, message))


@mcp.tool(description="List files in a course.", structured_output=False)
async def canvas_list_files(course_id: str) -> str:
    return _dump(_get_api().list_files(course_id))


@mcp.tool(description="List classic quizzes in a course.", structured_output=False)
async def canvas_list_quizzes(course_id: str) -> str:
    return _dump(_get_api().list_quizzes(course_id))


@mcp.tool(description="Get one classic quiz.", structured_output=False)
async def canvas_get_quiz(course_id: str, quiz_id: str) -> str:
    return _dump(_get_api().get_quiz(course_id, quiz_id))


@mcp.tool(description="List questions for a classic quiz (when API allows).", structured_output=False)
async def canvas_list_quiz_questions(course_id: str, quiz_id: str) -> str:
    return _dump(_get_api().list_quiz_questions(course_id, quiz_id))


@mcp.tool(description="List quiz submissions for a classic quiz.", structured_output=False)
async def canvas_list_quiz_submissions(course_id: str, quiz_id: str) -> str:
    return _dump(_get_api().list_quiz_submissions(course_id, quiz_id))


@mcp.tool(description="Start a classic quiz submission (optional access_code).", structured_output=False)
async def canvas_start_quiz_submission(course_id: str, quiz_id: str, access_code: str = "") -> str:
    return _dump(
        _get_api().start_quiz_submission(
            course_id, quiz_id, access_code=access_code or None
        )
    )


@mcp.tool(description="Complete a classic quiz submission.", structured_output=False)
async def canvas_complete_quiz_submission(
    course_id: str,
    quiz_id: str,
    submission_id: str,
    attempt: int = 0,
    validation_token: str = "",
) -> str:
    return _dump(
        _get_api().complete_quiz_submission(
            course_id,
            quiz_id,
            submission_id,
            attempt=attempt or None,
            validation_token=validation_token or None,
        )
    )


@mcp.tool(description="List Canvas Inbox conversations.", structured_output=False)
async def canvas_list_conversations(scope: str = "inbox") -> str:
    return _dump(_get_api().list_conversations(scope=scope))


@mcp.tool(description="Get one Inbox conversation.", structured_output=False)
async def canvas_get_conversation(conversation_id: str) -> str:
    return _dump(_get_api().get_conversation(conversation_id))


@mcp.tool(description="List calendar events (optional ISO start/end dates).", structured_output=False)
async def canvas_list_calendar_events(start_date: str = "", end_date: str = "") -> str:
    return _dump(
        _get_api().list_calendar_events(
            start_date=start_date or None,
            end_date=end_date or None,
        )
    )


@mcp.tool(description="Planner items (optional ISO start/end).", structured_output=False)
async def canvas_planner_items(start_date: str = "", end_date: str = "") -> str:
    return _dump(
        _get_api().planner_items(start_date=start_date or None, end_date=end_date or None)
    )


@mcp.tool(description="User activity stream.", structured_output=False)
async def canvas_activity_stream() -> str:
    return _dump(_get_api().activity_stream())


@mcp.tool(description="Cross-course sync: courses + upcoming assignments.", structured_output=False)
async def canvas_sync_summary(limit_courses: int = 10) -> str:
    return _dump(_get_api().sync_summary(limit_courses=limit_courses))


@mcp.tool(description="Submission status for an assignment (self).", structured_output=False)
async def canvas_submission_status(course_id: str, assignment_id: str) -> str:
    return _dump(_get_api().submission_status(course_id, assignment_id))


@mcp.tool(description="Submit finished online_text_entry work.", structured_output=False)
async def canvas_submit_assignment_text(course_id: str, assignment_id: str, body: str) -> str:
    return _dump(_get_api().submit_assignment_text(course_id, assignment_id, body))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
