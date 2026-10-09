"""Compare two explicitly selected page revisions in a passive offline document."""

from __future__ import annotations

import base64
import difflib
import html
import json
import math
import re
from typing import Any

from canvaspilot.page_revisions import page_path, positive_id

_MAX_ENVELOPE = 1_048_576
_MAX_BODY = 524_288
_MAX_HTML = 8_388_608
_NOT_COMPARABLE = "One or both revision bodies are absent or null."
_WORK_LIMIT = "Line comparison not computed: the bounded work limit was exceeded."


def validate_revision_comparison(
    course_id: int | str, page_url: str,
    before_revision: int | str, after_revision: int | str,
) -> dict[str, str]:
    """Validate all selectors without constructing a client or making a request."""
    course = positive_id(course_id, "course_id")
    page_path(course, page_url)
    before = positive_id(before_revision, "before_revision")
    after = positive_id(after_revision, "after_revision")
    if before == after:
        raise ValueError("Choose two distinct explicit numeric revision IDs")
    return {
        "course_id": course, "page_url": page_url,
        "before_revision": before, "after_revision": after,
    }


def _detach_json(value: Any) -> tuple[Any, int]:
    """Admit and detach ordinary JSON, bounding expanded nodes, depth and bytes."""
    active: set[int] = set()
    nodes = 0
    byte_count = 0

    def add(amount: int) -> None:
        nonlocal byte_count
        byte_count += amount
        if byte_count > _MAX_ENVELOPE:
            raise ValueError("A revision envelope exceeds 1048576 UTF-8 bytes")

    def scalar_size(item: Any) -> int:
        if type(item) is str:
            try:
                size = len(item.encode("utf-8"))
            except UnicodeEncodeError as error:
                raise ValueError("Revision data must contain Unicode scalar values") from error
            if size > _MAX_ENVELOPE:
                raise ValueError("A revision string exceeds the envelope byte limit")
        return len(json.dumps(
            item, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8"))

    def visit(item: Any, depth: int) -> Any:
        nonlocal nodes
        nodes += 1
        if nodes > 100_000:
            raise ValueError("Revision data exceeds 100000 expanded JSON nodes")
        kind = type(item)
        if kind in (dict, list):
            if depth >= 64:
                raise ValueError("Revision data exceeds 64 container levels")
            identity = id(item)
            if identity in active:
                raise ValueError("Revision data must not contain cycles")
            active.add(identity)
            try:
                add(2 + max(0, len(item) - 1))
                if kind is list:
                    return [visit(child, depth + 1) for child in item]
                result = {}
                for key, child in item.items():
                    if type(key) is not str:
                        raise TypeError("Revision JSON object keys must be strings")
                    add(scalar_size(key) + 1)
                    result[key] = visit(child, depth + 1)
                return result
            finally:
                active.remove(identity)
        if item is None or kind in (bool, int, str):
            add(scalar_size(item))
            return item
        if kind is float and math.isfinite(item):
            add(scalar_size(item))
            return item
        raise TypeError("Revision data must contain only finite ordinary JSON values")

    detached = visit(value, 0)
    return detached, byte_count


def _envelope(value: Any, selected: str) -> tuple[dict[str, Any], int]:
    result, size = _detach_json(value)
    if type(result) is not dict or type(result.get("revision")) is not dict:
        raise TypeError("The revision reader must return an envelope with a revision object")
    revision = result["revision"]
    if positive_id(revision.get("revision_id"), "returned revision_id") != selected:
        raise ValueError("Returned revision_id does not match the selected revision")
    if "body" not in revision:
        if "body_text" in result:
            raise ValueError("An absent body must have an absent inherited body_text")
    elif revision["body"] is None:
        if "body_text" not in result or result["body_text"] is not None:
            raise ValueError("A null body requires a null inherited body_text")
    elif type(revision["body"]) is str:
        if type(result.get("body_text")) is not str:
            raise ValueError("A text body requires an inherited text body_text")
        if len(revision["body"].encode("utf-8")) > _MAX_BODY:
            raise ValueError("A revision body exceeds 524288 UTF-8 bytes")
    else:
        raise TypeError("A supplied revision body must be text or null")
    return result, size


def _body_state(envelope: dict[str, Any]) -> str:
    revision = envelope["revision"]
    if "body" not in revision:
        return "absent"
    if revision["body"] is None:
        return "null"
    return "empty" if revision["body"] == "" else "text"


def _lines(body: str) -> list[str]:
    # str.splitlines() would also split Unicode separators, losing our line identity.
    result = []
    start = 0
    for match in re.finditer(r"\r\n|\r|\n", body):
        result.append(body[start:match.end()])
        start = match.end()
    if start < len(body):
        result.append(body[start:])
    return result


def _comparison(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left = before["revision"].get("body")
    right = after["revision"].get("body")
    left_lines = _lines(left) if type(left) is str else None
    right_lines = _lines(right) if type(right) is str else None
    comparable = left_lines is not None and right_lines is not None
    diff: dict[str, Any] = {
        "status": "computed" if comparable else "not-comparable",
        "reason": None if comparable else _NOT_COMPARABLE,
        "before_lines": len(left_lines) if left_lines is not None else None,
        "after_lines": len(right_lines) if right_lines is not None else None,
        "rows": [],
    }
    if comparable:
        if (len(left_lines) + len(right_lines) > 2000
                or len(left.encode("utf-8")) + len(right.encode("utf-8")) > 131_072
                or len(left_lines) * len(right_lines) > 1_000_000):
            diff["status"] = "limit"
            diff["reason"] = _WORK_LIMIT
        else:
            for tag, i, end_i, j, end_j in difflib.SequenceMatcher(
                None, left_lines, right_lines, autojunk=False,
            ).get_opcodes():
                if tag == "equal":
                    for offset, text in enumerate(left_lines[i:end_i]):
                        diff["rows"].append({
                            "kind": "equal", "before_line": i + offset + 1,
                            "after_line": j + offset + 1, "text": text,
                        })
                else:
                    for index in range(i, end_i):
                        diff["rows"].append({
                            "kind": "delete", "before_line": index + 1,
                            "after_line": None, "text": left_lines[index],
                        })
                    for index in range(j, end_j):
                        diff["rows"].append({
                            "kind": "insert", "before_line": None,
                            "after_line": index + 1, "text": right_lines[index],
                        })
    return {
        "before_body_state": _body_state(before),
        "after_body_state": _body_state(after),
        "raw_equal": left == right if comparable else None,
        "text_equal": before["body_text"] == after["body_text"] if comparable else None,
        "line_diff": diff,
    }


def _literal(value: Any) -> str:
    # ASCII JSON literals make controls, CR/LF and Unicode separators unambiguous.
    return html.escape(json.dumps(value, ensure_ascii=True, allow_nan=False), quote=True)


def _render(report: dict[str, Any]) -> bytes:
    selection = report["selection"]
    comparison = report["comparison"]
    diff = comparison["line_diff"]
    payload = (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    encoded = base64.b64encode(payload).decode("ascii")
    filename = (
        f"canvas-page-revisions-{selection['course_id']}-"
        f"{selection['before_revision']}-vs-{selection['after_revision']}.json"
    )
    cards = []
    for side in ("before", "after"):
        envelope = report[side]
        revision = envelope["revision"]
        fields = []
        for field in ("title", "url", "updated_at"):
            observed = _literal(revision[field]) if field in revision else "<em>absent</em>"
            fields.append(f"<dt>{field} as supplied</dt><dd><code>{observed}</code></dd>")
        cleaned = (
            _literal(envelope["body_text"]) if "body_text" in envelope else "<em>absent</em>"
        )
        complete = html.escape(
            json.dumps(envelope, ensure_ascii=True, indent=2, allow_nan=False), quote=True,
        )
        cards.append(
            f'<section class="card" aria-labelledby="{side}-heading">'
            f'<h2 id="{side}-heading">{side.title()} · revision '
            f'{selection[side + "_revision"]}</h2>'
            f'<p>Supplied body: <strong>{comparison[side + "_body_state"]}</strong></p>'
            f'<dl>{"".join(fields)}</dl>'
            f'<h3>Inherited cleaned text</h3><pre class="cleaned">{cleaned}</pre>'
            f'<details id="{side}-source"><summary>Complete {side} reader envelope</summary>'
            f'<pre>{complete}</pre></details></section>'
        )
    rows = "".join(
        f'<tr class="{row["kind"]}"><th scope="row">{row["kind"]}</th>'
        f'<td>{row["before_line"] if row["before_line"] is not None else "—"}</td>'
        f'<td>{row["after_line"] if row["after_line"] is not None else "—"}</td>'
        f'<td><code>{_literal(row["text"])}</code></td></tr>'
        for row in diff["rows"]
    )
    reason = html.escape(diff["reason"] or (
        "No line rows: both supplied bodies are empty." if not rows
        else "Complete raw-line comparison, including original terminators."
    ))
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Page revision comparison · {selection['before_revision']} / {selection['after_revision']}</title>
<style>
:root {{ color-scheme: light; font-family: system-ui, sans-serif; color: #18232f; background: #f4f6f8; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; line-height: 1.5; }}
main {{ max-width: 1120px; margin: auto; padding: 28px 20px 44px; }}
h1 {{ line-height: 1.15; margin: .3em 0; font-size: clamp(1.8rem, 5vw, 2.8rem); }}
h2 {{ font-size: 1.3rem; }} h3 {{ font-size: 1rem; }}
.kicker {{ text-transform: uppercase; letter-spacing: .1em; font-size: .8rem; color: #495c6e; }}
.scope, .card, .diff {{ background: white; border: 1px solid #d2dbe3; border-radius: 10px; padding: 20px; margin-top: 20px; min-width: 0; }}
.cards {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
a {{ color: #074e8c; }} .download {{ display: inline-block; padding: 11px 16px; border: 2px solid #074e8c; border-radius: 7px; font-weight: 650; }}
a:focus-visible, summary:focus-visible {{ outline: 3px solid #a33b00; outline-offset: 4px; }}
dt {{ font-size: .85rem; color: #495c6e; }} dd {{ margin: 2px 0 12px; }}
pre, code {{ white-space: pre-wrap; overflow-wrap: anywhere; font-size: .88rem; }}
pre {{ margin: 12px 0; padding: 12px; background: #f4f6f8; }}
summary {{ cursor: pointer; padding: 8px 0; font-weight: 600; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
th, td {{ border-bottom: 1px solid #ccd5de; padding: 8px 6px; vertical-align: top; text-align: left; overflow-wrap: anywhere; }}
th:nth-child(1) {{ width: 5.2em; }} th:nth-child(2), th:nth-child(3) {{ width: 4.2em; }}
.insert {{ background: #e8f5ea; }} .delete {{ background: #fff0eb; }}
.note {{ color: #495c6e; font-size: .92rem; }}
@media (max-width: 600px) {{ main {{ padding: 18px 12px; }} .cards {{ display: block; }} .scope, .card, .diff {{ padding: 14px; }} th, td {{ padding: 7px 3px; }} }}
@media print {{ :root {{ background: white; }} main {{ max-width: none; padding: 0; }} .download {{ display: none; }} .cards {{ display: block; }} .card, .scope, .diff {{ border-radius: 0; }} details {{ display: none; }} th, td {{ break-inside: avoid; }} }}
</style></head><body><main>
<p class="kicker">CanvasPilot · offline reading report</p>
<h1>Page revision comparison</h1>
<p>Before and After are your selected direction, not a claim about chronology.</p>
<section class="scope" aria-label="Selection and scope">
<p>Course <strong>{selection['course_id']}</strong> · Before <strong>{selection['before_revision']}</strong>
 → After <strong>{selection['after_revision']}</strong></p>
<p>Current locator used for both reads: <code id="page-locator">{_literal(selection['page_url'])}</code></p>
<p>Two sequential revision reads are not an atomic historical snapshot. Existing Canvas page edit rights are required.
Historic titles and URLs below are observations from the selected revisions; this report does not infer authorship, history completeness, or attachment/rendered equivalence.</p>
<a id="download-json" class="download" href="data:application/json;base64,{encoded}" download="{filename}">Download complete comparison JSON</a>
<p class="note">This passive file makes no network requests and changes no Canvas data. Full source envelopes remain available in the disclosures and JSON.
Printing includes the visible comparison and cleaned text; source disclosures and the download control are omitted.</p>
</section><div class="cards">{"".join(cards)}</div>
<section class="diff" aria-labelledby="diff-heading"><h2 id="diff-heading">Raw body lines</h2>
<p id="comparison-state">Raw bodies equal: <strong>{_literal(comparison['raw_equal'])}</strong> ·
Inherited cleaned texts equal: <strong>{_literal(comparison['text_equal'])}</strong></p>
<p>Line counts: Before {_literal(diff['before_lines'])} · After {_literal(diff['after_lines'])}.
Status: <strong id="diff-status">{diff['status']}</strong>.</p>
<p id="diff-reason">{reason}</p>
<p class="note">Each quoted JSON literal is one complete original line. Escaped CR/LF show its exact ending; a quote with no ending escape means no final newline.
Only CRLF, CR and LF split lines. Other Unicode separators stay inside a line. Delete/insert labels remain meaningful without color.</p>
<table aria-label="Exact raw line changes"><thead><tr><th>Change</th><th>Before</th><th>After</th><th>Complete line literal</th></tr></thead>
<tbody>{rows}</tbody></table></section></main></body></html>
"""
    content = document.encode("utf-8")
    if len(content) > _MAX_HTML:
        raise ValueError("The complete report exceeds 8388608 HTML UTF-8 bytes")
    return content


def build_page_revision_comparison(
    api: Any, course_id: int | str, page_url: str,
    before_revision: int | str, after_revision: int | str,
) -> tuple[bytes, dict[str, Any]]:
    """Read exactly two explicit revisions and return a complete detached report."""
    selection = validate_revision_comparison(course_id, page_url, before_revision, after_revision)
    before, before_size = _envelope(api.get_page_revision(
        selection["course_id"], selection["page_url"],
        selection["before_revision"], summary=False,
    ), selection["before_revision"])
    after, after_size = _envelope(api.get_page_revision(
        selection["course_id"], selection["page_url"],
        selection["after_revision"], summary=False,
    ), selection["after_revision"])
    if before_size + after_size > 2_097_152:
        raise ValueError("The two revision envelopes exceed 2097152 UTF-8 bytes")
    report = {
        "schema": "canvaspilot.page-revision-comparison.v1",
        "selection": selection, "before": before, "after": after,
        "comparison": _comparison(before, after),
    }
    return _render(report), report
