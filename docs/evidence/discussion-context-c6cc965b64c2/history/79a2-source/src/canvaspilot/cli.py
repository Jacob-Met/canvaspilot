"""CLI: login + live probes."""

from __future__ import annotations

import argparse
import json
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

    progress = sub.add_parser("module-progress", help="Inspect reported module progress and requirements")
    add_common(progress)
    progress.add_argument("course_id", help="Positive numeric Canvas course ID")
    progress.add_argument("--module-id", default=None, help="Inspect one returned module ID")

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
