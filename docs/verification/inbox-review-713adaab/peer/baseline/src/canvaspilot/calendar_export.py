"""Export selected Canvas assignment deadlines as a local iCalendar snapshot."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit, urlunsplit

if TYPE_CHECKING:
    from canvaspilot.api import CanvasAPI

BUCKETS = ("upcoming", "past", "overdue", "undated", "ungraded", "unsubmitted", "all")


def _identifier(value: Any, label: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise TypeError(f"{label} must be a positive numeric Canvas ID")
    text = str(value)
    if not re.fullmatch(r"[0-9]+", text) or not any(c != "0" for c in text):
        raise ValueError(f"{label} must be a positive numeric Canvas ID")
    return text.lstrip("0")


def _text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    if any(ord(c) < 32 and c not in "\n\t" or ord(c) == 127 for c in value):
        raise ValueError("Calendar text contains an unsupported control character")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Calendar text is not valid Unicode") from exc
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def _fold(line: str) -> str:
    """Fold at UTF-8 boundaries, counting the continuation space in 75 octets."""
    lines = []
    current = ""
    size = 0
    for char in line:
        width = len(char.encode("utf-8"))
        if size + width > 75:
            lines.append(current)
            current, size = " ", 1
        current += char
        size += width
    lines.append(current)
    return "\r\n".join(lines) + "\r\n"


def _web_url(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or any(ord(c) <= 32 or ord(c) >= 127 for c in value):
        raise ValueError(f"{label} must be an absolute ASCII HTTP(S) URL")
    try:
        parsed = urlsplit(value)
        port = parsed.port
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or "\\" in value):
            raise ValueError()
    except ValueError as exc:
        raise ValueError(f"{label} must be an absolute HTTP(S) URL without credentials") from exc
    # Validate the parsed port even when the caller retains the original URL.
    del port
    return value


def _source_identity(value: str) -> str:
    parsed = urlsplit(_web_url(value, "Canvas base URL"))
    if parsed.query or parsed.fragment:
        raise ValueError("Canvas base URL must not contain a query or fragment")
    host = parsed.hostname.lower()
    if ":" in host:
        host = "[" + host + "]"
    port = parsed.port
    if port is not None and (parsed.scheme, port) not in {("http", 80), ("https", 443)}:
        host += ":" + str(port)
    return urlunsplit((parsed.scheme.lower(), host, parsed.path.rstrip("/"), "", ""))


def _instant(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.0+)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])", value
    ):
        raise ValueError(f"{label} must be an ISO whole-second timestamp with a timezone")
    try:
        instant = datetime.fromisoformat(value)
        if instant.utcoffset() is None or instant.microsecond:
            raise ValueError()
        return instant.astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be a representable whole-second timestamp with a timezone") from exc


def _stamp(value: datetime) -> str:
    # strftime("%Y") can omit leading zeroes for years below 1000.
    return (f"{value.year:04d}{value.month:02d}{value.day:02d}T"
            f"{value.hour:02d}{value.minute:02d}{value.second:02d}Z")


def build_assignment_calendar(
    api: CanvasAPI,
    course_ids: list[int | str],
    *,
    bucket: str = "upcoming",
    generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Read selected courses and render deadline markers; never mutate Canvas.

    Coverage is exactly the rows returned by the existing assignment reader.
    A null due date is reported and omitted. Malformed dated rows or any course
    read failure refuse the export, so no partial course snapshot is published.
    """
    if bucket not in BUCKETS:
        raise ValueError("Unsupported assignment bucket")
    courses = list(dict.fromkeys(_identifier(value, "course_id") for value in course_ids))
    if not courses:
        raise ValueError("Select at least one course")
    source = _source_identity(api.client.base_url)
    now = generated_at if generated_at is not None else datetime.now(UTC)
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("generated_at must be a timezone-aware datetime")
    try:
        stamp = _stamp(now.astimezone(UTC))
    except (ValueError, OverflowError) as exc:
        raise ValueError("generated_at is outside the supported UTC range") from exc

    events = []
    omitted = []
    counts = []
    seen = set()
    for course in courses:
        rows = api.list_assignments(course, bucket=None if bucket == "all" else bucket)
        if not isinstance(rows, list):
            raise TypeError(f"Course {course} did not return an assignment list")
        exported = 0
        for row in rows:
            if not isinstance(row, dict):
                raise TypeError(f"Course {course} returned a malformed assignment")
            identity = _identifier(row.get("id"), "assignment_id")
            key = (course, identity)
            if key in seen:
                raise ValueError(f"Course {course} returned duplicate assignment {identity}")
            seen.add(key)
            if row.get("due_at") is None:
                omitted.append({"course_id": course, "assignment_id": identity, "reason": "no_due_date"})
                continue
            due = _instant(row["due_at"], f"Assignment {course}/{identity} due_at")
            name = row.get("name")
            if name is None:
                name = "Assignment " + identity
            if not isinstance(name, str):
                raise TypeError(f"Assignment {course}/{identity} name must be text")
            uid_key = json.dumps([source, course, identity], separators=(",", ":")).encode()
            uid = hashlib.sha256(uid_key).hexdigest() + "@canvaspilot"
            lines = [
                "BEGIN:VEVENT",
                "UID:" + uid,
                "DTSTAMP:" + stamp,
                "DTSTART:" + _stamp(due),
                "SUMMARY:" + _text(f"[Course {course}] {name}"),
                "DESCRIPTION:" + _text("Canvas assignment deadline. Exported snapshot; check Canvas for changes."),
                "TRANSP:TRANSPARENT",
            ]
            url = row.get("html_url")
            if url is not None:
                lines.append("URL:" + _web_url(url, f"Assignment {course}/{identity} URL"))
            lines.append("END:VEVENT")
            events.append((due, course, identity, lines))
            exported += 1
        counts.append({"course_id": course, "assignments_returned": len(rows), "events_exported": exported})

    if not events:
        raise ValueError(f"No dated assignments to export ({len(omitted)} without a due date); no file created")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//CanvasPilot//Assignment deadlines//EN", "CALSCALE:GREGORIAN"]
    for _, _, _, event in sorted(events, key=lambda e: e[:3]):
        lines.extend(event)
    lines.append("END:VCALENDAR")
    content = "".join(_fold(line) for line in lines).encode("utf-8")
    report = {
        "source": source,
        "bucket": bucket,
        "generated_at": now.astimezone(UTC).isoformat(),
        "course_ids": courses,
        "course_summaries": counts,
        "events_exported": len(events),
        "assignments_omitted": omitted,
        "coverage": "Returned assignment rows only; existing transport pagination limits apply.",
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    return content, report


def write_calendar(path: Path, content: bytes) -> None:
    """Publish complete bytes to a new local file without replacing any entry."""
    # Same-directory hard-link publication refuses existing files and symlinks.
    # Unsupported filesystems fail safely; no rename/replace fallback.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix="." + path.name + ".", suffix=".tmp",
                                         dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink()
