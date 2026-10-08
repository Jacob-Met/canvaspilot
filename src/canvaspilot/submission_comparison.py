"""Compare two explicitly selected Canvas-returned submission records offline."""

from __future__ import annotations

import base64
import json
import os
import re
import tempfile
from difflib import SequenceMatcher
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING, Any

from canvaspilot.submission_history import _numeric_id

if TYPE_CHECKING:
    from canvaspilot.api import CanvasAPI

MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_TEXT_LINES = 2_000
MAX_TEXT_CHARACTERS = 250_000
MAX_LINE_PAIRS = 1_000_000
_MISSING = object()
_SELECTOR = re.compile(r"history:([1-9][0-9]*)")
_MEDIA_FIELDS = ("media_comment", "media_comment_id", "media_comment_type")


def _validate_selector(selector: str) -> None:
    if not isinstance(selector, str) or (selector != "current" and not _SELECTOR.fullmatch(selector)):
        raise ValueError("Choose current or history:N, with N a positive index without leading zeroes")


def _validate_pair(before: str, after: str) -> None:
    _validate_selector(before)
    _validate_selector(after)
    if before == after:
        raise ValueError("Choose two different selectors; history positions may still contain equal records")


def _select(history: dict[str, Any], selector: str) -> dict[str, Any]:
    if selector == "current":
        record = history.get("current_submission")
        if not isinstance(record, dict):
            raise ValueError("Canvas returned a malformed current submission")
        return record
    returned = history.get("history")
    if not isinstance(returned, dict) or returned.get("returned") is not True:
        raise ValueError(f"{selector} is unavailable: Canvas did not return submission history")
    records = returned.get("records")
    if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
        raise ValueError("Canvas returned malformed submission history")
    digits = selector.removeprefix("history:")
    last = str(len(records))
    # Bound conversion by the actual list length, including very long selectors.
    if len(digits) > len(last) or (len(digits) == len(last) and digits > last):
        raise ValueError(f"{selector} is outside the {len(records)} returned history records")
    return records[int(digits) - 1]


def _identity(record: dict[str, Any], field: str, expected: str, context: str) -> None:
    if field in record and record[field] is not None:
        try:
            actual = _numeric_id(record[field], field)
        except ValueError:
            raise ValueError(f"{context} has an invalid {field}") from None
        if actual != expected:
            raise ValueError(f"{context} {field} does not match the requested assignment context")


def _json(value: Any, *, pretty: bool = False) -> str:
    try:
        return json.dumps(value, ensure_ascii=True, allow_nan=False,
                          indent=2 if pretty else None, sort_keys=not pretty)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError("Selected records must contain finite, serializable JSON values") from error


def _source_bytes(comparison: dict[str, Any]) -> bytes:
    # The reader returns JSON. Reject custom non-JSON values rather than silently
    # turning tuples or non-string dictionary keys into a different record.
    pending = [comparison]
    while pending:
        value = pending.pop()
        if type(value) is dict:
            if any(type(key) is not str for key in value):
                raise ValueError("Selected record object keys must be strings")
            pending.extend(value.values())
        elif type(value) is list:
            pending.extend(value)
        elif type(value) not in (str, int, float, bool, type(None)):
            raise ValueError("Selected records must contain JSON values")
    data = (_json(comparison, pretty=True) + "\n").encode("utf-8")
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("Selected source data exceeds the 2 MiB report limit; inspect submission-history JSON")
    return data


