"""Readable offline HTML for the unchanged cached discussion-thread report."""

from __future__ import annotations

import base64
import hashlib
import html
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from canvaspilot.discussion_thread import validate_discussion_selection

if TYPE_CHECKING:
    from canvaspilot.api import CanvasAPI

MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_HTML_BYTES = 16 * 1024 * 1024

_STYLE = """
:root { color-scheme: light; font: 16px/1.6 system-ui, sans-serif; color: #20343d; background: #eef3f4; }
* { box-sizing: border-box; }
body { margin: 0; }
main { max-width: 960px; margin: auto; padding: 36px 24px 60px; }
h1, h2, h3, p { margin-top: 0; }
h1 { font-size: clamp(1.8rem, 5vw, 2.7rem); line-height: 1.2; }
h2 { font-size: 1.5rem; line-height: 1.3; }
h3 { font-size: 1.12rem; }
h1, h2, h3, p, li, dt, dd, pre, a, summary { overflow-wrap: anywhere; }
.eyebrow { letter-spacing: .08em; text-transform: uppercase; font-weight: 700; color: #3e5e6b; }
.panel, .entry { background: white; border: 1px solid #c6d6dc; border-radius: 10px; padding: 24px; margin: 24px 0; }
.notice { border-left: 4px solid #416878; background: #e5eef1; padding: 12px 16px; }
.muted { color: #48606b; }
.body-text { white-space: pre-wrap; }
.badge { display: inline-block; border: 1px solid #bfd0d7; border-radius: 4px; padding: 3px 9px; margin: 0 6px 8px 0; font-size: .9rem; }
.context { border-left: 5px solid #8e753c; }
.facts { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); margin: 12px 0; }
.facts dt, .facts dd { min-width: 0; margin: 0; padding: 7px 10px; border-bottom: 1px solid #e2e9ec; }
.facts dt { font-weight: 600; }
pre, code { font: .87rem/1.5 ui-monospace, SFMono-Regular, Consolas, monospace; }
pre { white-space: pre-wrap; margin: 0; }
a { color: #125779; text-underline-offset: .18em; }
a:focus-visible, summary:focus-visible { outline: 3px solid #125779; outline-offset: 4px; }
summary { cursor: pointer; font-weight: 650; padding: 10px 0; }
details { margin-top: 12px; }
nav ol { padding-left: 24px; }
nav li { margin: 6px 0; }
.download { display: inline-block; padding: 10px 14px; border: 1px solid #125779; border-radius: 5px; background: #f0f7fa; }
.back, footer { font-size: .9rem; }
@media (max-width: 540px) {
  main { padding: 22px 12px 36px; }
  .panel, .entry { padding: 16px; }
  .facts { grid-template-columns: minmax(0, 1fr); }
  .facts dt { border-bottom: 0; padding-bottom: 0; }
  .facts dd { padding-top: 2px; }
}
@media print {
  :root { background: white; color: black; font-size: 10pt; }
  main { max-width: none; padding: 0; }
  .panel, .entry { border-radius: 0; padding: 14px; }
  h2, h3 { break-after: avoid; }
  .download, .back, nav { display: none; }
  a { color: black; }
}
"""


def _escape(text: str) -> str:
    visible = "".join(
        f"\\u{ord(character):04x}"
        if (ord(character) < 32 and character not in "\n\t")
        or 127 <= ord(character) <= 159
        or 0xD800 <= ord(character) <= 0xDFFF
        else character
        for character in text
    )
    return html.escape(visible, quote=True)


def _value(value: Any) -> str:
    return "<pre>" + _escape(json.dumps(
        value, ensure_ascii=True, allow_nan=False, indent=2,
    )) + "</pre>"


def _facts(values: dict[str, Any]) -> str:
    return '<dl class="facts">' + "".join(
        f'<dt>{_escape(key.replace("_", " ").capitalize())}</dt>'
        f'<dd data-field="{_escape(key)}">{_value(value)}</dd>'
        for key, value in values.items()
    ) + "</dl>"


