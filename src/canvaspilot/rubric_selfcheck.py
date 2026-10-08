"""Local rubric self-checks from the unchanged normalized assignment-brief reader."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import logging
import re
import sys
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from canvaspilot.study_workspace import (
    MAX_SNAPSHOT_BYTES,
    _embedded_json,
    _json,
    _source_url,
    _validate_brief,
    validate_output,
    validate_selection,
    write_study_workspace,
)

SCHEMA = "canvaspilot.rubric_selfcheck/1"
MAX_CRITERIA = 500
MAX_RATINGS = 5000


def _text(value: Any, missing: str = "Not supplied") -> str:
    if value is None:
        return missing
    return value if isinstance(value, str) else _json(value)


def _escape(value: Any, missing: str = "Not supplied") -> str:
    return html.escape(_text(value, missing), quote=True)


def _line(label: str, value: Any) -> str:
    return f"<p><strong>{html.escape(label)}:</strong> {_escape(value)}</p>"


def _show(settings: dict[str, Any], flag: str) -> bool:
    # Unknown or malformed flags conservatively suppress the corresponding labels.
    return flag not in settings or settings[flag] is False


def _criterion(key: str, index: int, criterion: dict[str, Any], show_points: bool) -> str:
    identifier = "criterion-" + key.replace(":", "-")
    title = _escape(criterion.get("description"), "Description unavailable")
    parts = [
        f'<article class="criterion" data-criterion-key="{key}">',
        f'<h3><span class="number">{index + 1:02d}</span> {title}</h3>',
        f'<p class="long-text">{_escape(criterion.get("long_description"), "No longer description supplied")}</p>',
        '<details><summary>Supplied rubric details and ratings</summary>',
        _line("Recorded criterion ID", criterion.get("id")),
    ]
    if show_points:
        parts.append(_line("Criterion point label", criterion.get("points")))
    for field, label in (
        ("criterion_use_range", "Uses a range"),
        ("ignore_for_scoring", "Ignored for scoring"),
        ("learning_outcome_id", "Learning outcome ID"),
        ("outcome_id", "Outcome ID"),
    ):
        if field in criterion:
            parts.append(_line(label, criterion[field]))
    ratings = criterion.get("ratings")
    if ratings is None:
        parts.append("<p>Ratings unavailable in this brief.</p>")
    elif not ratings:
        parts.append("<p>The supplied ratings list is empty.</p>")
    else:
        parts.append('<ol class="ratings">')
        for rating in ratings:
            parts.extend([
                "<li><strong>" + _escape(rating.get("description"), "Rating description unavailable") + "</strong>",
                '<p class="long-text">' + _escape(rating.get("long_description"), "No longer description supplied") + "</p>",
            ])
            if show_points:
                parts.append(_line("Supplied point label", rating.get("points")))
            parts.append("</li>")
        parts.append("</ol>")
    parts.extend([
        "</details>",
        '<div class="self-controls">',
        f'<label for="{identifier}-status">My self-check for criterion {index + 1}</label>',
        f'<select id="{identifier}-status" data-role="status" disabled>',
        '<option value="unreviewed">Unreviewed</option>',
        '<option value="needs-work">Needs work</option>',
        '<option value="checked">Checked locally</option></select>',
        f'<label for="{identifier}-notes">My evidence or next step for criterion {index + 1}</label>',
        f'<textarea id="{identifier}-notes" data-role="notes" maxlength="5000" rows="4" disabled placeholder="Record a passage, example, question or next step in your own words."></textarea>',
        '<span class="note-count" data-role="count"></span></div>',
        '<div class="print-self"><p><strong>My self-check:</strong> <span data-role="print-status">Unreviewed</span></p>',
        '<p class="long-text" data-role="print-notes">No evidence note recorded.</p></div>',
        "</article>",
    ])
    return "".join(parts)


def _render_assignments(source: dict[str, Any]) -> str:
    parts = []
    origin = urlsplit(source["source_base_url"])
    for item in source["assignments"]:
        brief = item["brief"]
        key = item["key"]
        parts.extend([
            f'<section class="assignment" id="assignment-{key.replace(":", "-")}">',
            '<div class="assignment-heading"><p class="eyebrow">Assignment ' + _escape(brief["assignment_id"]) + "</p>",
            "<h2>" + _escape(brief["title"], "Untitled assignment") + "</h2></div>",
            _line("Reported due date", brief["due_at"]),
            _line("Assignment point label", brief["points_possible"]),
            _line("Canvas reports rubric used for grading", brief["use_rubric_for_grading"]),
        ])
        link = brief["html_url"]
        if isinstance(link, str):
            parsed = urlsplit(link)
            if (
                parsed.scheme in ("http", "https")
                and parsed.scheme == origin.scheme
                and parsed.netloc == origin.netloc
                and parsed.username is None
                and parsed.password is None
                and not any(c.isspace() for c in link)
            ):
                parts.append(f'<p><a href="{html.escape(link, quote=True)}" rel="noopener noreferrer" target="_blank">Open this assignment in Canvas</a></p>')
        parts.append('<details><summary>Assignment prompt and source warnings</summary><p class="long-text">' + _escape(brief["prompt"]) + "</p>")
        if brief["rubric_warnings"]:
            parts.append("<ul>" + "".join("<li>" + html.escape(x) + "</li>" for x in brief["rubric_warnings"]) + "</ul>")
        else:
            parts.append("<p>No rubric warnings returned by the brief reader.</p>")
        parts.append("</details>")
        settings = brief["rubric_settings"] or {}
        parts.append(_line("Rubric title", settings.get("title")))
        if _show(settings, "hide_points") and _show(settings, "hide_score_total"):
            parts.append(_line("Supplied rubric total label", settings.get("points_possible")))
        parts.append("<p class=\"muted\">These are supplied labels, not a calculated self-check score.</p>")
        if not _show(settings, "hide_points") or not _show(settings, "hide_score_total"):
            parts.append("<p>Some rubric point labels are hidden by the supplied or unavailable visibility setting. The source snapshot still retains them.</p>")
        rubric = brief["rubric"]
        if rubric is None:
            parts.append('<p class="empty">Rubric unavailable. No criteria or self-checks are invented.</p>')
        elif not rubric:
            parts.append('<p class="empty">The supplied rubric is empty. There are no criteria to self-check.</p>')
        else:
            for index, criterion in enumerate(rubric):
                parts.append(_criterion(f"{key}:{index}", index, criterion, _show(settings, "hide_points")))
        parts.append("</section>")
    return "".join(parts)


def build_rubric_selfcheck(
    api: Any,
    course_id: str | int,
    assignment_ids: list[str | int] | tuple[str | int, ...],
    *,
    source_base_url: str,
    exported_at: str | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Capture each selected brief once, with no grades, submission or remote writes."""
    course, selected = validate_selection(course_id, assignment_ids)
    base = _source_url(source_base_url)
    entries, state = [], {}
    criteria_count = ratings_count = 0
    for assignment in selected:
        brief = api.assignment_brief(course, assignment)
        _validate_brief(brief, course, assignment)
        frozen = json.loads(_json(brief))
        key = f"{course}:{assignment}"
        rubric = frozen["rubric"]
        for index, criterion in enumerate(rubric or []):
            ratings = criterion.get("ratings")
            if ratings is not None and (
                not isinstance(ratings, list) or not all(isinstance(x, dict) for x in ratings)
            ):
                raise ValueError("Normalized criterion ratings must be a list of records or null")
            criteria_count += 1
            ratings_count += len(ratings or [])
            if criteria_count > MAX_CRITERIA or ratings_count > MAX_RATINGS:
                raise ValueError("Self-check limit: 500 criteria and 5000 ratings; no partial export")
            state[f"{key}:{index}"] = {"status": "unreviewed", "notes": ""}
        entries.append({"key": key, "brief": frozen})
        if len(_json(entries).encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            raise ValueError("Selected assignment snapshot exceeds the 4 MiB limit")
    source = {
        "schema_id": SCHEMA,
        "course_id": course,
        "source_base_url": base,
        "exported_at": exported_at or datetime.now(UTC).isoformat(timespec="seconds"),
        "reader": "CanvasAPI.assignment_brief",
        "source_boundary": {
            "requested_selection_ids": True,
            "upstream_response_identity": "not_observed",
            "prompt_representation": "existing_reader_cleaned_text",
            "canvas_completion_or_access": "not_inferred",
        },
        "assignments": entries,
    }
    text = _json(source)
    if len(text.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Selected assignment snapshot exceeds the 4 MiB limit")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    envelope = {
        "schema_id": SCHEMA, "source": text, "source_sha256": digest,
        "state": {"source_sha256": digest, "criteria": state},
    }
    assets = files("canvaspilot")
    template = (assets / "rubric_selfcheck.html").read_text(encoding="utf-8")
    style = (assets / "rubric_selfcheck.css").read_text(encoding="utf-8")
    script = (assets / "rubric_selfcheck.js").read_text(encoding="utf-8")
    replacements = {
        "__STYLE_HASH__": base64.b64encode(hashlib.sha256(style.encode()).digest()).decode(),
        "__SCRIPT_HASH__": base64.b64encode(hashlib.sha256(script.encode()).digest()).decode(),
        "__STYLE__": style, "__SCRIPT__": script, "__DATA__": _embedded_json(envelope),
        "__ASSIGNMENTS__": _render_assignments(source),
        "__SOURCE__": _escape(base), "__EXPORTED__": _escape(source["exported_at"]),
        "__HASH__": digest,
    }
    page = re.sub(
        r"__(?:STYLE_HASH|SCRIPT_HASH|STYLE|SCRIPT|DATA|ASSIGNMENTS|SOURCE|EXPORTED|HASH)__",
        lambda match: replacements[match.group()], template,
    ).encode("utf-8")
    return page, {
        "course_id": course, "assignment_ids": selected, "assignment_count": len(entries),
        "criterion_count": criteria_count, "rating_count": ratings_count,
        "snapshot_sha256": digest, "reader": source["reader"],
        "upstream_response_identity": "not_observed",
    }


def run_export_selfcheck(args: argparse.Namespace) -> None:
    """Normal CLI auth/read route; validation precedes transport and publication."""
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
    old_level = logger.level
    try:
        validate_selection(args.course_id, args.assignment_ids)
        validate_output(args.out)
        base = _source_url(args.base_url or default_base_url())
        api = CanvasAPI(CanvasClient(
            base_url=base, token=args.token,
            profile=Path(args.profile) if args.profile else default_profile(),
        ))
        logger.setLevel(max(logging.WARNING, old_level))
        content, report = build_rubric_selfcheck(
            api, args.course_id, args.assignment_ids, source_base_url=base,
        )
        write_study_workspace(args.out, content)
    except (
        CanvasAuthError, CanvasPaginationError, httpx.HTTPError,
        ValueError, TypeError, OSError, AttributeError,
    ) as error:
        print(json.dumps({"ok": False, "error": type(error).__name__, "message": str(error)}), file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        logger.setLevel(old_level)
        if api is not None:
            api.close()
    print(json.dumps({"ok": True, "output": str(args.out), **report}, indent=2))