def build_submission_comparison(
    history: dict[str, Any], *, course_id: int | str, assignment_id: int | str,
    before: str, after: str,
) -> dict[str, Any]:
    """Select by returned position, preserving both records without enrichment."""
    _validate_pair(before, after)
    course = _numeric_id(course_id, "course_id")
    assignment_id = _numeric_id(assignment_id, "assignment_id")
    if not isinstance(history, dict) or not isinstance(history.get("assignment"), dict):
        raise TypeError("Canvas returned a malformed assignment summary")
    assignment = history["assignment"]
    _identity(assignment, "id", assignment_id, "Assignment")
    _identity(assignment, "course_id", course, "Assignment")
    selected = {}
    for label, selector in (("before", before), ("after", after)):
        record = _select(history, selector)
        _identity(record, "assignment_id", assignment_id, selector)
        _identity(record, "course_id", course, selector)
        selected[label] = {"selector": selector, "record": record}
    returned = history.get("history")
    records = returned.get("records") if isinstance(returned, dict) else None
    comparison = {
        "format": "canvaspilot.submission-comparison.v1",
        "request": {"course_id": course, "assignment_id": assignment_id},
        "assignment": assignment,
        "history": {
            "returned": isinstance(returned, dict) and returned.get("returned") is True,
            "record_count": len(records) if isinstance(records, list) else None,
        },
        **selected,
    }
    return json.loads(_source_bytes(comparison))


def _visible(text: str) -> str:
    """Keep controls visible while preserving exact values in the JSON packet."""
    return "".join(
        f"\\u{ord(char):04x}"
        if ((ord(char) < 32 and char not in "\n\t")
            or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF
            or 0x202A <= ord(char) <= 0x202E or 0x2066 <= ord(char) <= 0x2069)
        else char for char in text
    )


def _html(text: str) -> str:
    return escape(_visible(text), quote=True)


def _value(value: Any) -> str:
    if value is _MISSING:
        return '<span class="state">Omitted — key not returned</span>'
    if value is None:
        return '<span class="state">Null — explicitly returned</span>'
    if type(value) is str and value == "":
        return '<span class="state">Blank string — &quot;&quot;</span>'
    if type(value) is list and not value:
        return '<span class="state">Empty list — []</span>'
    if type(value) is dict and not value:
        return '<span class="state">Empty object — {}</span>'
    text = value if isinstance(value, str) else json.dumps(
        value, ensure_ascii=False, allow_nan=False, indent=2,
    )
    return f'<pre class="value">{_html(text)}</pre>'


def _same(left: Any, right: Any) -> bool:
    if left is _MISSING or right is _MISSING:
        return left is right
    return _json(left) == _json(right)


def _status(left: Any, right: Any) -> str:
    if left is _MISSING and right is _MISSING:
        return "Omitted in both records"
    return "Same returned value" if _same(left, right) else "Different returned values"


