"""Readable offline snapshots of the existing normalized course-grade review."""

from __future__ import annotations

import base64
import hashlib
import html
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from canvaspilot.api import CanvasAPI

MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_HTML_BYTES = 16 * 1024 * 1024

_STYLE = """
:root { color-scheme: light; font: 16px/1.55 system-ui,sans-serif; color:#20313b; background:#eff3f5; }
* { box-sizing:border-box; }
body { margin:0; }
main { max-width:1100px; margin:auto; padding:32px 24px 64px; }
h1,h2,h3,h4,p { margin-top:0; }
h1 { font-size:clamp(1.8rem,5vw,2.75rem); line-height:1.15; margin-bottom:12px; }
h2 { font-size:1.45rem; line-height:1.25; }
h3 { font-size:1.1rem; }
h4 { font-size:1rem; margin-bottom:8px; }
.eyebrow { text-transform:uppercase; letter-spacing:.09em; font-weight:700; color:#365867; }
.muted { color:#4a606b; }
header,.panel,.group { margin-bottom:24px; }
.panel,.group { background:white; border:1px solid #cad7dc; border-radius:12px; padding:24px; }
.notice { border-left:4px solid #367081; padding:12px 16px; background:#e8f1f4; }
.warning { border-left-color:#916322; background:#fff6e5; }
.facts { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,2fr); margin:0 0 20px; }
.facts dt,.facts dd { min-width:0; margin:0; padding:7px 10px; border-bottom:1px solid #e1e9ed; }
.facts dt { color:#3b5663; font-weight:600; }
pre,code { font: .88rem/1.5 ui-monospace,SFMono-Regular,Consolas,monospace; }
pre { white-space:pre-wrap; margin:0; }
h1,h2,h3,h4,p,li,dt,dd,pre,code,a,summary { overflow-wrap:anywhere; }
a { color:#155b7b; text-underline-offset:.2em; }
a:focus-visible,summary:focus-visible { outline:3px solid #155b7b; outline-offset:4px; }
.download { display:inline-block; border:1px solid #155b7b; border-radius:6px; padding:10px 14px; font-weight:650; }
nav ul { padding-left:22px; }
nav li { margin:6px 0; }
.assignment { padding:20px 0 8px; border-top:2px solid #dbe5e9; }
.assignment h3 { margin-bottom:12px; }
.assignment-summary { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin-bottom:12px; }
.reading { padding:12px; border:1px solid #dbe5e9; border-radius:6px; }
.reading .label { display:block; font-size:.84rem; color:#4a606b; margin-bottom:6px; }
.flags { padding-left:22px; }
details { margin:14px 0; }
summary { cursor:pointer; color:#155b7b; font-weight:600; padding:4px 0; }
details[open] summary { margin-bottom:12px; }
.enrollment+.enrollment { border-top:1px solid #dbe5e9; padding-top:18px; }
footer { color:#4a606b; font-size:.9rem; }
@media (max-width:540px) {
 main { padding:22px 12px 36px; }
 .panel,.group { padding:16px; }
 .facts { grid-template-columns:minmax(0,1fr); }
 .facts dt { border-bottom:0; padding-bottom:0; }
 .facts dd { padding-top:2px; }
 .assignment-summary { grid-template-columns:minmax(0,1fr); }
}
@media print {
 :root { background:white; color:black; font-size:10pt; }
 main { max-width:none; padding:0; }
 .panel,.group { padding:12px; border-radius:0; }
 h2,h3,h4,summary { break-after:avoid; }
 .reading { break-inside:avoid; }
 .download,.back { display:none; }
 a,summary { color:black; }
 details:not([open]) > *:not(summary) { display:block !important; }
 details::details-content { content-visibility:visible !important; display:block !important; }
}
"""

_LABELS = {
    "computed_current_score": "Reported current score",
    "computed_final_score": "Reported final score",
    "computed_current_grade": "Reported current grade",
    "computed_final_grade": "Reported final grade",
    "computed_current_letter_grade": "Reported current letter grade",
    "current_period_computed_current_score": "Current period: reported current score",
    "current_period_computed_final_score": "Current period: reported final score",
    "current_period_computed_current_grade": "Current period: reported current grade",
    "current_period_computed_final_grade": "Current period: reported final grade",
    "grade_matches_current_submission": "Grade matches the current submission",
    "points_possible": "Assignment points possible",
    "group_weight": "Reported group weight",
    "drop_lowest": "Reported drop-lowest count",
    "drop_highest": "Reported drop-highest count",
    "never_drop": "Reported never-drop assignment IDs",
    "collection_complete": "Whole collection complete",
}
_STATE = {
    "not_returned": "Not returned by Canvas",
    "null": "Canvas returned null",
    "returned": "Returned by Canvas",
}
_VISIBILITY = {
    "reported_fields": "Only the grade fields returned by Canvas are shown.",
    "assignment_not_visible": "Canvas marks this assignment not visible. Its grade fields are withheld.",
    "not_posted": "Canvas reports that this grade is not posted. Its grade fields are withheld.",
}


