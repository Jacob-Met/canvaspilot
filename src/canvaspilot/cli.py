"""CLI: login + live probes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


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

    assigns = sub.add_parser("assignments", help="List assignments for a course")
    add_common(assigns)
    assigns.add_argument("course_id")
    assigns.add_argument("--bucket", default="upcoming")

    brief = sub.add_parser("brief", help="Assignment brief (cleaned prompt)")
    add_common(brief)
    brief.add_argument("course_id")
    brief.add_argument("assignment_id")

    disc = sub.add_parser("discussions", help="List discussion topics")
    add_common(disc)
    disc.add_argument("course_id")

    files = sub.add_parser("files", help="List course files")
    add_common(files)
    files.add_argument("course_id")

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
            print(json.dumps(api.sync_summary(), indent=2, default=str))
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
        elif args.cmd == "discussions":
            print(json.dumps(api.list_discussion_topics(args.course_id), indent=2, default=str))
        elif args.cmd == "files":
            print(json.dumps(api.list_files(args.course_id), indent=2, default=str))
    finally:
        api.close()


def _session_cmd(args: argparse.Namespace) -> None:
    import httpx

    from canvaspilot.client import BROKER_PORT, broker_base, broker_health
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
        broker_main(argv)
        return
    if args.scmd == "status":
        h = broker_health()
        if not h:
            print(json.dumps({"ok": False, "error": "broker not running", "url": broker_base()}, indent=2))
            sys.exit(1)
        try:
            st = httpx.get(f"{broker_base()}/status", timeout=30.0).json()
        except Exception as exc:
            st = {"error": str(exc)}
        print(json.dumps({"health": h, "status": st}, indent=2))
        return
    if args.scmd == "stop":
        try:
            r = httpx.post(f"{broker_base()}/shutdown", json={}, timeout=5.0)
            print(r.text)
        except Exception as exc:
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
