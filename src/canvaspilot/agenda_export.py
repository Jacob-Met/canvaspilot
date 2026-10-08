"""Render a complete native course agenda as a portable, read-only HTML view."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from canvaspilot.agenda import _record_course, _timing, agenda_selection
from canvaspilot.api import strip_html

MAX_RECORDS = 2000
MAX_NATIVE_BYTES = 4 * 1024 * 1024
GROUPS = ("timed", "all_day", "timing_unavailable")
LABELS = {
    "timed": "Timed",
    "all_day": "All-day",
    "timing_unavailable": "Timing unavailable",
}


def _native_bytes(report: dict[str, Any]) -> bytes:
    """Match the existing agenda CLI representation, including its final LF."""
    try:
        content = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError("Agenda must contain serializable native JSON values") from error
    if len(content) > MAX_NATIVE_BYTES:
        raise ValueError("Agenda exceeds the 4 MiB native JSON limit; choose a smaller selection")
    return content


def _validate(report: Any) -> None:
    if not isinstance(report, dict) or report.get("schema") != "canvaspilot.course-agenda.v1":
        raise ValueError("Expected a native canvaspilot.course-agenda.v1 report")
    selection = report.get("selection")
    if not isinstance(selection, dict):
        raise TypeError("Agenda selection is missing")
    canonical = agenda_selection(
        selection.get("course_ids"),
        start_date=selection.get("start_date"), end_date=selection.get("end_date"),
    )
    if any(selection.get(key) != value for key, value in canonical.items()):
        raise ValueError("Agenda selection must retain its canonical native course context")
    counts, collections = report.get("counts"), report.get("collection_counts")
    if not isinstance(counts, dict) or not isinstance(collections, dict):
        raise TypeError("Agenda counts are missing")
    for group in GROUPS:
        if not isinstance(report.get(group), list):
            raise TypeError(f"Agenda {group} must be a complete list")
    total = sum(len(report[group]) for group in GROUPS)
    if total > MAX_RECORDS:
        raise ValueError("Agenda exceeds the 2000-record limit; choose a smaller selection")
    for name, actual in [("total", total), *((g, len(report[g])) for g in GROUPS)]:
        if type(counts.get(name)) is not int or counts[name] != actual:
            raise ValueError(f"Agenda {name} count does not match its complete records")
    for kind in ("event", "assignment"):
        if type(collections.get(kind)) is not int or not 0 <= collections[kind] <= MAX_RECORDS:
            raise ValueError("Agenda collection counts must be nonnegative integers")
    if sum(collections[kind] for kind in ("event", "assignment")) != total:
        raise ValueError("Agenda collection counts do not match its complete records")
    selected = set(canonical["course_ids"])
    seen: dict[str, set[int]] = {"event": set(), "assignment": set()}
    for group in GROUPS:
        order = []
        for entry in report[group]:
            if not isinstance(entry, dict):
                raise TypeError("Agenda entries must be native objects")
            kind, source, record = entry.get("kind"), entry.get("source"), entry.get("record")
            if not isinstance(kind, str) or kind not in seen or not isinstance(source, dict):
                raise ValueError("Agenda entry source is missing")
            index = source.get("index")
            if (source.get("collection") != kind or type(index) is not int
                    or not 0 <= index < collections[kind] or index in seen[kind]):
                raise ValueError("Agenda source locations must identify every returned record once")
            seen[kind].add(index)
            if not isinstance(record, dict):
                raise TypeError("Agenda source record must be an object")
            # Reuse the producer's validators; do not introduce a second clock
            # parser, a different course binding, or inferred all-day semantics.
            location = f"{kind}[{index}]"
            if entry.get("course_id") != _record_course(record, selected, location):
                raise ValueError("Agenda entry course does not match its supplied source")
            actual_group, key, issue = _timing(record)
            if actual_group != group or entry.get("timing_issue") != issue:
                raise ValueError("Agenda timing group does not match its supplied source")
            origin = (0 if kind == "event" else 1, index)
            order.append(origin if group == "timing_unavailable" else (key, *origin))
        if order != sorted(order):
            raise ValueError("Agenda must retain the native stable order within each timing group")


def _visible(text: str) -> str:
    """Make unrenderable source code points explicit, retaining raw JSON too."""
    return "".join(
        f"\\u{ord(char):04x}"
        if (ord(char) < 32 and char not in "\n\r\t") or ord(char) == 127
        or 0xD800 <= ord(char) <= 0xDFFF else char
        for char in text
    )


def _escape(text: str) -> str:
    return html.escape(_visible(text), quote=True)


def _value(value: Any) -> str:
    # JSON spelling keeps null, false, zero, strings and empty strings distinct.
    return _escape(json.dumps(value, ensure_ascii=False))


def _field(label: str, value: Any) -> str:
    return f"<div><dt>{_escape(label)}</dt><dd>{_value(value)}</dd></div>"


def _entry(entry: dict[str, Any], group: str, position: int) -> str:
    record, course, source = entry["record"], entry["course_id"], entry["source"]
    supplied_title = record.get("title")
    title = supplied_title if isinstance(supplied_title, str) and supplied_title.strip() else "Untitled calendar record"
    if group == "timed":
        source_date = record["start_at"][:10]
        time_label = "Start as supplied"
        time_value = record["start_at"]
        timing = "Original timestamp and offset; no time-zone conversion."
    elif group == "all_day":
        source_date = record["all_day_date"]
        time_label, time_value = "Declared all-day date", source_date
        timing = "The source explicitly marks this record all-day."
    else:
        source_date = ""
        time_label, time_value = "Timing", "Unavailable"
        issue = entry["timing_issue"]
        timing = f"{issue['field']}: {issue['reason']}"
    details = [
        _field("Source ID", record["id"]),
        _field("Source location", f"{source['collection']}[{source['index']}]"),
    ]
    for key, label in (
        ("context_code", "Original context"), ("effective_context_code", "Effective context"),
        ("start_at", "Original start"), ("end_at", "Original end"),
        ("all_day", "Original all-day flag"), ("all_day_date", "Original all-day date"),
        ("cancelled", "Source cancellation flag"),
        ("location_name", "Location name"), ("location_address", "Location address"),
        ("html_url", "Source URL (saved text)"),
    ):
        if key in record:
            details.append(_field(label, record[key]))
    assignment = record.get("assignment")
    if isinstance(assignment, dict):
        for key, label in (("id", "Assignment ID"), ("due_at", "Assignment due as supplied"),
                           ("points_possible", "Points possible as supplied")):
            if key in assignment:
                details.append(_field(label, assignment[key]))
    description = record.get("description")
    if isinstance(description, str):
        readable = strip_html(description)
        description_html = (
            '<div class="description"><h4>Description · text from supplied HTML</h4>'
            f"<p>{_escape(readable) if readable else 'No readable text in the supplied description.'}</p></div>"
        )
    else:
        description_html = '<p class="quiet">No description text was supplied. Original fields remain below.</p>'
    cancel = '<span class="source-flag">Source cancelled: true</span>' if record.get("cancelled") is True else ""
    raw = _escape(json.dumps(entry, indent=2, ensure_ascii=False))
    return f"""<article class="agenda-entry" data-course="{_escape(course)}" data-date="{source_date}" data-group="{group}" aria-labelledby="entry-{group}-{position}">
