"""An offline, local-only assignment study workspace built from existing briefs."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import math
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

MAX_ASSIGNMENTS = 25
MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024
MAX_ID = 2**63 - 1
SCHEMA = "canvaspilot.study_workspace/1"
BRIEF_FIELDS = {
    "title",
    "due_at",
    "points_possible",
    "submission_types",
    "prompt",
    "html_url",
    "course_id",
    "assignment_id",
    "rubric",
    "rubric_settings",
    "use_rubric_for_grading",
    "rubric_warnings",
}


def canvas_id(value: str | int) -> str:
    """Canonical decimal strings preserve full Canvas IDs in browser JSON."""
    if type(value) not in (str, int) or not re.fullmatch(r"[0-9]+", str(value)):
        raise ValueError("Canvas IDs must contain only positive ASCII decimal digits")
    if len(str(value)) > 19 or not 0 < int(value) <= MAX_ID:
        raise ValueError(
            "Canvas IDs must be in the range 1 through 9223372036854775807"
        )
    return str(int(value))


def validate_selection(
    course_id: str | int,
    assignment_ids: list[str | int] | tuple[str | int, ...],
) -> tuple[str, list[str]]:
    if (
        not isinstance(assignment_ids, (list, tuple))
        or not 1 <= len(assignment_ids) <= MAX_ASSIGNMENTS
    ):
        raise ValueError(f"Select between 1 and {MAX_ASSIGNMENTS} assignments")
    course = canvas_id(course_id)
    selected = [canvas_id(value) for value in assignment_ids]
    if len(set(selected)) != len(selected):
        raise ValueError("Each assignment may be selected only once")
    return course, selected


def _source_url(value: str) -> str:
    if not isinstance(value, str) or any(c.isspace() for c in value):
        raise ValueError("Canvas base URL must be an absolute HTTP(S) URL")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Canvas base URL must not include credentials, a query, or a fragment"
        )
    _ = parsed.port  # Refuse malformed port syntax before any API read.
    return value.rstrip("/")


def _validate_brief(brief: Any, course: str, assignment: str) -> None:
    if not isinstance(brief, dict) or set(brief) != BRIEF_FIELDS:
        raise ValueError("The assignment brief has an unsupported shape")
    if brief["course_id"] != course or brief["assignment_id"] != assignment:
        raise ValueError("The normalized brief does not match the requested selection")
    for field in ("title", "due_at", "prompt", "html_url"):
        if brief[field] is not None and not isinstance(brief[field], str):
            raise ValueError(f"Assignment {assignment}: {field} must be text or null")
    points = brief["points_possible"]
    if points is not None and (
        type(points) not in (int, float)
        or abs(points) > 2**53 - 1
        or not math.isfinite(points)
    ):
        raise ValueError(
            f"Assignment {assignment}: points_possible is not a usable number"
        )
    types = brief["submission_types"]
    if types is not None and (
        not isinstance(types, list) or not all(isinstance(x, str) for x in types)
    ):
        raise ValueError(
            f"Assignment {assignment}: submission_types must be a list or null"
        )
    rubric = brief["rubric"]
    if rubric is not None and (
        not isinstance(rubric, list) or not all(isinstance(x, dict) for x in rubric)
    ):
        raise ValueError(f"Assignment {assignment}: rubric must be a list or null")
    if brief["rubric_settings"] is not None and not isinstance(
        brief["rubric_settings"], dict
    ):
        raise ValueError(
            f"Assignment {assignment}: rubric_settings must be an object or null"
        )
    if (
        brief["use_rubric_for_grading"] is not None
        and type(brief["use_rubric_for_grading"]) is not bool
    ):
        raise ValueError(
            f"Assignment {assignment}: grading use must be Boolean or null"
        )
    if not isinstance(brief["rubric_warnings"], list) or not all(
        isinstance(x, str) for x in brief["rubric_warnings"]
    ):
        raise ValueError(
            f"Assignment {assignment}: rubric_warnings must be a list of text"
        )


def _json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _embedded_json(value: Any) -> str:
    return (
        _json(value)
        .replace("&", r"\u0026")
        .replace("<", r"\u003c")
        .replace(">", r"\u003e")
        .replace("\u2028", r"\u2028")
        .replace("\u2029", r"\u2029")
    )


def build_study_workspace(
    api: Any,
    course_id: str | int,
    assignment_ids: list[str | int] | tuple[str | int, ...],
    *,
    source_base_url: str,
    exported_at: str | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Read exactly the selected normalized briefs; never mutate caller/source data."""
    course, selected = validate_selection(course_id, assignment_ids)
    source_base_url = _source_url(source_base_url)
    entries = []
    for assignment in selected:
        brief = api.assignment_brief(course, assignment)
        _validate_brief(brief, course, assignment)
        # Freeze each reader result before another call can reuse its mutable object.
        frozen = json.loads(_json(brief))
        entries.append({"key": f"{course}:{assignment}", "brief": frozen})
        if len(_json(entries).encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            raise ValueError("Selected assignment snapshot exceeds the 4 MiB limit")
    source = {
        "schema_id": SCHEMA,
        "course_id": course,
        "source_base_url": source_base_url,
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
    source_text = _json(source)
    if len(source_text.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Selected assignment snapshot exceeds the 4 MiB limit")
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    envelope = {
        "schema_id": SCHEMA,
        "source": source_text,
        "source_sha256": digest,
        "state": {
            "source_sha256": digest,
            "assignments": {
                item["key"]: {"notes": "", "reviewed": False} for item in entries
            },
        },
    }
    assets = files("canvaspilot")
    template = (assets / "study_workspace.html").read_text(encoding="utf-8")
    style = (assets / "study_workspace.css").read_text(encoding="utf-8")
    script = (assets / "study_workspace.js").read_text(encoding="utf-8")
    replacements = {
        "__STYLE_HASH__": base64.b64encode(
            hashlib.sha256(style.encode()).digest()
        ).decode(),
        "__SCRIPT_HASH__": base64.b64encode(
            hashlib.sha256(script.encode()).digest()
        ).decode(),
        "__STYLE__": style,
        "__SCRIPT__": script,
        "__DATA__": _embedded_json(envelope),
    }
    # One pass prevents source text containing a template token being substituted.
    page = re.sub(
        r"__(?:STYLE_HASH|SCRIPT_HASH|STYLE|SCRIPT|DATA)__",
        lambda match: replacements[match.group()],
        template,
    ).encode("utf-8")
    return page, {
        "course_id": course,
        "assignment_ids": selected,
        "assignment_count": len(entries),
        "snapshot_sha256": digest,
        "reader": source["reader"],
        "upstream_response_identity": "not_observed",
    }


def validate_output(path: Path) -> None:
    if path.suffix.lower() != ".html":
        raise ValueError("Choose a new output path ending in .html")
    if os.path.lexists(path):
        raise FileExistsError("Output path already exists; choose a new .html file")
    if not path.parent.is_dir():
        raise FileNotFoundError("Output parent directory does not exist")


def write_study_workspace(path: Path, content: bytes) -> None:
    """Publish a fully written new file atomically, without replacing any path."""
    validate_output(path)
    temporary: Path | None = None
    try:
        fd, name = tempfile.mkstemp(
            prefix=".canvaspilot-study-", suffix=".tmp", dir=path.parent
        )
        temporary = Path(name)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        # A same-filesystem hard link publishes the complete bytes, or refuses a
        # destination created since preflight. No replacement/overwrite mode exists.
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run_export_study(args: argparse.Namespace) -> None:
    """Separate CLI boundary; existing command dispatch and transport stay intact."""
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
        base_url = _source_url(args.base_url or default_base_url())
        client = CanvasClient(
            base_url=base_url,
            token=args.token,
            profile=Path(args.profile) if args.profile else default_profile(),
        )
        api = CanvasAPI(client)
        logger.setLevel(max(logging.WARNING, old_level))
        content, report = build_study_workspace(
            api,
            args.course_id,
            args.assignment_ids,
            source_base_url=base_url,
        )
        write_study_workspace(args.out, content)
    except (
        CanvasAuthError,
        CanvasPaginationError,
        httpx.HTTPError,
        ValueError,
        TypeError,
        OSError,
        AttributeError,
    ) as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": type(error).__name__,
                    "message": str(error),
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    finally:
        logger.setLevel(old_level)
        if api is not None:
            api.close()
    print(json.dumps({"ok": True, "output": str(args.out), **report}, indent=2))