class _BodyText(HTMLParser):
    _BLOCKS = frozenset({
        "address", "article", "aside", "blockquote", "div", "dl", "dt", "dd",
        "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3",
        "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p",
        "pre", "section", "table", "tr", "ul",
    })
    _IGNORED = frozenset({"script", "style", "template", "noscript"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._IGNORED:
            self.ignored.append(tag)
        if self.ignored:
            return
        if tag in self._BLOCKS or tag == "br":
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append("\t")
        elif tag == "img":
            alt = next((value for name, value in attrs if name == "alt"), None)
            if alt:
                self.parts.append(f"[Image: {alt}]")

    def handle_endtag(self, tag: str) -> None:
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
            return
        if tag in self._BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.parts.append(data)


def readable_body(body: str) -> str:
    """A text reading aid, not rendered HTML or an exact body representation."""
    parser = _BodyText()
    parser.feed(body)
    parser.close()
    return "".join(parser.parts).replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def _pair(left: str, right: str, *, left_label: str = "Before", right_label: str = "After") -> str:
    return (
        '<div class="pair">'
        f'<div class="side"><h3>{_html(left_label)}</h3>{left}</div>'
        f'<div class="side"><h3>{_html(right_label)}</h3>{right}</div></div>'
    )


def _line(number: int | None, text: str, kind: str) -> str:
    if number is None:
        return '<div class="diff-line empty" aria-hidden="true"></div>'
    marker = {"removed": "−", "added": "+", "context": " "}[kind]
    label = {"removed": "Removed", "added": "Added", "context": "Context"}[kind]
    return (
        f'<div class="diff-line {kind}"><span class="line-number">{number}</span>'
        f'<span class="marker" aria-label="{label}">{marker}</span>'
        f'<code>{_html(text) if text else "&#8203;"}</code></div>'
    )


def _body_section(before: dict[str, Any], after: dict[str, Any]) -> str:
    left, right = before.get("body", _MISSING), after.get("body", _MISSING)
    title = '<section id="body"><div class="section-heading"><span class="step">01</span><h2>Submitted text</h2></div>'
    explanation = (
        '<p class="muted">Readable text extracted from the returned body. Paragraphs and line breaks '
        'are retained as text boundaries; formatting, images and embedded content are not reconstructed. '
        'Script, style and template content is excluded from this reading aid.</p>'
    )
    if not isinstance(left, str) or not isinstance(right, str):
        content = (
            '<p class="notice">Text highlighting is unavailable: both body values must be strings.</p>'
            + _pair(_value(left), _value(right))
        )
    else:
        left_text, right_text = readable_body(left), readable_body(right)
        left_lines, right_lines = left_text.splitlines(), right_text.splitlines()
        bounded = (
            len(left_lines) <= MAX_TEXT_LINES and len(right_lines) <= MAX_TEXT_LINES
            and len(left_text) + len(right_text) <= MAX_TEXT_CHARACTERS
            and len(left_lines) * len(right_lines) <= MAX_LINE_PAIRS
        )
        if left_text == right_text:
            message = (
                "The body source is identical; the readable text is shown below."
                if left == right else
                "Readable text matches, but the exact body source differs. Inspect the source below."
            )
            content = f'<p class="notice">{message}</p>' + _pair(_value(left_text), _value(right_text))
        elif not bounded:
            content = (
                '<p class="notice">Highlighting was not computed for this pair. The complete readable text '
                'is shown below. Highlighting supports at most 2,000 lines per side, 250,000 combined '
                'characters and 1,000,000 line pairs.</p>'
                + _pair(_value(left_text), _value(right_text))
            )
        else:
            rows = []
            for tag, i1, i2, j1, j2 in SequenceMatcher(
                None, left_lines, right_lines, autojunk=False,
            ).get_opcodes():
                for offset in range(max(i2 - i1, j2 - j1)):
                    i, j = i1 + offset, j1 + offset
                    rows.append(
                        '<div class="diff-row">'
                        + _line(i + 1 if i < i2 else None, left_lines[i] if i < i2 else "",
                                "context" if tag == "equal" else "removed")
                        + _line(j + 1 if j < j2 else None, right_lines[j] if j < j2 else "",
                                "context" if tag == "equal" else "added")
                        + "</div>"
                    )
            content = (
                '<p class="diff-key"><span>− Removed from before</span><span>+ Added in after</span></p>'
                '<div class="diff" aria-label="Readable text changes"><div class="diff-head">'
                '<strong>Before</strong><strong>After</strong></div>'
                + "".join(rows) + "</div>"
            )
    source = (
        '<details class="source-detail"><summary>Inspect exact body source and value states</summary>'
        + _pair(_value(left), _value(right)) + "</details>"
    )
    return title + explanation + content + source + "</section>"


def _metadata(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return _value(value)
    return '<table class="metadata"><tbody>' + "".join(
        f'<tr><th scope="row">{_html(key)}</th><td>{_value(item)}</td></tr>'
        for key, item in value.items()
    ) + "</tbody></table>"


def _attachments(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return _value(value)
    return "".join(
        f'<article class="attachment"><h4>Returned attachment {index}</h4>{_metadata(item)}</article>'
        for index, item in enumerate(value, 1)
    )


def _field_section(before: dict[str, Any], after: dict[str, Any], *,
                   key: str, title: str, step: str, note: str, attachments: bool = False) -> str:
    left, right = before.get(key, _MISSING), after.get(key, _MISSING)
    render = _attachments if attachments else _value
    return (
        f'<section id="{key}"><div class="section-heading"><span class="step">{step}</span>'
        f'<h2>{title}</h2></div><p class="muted">{note}</p>'
        f'<p class="status">{_status(left, right)}</p>'
        + _pair(render(left), render(right)) + "</section>"
    )


_CSS = """
:root{color-scheme:light;--ink:#18283d;--muted:#506077;--line:#cbd4df;--paper:#fff;--accent:#394ca1}
*{box-sizing:border-box}body{margin:0;background:#f2f4f8;color:var(--ink);font:16px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1200px;margin:0 auto;padding:32px 24px 48px}h1,h2,h3,h4,p{margin-top:0}h1{font-size:clamp(1.8rem,4vw,2.8rem);line-height:1.15;letter-spacing:-.035em;margin-bottom:16px;overflow-wrap:anywhere}
h2{font-size:1.4rem;line-height:1.3;margin:0}h3{font-size:.82rem;text-transform:uppercase;letter-spacing:.075em;color:var(--muted);margin-bottom:12px}h4{font-size:1rem;margin-bottom:8px}
a{color:var(--accent);text-underline-offset:3px}a:focus-visible,summary:focus-visible{outline:3px solid #8d5ad1;outline-offset:5px}
.hero{background:#17283f;color:#fff;padding:32px;border-radius:18px;margin-bottom:24px}.eyebrow{text-transform:uppercase;font-size:.78rem;letter-spacing:.13em;color:#c2cffc;margin-bottom:14px}
.hero .context{color:#dce5f6;margin-bottom:18px;overflow-wrap:anywhere}.hero .lede{max-width:72ch;color:#e2e8f2;margin-bottom:24px}.hero .download{display:inline-block;background:#e0e7ff;color:#21315e;border-radius:8px;padding:11px 16px;font-weight:650;text-decoration:none}
nav{display:flex;flex-wrap:wrap;gap:12px 24px;margin:22px 0 28px;font-size:.94rem}.record-grid,.pair{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px}
.record{border:1px solid var(--line);background:var(--paper);border-radius:12px;padding:22px;min-width:0}.record .selector{font:700 1.35rem ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;margin-bottom:14px}
.metadata{border-collapse:collapse;width:100%;table-layout:fixed;font-size:.9rem}.metadata th,.metadata td{padding:8px 0;border-bottom:1px solid #e3e8f0;vertical-align:top;text-align:left;overflow-wrap:anywhere}.metadata th{font-weight:550;width:39%;padding-right:14px;color:var(--muted)}
.metadata tr:last-child th,.metadata tr:last-child td{border-bottom:0}.metadata .value{font-size:.82rem}
section{background:var(--paper);border:1px solid var(--line);border-radius:12px;margin-top:24px;padding:26px;min-width:0}.section-heading{display:flex;align-items:center;gap:12px;margin-bottom:15px}.step{display:inline-flex;align-items:center;justify-content:center;flex:none;width:32px;height:32px;border-radius:50%;background:#e9edfb;color:#334893;font-size:.8rem;font-weight:700}
.muted{color:var(--muted);font-size:.92rem;max-width:90ch}.notice{padding:12px 15px;border-left:3px solid #6474bc;background:#f0f3fc;font-size:.94rem;overflow-wrap:anywhere}.status{font-weight:650;font-size:.92rem;margin-bottom:18px}
.value{margin:0;font: .9rem/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;word-break:normal;tab-size:2}.state{display:inline-block;color:#5a466a;background:#f3eef8;border-radius:5px;padding:3px 7px;font-size:.85rem;overflow-wrap:anywhere}
.side{min-width:0}.source-detail{margin-top:22px;border-top:1px solid var(--line);padding-top:15px}summary{cursor:pointer;font-weight:600;font-size:.92rem;overflow-wrap:anywhere}details[open]>summary{margin-bottom:18px}.attachment{padding:14px;border:1px solid var(--line);border-radius:8px;margin-bottom:12px;min-width:0}
.diff{border:1px solid var(--line);border-radius:8px;overflow:hidden}.diff-head,.diff-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.diff-head{background:#eaf0f7;color:#35475d;font-size:.83rem}.diff-head strong{padding:9px 12px}.diff-key{display:flex;flex-wrap:wrap;gap:8px 24px;font-size:.83rem;color:#445166}
.diff-line{display:grid;grid-template-columns:2.5em 1.4em minmax(0,1fr);padding:5px 8px;min-width:0;font:.86rem/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;border-top:1px solid #e7ebf1}.diff-line:nth-child(2){border-left:1px solid var(--line)}.diff-line code{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}.line-number{color:#647184;user-select:none}.marker{font-weight:700}.removed{background:#fff0ee;color:#7e2520}.added{background:#ecf8f0;color:#175239}.empty{background:#f6f7fa}.boundary{margin:22px 0 0;color:var(--muted);font-size:.9rem;max-width:95ch}
footer{margin-top:28px;color:var(--muted);font-size:.82rem;overflow-wrap:anywhere}
@media(max-width:680px){main{padding:16px 12px 30px}.hero{padding:24px 20px;border-radius:12px}.record-grid,.pair{grid-template-columns:minmax(0,1fr);gap:18px}.record{padding:18px}section{padding:20px 16px}.metadata th{width:36%;padding-right:10px}.diff-head{display:none}.diff-row{grid-template-columns:minmax(0,1fr);border-top:1px solid var(--line)}.diff-line{border:0!important;padding:7px 6px;grid-template-columns:2em 1.3em minmax(0,1fr)}.diff-line:first-child::before{content:"Before";grid-column:1/-1;font:600 .7rem system-ui;color:#526075;margin-bottom:3px}.diff-line:nth-child(2)::before{content:"After";grid-column:1/-1;font:600 .7rem system-ui;color:#526075;margin-bottom:3px}.diff-line.empty{display:none}.value{font-size:.83rem}}
@media print{@page{size:auto;margin:16mm}body{background:#fff;font-size:10pt}main{max-width:none;padding:0}.hero{background:#fff;color:#18283d;border:1px solid #aaa;padding:18px}.hero .eyebrow,.hero .context,.hero .lede{color:#33445c}.hero .download,nav{display:none}h1{font-size:24pt}.record-grid,.pair{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px}section{padding:16px;margin-top:16px}.section-heading,h3,h4,summary{break-after:avoid}.diff-row,tr{break-inside:avoid}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:inherit}.value,.diff-line{font-size:8pt}details:not([open]){display:none}.boundary,footer{font-size:8pt}}
"""


def render_submission_comparison(comparison: dict[str, Any]) -> str:
    """Render trusted structure with all returned content escaped and inert."""
    source = _source_bytes(comparison)
    before, after = comparison["before"]["record"], comparison["after"]["record"]
    request, assignment = comparison["request"], comparison["assignment"]
    name = assignment.get("name")
    title = name if isinstance(name, str) and name else f"Assignment {request['assignment_id']}"
    cards = []
    for label in ("before", "after"):
        selected = comparison[label]
        record = selected["record"]
        metadata = {field: record.get(field, _MISSING) for field in (
            "attempt", "submitted_at", "submission_type", "id", "assignment_id", "user_id",
        )}
        cards.append(
            f'<article class="record"><h3>{label.title()} selection</h3>'
            f'<p class="selector">{_html(selected["selector"])}</p>{_metadata(metadata)}</article>'
        )
    media = "".join(
        f'<h4>{key}</h4><p class="status">{_status(before.get(key, _MISSING), after.get(key, _MISSING))}</p>'
        + _pair(_value(before.get(key, _MISSING)), _value(after.get(key, _MISSING)))
        for key in _MEDIA_FIELDS
    )
    record_count = comparison["history"]["record_count"]
    count_text = "not returned" if record_count is None else str(record_count)
    encoded = base64.b64encode(source).decode("ascii")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
        f'<title>Submission comparison · {_html(title)}</title><style>{_CSS}</style></head><body><main>'
        '<header class="hero"><p class="eyebrow">CanvasPilot · Submission comparison</p>'
        f'<h1>{_html(title)}</h1><p class="context">Course {_html(request["course_id"])} · '
        f'Assignment {_html(request["assignment_id"])} · History records: {count_text}</p>'
        '<p class="lede">Read two submitted records side by side. The selections below identify exactly '
        'which returned records are being compared.</p>'
        f'<a id="download-records" class="download" download="selected-submission-records.json" '
        f'href="data:application/json;base64,{encoded}">Save selected records (.json)</a></header>'
        '<div class="record-grid">' + "".join(cards) + "</div>"
        '<p class="boundary">history:N means position N in the returned history list, starting at 1. '
        'Records retain their returned order, including duplicate attempt numbers. “Before” and “After” '
        'are your selection labels; they do not establish chronology or a complete attempt history.</p>'
        '<nav aria-label="Report sections"><a href="#body">Submitted text</a><a href="#url">Submitted URL</a>'
        '<a href="#attachments">Attachments</a><a href="#media">Media</a><a href="#records">Exact records</a></nav>'
        + _body_section(before, after)
        + _field_section(before, after, key="url", title="Submitted URL", step="02",
                         note="Exact returned URL text. Spelling, case, escapes and fragments are retained; no URL is opened.")
        + _field_section(before, after, key="attachments", title="Returned attachments", step="03",
                         note="Metadata only, in returned order. Matching metadata cannot establish equal file bytes or historical file availability.",
                         attachments=True)
        + '<section id="media"><div class="section-heading"><span class="step">04</span><h2>Returned media metadata</h2></div>'
        '<p class="muted">These returned values are shown without loading or playing linked media.</p>'
        + media + "</section>"
        '<section id="records"><div class="section-heading"><span class="step">05</span><h2>Exact selected records</h2></div>'
        '<p class="muted">The local JSON download retains both selectors and complete selected record values, '
        'including unknown fields and record-local metadata. No current comments or grades are copied into a historical record. '
        'The assignment summary comes from the existing history reader, which normalizes missing summary fields to null.</p>'
        '<details><summary>Inspect before record</summary>' + _value(before) + "</details>"
        '<details class="source-detail"><summary>Inspect after record</summary>' + _value(after) + "</details></section>"
        '<footer>Generated locally by CanvasPilot. Omitted, null, blank and empty-list states remain distinct. '
        'Visible control characters are escaped; the JSON download preserves their exact values. '
        'This document loads no submitted markup, external resources or file contents. '
        'Use your browser’s print command for a paper copy.</footer></main></body></html>'
    )


def _new_output(out: Path | str) -> Path:
    target = Path(out)
    if os.path.lexists(target):
        raise FileExistsError("Output path already exists; choose a new comparison file")
    if not target.parent.is_dir():
        raise FileNotFoundError("Output parent must be an existing directory")
    return target


def write_submission_comparison(out: Path | str, content: str) -> None:
    """Publish a complete report without replacing an existing or raced target."""
    target = _new_output(out)
    data = content.encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=".canvaspilot-comparison-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def export_submission_comparison(
    api: CanvasAPI, course_id: int | str, assignment_id: int | str, *,
    before: str, after: str, out: Path | str,
) -> dict[str, Any]:
    """Read the established history API once and save a new local HTML report."""
    _validate_pair(before, after)
    course = _numeric_id(course_id, "course_id")
    assignment = _numeric_id(assignment_id, "assignment_id")
    target = _new_output(out)
    history = api.submission_history(course, assignment)
    comparison = build_submission_comparison(
        history, course_id=course, assignment_id=assignment, before=before, after=after,
    )
    content = render_submission_comparison(comparison)
    write_submission_comparison(target, content)
    return {
        "output": str(target), "before": before, "after": after,
        "history_records_returned": comparison["history"]["record_count"],
    }
