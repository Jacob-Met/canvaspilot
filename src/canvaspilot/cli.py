"""CLI: login + live probes."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="canvaspilot")
    sub = parser.add_subparsers(dest="cmd", required=True)

    login = sub.add_parser("login", help="Open headed browser for Canvas SSO (one-shot)")
    login.add_argument("--base-url", default=None)
    login.add_argument("--profile", default=None)

    sess = sub.add_parser("session", help="Stay-open session broker")
    sess_sub = sess.add_subparsers(dest="scmd", required=True)
    s_start = sess_sub.add_parser("start", help="Start session broker (leave open)")
    s_start.add_argument("--base-url", default=None)
    s_start.add_argument("--profile", default=None)
    s_start.add_argument("--port", type=int, default=None)
    s_start.add_argument(
        "--headless",
        action="store_true",
        help="Headless after a prior headed login into the same profile",
    )
    s_start.add_argument(
        "--read-only",
        action="store_true",
        help="Broker rejects non-GET/HEAD fetch ops (for unattended agent use)",
    )
    sess_sub.add_parser("status", help="Broker health/status")
    sess_sub.add_parser("stop", help="Shutdown broker")

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--base-url", default=None)
        p.add_argument("--profile", default=None)
        p.add_argument("--token", default=None)

    for name, help_ in [
        ("whoami", "GET /users/self/profile"),
        ("courses", "List active courses"),
        ("sync", "Courses + upcoming assignments digest"),
    ]:
        p = sub.add_parser(name, help=help_)
        add_common(p)
        if name == "sync":
            p.add_argument("--limit-courses", type=_positive_int, default=10,
                           help="Maximum courses to inspect (default: 10)")
            p.add_argument("--limit-assignments-per-course", type=_positive_int, default=5,
                           help="Maximum assignments to include per course (default: 5)")

    announcements = sub.add_parser(
        "announcements", help="Read active announcements for selected courses",
    )
    add_common(announcements)
    announcements.add_argument("course_ids", nargs="+", type=_positive_int)
    announcements.add_argument(
        "--start-date", default=None,
        help="Canvas start_date filter (YYYY-MM-DD or ISO 8601); omitted uses Canvas defaults",
    )
    announcements.add_argument(
        "--detail", choices=("compact", "full"), default="compact",
        help="compact limits message text to 400 characters; full keeps the complete stripped text",
    )

    grades = sub.add_parser("grade-review", help="Review Canvas-reported grades and assignment groups")
    add_common(grades)
    grades.add_argument("course_id", help="Positive numeric Canvas course ID")

    grade_export = sub.add_parser(
        "export-grade-review", help="Save reported course grades to a new offline HTML file",
    )
    add_common(grade_export)
    grade_export.add_argument("course_id", type=_positive_int)
    grade_export.add_argument(
        "--out", required=True, type=Path, help="New HTML report; existing paths are protected",
    )

    assigns = sub.add_parser("assignments", help="List assignments for a course")
    add_common(assigns)
    assigns.add_argument("course_id")
    assigns.add_argument("--bucket", default="upcoming")

    brief = sub.add_parser("brief", help="Assignment brief (cleaned prompt and supplied rubric)")
    add_common(brief)
    brief.add_argument("course_id")
    brief.add_argument("assignment_id")

    feedback = sub.add_parser(
        "feedback",
        help="Read self submission comments, rubric feedback, and grade/attempt metadata",
        description=(
            "Read self submission comments and rubric feedback. A false "
            "grade_matches_current_submission means grading preceded the latest resubmission."
        ),
    )
    add_common(feedback)
    feedback.add_argument("course_id")
    feedback.add_argument("assignment_id")

    inbox = sub.add_parser("inbox", help="List your inbox without changing conversation state")
    add_common(inbox)
    inbox.add_argument(
        "--scope", choices=("inbox", "unread", "starred", "archived", "sent"),
        default="inbox", help="inbox includes read and unread, non-archived conversations",
    )

    conversation = sub.add_parser(
        "conversation", help="Read one conversation while preserving unread state",
    )
    add_common(conversation)
    conversation.add_argument("conversation_id", type=_positive_int)

    disc = sub.add_parser("discussions", help="List discussion topics")
    add_common(disc)
    disc.add_argument("course_id")

    discussion = sub.add_parser(
        "discussion", help="Read one cached discussion; unread focus retains reply context"
    )
    add_common(discussion)
    discussion.add_argument("course_id", help="Positive numeric Canvas course ID")
    discussion.add_argument("topic_id", help="Positive numeric Canvas discussion topic ID")
    discussion.add_argument(
        "--unread-only", action="store_true", help="Keep known unread entries and their ancestors"
    )

    files = sub.add_parser("files", help="List course files")
    add_common(files)
    files.add_argument("course_id")

    browse = sub.add_parser("browse-files", help="Browse one course folder; metadata only")
    add_common(browse)
    browse.add_argument("course_id", help="Positive numeric Canvas course ID")
    browse.add_argument("--folder-id", default="root", help="root or a returned numeric folder ID")
    browse.add_argument("--folders-page", type=int, default=1)
    browse.add_argument("--files-page", type=int, default=1)
    browse.add_argument("--per-page", type=int, default=50, help="Requested child-page size, 1–100")

    export = sub.add_parser("export-calendar", help="Save selected assignment deadlines to a new .ics file")
    add_common(export)
    export.add_argument("course_ids", nargs="+", type=_positive_int)
    export.add_argument("--out", required=True, type=Path, help="New calendar file; existing paths are protected")
    export.add_argument("--bucket", choices=("upcoming", "past", "overdue", "undated", "ungraded", "unsubmitted", "all"),
                        default="upcoming", help="Canvas assignment selection (default: upcoming)")


    page_export = sub.add_parser(
        "export-pages", help="Save explicitly selected course pages to a new offline HTML reading packet"
    )
    add_common(page_export)
    page_export.add_argument("course_id", help="Positive numeric Canvas course ID")
    page_export.add_argument("pages", nargs="+", help="Page URL locators, or page_id:ID for an explicit numeric ID")
    page_export.add_argument("--out", required=True, type=Path, help="New HTML file; existing paths are protected")
    study = sub.add_parser(
        "export-study", help="Save selected assignment briefs as an offline study workspace",
    )
    add_common(study)
    study.add_argument("course_id", help="Positive decimal Canvas course ID")
    study.add_argument("assignment_ids", nargs="+", help="1–25 explicit assignment IDs")
    study.add_argument("--out", required=True, type=Path, help="New .html file; existing paths are protected")

    syllabus = sub.add_parser(
        "export-syllabus", help="Save selected course syllabi as a new offline HTML reading packet",
    )
    add_common(syllabus)
    syllabus.add_argument("course_ids", nargs="+", type=_positive_int)
    syllabus.add_argument("--out", required=True, type=Path, help="New HTML file; existing paths are protected")

    progress = sub.add_parser("module-progress", help="Inspect reported module progress and requirements")
    add_common(progress)
    progress.add_argument("course_id", help="Positive numeric Canvas course ID")
    progress.add_argument("--module-id", default=None, help="Inspect one returned module ID")

    progress_export = sub.add_parser(
        "export-module-progress", help="Save reported module progress to a new offline HTML file",
    )
    add_common(progress_export)
    progress_export.add_argument("course_id", type=_positive_int)
    progress_export.add_argument("--module-id", type=_positive_int, default=None)
    progress_export.add_argument(
        "--out", required=True, type=Path, help="New HTML report; existing paths are protected",
    )

    history = sub.add_parser(
        "submission-history",
        help="Read your returned submission versions and their submitted content",
        description=(
            "Read the current self submission and Canvas-returned history. "
            "Missing history stays unavailable; grades and comments are not "
            "assigned to other attempts."
        ),
    )
    add_common(history)
    history.add_argument("course_id", help="Positive numeric Canvas course ID")
    history.add_argument("assignment_id", help="Positive numeric Canvas assignment ID")

    comparison = sub.add_parser(
        "compare-submissions", help="Compare two returned submission records in a new offline HTML report",
        description=(
            "Select current or history:N, where N is the one-based returned history position. "
            "Before and after are labels, not a chronology inference. File metadata is compared; "
            "file bytes are not downloaded."
        ),
    )
    add_common(comparison)
    comparison.add_argument("course_id", help="Positive numeric Canvas course ID")
    comparison.add_argument("assignment_id", help="Positive numeric Canvas assignment ID")
    comparison.add_argument("--before", required=True, help="current or history:N")
    comparison.add_argument("--after", required=True, help="current or history:N")
    comparison.add_argument("--out", required=True, type=Path, help="New HTML file; existing paths are protected")

    agenda = sub.add_parser(
        "agenda", help="Read selected course events and assignment deadlines together",
        description=(
            "Read 1-10 course calendars for an explicit inclusive Canvas date range. "
            "Known timed, declared all-day, and unavailable timing remain separate."
        ),
    )
    add_common(agenda)
    agenda.add_argument("course_ids", nargs="+", help="Positive numeric Canvas course IDs")
    agenda.add_argument("--start", dest="start_date", required=True, help="YYYY-MM-DD")
    agenda.add_argument("--end", dest="end_date", required=True, help="YYYY-MM-DD")

    quizzes = sub.add_parser("quizzes", help="List classic quizzes for a course")
    add_common(quizzes)
    quizzes.add_argument("course_id", type=_positive_int, help="Positive numeric Canvas course ID")

    quiz = sub.add_parser("quiz", help="Read one classic quiz without starting an attempt")
    add_common(quiz)
    quiz.add_argument("course_id", type=_positive_int, help="Positive numeric Canvas course ID")
    quiz.add_argument("quiz_id", type=_positive_int, help="Positive numeric Canvas quiz ID")

    planner = sub.add_parser(
        "planner", help="Read your planner items without changing completion or visibility",
    )
    add_common(planner)
    planner.add_argument(
        "--start-date", default=None, help="Native date filter: YYYY-MM-DD or ISO 8601 timestamp",
    )
    planner.add_argument(
        "--end-date", default=None, help="Native date filter: YYYY-MM-DD or ISO 8601 timestamp",
    )

    mcp = sub.add_parser("mcp", help="Run MCP stdio server")
    add_common(mcp)

    args = parser.parse_args(argv)

    if args.cmd == "login":
        _login(base_url=args.base_url, profile=args.profile)
        return
    if args.cmd == "session":
        _session_cmd(args)
        return
    if args.cmd == "mcp":
        from canvaspilot.mcp_server import main as mcp_main

        mcp_main()
        return

    if args.cmd == "export-study":
        from canvaspilot.study_workspace import run_export_study

        run_export_study(args)
        return

    from canvaspilot.api import CanvasAPI
    from canvaspilot.client import CanvasClient, default_base_url, default_profile

    client = CanvasClient(
        base_url=args.base_url or default_base_url(),
        token=args.token,
        profile=Path(args.profile) if args.profile else default_profile(),
    )
    api = CanvasAPI(client)
    try:
        if args.cmd == "whoami":
            print(json.dumps(api.whoami(), indent=2, default=str))
        elif args.cmd == "courses":
            print(json.dumps(api.list_courses(), indent=2, default=str))
        elif args.cmd == "sync":
            print(json.dumps(api.sync_summary(
                limit_courses=args.limit_courses,
                limit_assignments_per_course=args.limit_assignments_per_course,
            ), indent=2, default=str))
        elif args.cmd == "announcements":
            import httpx

            from canvaspilot.client import CanvasAuthError, CanvasPaginationError

            # Keep the terminal result structured when MCP initialization has
            # enabled HTTPX request logging; restore the caller's logger level.
            http_log = logging.getLogger("httpx")
            previous_level = http_log.level
            http_log.setLevel(max(http_log.getEffectiveLevel(), logging.WARNING))
            try:
                result = api.list_announcements(
                    args.course_ids, start_date=args.start_date, detail=args.detail,
                )
            except (CanvasAuthError, CanvasPaginationError, httpx.HTTPError, ValueError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            finally:
                http_log.setLevel(previous_level)
            print(json.dumps(result, indent=2))
        elif args.cmd == "grade-review":
            import httpx

            try:
                result = api.grade_review(args.course_id)
            except (RuntimeError, httpx.HTTPError, ValueError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            print(json.dumps(result, indent=2, allow_nan=False))
        elif args.cmd == "export-grade-review":
            import os

            import httpx

            from canvaspilot.calendar_export import write_calendar
            from canvaspilot.grade_review_export import build_grade_review_report

            http_log = logging.getLogger("httpx")
            previous_level = http_log.level
            http_log.setLevel(max(http_log.getEffectiveLevel(), logging.WARNING))
            try:
                if os.path.lexists(args.out):
                    raise FileExistsError("Output path already exists; choose a new HTML file")
                content, report = build_grade_review_report(api, args.course_id)
                write_calendar(args.out, content)
            except (RuntimeError, httpx.HTTPError, ValueError, TypeError, OSError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            finally:
                http_log.setLevel(previous_level)
            print(json.dumps({"ok": True, "path": str(args.out), **report}, indent=2))
        elif args.cmd == "assignments":
            print(
                json.dumps(
                    api.list_assignments(args.course_id, bucket=args.bucket or None),
                    indent=2,
                    default=str,
                )
            )
        elif args.cmd == "brief":
            print(
                json.dumps(
                    api.assignment_brief(args.course_id, args.assignment_id),
                    indent=2,
                    default=str,
                )
            )
        elif args.cmd == "feedback":
            print(
                json.dumps(
                    api.submission_feedback(args.course_id, args.assignment_id),
                    indent=2,
                    default=str,
                )
            )
        elif args.cmd in {"quizzes", "quiz"}:
            import httpx

            from canvaspilot.client import CanvasAuthError, CanvasPaginationError

            http_log = logging.getLogger("httpx")
            previous_level = http_log.level
            http_log.setLevel(max(http_log.getEffectiveLevel(), logging.WARNING))
            try:
                if args.cmd == "quizzes":
                    result = api.list_quizzes(args.course_id)
                else:
                    result = api.get_quiz(args.course_id, args.quiz_id)
            except (CanvasAuthError, CanvasPaginationError, httpx.HTTPError, ValueError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            finally:
                http_log.setLevel(previous_level)
            print(json.dumps(result, indent=2, default=str))
        elif args.cmd == "discussions":
            print(json.dumps(api.list_discussion_topics(args.course_id), indent=2, default=str))
        elif args.cmd == "discussion":
            import httpx

            from canvaspilot.client import CanvasAuthError

            try:
                result = api.discussion_thread(
                    args.course_id, args.topic_id, unread_only=args.unread_only
                )
            except (CanvasAuthError, httpx.HTTPError, ValueError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            print(json.dumps(result, indent=2))
        elif args.cmd == "files":
            print(json.dumps(api.list_files(args.course_id), indent=2, default=str))
        elif args.cmd in ("inbox", "conversation"):
            import httpx

            from canvaspilot.client import CanvasAuthError, CanvasPaginationError

            try:
                if args.cmd == "inbox":
                    result = api.list_conversations(scope=args.scope)
                else:
                    result = api.get_conversation(args.conversation_id)
            except (CanvasAuthError, CanvasPaginationError, httpx.HTTPError, ValueError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.cmd == "export-calendar":
            import os

            import httpx

            from canvaspilot.calendar_export import (
                build_assignment_calendar,
                write_calendar,
            )
            from canvaspilot.client import CanvasAuthError, CanvasPaginationError

            try:
                if os.path.lexists(args.out):
                    raise FileExistsError("Output path already exists; choose a new .ics file")
                content, report = build_assignment_calendar(api, args.course_ids, bucket=args.bucket)
                write_calendar(args.out, content)
            except (CanvasAuthError, CanvasPaginationError, httpx.HTTPError, ValueError, TypeError, OSError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            print(json.dumps({"ok": True, "output": str(args.out), **report}, indent=2))
        elif args.cmd == "planner":
            import httpx

            from canvaspilot.client import CanvasAuthError, CanvasPaginationError

            http_log = logging.getLogger("httpx")
            previous_level = http_log.level
            http_log.setLevel(max(http_log.getEffectiveLevel(), logging.WARNING))
            try:
                result = api.planner_items(
                    start_date=args.start_date, end_date=args.end_date,
                )
            except (CanvasAuthError, CanvasPaginationError, httpx.HTTPError, ValueError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            finally:
                http_log.setLevel(previous_level)
            print(json.dumps(result, indent=2, default=str))
        elif args.cmd == "agenda":
            import httpx

            from canvaspilot.client import CanvasAuthError, CanvasPaginationError

            http_log = logging.getLogger("httpx")
            previous_level = http_log.level
            http_log.setLevel(max(http_log.getEffectiveLevel(), logging.WARNING))
            try:
                result = api.course_agenda(
                    args.course_ids, start_date=args.start_date, end_date=args.end_date,
                )
            except (CanvasAuthError, CanvasPaginationError, httpx.HTTPError, ValueError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            finally:
                http_log.setLevel(previous_level)
            print(json.dumps(result, indent=2))
        elif args.cmd == "export-module-progress":
            import os

            import httpx

            from canvaspilot.calendar_export import write_calendar
            from canvaspilot.client import CanvasAuthError, CanvasPaginationError
            from canvaspilot.module_progress_export import build_module_progress_report

            http_log = logging.getLogger("httpx")
            previous_level = http_log.level
            http_log.setLevel(max(http_log.getEffectiveLevel(), logging.WARNING))
            try:
                if os.path.lexists(args.out):
                    raise FileExistsError("Output path already exists; choose a new HTML file")
                content, report = build_module_progress_report(
                    api, args.course_id, module_id=args.module_id,
                )
                # The existing calendar publisher writes arbitrary complete bytes
                # to a new file; it never replaces a path or follows its symlink.
                write_calendar(args.out, content)
            except (CanvasAuthError, CanvasPaginationError, httpx.HTTPError, ValueError, TypeError, OSError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            finally:
                http_log.setLevel(previous_level)
            print(json.dumps({"ok": True, "output": str(args.out), **report}, indent=2))
        elif args.cmd == "compare-submissions":
            import httpx

            from canvaspilot.client import CanvasAuthError
            from canvaspilot.submission_comparison import export_submission_comparison

            http_log = logging.getLogger("httpx")
            previous_level = http_log.level
            http_log.setLevel(max(http_log.getEffectiveLevel(), logging.WARNING))
            try:
                result = export_submission_comparison(
                    api, args.course_id, args.assignment_id,
                    before=args.before, after=args.after, out=args.out,
                )
            except (CanvasAuthError, httpx.HTTPError, ValueError, TypeError, OSError, RecursionError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            finally:
                http_log.setLevel(previous_level)
            print(json.dumps({"ok": True, **result}, indent=2))
        elif args.cmd == "export-syllabus":
            import os

            import httpx

            from canvaspilot.client import CanvasAuthError
            from canvaspilot.syllabus_packet import (
                build_syllabus_packet,
                write_syllabus_packet,
            )

            http_log = logging.getLogger("httpx")
            previous_level = http_log.level
            http_log.setLevel(max(http_log.getEffectiveLevel(), logging.WARNING))
            try:
                if os.path.lexists(args.out):
                    raise FileExistsError("Output path already exists; choose a new HTML file")
                content, report = build_syllabus_packet(api, args.course_ids)
                write_syllabus_packet(args.out, content)
            except (CanvasAuthError, httpx.HTTPError, ValueError, TypeError, OSError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            finally:
                http_log.setLevel(previous_level)
            print(json.dumps({"ok": True, "output": str(args.out), **report}, indent=2))
        elif args.cmd == "submission-history":
            import httpx

            from canvaspilot.client import CanvasAuthError

            # MCP initialization can enable HTTPX request logs; keep this CLI
            # report machine-readable and restore the caller's logging setting.
            http_log = logging.getLogger("httpx")
            previous_level = http_log.level
            http_log.setLevel(max(http_log.getEffectiveLevel(), logging.WARNING))
            try:
                result = api.submission_history(args.course_id, args.assignment_id)
            except (CanvasAuthError, httpx.HTTPError, ValueError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            finally:
                http_log.setLevel(previous_level)
            print(json.dumps(result, indent=2))
        elif args.cmd == "export-pages":
            import os

            import httpx

            from canvaspilot.client import CanvasAuthError
            from canvaspilot.page_export import build_page_packet, write_page_packet

            try:
                if os.path.lexists(args.out):
                    raise FileExistsError("Output path already exists; choose a new HTML file")
                content, report = build_page_packet(api, args.course_id, args.pages)
                cleanup_warning = write_page_packet(args.out, content)
            except (CanvasAuthError, httpx.HTTPError, ValueError, TypeError, OSError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            if cleanup_warning:
                report["cleanup_warning"] = cleanup_warning
            print(json.dumps({"ok": True, "output": str(args.out), **report}, indent=2))
        elif args.cmd == "module-progress":
            import httpx

            from canvaspilot.client import CanvasAuthError

            try:
                result = api.module_progress(args.course_id, module_id=args.module_id)
            except (CanvasAuthError, httpx.HTTPError, ValueError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            print(json.dumps(result, indent=2))
        elif args.cmd == "browse-files":
            import httpx

            from canvaspilot.client import CanvasAuthError

            try:
                result = api.browse_files(
                    args.course_id, args.folder_id,
                    folders_page=args.folders_page, files_page=args.files_page,
                    per_page=args.per_page,
                )
            except (CanvasAuthError, httpx.HTTPError, ValueError) as error:
                print(json.dumps({
                    "ok": False, "error": type(error).__name__, "message": str(error),
                }), file=sys.stderr)
                raise SystemExit(1) from None
            print(json.dumps(result, indent=2))
    finally:
        api.close()


def _session_cmd(args: argparse.Namespace) -> None:
    from canvaspilot.client import (
        BROKER_PORT,
        _broker_request,
        broker_base,
        broker_health,
    )
    from canvaspilot.session_broker import main as broker_main

    port = getattr(args, "port", None) or BROKER_PORT
    if args.scmd == "start":
        # foreground — user leaves this running
        argv = []
        if args.base_url:
            argv += ["--base-url", args.base_url]
        if args.profile:
            argv += ["--profile", args.profile]
        argv += ["--port", str(port)]
        if getattr(args, "headless", False):
            argv.append("--headless")
        if getattr(args, "read_only", False):
            argv.append("--read-only")
        broker_main(argv)
        return
    if args.scmd == "status":
        h = broker_health()
        if not h:
            print(json.dumps({"ok": False, "error": "broker not running", "url": broker_base()}, indent=2))
            sys.exit(1)
        try:
            st = _broker_request("GET", f"{broker_base()}/status", timeout=30.0).json()
        except Exception as exc:  # noqa: BLE001 — report broker comms failures as JSON, never traceback
            st = {"error": str(exc)}
        print(json.dumps({"health": h, "status": st}, indent=2))
        return
    if args.scmd == "stop":
        try:
            r = _broker_request("POST", f"{broker_base()}/shutdown", json={}, timeout=5.0)
            print(r.text)
        except Exception as exc:  # noqa: BLE001 — report shutdown failures as JSON, never traceback
            print(json.dumps({"ok": False, "error": str(exc)}))
            sys.exit(1)


def _login(*, base_url: str | None, profile: str | None) -> None:
    from canvaspilot.client import default_base_url, default_profile

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("pip install canvaspilot[browser]") from exc

    base = (base_url or default_base_url()).rstrip("/")
    prof = Path(profile) if profile else default_profile()
    prof.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"status": "opening", "base_url": base, "profile": str(prof)}, indent=2))
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(prof),
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=["--disable-popup-blocking"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(base, wait_until="domcontentloaded")
        print(
            json.dumps(
                {
                    "status": "waiting_for_human",
                    "message": "Finish SSO/login, then press Enter here.",
                },
                indent=2,
            )
        )
        try:
            input()
        except EOFError:
            import time

            time.sleep(30)
        ctx.close()
    print(json.dumps({"status": "closed", "profile": str(prof)}, indent=2))


if __name__ == "__main__":
    main()