def _escape(value: str) -> str:
    # Keep control characters and unpaired surrogates visible in HTML without
    # changing the original normalized JSON carried in the report download.
    visible = "".join(
        f"\\u{ord(char):04x}"
        if (ord(char) < 32 and char not in "\n\t")
        or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF
        else char
        for char in value
    )
    return html.escape(visible, quote=True)


def _value(value: Any) -> str:
    return "<pre>" + _escape(json.dumps(
        value, ensure_ascii=False, allow_nan=False, indent=2,
    )) + "</pre>"


def _field(fields: dict[str, Any], key: str) -> str:
    return _value(fields[key]) if key in fields else '<span class="muted">Not returned</span>'


def _facts(fields: dict[str, Any]) -> str:
    if not fields:
        return '<p class="muted">No fields were returned in this object.</p>'
    rows = []
    for key, value in fields.items():
        label = _LABELS.get(key, key.replace("_", " ").capitalize())
        rows.append(
            f'<dt>{_escape(label)} <code>({_escape(key)})</code></dt>'
            f'<dd data-field="{_escape(key)}">{_value(value)}</dd>'
        )
    return '<dl class="facts">' + "".join(rows) + "</dl>"


def _title(value: Any, fallback: str) -> str:
    return _escape(value) if isinstance(value, str) and value else _escape(fallback)


def _reading(label: str, value: str) -> str:
    return '<div class="reading"><span class="label">' + _escape(label) + "</span>" + value + "</div>"


def _assignment(assignment: dict[str, Any], index: int, group_index: int) -> str:
    fields = assignment["fields"]
    state = assignment["submission_state"]
    submission = assignment["submission"]
    detail = submission["fields"] if submission is not None else {}
    title = _title(fields.get("name"), f"Assignment {fields['id']}")
    parts = [
        f'<article class="assignment" id="assignment-{group_index}-{index}">',
        f"<h3>{title}</h3>",
        '<div class="assignment-summary">',
        _reading("Due date as returned", _field(fields, "due_at")),
        _reading("Assignment points possible", _field(fields, "points_possible")),
    ]
    if submission is not None:
        visibility = submission["grade_visibility"]
        if visibility == "reported_fields":
            parts.extend([
                _reading("Reported submission score", _field(detail, "score")),
                _reading("Reported submission grade", _field(detail, "grade")),
            ])
        else:
            parts.append(_reading("Submission grade", "Withheld by the reader"))
        parts.extend([
            "</div>",
            '<p class="notice">' + _escape(_VISIBILITY.get(
                visibility, f"Reader visibility: {visibility}",
            )) + "</p>",
        ])
        if detail.get("grade_matches_current_submission") is False:
            parts.append(
                '<p class="notice warning">Canvas reports that this grade does not match '
                "the current submission. Do not treat it as the grade for the latest attempt.</p>"
            )
        elif detail.get("grade_matches_current_submission") is not True:
            parts.append(
                '<p class="muted">Whether the grade matches the current submission is unknown.</p>'
            )
    else:
        parts.extend([
            "</div>", '<p class="notice">Submission: ',
            _escape(_STATE.get(state, state)),
            ". No grade or missing-work status is inferred.</p>",
        ])
    parts.extend([
        "<h4>Submission context</h4>",
        '<dl class="facts">',
    ])
    for key in ("attempt", "workflow_state", "excused", "missing", "late"):
        parts.append(
            f"<dt>{_escape(key.replace('_', ' ').capitalize())}</dt><dd>"
            + _field(detail, key) + "</dd>"
        )
    parts.extend([
        "</dl>",
        "<details><summary>All returned assignment and submission fields</summary>",
        "<h4>Assignment</h4>", _facts(fields),
        "<h4>Submission</h4>", _value({
            "submission_state": state, "submission": submission,
        }),
        "</details></article>",
    ])
    return "".join(parts)


def _group(group: dict[str, Any], index: int) -> str:
    title = _title(group.get("name"), f"Assignment group {group['id']}")
    parts = [
        f'<section class="group" id="group-{index}" aria-labelledby="group-{index}-title">',
        f'<h2 id="group-{index}-title">{title}</h2>',
        _facts({key: value for key, value in group.items() if key != "assignments"}),
        '<p class="muted">Group weights and drop rules are reported context. '
        "This file does not select dropped work or recalculate a grade.</p>",
    ]
    assignments = group["assignments"]
    if assignments is None:
        parts.append('<p class="notice">Assignment list: '
                     + _escape(_STATE.get(group["assignments_state"], group["assignments_state"]))
                     + ". This does not mean the group has no assignments.</p>")
    elif not assignments:
        parts.append('<p class="muted">Canvas returned an empty assignment list for this group.</p>')
    else:
        parts.extend(_assignment(item, offset, index) for offset, item in enumerate(assignments))
    parts.append('<a class="back" href="#top">Back to report overview</a></section>')
    return "".join(parts)


