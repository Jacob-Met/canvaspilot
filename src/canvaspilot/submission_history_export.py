"""Readable offline copy of the existing self submission-history report."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from canvaspilot.submission_history import _numeric_id

if TYPE_CHECKING:
    from canvaspilot.api import CanvasAPI

MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_HTML_BYTES = 16 * 1024 * 1024

_STYLE = """
:root{color-scheme:light;font:16px/1.55 system-ui,sans-serif;color:#202d39;background:#f2f1ec}
*{box-sizing:border-box}body{margin:0}main{max-width:1100px;margin:auto;padding:40px 24px 64px}
h1,h2,h3,p{margin-top:0}h1{font-size:clamp(1.9rem,5vw,3.1rem);line-height:1.1;margin-bottom:18px}
h2{font-size:1.45rem;line-height:1.25}h3{font-size:1.1rem;line-height:1.3}
.eyebrow{font-size:.8rem;font-weight:750;letter-spacing:.1em;text-transform:uppercase;color:#476055}
header,nav,.panel{margin-bottom:24px}.panel,nav{background:#fff;border:1px solid #d4d8d1;border-radius:12px;padding:24px}
.muted,footer{color:#4d5d67}.notice{padding:14px 18px;border-left:4px solid #a76924;background:#fff4e4}
.context{padding:12px 16px;background:#eef4f0;border-left:4px solid #466753}
nav ol{padding-left:24px}nav li{margin:7px 0}a{color:#215941;text-underline-offset:.2em}
a:focus-visible{outline:3px solid #215941;outline-offset:5px}.download{display:inline-block;padding:11px 16px;border:1px solid #215941;border-radius:6px;font-weight:700;text-decoration:none;background:#edf5ef}
.fields{margin:0}.field{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr);border-top:1px solid #e4e7e1}
dt,dd{min-width:0;margin:0;padding:10px 12px}dt{color:#42564d;font-weight:650}
pre,code{font:.88rem/1.55 ui-monospace,SFMono-Regular,Consolas,monospace}
pre{white-space:pre-wrap;margin:0}h1,h2,h3,p,li,dt,dd,pre,code,a{overflow-wrap:anywhere}
.history-record,.top-comment{padding:20px 0 6px;border-top:2px solid #d7dfd6}
.history-record:target{outline:3px solid #4f735e;outline-offset:8px}
.empty{padding:12px 0}.back{display:inline-block;margin:14px 0}.integrity{font-size:.85rem;margin-top:16px}
@media(max-width:540px){main{padding:24px 12px 40px}.panel,nav{padding:17px}.field{grid-template-columns:minmax(0,1fr)}dt{padding-bottom:0}dd{padding-top:4px}h1{font-size:2.1rem}}
@media print{:root{background:white;color:black;font-size:10pt}main{padding:0;max-width:none}.panel,nav{border-radius:0;padding:14px}h2,h3,dt{break-after:avoid}.download,.back,.integrity{display:none}a{color:black}.history-record:target{outline:none}}
"""


def _escape(text: str) -> str:
    # Keep HTML-incompatible characters visible; the JSON download is exact.
    visible = "".join(
        f"\\u{ord(char):04x}"
        if (ord(char) < 32 and char not in "\n\t")
        or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF
        else char
        for char in text
    )
    return html.escape(visible, quote=True)


def _json_text(value: Any) -> str:
    return _escape(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))


def _fields(record: dict[str, Any]) -> str:
    if not record:
        return '<dl class="fields"></dl><p class="empty">An empty object was returned.</p>'
    rows = []
    for index, (key, value) in enumerate(record.items()):
        rows.append(
            f'<div class="field" data-field-index="{index}">'
            f"<dt><code>{_json_text(key)}</code></dt>"
            f"<dd><pre>{_json_text(value)}</pre></dd></div>"
        )
    return '<dl class="fields">' + "".join(rows) + "</dl>"


def _json_values(value: Any) -> None:
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("Submission-history values must be finite JSON")
        return
    if type(value) is list:
        for item in value:
            _json_values(item)
        return
    if type(value) is dict and all(isinstance(key, str) for key in value):
        for item in value.values():
            _json_values(item)
        return
    raise TypeError("Submission history must contain only JSON values with string object keys")


def _snapshot(report: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    if not isinstance(report, dict) or not {
        "assignment", "current_submission", "history", "submission_comments"
    }.issubset(report):
        raise ValueError("Expected a complete normalized submission-history report")
    if not isinstance(report["assignment"], dict) or not isinstance(report["current_submission"], dict):
        raise TypeError("Assignment and current submission must be objects")
    history = report["history"]
    if not isinstance(history, dict) or type(history.get("returned")) is not bool or "records" not in history:
        raise ValueError("History availability and records must be explicit")
    records = history["records"]
    if history["returned"]:
        if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
            raise ValueError("Returned history must be a list of record objects")
    elif records is not None:
        raise ValueError("Unavailable history must retain null records")
    comments = report["submission_comments"]
    if comments is not None and (
        not isinstance(comments, list) or any(not isinstance(item, dict) for item in comments)
    ):
        raise ValueError("Submission comments must be null or a list of objects")
    try:
        _json_values(report)
        payload = (json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode("ascii")
    except RecursionError as error:
        raise ValueError("Submission-history nesting exceeds the supported JSON encoder depth") from error
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("Normalized submission-history JSON exceeds the 4 MiB export limit")
    # HTML and its complete JSON download must describe the same frozen values.
    return json.loads(payload), payload


def _created_at(value: datetime | None) -> str:
    stamp = datetime.now(UTC) if value is None else value
    if not isinstance(stamp, datetime) or stamp.utcoffset() is None:
        raise ValueError("Report creation time must be a timezone-aware datetime")
    try:
        return stamp.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (ValueError, OverflowError) as error:
        raise ValueError("Report creation time must be representable in UTC") from error


def render_submission_history_report(
    report: dict[str, Any], *, course_id: int | str, assignment_id: int | str,
    generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Render the unchanged normalized report; no historical attribution is added."""
    course = _numeric_id(course_id, "course_id")
    assignment = _numeric_id(assignment_id, "assignment_id")
    created = _created_at(generated_at)
    view, payload = _snapshot(report)
    history = view["history"]
    records = history["records"]
    comments = view["submission_comments"]
    payload_hash = hashlib.sha256(payload).hexdigest()
    encoded = base64.b64encode(payload).decode("ascii")
    title = view["assignment"].get("name")
    title = title if isinstance(title, str) and title else "Submission history snapshot"
    match = view["current_submission"].get("grade_matches_current_submission")
    if match is False:
        grade_context = (
            "Canvas reports that the current grade does not match the latest submission. "
            "It may describe an earlier attempt; this report does not choose which one."
        )
    elif match is True:
        grade_context = (
            "Canvas reports that the grade matches the current submission. Historical "
            "grades remain only on the records where Canvas returned them."
        )
    else:
        grade_context = (
            "Whether the current grade matches this submission is unavailable or "
            "unrecognized. No match is inferred."
        )
    availability = (
        f"Canvas returned {len(records)} history records, retained in response order."
        if records else "Canvas returned an empty history list."
        if history["returned"] else "Submission history is unavailable in the returned response."
    )
    comment_availability = (
        f"Canvas returned {len(comments)} top-level comments, retained in response order."
        if comments else "Canvas returned an empty top-level comment list."
        if comments is not None else "Top-level submission comments are unavailable in the returned response."
    )
    navigation = [
        '<li><a href="#current-record">Current submission</a></li>',
        '<li><a href="#history-section">Returned history</a></li>',
    ]
    navigation.extend(
        f'<li><a href="#history-record-{index + 1}">Returned record {index + 1}</a></li>'
        for index in range(len(records or []))
    )
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="referrer" content="no-referrer">',
        (
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
        ),
        f"<title>{_escape(title)} — CanvasPilot submission history</title>",
        "<style>", _STYLE, '</style></head><body><main id="top">',
        '<header><p class="eyebrow">CanvasPilot · Saved submission history</p>',
        f"<h1>{_escape(title)}</h1>",
        f"<p>Requested course {_escape(course)} · Assignment {_escape(assignment)}</p>",
        f'<p class="muted">Report created <time datetime="{created}">{created}</time></p>',
        (
            '<p class="notice">This is a fixed copy of the self-submission report returned by '
            "CanvasPilot. Current data, historical records and top-level comments remain separate. "
            "Returned history is not a complete attempt ledger, and no missing version or grade "
            "is reconstructed. Creation time is not a Canvas observation or submission time.</p></header>"
        ),
        '<nav aria-label="Submission report contents"><h2>In this report</h2><ol>',
        "".join(navigation), "</ol></nav>",
        '<section class="panel" id="assignment-record" aria-labelledby="assignment-title">',
        '<h2 id="assignment-title">Assignment metadata</h2>',
        (
            '<p class="muted">These fields are retained as returned, including the reported Canvas '
            "link when available. Requested selectors above remain separate from returned identity fields.</p>"
        ),
        _fields(view["assignment"]), "</section>",
        '<section class="panel" id="current-record" aria-labelledby="current-title">',
        '<h2 id="current-title">Current submission</h2>',
        f'<p class="context" id="current-grade-context">{grade_context}</p>',
        _fields(view["current_submission"]), "</section>",
        '<section class="panel" id="history-section" aria-labelledby="history-title">',
        '<h2 id="history-title">History in returned order</h2>',
        f'<p id="history-availability">{availability}</p>',
        (
            '<p class="muted">Record numbers below are positions in the returned list. Duplicate '
            "or absent attempt values remain as supplied. Fields are never copied from the current "
            "submission or another record. Submitted HTML, links, attachments and media are shown "
            "as literal source text or metadata; their linked content was not downloaded.</p>"
        ),
    ]
    extra_history = {key: value for key, value in history.items() if key not in {"returned", "records"}}
    if extra_history:
        parts.extend(["<h3>Additional history fields</h3>", _fields(extra_history)])
    for index, record in enumerate(records or [], start=1):
        parts.extend([
            f'<article class="history-record" id="history-record-{index}" aria-labelledby="history-record-{index}-title">',
            f'<h3 id="history-record-{index}-title">Returned record {index}</h3>',
            _fields(record), '<a class="back" href="#top">Back to report contents</a></article>',
        ])
    parts.extend([
        '</section><section class="panel" id="comments-section" aria-labelledby="comments-title">',
        '<h2 id="comments-title">Top-level submission comments</h2>',
        (
            '<p id="comments-context" class="context">These comments are not assigned to historical '
            "records by this report. Their own author, attempt, time and content fields remain "
            "as returned. Comments nested inside a record remain on that original record.</p>"
        ),
        f'<p id="comments-availability">{comment_availability}</p>',
    ])
    for index, comment in enumerate(comments or [], start=1):
        parts.extend([
            f'<article class="top-comment" id="top-comment-{index}">',
            f"<h3>Top-level comment {index}</h3>", _fields(comment), "</article>",
        ])
    parts.append("</section>")
    extra = {key: value for key, value in view.items() if key not in {
        "assignment", "current_submission", "history", "submission_comments"
    }}
    if extra:
        parts.extend(['<section class="panel"><h2>Additional report fields</h2>', _fields(extra), "</section>"])
    parts.extend([
        '<section class="panel" aria-labelledby="source-title"><h2 id="source-title">Complete report data</h2>',
        (
            '<p>Values use JSON notation so an absent field, null, false, zero, empty text and an '
            "empty collection keep different meanings. Every original field remains on its record. "
            "The download contains the complete normalized reader result, not the raw HTTP pages, "
            "attached files or a restorable Canvas backup.</p>"
        ),
        (
            f'<p><a class="download" id="download-history" download="submission-history.json" '
            f'href="data:application/json;base64,{encoded}">Download complete report JSON</a></p>'
        ),
        f'<p class="integrity">JSON SHA-256: <code id="json-sha256">{payload_hash}</code></p></section>',
        (
            "<footer>Open this file directly in a browser, or use the browser's Print command. "
            "It contains the returned submission content and comments and does not refresh. "
            "No submission, grade, comment or read state was changed by this export.</footer>"
        ),
        "</main></body></html>\n",
    ])
    content = "".join(parts).encode("utf-8")
    if len(content) > MAX_HTML_BYTES:
        raise ValueError("Rendered submission-history HTML exceeds the 16 MiB export limit")
    return content, {
        "requested_course_id": course, "requested_assignment_id": assignment,
        "generated_at": created, "history_returned": history["returned"],
        "history_records_returned": len(records) if records is not None else None,
        "top_level_comments_returned": len(comments) if comments is not None else None,
        "html_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
        "json_bytes": len(payload), "json_sha256": payload_hash,
    }


def build_submission_history_report(
    api: CanvasAPI, course_id: int | str, assignment_id: int | str, *,
    generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Read the existing self-history report once, then render it locally."""
    course = _numeric_id(course_id, "course_id")
    assignment = _numeric_id(assignment_id, "assignment_id")
    if generated_at is not None:
        _created_at(generated_at)
    report = api.submission_history(course, assignment)
    return render_submission_history_report(
        report, course_id=course, assignment_id=assignment, generated_at=generated_at,
    )