<header class="entry-heading"><p class="entry-context">Course {_escape(course)} <span>· {entry['kind']}</span> {cancel}</p>
<h3 id="entry-{group}-{position}">{_escape(title)}</h3></header>
<p class="entry-time"><span>{time_label}</span><strong>{_escape(time_value)}</strong></p>
<p class="timing-note">{_escape(timing)}</p>
{description_html}
<dl class="entry-metadata">{''.join(details)}</dl>
<details class="source-details"><summary>Inspect complete saved source</summary><pre tabindex="0" aria-label="Complete saved source for {_escape(title)}">{raw}</pre></details>
</article>"""


def render_agenda_html(report: dict[str, Any]) -> bytes:
    """Prepare the whole view; never mutate the native report or contact Canvas."""
    _validate(report)
    native = _native_bytes(report)
    selection, counts = report["selection"], report["counts"]
    courses = selection["course_ids"]
    options = '<option value="">All selected courses</option>' + "".join(
        f'<option value="{_escape(course)}">Course {_escape(course)}</option>' for course in courses
    )
    course_text = ", ".join(f"Course {course}" for course in courses)
    date_text = f"{selection['start_date']} to {selection['end_date']}"
    explanations = {
        "timed": "Ordered by the native exact instant, with the original timestamp and offset displayed.",
        "all_day": "Only records with an explicit all-day flag and a valid supplied date.",
        "timing_unavailable": "No date or instant is inferred. These entries stay in every source-date view after course and text filtering.",
    }
    sections = []
    for group in GROUPS:
        entries = "\n".join(_entry(entry, group, i) for i, entry in enumerate(report[group]))
        empty = "" if not counts[group] else " hidden"
        sections.append(f"""<section class="agenda-section" id="section-{group}" aria-labelledby="heading-{group}">
