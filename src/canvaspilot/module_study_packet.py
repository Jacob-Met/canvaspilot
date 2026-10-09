"""Save one module's returned readings as a passive offline study packet."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import logging
import os
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from canvaspilot.calendar_export import _calendar_source
from canvaspilot.page_export import (
    _identifier,
    _page_url,
    _reading_text,
    _text,
    write_page_packet,
)
from canvaspilot.study_workspace import _validate_brief

if TYPE_CHECKING:
    from canvaspilot.api import CanvasAPI

MAX_ITEMS = 100
MAX_RESOURCES = 20
MAX_BODY_BYTES = 512 * 1024
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_HTML_BYTES = 16 * 1024 * 1024
SCHEMA = "canvaspilot.module_study_packet/1"


def _json_bytes(value: Any, limit: int = MAX_JSON_BYTES) -> bytes:
    # ASCII JSON retains all decoded Unicode/code points and large integer IDs.
    data = json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("ascii")
    if len(data) > limit:
        raise ValueError(f"Retained source exceeds the {limit:,}-byte limit")
    return data


def _h(value: str) -> str:
    # Render unsupported control/code points visibly, retaining originals in JSON.
    visible = "".join(
        f"\\u{ord(char):04x}" if (ord(char) < 32 and char not in "\n\t") or
        127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF else char
        for char in value
    )
    return html.escape(visible, quote=True)


def _observed(row: dict[str, Any], key: str) -> str:
    if key not in row:
        return "Not returned"
    value = row[key]
    if value is None:
        return "Unavailable (null)"
    if value == "" and isinstance(value, str):
        return "Empty text"
    if isinstance(value, str):
        return value
    return _json_bytes(value).decode("ascii")


def _fields(row: dict[str, Any], fields: tuple[tuple[str, str], ...]) -> str:
    return "<dl>" + "".join(
        f"<dt>{_h(label)}</dt><dd>{_h(_observed(row, key))}</dd>"
        for key, label in fields
    ) + "</dl>"


def validate_selection(course_id: int | str, module_id: int | str) -> tuple[str, str]:
    return _identifier(course_id, "Course ID"), _identifier(module_id, "Module ID")


def _select_module(
    rows: Any, course: str, selected_id: str,
) -> tuple[dict[str, Any], list[tuple[str, str]], list[int | None]]:
    if not isinstance(rows, list):
        raise TypeError("The full module reader did not return a list")
    selected = None
    seen_modules = set()
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("The full module reader returned a malformed module")
        identity = _identifier(row.get("id"), "Returned module ID")
        if identity in seen_modules:
            raise ValueError("The full module reader returned duplicate module IDs")
        seen_modules.add(identity)
        if "course_id" in row and _identifier(row["course_id"], "Returned course ID") != course:
            raise ValueError("A returned module belongs to a different course")
        if identity == selected_id:
            selected = deepcopy(row)
    if selected is None:
        raise ValueError("Requested module is absent from the returned course modules")
    items = selected.get("items")
    if not isinstance(items, list):
        raise TypeError("The selected module did not return an item list")
    if len(items) > MAX_ITEMS:
        raise ValueError(f"The selected module exceeds the {MAX_ITEMS}-item limit")
    count = selected.get("items_count")
    if type(count) is not int or count < 0 or count != len(items):
        raise ValueError("Selected module items do not match a usable reported items_count")
    # This check is before content fetches, including unknown source metadata.
    _json_bytes(selected)
    seen_items: set[str] = set()
    resources: list[tuple[str, str]] = []
    resource_indexes: dict[tuple[str, str], int] = {}
    item_resources: list[int | None] = []
    for item in items:
        if not isinstance(item, dict):
            raise TypeError("The selected module contains a malformed item")
        identity = _identifier(item.get("id"), "Module item ID")
        if identity in seen_items:
            raise ValueError("The selected module contains duplicate item IDs")
        seen_items.add(identity)
        if "module_id" in item and _identifier(item["module_id"], "Item module ID") != selected_id:
            raise ValueError("A returned item belongs to a different module")
        kind = item.get("type")
        target = None
        if kind == "Page":
            target = ("Page", _page_url(item.get("page_url")))
        elif kind == "Assignment":
            target = ("Assignment", _identifier(item.get("content_id"), "Assignment content ID"))
        if target is not None:
            if target not in resource_indexes:
                resource_indexes[target] = len(resources)
                resources.append(target)
            item_resources.append(resource_indexes[target])
        else:
            item_resources.append(None)
    if len(resources) > MAX_RESOURCES:
        raise ValueError(f"The selected module exceeds the {MAX_RESOURCES}-unique-content limit")
    return selected, resources, item_resources


_STYLE = """
:root{color-scheme:light;font:17px/1.55 system-ui,sans-serif;color:#202c38;background:#f3f5f7}
*{box-sizing:border-box}body{margin:0}main{max-width:980px;margin:auto;padding:2rem 1.25rem}
h1,h2,h3,p,li,dd,a{overflow-wrap:anywhere}h1{font-size:2rem;line-height:1.15}
h2{font-size:1.4rem}h3{font-size:1.08rem}a{color:#165579}a:focus-visible,summary:focus-visible{outline:3px solid #e29b00;outline-offset:4px}
header,.summary,nav,.item{background:white;border:1px solid #ccd5df;border-radius:12px;padding:1.25rem;margin-bottom:1.25rem}
.eyebrow{font-size:.8rem;letter-spacing:.06em;text-transform:uppercase;color:#4c6175}
.muted,.notice{color:#4b5f70}.notice{border-left:4px solid #b46d10;background:#fff7e9;padding:.7rem 1rem}
.reading{white-space:pre-wrap;overflow-wrap:anywhere;font-family:inherit}
dl{display:grid;grid-template-columns:minmax(8rem,1fr) minmax(0,3fr);gap:.35rem 1rem}
dt{font-weight:600}dd{margin:0;white-space:pre-wrap}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font: .83rem/1.5 ui-monospace,monospace;background:#f2f4f6;padding:1rem;border-radius:6px}
details{margin:1rem 0}summary{cursor:pointer;font-weight:600}.criterion{border-top:1px solid #dce2e8;padding-top:.5rem}
nav ol{padding-left:1.5rem}nav li+li{margin-top:.4rem}.download{display:inline-block;padding:.6rem .9rem;border:1px solid #aebfce;border-radius:6px}
@media(max-width:500px){main{padding:1rem .7rem}header,.summary,nav,.item{padding:1rem}h1{font-size:1.7rem}dl{grid-template-columns:1fr;gap:.15rem}dd{margin-bottom:.5rem}}
@media print{:root{font-size:11pt;background:white}main{max-width:none;padding:0}.item,header,.summary,nav{border:0;border-radius:0;padding:0;margin-bottom:1.2rem}h2,h3{break-after:avoid}.item{break-before:auto}.download,.raw-source{display:none}a{color:inherit}pre{background:white}}
"""


def _page_content(page: dict[str, Any]) -> str:
    metadata = _fields(page, (
        ("page_id", "Page ID"), ("url", "Page locator"), ("title", "Page title"),
        ("published", "Publication reported"), ("locked_for_user", "Locked for caller"),
        ("lock_explanation", "Lock explanation"), ("editor", "Editor reported"),
        ("updated_at", "Updated at"),
    ))
    if "body" not in page:
        reading = '<p class="notice">Page body was not returned.</p>'
    elif page["body"] is None:
        reading = '<p class="notice">Page body is unavailable (null).</p>'
    elif page["body"] == "":
        reading = '<p class="notice">The supplied page body is empty.</p>'
    else:
        body = page["body"]
        text = _reading_text(body)
        projected = _h(text) if text else "No readable text was extracted; inspect the retained original HTML."
        reading = f'<div class="reading">{projected}</div>'
    if isinstance(page.get("body"), str):
        body = page["body"]
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        original = (
            '<details class="raw-source"><summary>Original page HTML (inert text)</summary>'
            f'<p class="muted">SHA-256 <code>{digest}</code></p><pre>{_h(body)}</pre></details>'
        )
    else:
        original = ""
    return (
        metadata + '<p class="muted">Page text is extracted from supplied HTML. Formatting and '
        'embedded media are not reproduced; link destinations are text references. '
        'The returned lock observation is retained without an inferred access decision.</p>'
        + reading + original
    )


def _assignment_content(brief: dict[str, Any]) -> str:
    fields = _fields(brief, (
        ("title", "Assignment title"), ("due_at", "Due at"),
        ("points_possible", "Possible points"), ("submission_types", "Submission types"),
        ("use_rubric_for_grading", "Rubric used for grading"),
    ))
    prompt = brief.get("prompt")
    if prompt is None:
        prompt_html = '<p class="notice">Normalized prompt is unavailable (null).</p>'
    elif prompt == "":
        prompt_html = '<p class="notice">The normalized brief contains no prompt text.</p>'
    else:
        prompt_html = f'<div class="reading">{_h(prompt)}</div>'
    rubric = brief.get("rubric")
    if rubric is None:
        rubric_html = '<p class="muted">Rubric unavailable (null in the normalized brief).</p>'
    elif not rubric:
        rubric_html = '<p class="muted">The normalized rubric is an empty list.</p>'
    else:
        rubric_html = "".join(
            f'<section class="criterion"><h3>Criterion {index}</h3>'
            f'<pre>{_h(_json_bytes(criterion).decode("ascii"))}</pre></section>'
            for index, criterion in enumerate(rubric, 1)
        )
    warnings = "".join(f'<li>{_h(warning)}</li>' for warning in brief["rubric_warnings"])
    warning_html = f'<ul class="notice">{warnings}</ul>' if warnings else ""
    settings = _fields(brief, (("rubric_settings", "Supplied rubric settings"),))
    return (
        fields + '<p class="muted">This is the existing normalized assignment brief. '
        'Requested identities and cleaned text do not independently establish raw HTTP '
        'identity or whether original prompt HTML was missing, null or empty. '
        'Rubric criteria are evidence; no grade or rubric total is calculated.</p>'
        + prompt_html + '<h3>Rubric evidence</h3>' + rubric_html + settings + warning_html
    )


def _render(snapshot: dict[str, Any], source_json: bytes) -> bytes:
    module = snapshot["module"]
    resources = snapshot["resources"]
    toc = []
    sections = []
    for index, (item, resource_index) in enumerate(
        zip(module["items"], snapshot["item_resources"], strict=True), 1,
    ):
        title = _observed(item, "title")
        kind = _observed(item, "type")
        toc.append(f'<li><a href="#item-{index}">{index}. {_h(title)}</a> <span class="muted">({_h(kind)})</span></li>')
        metadata = _fields(item, (
            ("id", "Module item ID"), ("position", "Reported position"), ("indent", "Reported indent"),
            ("type", "Item type"), ("published", "Publication reported"),
            ("completion_requirement", "Reported completion requirement"),
        ))
        if resource_index is None:
            content = (
                '<p class="notice">Reference only. No body, file, discussion, quiz, '
                'external tool or linked resource was downloaded for this item.</p>'
                + _fields(item, (("content_id", "Content ID"), ("html_url", "Canvas reference"),
                                 ("external_url", "External reference")))
            )
        else:
            resource = resources[resource_index]
            content = (_page_content(resource["page"]) if resource["kind"] == "Page"
                       else _assignment_content(resource["brief"]))
        raw_item = _h(_json_bytes(item).decode("ascii"))
        sections.append(
            f'<article class="item" id="item-{index}" data-module-item-index="{index}">'
            f'<p class="eyebrow">Module item {index} of {len(module["items"])}</p>'
            f'<h2>{_h(title)}</h2>{metadata}{content}'
            '<details class="raw-source"><summary>Retained module item</summary>'
            f'<pre>{raw_item}</pre></details><p><a href="#contents">Back to contents</a></p></article>'
        )
    module_fields = _fields(module, (
        ("id", "Module ID"), ("position", "Reported module position"),
        ("state", "Canvas-reported module state"), ("requirement_type", "Reported all/one rule"),
        ("require_sequential_progress", "Sequential progress reported"),
        ("prerequisite_module_ids", "Prerequisite module IDs"), ("unlock_at", "Unlock at"),
        ("completed_at", "Completed at"), ("items_count", "Reported item count"),
    ))
    source_digest = hashlib.sha256(source_json).hexdigest()
    encoded = base64.b64encode(source_json).decode("ascii")
    title = _observed(module, "name")
    empty = '<p class="notice">The selected module returned zero items and reports items_count 0.</p>' if not module["items"] else ""
    result = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="no-referrer"><title>{_h(title)} — module study packet</title><style>{_STYLE}</style></head>
<body><main><header><p class="eyebrow">CanvasPilot · Offline module reading</p><h1>{_h(title)}</h1>
<p>Course {_h(snapshot["course_id"])} · Module {_h(snapshot["module_id"])} · {len(module["items"])} returned items</p>
<p class="muted">Saved {_h(snapshot["generated_at"])} · Source {_h(snapshot["source"])}</p></header>
<section class="summary" aria-label="Module source context">{module_fields}
<p class="notice">A saved reading observation, not a live course view or an atomic backup. Returned item count matches the module's reported count; this does not certify course-wide completeness or later changes.</p>
<p class="muted">Items retain returned order, including repeated positions and content. {len(resources)} distinct Page/Assignment resources were read once each. Other item kinds are references only. No completion percentage, grade, prerequisite satisfaction or item accessibility is inferred.</p>
<p class="muted">Module structure comes from the existing full module reader, Page records from existing GET requests and assignment briefs from their existing normalized reader. Missing student fields stay unknown. All-versus-one and sequential rules are source context, not locally applied progress logic.</p>
<a class="download" download="module-study-source.json" href="data:application/json;base64,{encoded}">Download complete retained source JSON</a>
<p class="muted">Decoded-source JSON: {len(source_json):,} bytes · SHA-256 <code>{source_digest}</code>. This is not the original HTTP wire representation.</p></section>
<nav id="contents" aria-label="Module contents"><h2>Contents in returned order</h2>{empty}<ol>{"".join(toc)}</ol></nav>
{"".join(sections)}
<footer class="muted"><p>This file opens without scripts or automatic network requests. Images, attachments, media and external content were not downloaded. Canvas source may change after these sequential reads. No submission, quiz attempt, completion, grade or read-state action was requested.</p></footer>
</main></body></html>'''
    data = result.encode("utf-8")
    if len(data) > MAX_HTML_BYTES:
        raise ValueError(f"Rendered packet exceeds the {MAX_HTML_BYTES:,}-byte limit")
    return data


def build_module_study_packet(
    api: CanvasAPI, course_id: int | str, module_id: int | str, *,
    generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Read the complete bounded selection before preparing passive output."""
    course, selected_id = validate_selection(course_id, module_id)
    if generated_at is not None and (
        not isinstance(generated_at, datetime) or generated_at.utcoffset() is None
    ):
        raise ValueError("generated_at must be a timezone-aware datetime")
    source = _calendar_source(api.client)

    def unchanged_source() -> None:
        if _calendar_source(api.client) != source:
            raise ValueError("Canvas provider changed during export; no packet created")

    rows = api.list_modules(course, detail="full")
    unchanged_source()
    module, targets, item_resources = _select_module(rows, course, selected_id)
    snapshot: dict[str, Any] = {
        "schema": SCHEMA, "course_id": course, "module_id": selected_id,
        "source": source, "mode": api.client.mode,
        "generated_at": (generated_at or datetime.now(UTC)).isoformat(),
        "reader_source": "CanvasAPI.list_modules(detail=full); Page GET objects; normalized assignment_brief",
        "upstream_module_shape": "not_observed",
        "count_correspondence": "returned_item_count_equals_reported_items_count",
        "collection_complete": None, "modules_returned": len(rows),
        "module": module, "item_resources": item_resources, "resources": [],
    }
    _json_bytes(snapshot)
    for kind, locator in targets:
        unchanged_source()
        if kind == "Page":
            page = api.api_request("GET", f"/api/v1/courses/{course}/pages/{quote(locator, safe='')}")
            unchanged_source()
            if not isinstance(page, dict):
                raise TypeError("Page reader returned a malformed object")
            _identifier(page.get("page_id"), "Returned page ID")
            if "course_id" in page and _identifier(page["course_id"], "Page course ID") != course:
                raise ValueError("Returned page belongs to a different course")
            if page.get("url") != locator:
                raise ValueError("Returned page locator does not match the selected module item")
            if page.get("body") is not None:
                _text(page["body"], "Page body", MAX_BODY_BYTES)
            resource = {"kind": kind, "requested_locator": locator, "page": deepcopy(page)}
        else:
            brief = api.assignment_brief(course, locator)
            unchanged_source()
            _validate_brief(brief, course, locator)
            _json_bytes(brief, MAX_BODY_BYTES)
            resource = {"kind": kind, "requested_id": locator, "brief": deepcopy(brief)}
        snapshot["resources"].append(resource)
        _json_bytes(snapshot)
    source_json = _json_bytes(snapshot)
    content = _render(snapshot, source_json)
    return content, {
        "schema": SCHEMA, "course_id": course, "module_id": selected_id,
        "items": len(module["items"]), "unique_resources": len(targets),
        "reference_only_items": sum(index is None for index in item_resources),
        "source_json_bytes": len(source_json),
        "source_json_sha256": hashlib.sha256(source_json).hexdigest(),
        "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
    }


def run_export_module(args: argparse.Namespace) -> None:
    """Own only this CLI boundary; preserve other command and client behavior."""
    import httpx

    from canvaspilot.api import CanvasAPI
    from canvaspilot.client import (
        CanvasAuthError,
        CanvasClient,
        CanvasPaginationError,
        default_base_url,
        default_profile,
    )

    api = None
    logger = logging.getLogger("httpx")
    previous_level = logger.level
    try:
        validate_selection(args.course_id, args.module_id)
        if os.path.lexists(args.out):
            raise FileExistsError("Output path already exists; choose a new HTML file")
        logger.setLevel(max(logger.getEffectiveLevel(), logging.WARNING))
        api = CanvasAPI(CanvasClient(
            base_url=args.base_url or default_base_url(), token=args.token,
            profile=Path(args.profile) if args.profile else default_profile(),
        ))
        content, report = build_module_study_packet(api, args.course_id, args.module_id)
        warning = write_page_packet(args.out, content)
    except (
        CanvasAuthError, CanvasPaginationError, httpx.HTTPError, ValueError,
        TypeError, OSError, AttributeError, RecursionError,
    ) as error:
        print(json.dumps({"ok": False, "error": type(error).__name__, "message": str(error)}), file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        logger.setLevel(previous_level)
        if api is not None:
            api.close()
    if warning:
        report["cleanup_warning"] = warning
    print(json.dumps({"ok": True, "output": str(args.out), **report}, indent=2))
