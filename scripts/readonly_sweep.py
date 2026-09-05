"""Read-only live sweep — no submits/posts/profile writes."""
from __future__ import annotations

import json
import traceback
from datetime import datetime, timedelta, timezone

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient, broker_health

results = []

def check(name: str, fn):
    try:
        data = fn()
        entry = {"name": name, "ok": True}
        if isinstance(data, list):
            entry["count"] = len(data)
            if data and isinstance(data[0], dict):
                entry["sample"] = {k: data[0].get(k) for k in list(data[0])[:6]}
        elif isinstance(data, dict):
            entry["keys"] = list(data.keys())[:12]
            if "name" in data:
                entry["name_field"] = data.get("name")
            if "title" in data:
                entry["title"] = data.get("title")
            if "profile" in data:
                entry["profile_name"] = (data.get("profile") or {}).get("name")
            if "upcoming_assignments" in data:
                entry["upcoming"] = len(data.get("upcoming_assignments") or [])
        else:
            entry["type"] = type(data).__name__
        results.append(entry)
        print(json.dumps({"PASS": name, **{k: v for k, v in entry.items() if k != "name"}}, default=str), flush=True)
        return data
    except Exception as e:
        results.append({"name": name, "ok": False, "error": str(e), "trace": traceback.format_exc().splitlines()[-3:]})
        print(json.dumps({"FAIL": name, "error": str(e)}, default=str), flush=True)
        return None

assert broker_health(), "broker down"
api = CanvasAPI(CanvasClient())

who = check("whoami", api.whoami)
courses = check("list_courses", api.list_courses) or []
# Prefer Fall 2026 credit courses
fall = [c for c in courses if c.get("term") == "Fall 2026" and "Sec" in (c.get("name") or "")]
pick = fall[0] if fall else (courses[0] if courses else None)
cid = pick["id"] if pick else None
print(json.dumps({"picked_course": pick}), flush=True)

check("sync_summary", lambda: api.sync_summary(limit_courses=5))
check("planner_items", api.planner_items)

if cid:
    assigns = check("list_assignments_upcoming", lambda: api.list_assignments(cid, bucket="upcoming"))
    assigns_all = check("list_assignments_all", lambda: api.list_assignments(cid, bucket=None))
    check("list_discussion_topics", lambda: api.list_discussion_topics(cid))
    check("list_modules", lambda: api.list_modules(cid))
    check("list_files", lambda: api.list_files(cid))
    check("list_announcements", lambda: api.list_announcements([cid]))

    # grades / enrollments read
    check(
        "course_enrollments_self",
        lambda: api.client.request(
            "GET",
            f"/api/v1/courses/{cid}/enrollments",
            params=[("user_id", "self"), ("per_page", "10")],
        ),
    )
    check(
        "calendar_events",
        lambda: api.client.request(
            "GET",
            "/api/v1/calendar_events",
            params=[
                ("type", "event"),
                ("context_codes[]", f"course_{cid}"),
                ("start_date", (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat()),
                ("end_date", (datetime.now(timezone.utc) + timedelta(days=45)).date().isoformat()),
                ("per_page", "20"),
            ],
        ),
    )
    check(
        "conversations_unread",
        lambda: api.client.request("GET", "/api/v1/conversations/unread_count"),
    )
    check(
        "list_conversations",
        lambda: api.client.request("GET", "/api/v1/conversations", params={"per_page": 10}),
    )
    check(
        "dashboard_cards",
        lambda: api.client.request("GET", "/api/v1/dashboard/dashboard_cards"),
    )
    check(
        "favorites_courses",
        lambda: api.client.request("GET", "/api/v1/users/self/favorites/courses"),
    )
    check(
        "activity_stream_summary",
        lambda: api.client.request("GET", f"/api/v1/courses/{cid}/activity_stream/summary"),
    )

    # pick an assignment for get/brief/submission_status
    pool = assigns_all or assigns or []
    non_quiz = [a for a in pool if "online_quiz" not in (a.get("submission_types") or [])]
    target = (non_quiz or pool)[0] if pool else None
    if target:
        aid = target["id"]
        print(json.dumps({"picked_assignment": {"id": aid, "name": target.get("name"), "types": target.get("submission_types")}}), flush=True)
        check("get_assignment", lambda: api.get_assignment(cid, aid))
        check("assignment_brief", lambda: api.assignment_brief(cid, aid))
        check("submission_status", lambda: api.submission_status(cid, aid))

    topics = None
    for r in results:
        if r.get("name") == "list_discussion_topics" and r.get("ok"):
            topics = api.list_discussion_topics(cid)
            break
    if topics:
        tid = topics[0]["id"]
        check("get_discussion", lambda: api.get_discussion(cid, tid))

# Quizzes allowed
check("list_quizzes", lambda: api.client.request("GET", f"/api/v1/courses/{cid}/quizzes") if cid else [])

# Explicitly NOT calling writes in this sweep: submit, post discussion, send conversation

api.close()
passed = sum(1 for r in results if r["ok"])
failed = [r for r in results if not r["ok"]]
summary = {"passed": passed, "failed": len(failed), "total": len(results), "failures": failed}
print(json.dumps({"SUMMARY": summary}, indent=2, default=str), flush=True)
import os
from pathlib import Path

out_dir = Path(os.environ.get("CANVASPILOT_REPORTS") or Path.home() / ".canvaspilot" / "reports")
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "readonly_sweep.json").write_text(
    json.dumps({"summary": summary, "results": results}, indent=2, default=str), encoding="utf-8"
)