def _body(value: str | None, *, deleted: bool = False) -> str:
    if deleted:
        return '<p class="body-text muted">Deleted entry; body text is unavailable.</p>'
    if value is None:
        return '<p class="body-text muted">The reader returned no body text.</p>'
    if value == "":
        return '<p class="body-text muted">The reader returned empty text.</p>'
    return '<p class="body-text">' + _escape(value) + "</p>"


def _author(row: dict[str, Any]) -> str:
    if row["entry"].get("deleted") is True:
        return "Author unavailable for this deleted entry"
    author = row["author"]
    if author is None:
        return "Author unavailable or ambiguous"
    name = author.get("display_name")
    if isinstance(name, str) and name:
        return name
    return "Matched participant; display name unavailable"


def _entry(row: dict[str, Any], index: int, by_path: dict[tuple[int, ...], int]) -> str:
    identity = f"entry-{index}"
    parent = row["parent_path"]
    parent_index = by_path.get(tuple(parent)) if parent is not None else None
    parent_navigation = (
        f'<a href="#entry-{parent_index}">Go to parent entry {parent_index + 1}</a>'
        if parent_index is not None
        else "Root entry in the returned tree" if parent is None
        else "Parent is not in this selection"
    )
    context = bool(row["context_only"])
    metadata = {key: value for key, value in row.items()
                if key not in {"entry", "message_text", "author"}}
    return "".join([
        (
            f'<article class="entry{" context" if context else ""}" id="{identity}" '
            f'aria-labelledby="{identity}-title">'
        ),
        f'<h3 id="{identity}-title">Entry {index + 1} · {_escape(_author(row))}</h3>',
        f'<span class="badge">Read state: {_escape(row["read_state"])}</span>',
        '<span class="badge">Context for an unread descendant</span>' if context else "",
        f'<p class="muted">{parent_navigation}</p>',
        _body(row["message_text"], deleted=row["entry"].get("deleted") is True),
        _facts(metadata),
        "<details><summary>Author association and original entry fields</summary>",
        (
            '<p class="muted">Source markup and URLs below are text, not active content. '
            "The original parent ID does not replace the structural parent path.</p>"
        ),
        _facts({"author": row["author"], "entry": row["entry"]}),
        "</details>",
        '<a class="back" href="#entries-nav">Back to entries</a></article>',
    ])


