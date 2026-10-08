"""Offline HTML for the existing normalized, read-only module-progress report."""

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
:root { color-scheme: light; font: 16px/1.55 system-ui, sans-serif; color: #192d38; background: #eef3f4; }
* { box-sizing: border-box; }
body { margin: 0; }
main { max-width: 1050px; margin: auto; padding: 36px 24px 64px; }
h1, h2, h3, p { margin-top: 0; }
h1 { font-size: clamp(1.8rem, 5vw, 2.8rem); line-height: 1.16; margin-bottom: 14px; }
h2 { font-size: 1.45rem; line-height: 1.3; }
h3 { font-size: 1.05rem; margin-bottom: 10px; }
.eyebrow { letter-spacing: .09em; text-transform: uppercase; font-weight: 700; color: #365565; }
.muted { color: #465c68; }
header, .overview, .module { margin-bottom: 24px; }
.overview, .module { background: white; border: 1px solid #cad8de; border-radius: 12px; padding: 24px; }
.notice { border-left: 4px solid #466d7b; padding: 12px 16px; background: #e8f0f3; }
.facts { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); margin: 0 0 24px; }
.facts dt, .facts dd { min-width: 0; margin: 0; padding: 8px 10px; border-bottom: 1px solid #e3e9ec; }
.facts dt { color: #38515e; font-weight: 600; }
pre, code { font: .9rem/1.5 ui-monospace, SFMono-Regular, Consolas, monospace; }
pre { white-space: pre-wrap; margin: 0; }
h1, h2, h3, p, li, dt, dd, code, pre, a { overflow-wrap: anywhere; }
nav ul { padding-left: 22px; }
nav li { margin: 7px 0; }
a { color: #125781; text-decoration-thickness: .1em; text-underline-offset: .18em; }
a:focus-visible { outline: 3px solid #125781; outline-offset: 4px; }
.download { display: inline-block; padding: 10px 16px; border: 1px solid #125781; border-radius: 6px; background: #f0f7fa; font-weight: 650; }
.badge { display: inline-block; font-size: .9rem; font-weight: 650; background: #edf2f4; padding: 4px 10px; border-radius: 5px; margin: 0 0 12px; }
.items { padding-left: 22px; margin-bottom: 0; }
.item { padding: 18px 0 6px 6px; border-top: 2px solid #d9e4e9; }
.item .facts { margin-bottom: 14px; }
.empty { padding: 14px 0; }
.back { font-size: .9rem; }
footer { color: #465c68; font-size: .9rem; }
@media (max-width: 540px) {
  main { padding: 22px 12px 36px; }
  .overview, .module { padding: 16px; }
  .facts { grid-template-columns: minmax(0, 1fr); }
  .facts dt { border-bottom: 0; padding-bottom: 0; }
  .facts dd { padding-top: 2px; }
}
@media print {
  :root { background: white; font-size: 10pt; color: black; }
  main { max-width: none; padding: 0; }
  .overview, .module { padding: 14px; border-radius: 0; }
  h2, h3, dt { break-after: avoid; }
  .download, .back { display: none; }
  a { color: black; }
}
"""

_LABELS = {
    "state": "State from the progress reader",
    "reported_state": "Original reported state",
    "requirement_type": "All-versus-one requirement rule",
    "reported_requirement_type": "Original reported requirement rule",
    "require_sequential_progress": "Sequential progress required",
    "prerequisite_module_ids": "Prerequisite module IDs",
    "reported_prerequisite_module_ids": "Original prerequisite module IDs",
    "collection_complete": "Whole collection complete",
    "completion_status": "Requirement completion status",
    "completion_requirement": "Complete reported requirement and thresholds",
    "requirement_type_supported": "Requirement type supported by the reader",
    "required_action": "Reported required action",
    "module_locked": "Module locked",
    "item_access": "Individual item access",
    "reported_count": "Reported item count",
    "returned_count": "Returned item count",
    "incomplete_item_ids": "Reported incomplete item IDs",
    "unknown_completion_item_ids": "Item IDs with unknown completion",
}


def _escape(text: str) -> str:
    # Headings can contain provider text. Make HTML-incompatible characters
    # visible instead of allowing the browser to silently replace them.
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
    # JSON notation distinguishes null, false, zero, empty text and empty lists.
    return "<pre>" + _escape(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)) + "</pre>"


def _facts(values: dict[str, Any]) -> str:
    rows = []
    for key, value in values.items():
        label = _LABELS.get(key, key.replace("_", " ").capitalize())
        rows.append(
            f'<dt>{_escape(label)}</dt><dd data-field="{_escape(key)}">{_value(value)}</dd>'
        )
    return '<dl class="facts">' + "".join(rows) + "</dl>"


def _heading(value: Any, fallback: str) -> str:
    return _escape(value) if isinstance(value, str) and value else _escape(fallback)


def _module(module: dict[str, Any], index: int) -> str:
    identity = f"module-{index}"
    title = _heading(module["name"], f"Module {module['id']}")
    grouped = {"items", "item_coverage", "requirement_counts", "remaining_work", "diagnostics"}
    parts = [
        f'<section class="module" id="{identity}" aria-labelledby="{identity}-title">',
        f'<h2 id="{identity}-title">{title}</h2>',
        f'<p class="badge">Reported module state: {_escape(module["state"])}</p>',
        _facts({key: value for key, value in module.items() if key not in grouped}),
        "<h3>Returned item coverage</h3>",
        _facts(module["item_coverage"]),
        "<h3>Requirement counts in returned items</h3>",
        _facts(module["requirement_counts"]),
        "<h3>Reported remaining work</h3>",
        (
            '<p class="muted">Read these IDs with the reported rule. Under a one-of rule, '
            "incomplete items are alternatives, not a count of required tasks. A completed "
            "module can still contain incomplete alternatives. Item access is not assessed.</p>"
        ),
        _facts(module["remaining_work"]),
        "<h3>Reader diagnostics</h3>",
    ]
    diagnostics = module["diagnostics"]
    parts.append(
        "<ul>" + "".join("<li>" + _escape(message) + "</li>" for message in diagnostics) + "</ul>"
        if diagnostics else "<p>No reader diagnostics were returned.</p>"
    )
    parts.append("<h3>Items in returned order</h3>")
    if not module["items"]:
        parts.append('<p class="empty">No items were returned for this module. '
                     "This does not establish completion or optionality.</p>")
    else:
        parts.append('<ol class="items">')
        for item_index, item in enumerate(module["items"]):
            item_title = _heading(item["title"], f"Item {item['id']}")
            parts.extend([
                f'<li class="item" id="{identity}-item-{item_index}">',
                f"<h3>{item_title}</h3>",
                _facts(item),
                "</li>",
            ])
        parts.append("</ol>")
    parts.append('<a class="back" href="#top">Back to report overview</a></section>')
    return "".join(parts)


def render_module_progress_report(
    report: dict[str, Any], *, generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Render a normalized CanvasAPI.module_progress result without rewriting it.

    The complete JSON download is the report, not raw Canvas response pages.
    Values and array order are retained. The timestamp records report creation,
    not a transactionally consistent observation time at Canvas.
    """
    stamp = datetime.now(UTC) if generated_at is None else generated_at
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("Report creation time must include a timezone")
    created = stamp.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = (json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode("ascii")
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("Normalized module-progress JSON exceeds the 4 MiB export limit")
    payload_hash = hashlib.sha256(payload).hexdigest()
    encoded = base64.b64encode(payload).decode("ascii")
    modules = report["modules"]
    top = {key: value for key, value in report.items() if key not in {"modules", "module_state_counts"}}
    navigation = []
    for index, module in enumerate(modules):
        title = _heading(module["name"], f"Module {module['id']}")
        navigation.append(
            f'<li><a href="#module-{index}">{title}</a>'
            f' <span class="muted">· {_escape(module["state"])}</span></li>'
        )
    navigation_panel = (
        '<nav class="overview" aria-label="Modules in returned order">'
        '<h2>Modules in this report</h2><ul>' + "".join(navigation) + "</ul></nav>"
        if modules else '<section class="overview"><p class="empty">No modules were returned. '
        "This does not establish that the course has no modules.</p></section>"
    )
    parts = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="referrer" content="no-referrer">',
        (
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
        ),
        "<title>Module progress snapshot — CanvasPilot</title>",
        "<style>", _STYLE, "</style></head><body><main id=\"top\">",
        '<header><p class="eyebrow">CanvasPilot · Saved progress report</p>',
        "<h1>Module progress snapshot</h1>",
        (
            f'<p>Course {_escape(str(report["course_id"]))} · Report created '
            f'<time datetime="{created}">{created}</time></p>'
        ),
        (
            '<p class="notice">This is a saved observation for the authenticated caller. '
            "It does not refresh. Canvas supplies the module state; this report does not "
            "calculate completion, a percentage, or item access. Counts describe returned "
            "rows, and whole-course completeness remains unknown.</p></header>"
        ),
        navigation_panel,
        '<section class="overview" aria-labelledby="overview-title">',
        '<h2 id="overview-title">Report scope</h2>',
        (
            '<p class="muted">Values use JSON notation so null, false, zero, empty text, '
            "and empty lists stay distinct. Unsupported original "
            "values and thresholds stay visible.</p>"
        ),
        _facts(top),
        "<h3>Module state counts in this selection</h3>",
        _facts(report["module_state_counts"]),
        (
            f'<p><a class="download" id="download-report" download="module-progress.json" '
            f'href="data:application/json;base64,{encoded}">Download complete report JSON</a></p>'
        ),
        (
            '<p class="muted">This download contains the complete normalized progress '
            "report used below. It does not contain the original HTTP response pages.</p>"
        ),
        f'<p class="muted">JSON SHA-256: <code id="json-sha256">{payload_hash}</code></p>',
    ]
    parts.append("</section>")
    parts.extend(_module(module, index) for index, module in enumerate(modules))
    parts.append("<footer>Open this file directly in a browser. Use the browser's Print command "
                 "for a paper copy or PDF. The report has no scripts, external resources, or "
                 "editable completion controls.</footer></main></body></html>\n")
    content = "".join(parts).encode("utf-8")
    if len(content) > MAX_HTML_BYTES:
        raise ValueError("Rendered module-progress HTML exceeds the 16 MiB export limit")
    return content, {
        "course_id": report["course_id"],
        "module_id": report["module_id"],
        "modules_returned": report["modules_returned"],
        "modules_included": report["modules_included"],
        "generated_at": created,
        "html_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "json_bytes": len(payload),
        "json_sha256": payload_hash,
    }


def build_module_progress_report(
    api: CanvasAPI, course_id: int | str, *,
    module_id: int | str | None = None, generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Read the existing progress report exactly once, then render it locally."""
    report = api.module_progress(course_id, module_id=module_id)
    return render_module_progress_report(report, generated_at=generated_at)