def render_grade_review_report(
    report: dict[str, Any], *, generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Render an unchanged CanvasAPI.grade_review result and its exact JSON values."""
    stamp = datetime.now(UTC) if generated_at is None else generated_at
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("Report creation time must include a timezone")
    created = stamp.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = (json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode("ascii")
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("Normalized grade-review JSON exceeds the 4 MiB export limit")
    payload_hash = hashlib.sha256(payload).hexdigest()
    encoded = base64.b64encode(payload).decode("ascii")
    course = report["course"]
    title = _title(course.get("name"), f"Course {course['id']}")
    groups = report["assignment_groups"]
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="referrer" content="no-referrer">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">",
        "<title>Course grade review — CanvasPilot</title><style>", _STYLE,
        '</style></head><body><main id="top"><header>',
        '<p class="eyebrow">CanvasPilot · Saved course review</p>',
        f"<h1>{title}</h1>",
        f'<p>Report created <time datetime="{created}">{created}</time></p>',
        '<p class="notice">This saved observation shows Canvas-reported values for the '
        "authenticated caller. It does not refresh or calculate a replacement grade. "
        "Counts cover returned rows; whole-course completeness remains unknown.</p>",
        '<p class="muted">Values use JSON notation: null means unavailable, false differs '
        'from a missing flag, 0 stays zero, and "" is an explicitly returned empty string. '
        "A field marked Not returned is unknown.</p></header>",
        '<section class="panel" aria-labelledby="totals-title"><h2 id="totals-title">Reported course totals</h2>',
    ]
    if report["totals_visibility"] == "hidden_by_course":
        parts.append('<p class="notice">This course hides final grades. The reader withheld enrollment totals.</p>')
    else:
        parts.append('<p class="muted">Each enrollment stays separate. Current, final and grading-period '
                     "values retain their original Canvas field names; no enrollment is chosen for you.</p>")
    enrollments = report["enrollments"]
    if enrollments is None:
        parts.append("<p>Enrollments: " + _escape(_STATE.get(
            report["enrollments_state"], report["enrollments_state"],
        )) + ".</p>")
    elif not enrollments:
        parts.append("<p>Canvas returned an empty enrollment list.</p>")
    else:
        for index, enrollment in enumerate(enrollments):
            parts.extend([
                '<article class="enrollment">', f"<h3>Returned enrollment {index + 1}</h3>",
                _facts(enrollment["context"]), "<h4>Reported totals</h4>",
                _facts(enrollment["reported_totals"]), "</article>",
            ])
    parts.append("</section>")
    if groups:
        parts.extend([
            '<nav class="panel" aria-label="Assignment groups"><h2>Assignment groups</h2><ul>',
            "".join(f'<li><a href="#group-{index}">'
                    + _title(group.get("name"), f"Assignment group {group['id']}") + "</a></li>"
                    for index, group in enumerate(groups)),
            "</ul></nav>",
        ])
    else:
        parts.append('<section class="panel"><p>No assignment groups were returned. '
                     "This does not establish that the course has none.</p></section>")
    parts.extend(_group(group, index) for index, group in enumerate(groups))
    parts.extend([
        '<section class="panel" aria-labelledby="scope-title"><h2 id="scope-title">Report context</h2>',
        "<h3>Course and authenticated caller</h3>",
        _facts({"course": course, "authenticated_user_id": report["authenticated_user_id"]}),
        "<h3>Grading periods</h3>",
        _facts({"grading_periods_state": report["grading_periods_state"],
                "grading_periods": report["grading_periods"]}),
        "<h3>Returned-row counts and reader boundaries</h3>",
        _facts({key: value for key, value in report.items()
                if key not in {"course", "authenticated_user_id", "enrollments",
                               "grading_periods", "assignment_groups", "warnings"}}),
        "<h3>Reader warnings</h3>",
        "<ul>" + "".join("<li>" + _escape(message) + "</li>" for message in report["warnings"])
        + "</ul>" if report["warnings"] else "<p>No reader warnings were returned.</p>",
        f'<p><a class="download" id="download-report" download="course-grade-review.json" '
        f'href="data:application/json;base64,{encoded}">Download complete report JSON</a></p>',
        '<p class="muted">The download preserves the complete normalized report used here. '
        "Original Canvas response pages are not included.</p>",
        f'<p class="muted">JSON SHA-256: <code id="json-sha256">{payload_hash}</code></p>',
        "</section><footer>Open this file directly in a browser. Use the browser's Print command "
        "for paper or PDF. Source links are shown as text; this report has no scripts, "
        "remote assets or grade-editing controls.</footer></main></body></html>\n",
    ])
    content = "".join(parts).encode("utf-8")
    if len(content) > MAX_HTML_BYTES:
        raise ValueError("Rendered grade-review HTML exceeds the 16 MiB export limit")
    return content, {
        "course_id": course["id"], "generated_at": created,
        "groups_returned": report["counts"]["groups_returned"],
        "assignments_returned": report["counts"]["assignments_returned"],
        "html_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
        "json_bytes": len(payload), "json_sha256": payload_hash,
    }


def build_grade_review_report(
    api: CanvasAPI, course_id: int | str, *, generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Read the existing course-grade review exactly once, then render locally."""
    return render_grade_review_report(api.grade_review(course_id), generated_at=generated_at)