<div class="section-heading"><h2 id="heading-{group}">{LABELS[group]}</h2><p><span data-visible-count="{group}">{counts[group]}</span> of {counts[group]} shown</p></div>
<p class="section-explanation">{explanations[group]}</p>
<p class="empty-state" data-empty="{group}"{empty}>No {LABELS[group].lower()} entries in this view.</p>
<div class="entry-list">{entries}</div></section>""")
    asset_root = Path(__file__).with_name("agenda_view")
    style = (asset_root / "style.css").read_text(encoding="utf-8")
    script = (asset_root / "controls.js").read_text(encoding="utf-8")
    encoded = base64.b64encode(native).decode("ascii")
    native_sha = hashlib.sha256(native).hexdigest()
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer"><title>Course agenda · {_escape(date_text)}</title>
<style>{style}</style></head>
<body><a class="skip-link" href="#agenda">Skip to agenda</a><main class="page">
<header class="page-header"><p class="eyebrow">CanvasPilot · saved course agenda</p>
<h1>Your selected-course agenda</h1><p class="lede">Events and assignment calendar records, together in one readable snapshot.</p>
<dl class="snapshot-context"><div><dt>Selected courses</dt><dd>{_escape(course_text)}</dd></div>
<div><dt>Requested Canvas date range</dt><dd>{_escape(date_text)}</dd></div>
<div><dt>Returned collections</dt><dd>{report['collection_counts']['event']} event records · {report['collection_counts']['assignment']} assignment records</dd></div></dl>
<p class="snapshot-note">Saved read-only observation. Canvas chose the returned date range; the two calendar collections were read sequentially. Check Canvas for changes. This view does not infer completion, grades, attendance or availability.</p>
<div class="actions"><a class="button secondary" id="download-native" download="course-agenda.json" data-sha256="{native_sha}" href="data:application/json;base64,{encoded}">Download original agenda JSON</a>
<button class="button" type="button" id="print-agenda" hidden>Print this view</button></div></header>
<section class="view-tools" aria-labelledby="view-title" hidden id="view-tools"><h2 id="view-title">Choose your view</h2>
<form id="agenda-filters"><div class="filters"><label>Course<select id="course-filter">{options}</select></label>
<label>Source date<input type="date" id="date-filter" aria-describedby="date-help"></label>
<label class="search-label">Search saved entries<input type="search" id="search-filter" placeholder="Title, course, location or source text" autocomplete="off"></label>
<button class="button secondary" type="reset">Reset view</button></div></form>
<p class="filter-help" id="date-help">Source date means the date written in the original timestamp or declared all-day date, without time-zone conversion. Unavailable timing remains visible for the selected course and search.</p></section>
<noscript><p class="noscript-note">The complete saved agenda is shown. Enable JavaScript to filter; the original JSON download and all saved entries work without it.</p></noscript>
<section class="view-summary" aria-label="Current view"><p id="view-count" role="status" aria-live="polite">Showing {counts['total']} of {counts['total']} saved entries</p>
<p id="view-context">All selected courses · All source dates · No text filter</p></section>
<div id="agenda" tabindex="-1">{''.join(sections)}</div>
<footer><h2>Keep the source context</h2><p>Course IDs are the selected identifiers, not inferred course names. Source IDs retain their original JSON type. Repeated records remain separate at their original collection positions. Original descriptions and all nested fields are retained in each source disclosure and in the byte-identical native JSON download.</p>
<p>Filters affect only this displayed and printed view. Nothing is saved to browser storage or sent to Canvas. A new export is needed for a newer observation.</p>
<details class="report-details"><summary>Inspect the complete native agenda report</summary><pre tabindex="0" aria-label="Complete native agenda report">{_escape(native.decode('utf-8'))}</pre></details>
<p class="native-digest">Native JSON SHA256 <code>{native_sha}</code></p></footer>
</main><script>{script}</script></body></html>
"""
    return page.encode("utf-8")


def write_agenda_html(path: Path, content: bytes) -> None:
    """Publish complete bytes to a new path, preserving every existing entry."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="." + path.name + ".", suffix=".tmp", dir=path.parent, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        # Atomic create-only publication; no replacement or rename fallback.
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink()
