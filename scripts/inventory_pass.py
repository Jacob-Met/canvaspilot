"""Full Canvas inventory across courses — read-only."""
from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from canvaspilot.api import CanvasAPI, strip_html
from canvaspilot.client import CanvasClient, broker_health

THIRD_PARTY = re.compile(
    r"classavo|tophat|top\s*hat|labflow|lab\s*flow|pearson|wiley|mcgraw|connect|cengage|"
    r"webassign|gradescope|packback|perusall|hypothesis|zoom|youtube|khan|aleks|"
    r"mastering|launchpad|achieve|sapling|chegg|courseware|lti|external.?tool|"
    r"day\s*1\s*digital|inclusive\s*access|vitalsource|redshelf",
    re.I,
)

assert broker_health() and broker_health().get("ready"), "broker down"
api = CanvasAPI(CanvasClient())

courses = api.list_courses()
# Focus active-looking: Fall 2026 + current-ish + orgs user cares about
fall = [c for c in courses if c.get("term") == "Fall 2026"]
other_recent = [c for c in courses if c.get("term") in {"Spring 2026", "Fall 2025", "Summer 2025"}]
orgs = [c for c in courses if c.get("term") in {"Organization", "Library"}]
# Full pass on Fall 2026; lighter on rest
targets = fall + other_recent  # skip deep-dive every org unless quick tabs

inventory = {
    "whoami": api.whoami()["profile"]["name"],
    "course_total": len(courses),
    "scanned": [],
    "third_party_hits": [],
    "tool_counter": Counter(),
    "tab_counter": Counter(),
    "errors": [],
}

def safe(label, fn):
    try:
        return fn()
    except Exception as e:
        inventory["errors"].append({"where": label, "error": str(e)})
        return None

for c in targets:
    cid = c["id"]
    entry = {
        "id": cid,
        "name": c.get("name"),
        "code": c.get("course_code"),
        "term": c.get("term"),
        "tabs": [],
        "external_tab_labels": [],
        "external_tools_api": [],
        "modules": [],
        "assignment_count": None,
        "discussion_count": None,
        "announcement_titles": [],
        "files_ok": None,
        "files_count": None,
        "has_quizzes_tab": False,
        "third_party_mentions": [],
    }

    tabs = safe(f"{cid}.tabs", lambda: api.client.request("GET", f"/api/v1/courses/{cid}/tabs"))
    if isinstance(tabs, list):
        for t in tabs:
            tid = t.get("id")
            label = t.get("label") or t.get("id")
            entry["tabs"].append({"id": tid, "label": label, "type": t.get("type"), "url": t.get("full_url") or t.get("html_url")})
            inventory["tab_counter"][str(tid)] += 1
            if tid == "quizzes" or (label or "").lower() == "quizzes":
                entry["has_quizzes_tab"] = True
            if str(tid).startswith("context_external_tool") or t.get("type") == "external":
                entry["external_tab_labels"].append(label)
                inventory["tool_counter"][label or tid] += 1

    tools = safe(
        f"{cid}.external_tools",
        lambda: api.client.request("GET", f"/api/v1/courses/{cid}/external_tools", params={"per_page": 50}),
    )
    if isinstance(tools, list):
        for tool in tools:
            name = tool.get("name") or tool.get("consumer_key") or str(tool.get("id"))
            entry["external_tools_api"].append({
                "id": tool.get("id"),
                "name": name,
                "domain": tool.get("domain"),
                "url": tool.get("url"),
            })
            inventory["tool_counter"][name] += 1

    mods = safe(f"{cid}.modules", lambda: api.list_modules(cid))
    if isinstance(mods, list):
        for m in mods[:30]:
            items = m.get("items") or []
            item_types = Counter((i.get("type") for i in items if isinstance(i, dict)))
            entry["modules"].append({
                "name": m.get("name"),
                "items": len(items),
                "item_types": dict(item_types),
            })
            # scan item titles for third party
            for i in items:
                title = f"{i.get('title')} {i.get('external_url')} {i.get('html_url')}"
                if THIRD_PARTY.search(title or ""):
                    hit = {"course": c.get("name"), "module": m.get("name"), "item": i.get("title"), "type": i.get("type")}
                    entry["third_party_mentions"].append(hit)
                    inventory["third_party_hits"].append(hit)

    assigns = safe(f"{cid}.assignments", lambda: api.list_assignments(cid, bucket=None))
    if isinstance(assigns, list):
        entry["assignment_count"] = len(assigns)
        entry["submission_type_counts"] = dict(
            Counter(tuple(a.get("submission_types") or []) for a in assigns)
        )
        # stringify submission types for readability
        flat = Counter()
        for a in assigns:
            for t in a.get("submission_types") or []:
                flat[t] += 1
            blob = f"{a.get('name')} {a.get('description_text')}"
            if THIRD_PARTY.search(blob or ""):
                hit = {"course": c.get("name"), "assignment": a.get("name")}
                entry["third_party_mentions"].append(hit)
                inventory["third_party_hits"].append(hit)
        entry["submission_types_flat"] = dict(flat)

    discs = safe(f"{cid}.discussions", lambda: api.list_discussion_topics(cid))
    if isinstance(discs, list):
        entry["discussion_count"] = len(discs)
        for d in discs:
            text = f"{d.get('title')} {d.get('message_text')}"
            if THIRD_PARTY.search(text or ""):
                # extract short snippet around match
                m = THIRD_PARTY.search(text)
                hit = {
                    "course": c.get("name"),
                    "discussion": d.get("title"),
                    "match": m.group(0) if m else None,
                }
                entry["third_party_mentions"].append(hit)
                inventory["third_party_hits"].append(hit)

    anns = safe(f"{cid}.announcements", lambda: api.list_announcements([cid]))
    if isinstance(anns, list):
        entry["announcement_titles"] = [a.get("title") for a in anns[:10]]
        for a in anns:
            text = f"{a.get('title')} {a.get('message_text')}"
            if THIRD_PARTY.search(text or ""):
                m = THIRD_PARTY.search(text)
                hit = {
                    "course": c.get("name"),
                    "announcement": a.get("title"),
                    "match": m.group(0) if m else None,
                    "snippet": (text[max(0, m.start()-40): m.end()+80] if m else None),
                }
                entry["third_party_mentions"].append(hit)
                inventory["third_party_hits"].append(hit)

    try:
        files = api.list_files(cid)
        entry["files_ok"] = True
        entry["files_count"] = len(files)
    except Exception as e:
        entry["files_ok"] = False
        entry["files_error"] = str(e)

    inventory["scanned"].append(entry)
    print(json.dumps({
        "scanned": c.get("name"),
        "tabs": [t["label"] for t in entry["tabs"]],
        "external": entry["external_tab_labels"] or [t["name"] for t in entry["external_tools_api"][:5]],
        "modules": len(entry["modules"]),
        "assignments": entry["assignment_count"],
        "third_party_n": len(entry["third_party_mentions"]),
    }, default=str), flush=True)