def render_discussion_report(
    report: dict[str, Any], *, course_id: int | str, topic_id: int | str,
    generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Present a normalized report without rewriting its fields or returned order.

    Requested IDs belong to export context, not the normalized JSON download.
    Creation time is not the observation time or freshness of Canvas's cache.
    """
    course, topic = validate_discussion_selection(course_id, topic_id, False)
    stamp = datetime.now(UTC) if generated_at is None else generated_at
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("Report creation time must include a timezone")
    created = stamp.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = (json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode("ascii")
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("Normalized discussion JSON exceeds the 4 MiB export limit")
    payload_hash = hashlib.sha256(payload).hexdigest()
    encoded = base64.b64encode(payload).decode("ascii")
    entries = report["entries"]
    by_path = {tuple(row["path"]): index for index, row in enumerate(entries)}
    title = report["topic"].get("title")
    title = title if isinstance(title, str) and title else "Discussion thread"
    navigation = "".join(
        f'<li><a href="#entry-{index}">Entry {index + 1} · {_escape(_author(row))}</a>'
        f' <span class="muted">· {_escape(row["read_state"])}'
        f'{" · context only" if row["context_only"] else ""}</span></li>'
        for index, row in enumerate(entries)
    )
    warnings = report["warnings"]
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="referrer" content="no-referrer">',
        (
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
        ),
        "<title>Discussion snapshot — CanvasPilot</title><style>", _STYLE,
        '</style></head><body><main id="top">',
        '<header><p class="eyebrow">CanvasPilot · Saved discussion</p>',
        f"<h1>{_escape(title)}</h1>",
        (
            f"<p>Requested course {_escape(course)} · topic {_escape(topic)}<br>"
            f'Report created <time datetime="{created}">{created}</time></p>'
        ),
        (
            '<p class="notice">This is a saved reading of Canvas\'s cached, eventually consistent '
            "discussion view. It does not refresh or establish that the cache contains the latest "
            "posts. Creating this report does not post, mark entries read, rate, or subscribe. "
            "Creation time is not Canvas's observation time.</p></header>"
        ),
        '<section class="panel" aria-labelledby="scope-title"><h2 id="scope-title">Reading scope</h2>',
        _facts({"selection": report["selection"], **report["counts"]}),
        (
            '<p class="muted">Counts describe the observed tree and returned selection. Topic counts '
            "may differ. Unread focus includes known unread entries and their ancestors; context "
            "entries are not additional unread replies. Unknown read states stay unknown.</p>"
        ),
        "<h3>Reader warnings</h3>",
        "<ul>" + "".join("<li>" + _escape(warning) + "</li>" for warning in warnings) + "</ul>"
        if warnings else "<p>No reader warnings were returned.</p>",
        _facts({"unmatched_unread_entries": report["unmatched_unread_entries"]}),
        '<details><summary>Cache source and original view metadata</summary>',
        _facts({"source": report["source"], "view_metadata": report["view_metadata"]}),
        (
            '<p class="muted">A separate new-entry stream, when supplied in metadata, is not merged '
            "into the returned tree. Paths describe this view only and are not persistent entry IDs.</p>"
        ),
        "</details>",
        (
            f'<p><a class="download" id="download-report" download="discussion-thread.json" '
            f'href="data:application/json;base64,{encoded}">Download complete report JSON</a></p>'
        ),
        (
            '<p class="muted">The download is the complete normalized reader report, not the original '
            "HTTP response pages. Requested IDs and report creation time are separate export context.</p>"
        ),
        f'<p class="muted">JSON SHA-256: <code id="json-sha256">{payload_hash}</code></p></section>',
        '<section class="panel" aria-labelledby="topic-title"><h2 id="topic-title">Topic</h2>',
        _body(report["topic_message_text"]),
        "<details><summary>Original topic fields</summary>",
        _facts({"topic": report["topic"]}), "</details></section>",
        (
            '<nav class="panel" id="entries-nav" aria-label="Entries in returned order">'
            "<h2>Entries in returned order</h2>"
        ),
        "<ol>" + navigation + "</ol>" if entries else
        '<p>No entries are included in this selection. This does not establish that the '
        "discussion has no posts or that the cached view is complete.</p>",
        "</nav>",
    ]
    parts.extend(_entry(row, index, by_path) for index, row in enumerate(entries))
    parts.append(
        "<footer>Open this file directly in a browser. Use the browser's Print command "
        "for paper or PDF. The report has no scripts, external resources, or read-state controls. "
        "Source fields use JSON notation so null, false, zero, empty text and empty lists "
        "remain distinct.</footer></main></body></html>\n"
    )
    content = "".join(parts).encode("utf-8")
    if len(content) > MAX_HTML_BYTES:
        raise ValueError("Rendered discussion HTML exceeds the 16 MiB export limit")
    return content, {
        "course_id": course, "topic_id": topic, "selection": report["selection"],
        "entries_included": len(entries), "generated_at": created,
        "html_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
        "json_bytes": len(payload), "json_sha256": payload_hash,
    }


def build_discussion_report(
    api: CanvasAPI, course_id: int | str, topic_id: int | str, *,
    unread_only: bool = False, generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Read the existing discussion report once, then render it locally."""
    report = api.discussion_thread(course_id, topic_id, unread_only=unread_only)
    return render_discussion_report(
        report, course_id=course_id, topic_id=topic_id, generated_at=generated_at,
    )