# Rollup
by_tool = defaultdict(list)
for hit in inventory["third_party_hits"]:
    key = hit.get("match") or hit.get("item") or hit.get("assignment") or "unknown"
    by_tool[str(key).lower()].append(hit.get("course"))

summary = {
    "whoami": inventory["whoami"],
    "courses_enrolled": inventory["course_total"],
    "courses_deep_scanned": len(inventory["scanned"]),
    "fall_2026": [c["name"] for c in fall],
    "external_tool_labels": dict(inventory["tool_counter"].most_common()),
    "common_tabs": dict(inventory["tab_counter"].most_common(20)),
    "third_party_by_keyword": {k: sorted(set(v)) for k, v in sorted(by_tool.items())},
    "files_enabled_courses": [s["name"] for s in inventory["scanned"] if s.get("files_ok")],
    "files_blocked_courses": [s["name"] for s in inventory["scanned"] if s.get("files_ok") is False],
    "error_count": len(inventory["errors"]),
    "canvas_native_ok": [
        "whoami", "courses", "assignments", "modules", "discussions", "announcements",
        "tabs", "planner", "inbox_list", "submission_status_read", "grades_via_enrollments",
    ],
    "deferred_separate_mcps": sorted({
        k for k in by_tool if any(x in k for x in ["classavo", "tophat", "top hat", "labflow", "lab flow", "zoom", "vitalsource"])
    }),
}

out_dir = Path(os.environ.get("CANVASPILOT_REPORTS") or Path.home() / ".canvaspilot" / "reports")
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "course_inventory.json").write_text(
    json.dumps({"summary": summary, "courses": inventory["scanned"], "errors": inventory["errors"]}, indent=2, default=str),
    encoding="utf-8",
)
# markdown-friendly summary next to the JSON
research = out_dir / "course_inventory.md"
lines = [
    "# Canvas course inventory (live session)",
    "",
    f"Student: {summary['whoami']}",
    f"Enrolled courses listed: {summary['courses_enrolled']}",
    f"Deep-scanned: {summary['courses_deep_scanned']} (Fall 2026 + recent terms)",
    "",
    "## Fall 2026",
]
for n in summary["fall_2026"]:
    lines.append(f"- {n}")
lines += ["", "## External / LTI tab labels seen", ""]
for k, v in summary["external_tool_labels"].items():
    lines.append(f"- **{k}**: {v} course(s)")
lines += ["", "## Third-party mentions (announcements/modules/assignments)", ""]
for k, courses_ in summary["third_party_by_keyword"].items():
    lines.append(f"- **{k}**: " + "; ".join(courses_))
lines += ["", "## Files tab", ""]
lines.append("Enabled: " + (", ".join(summary["files_enabled_courses"]) or "(none)"))
lines.append("Blocked/403: " + (", ".join(summary["files_blocked_courses"]) or "(none)"))
lines += ["", "## Deferred (not Canvas MCP)", ""]
for x in summary["deferred_separate_mcps"] or ["(scan for classavo/tophat/labflow in JSON for details)"]:
    lines.append(f"- {x}")
lines += ["", f"Raw JSON: `{out_dir / 'course_inventory.json'}`", ""]
research.write_text("\n".join(lines), encoding="utf-8")

print(json.dumps({"SUMMARY": summary}, indent=2, default=str), flush=True)
api.close()
