"""Passive, new-file-only reading packets from the existing course reader."""

from __future__ import annotations

import base64
import hashlib
import os
import re
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlsplit

if TYPE_CHECKING:
    from canvaspilot.api import CanvasAPI

MAX_COURSES = 10
MAX_BODY_BYTES = 512 * 1024
MAX_TOTAL_BODY_BYTES = 2 * 1024 * 1024
MAX_PACKET_BYTES = 32 * 1024 * 1024
MAX_TAGS = 20_000
MAX_DEPTH = 256
_MISSING = object()
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
         "link", "meta", "param", "source", "track", "wbr"}
_PASSIVE = {
    "p", "div", "section", "article", "header", "footer", "address",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "code",
    "kbd", "samp", "var", "strong", "b", "em", "i", "u", "s", "del",
    "ins", "sub", "sup", "mark", "small", "span", "abbr", "cite", "q",
    "ul", "ol", "li", "dl", "dt", "dd", "table", "thead", "tbody",
    "tfoot", "tr", "th", "td", "caption", "colgroup", "col", "br", "hr", "wbr",
}
_SUPPRESS = {"script", "style", "iframe", "object", "canvas", "svg", "math", "template"}
_RESOURCE = {
    "img", "audio", "video", "source", "track", "embed", "applet",
    "form", "input", "select", "button", "textarea", "link", "meta", "base",
    "area", "param",
}
_CSS = """
:root{color-scheme:light;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#20322f;background:#f4f6f2;line-height:1.6}
*{box-sizing:border-box}body{margin:0}main{max-width:72rem;margin:auto;padding:2rem 1.25rem 4rem}
.packet-header{border-top:6px solid #146756;padding:1rem 0}.eyebrow{font-size:.82rem;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:#275d50}
h1{line-height:1.15;font-size:clamp(2rem,5vw,3.25rem);margin:.5rem 0 1rem}h2,h3,h4,h5,h6{line-height:1.3}
a{color:#085d51;text-underline-offset:.18em}a:focus-visible,summary:focus-visible{outline:3px solid #914a00;outline-offset:3px}
nav,.notice,.course{border:1px solid #acbfb5;border-radius:.6rem;background:#fff;padding:1rem 1.25rem;margin:1.25rem 0}
.notice{border-left:5px solid #8b5a15;background:#fff9e9}.course{padding:1.5rem}.course>h2{margin-top:0}
dl.meta{display:grid;grid-template-columns:minmax(8rem,13rem) minmax(0,1fr);gap:.3rem 1rem;font-size:.92rem}
dt{font-weight:700}dd{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}.status{font-weight:700}
.syllabus{border-top:1px solid #acbfb5;margin-top:1rem;padding-top:.75rem;overflow-wrap:anywhere}
.syllabus h1{font-size:1.8rem}.syllabus h2{font-size:1.5rem}.syllabus pre,pre.source{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef3ef;border:1px solid #c7d4cc;border-radius:.3rem;padding:.9rem}
.syllabus blockquote{border-left:4px solid #719483;margin-left:.4rem;padding-left:1rem}.syllabus li{margin:.3rem 0}
.table-wrap{max-width:100%;overflow:auto;margin:1rem 0}table{border-collapse:collapse;width:100%}th,td{border:1px solid #9eb3a7;padding:.5rem;text-align:start;vertical-align:top}th{background:#e6eee8}caption{font-weight:700;text-align:start;padding:.4rem 0}
.destination,.omission{display:inline;color:#5d431a;font-size:.88rem;overflow-wrap:anywhere}.omission{font-weight:600}
.packet-source{border-top:1px dashed #a1b4a8;margin-top:1.5rem;padding-top:1rem}summary{cursor:pointer;font-weight:700}.source{font-size:.82rem}
.small{font-size:.88rem}.top-link{font-size:.85rem}footer{font-size:.88rem;color:#42594e}
@media(max-width:40rem){main{padding:1rem .75rem 2rem}.course,nav,.notice{padding:1rem}dl.meta{display:block}dt{margin-top:.5rem}.syllabus ul,.syllabus ol{padding-left:1.5rem}}
@page{size:auto;margin:14mm}
@media print{body,:root{background:white;color:black}main{max-width:none;padding:0}.course{border:0;border-top:1px solid #555;border-radius:0;padding:.8rem 0;break-before:page}.course h2,.syllabus h1,.syllabus h2,.syllabus h3{break-after:avoid}nav,.top-link,.packet-source,.packet-footer{display:none}.notice{background:white;border-color:#555}a{color:black}.table-wrap{overflow:visible}thead{display:table-header-group}tr{break-inside:avoid}th{background:white}}
"""


def _text(value: str) -> str:
    # Character references preserve CR in the DOM; NUL has no exact HTML text
    # representation. The source download, not its preview, preserves all bytes.
    return escape(value, quote=True).replace("\r", "&#13;").replace("\x00", "&#xfffd;")


def _course_ids(values: Sequence[int | str]) -> list[int]:
    if isinstance(values, (str, bytes)) or not 1 <= len(values) <= MAX_COURSES:
        raise ValueError("Select 1 to 10 unique positive course IDs")
    result = []
    for value in values:
        if type(value) is int:
            parsed = value
        elif isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
            parsed = int(value)
        else:
            raise ValueError("Course IDs must be positive integers")
        if parsed <= 0:
            raise ValueError("Course IDs must be positive integers")
        if parsed in result:
            raise ValueError("Duplicate course IDs are not allowed")
        result.append(parsed)
    return result


def _safe_url(value: str) -> str | None:
    if not value or "\\" in value or any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in value):
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"https", "http"} or not parts.hostname:
            return None
        if parts.username is not None or parts.password is not None:
            return None
        _ = parts.port
    except ValueError:
        return None
    return value


def _metadata(course: dict[str, Any], key: str) -> str:
    value = course.get(key, _MISSING)
    if value is _MISSING:
        return "Not supplied"
    if value is None:
        return "Unavailable (null)"
    if not isinstance(value, str):
        raise TypeError(f"Course {key} must be a string, null, or absent")
    if len(value.encode("utf-8")) > 4096:
        raise ValueError(f"Course {key} exceeds the 4 KiB metadata limit")
    return value if value else "Empty string supplied"


class _ReadingHTML(HTMLParser):
    """Rebuild an allowlisted reading projection; never copy active markup."""

    def __init__(self, course_url: str, course_id: int) -> None:
        super().__init__(convert_charrefs=True)
        self.course_url = course_url
        self.prefix = f"source-{course_id}-"
        self.parts: list[str] = []
        self.frames: list[tuple[str, str, bool]] = []
        self.suppressed = 0
        self.tags = 0
        self.omissions = 0

    def _destination(self, raw: str) -> tuple[str | None, str]:
        try:
            resolved = urljoin(self.course_url, raw)
            safe = _safe_url(resolved) if raw else None
        except ValueError:
            # A malformed destination remains useful source evidence, not a
            # reason to lose otherwise readable course material.
            resolved, safe = raw, None
        note = "Link target: " + (raw if raw else "(empty)")
        if safe and resolved != raw:
            note += "; resolved against configured Canvas URL: " + resolved
        note += "; linked content is not included"
        if not safe:
            note += "; destination kept as text only"
        return safe, '<span class="destination"> [' + _text(note) + "]</span>"

    def _omission(self, tag: str, attrs: dict[str, str | None]) -> None:
        self.omissions += 1
        note = f"{tag} element not embedded; its behavior or resource content is omitted"
        for name in ("alt", "title", "aria-label", "src", "srcset", "href", "data", "poster"):
            if attrs.get(name) is not None:
                note += f"; {name}: {attrs[name]}"
        self.parts.append('<span class="omission"> [' + _text(note) + "]</span>")

    def _attributes(self, tag: str, attrs: dict[str, str | None]) -> str:
        out = []
        for name in ("title", "lang", "dir"):
            value = attrs.get(name)
            if value is not None and (name != "dir" or value in {"ltr", "rtl", "auto"}):
                out.append(f' {name}="{_text(value)}"')
        if attrs.get("id") is not None:
            out.append(f' id="{_text(self.prefix + attrs["id"])}"')
        for name in (("start",) if tag == "ol" else ("value",) if tag == "li" else ()):
            value = attrs.get(name)
            if value is not None:
                # These numeric-only HTML attributes are passive. Let the
                # browser keep its native integer parsing and numbering.
                out.append(f' {name}="{_text(value)}"')
        if tag == "ol":
            if "reversed" in attrs:
                out.append(" reversed")
            if attrs.get("type") in {"1", "a", "A", "i", "I"}:
                out.append(f' type="{attrs["type"]}"')
        if tag in {"td", "th"}:
            for name, maximum, minimum in (("colspan", 1000, 1), ("rowspan", 65534, 0)):
                value = attrs.get(name)
                if value is not None:
                    if not re.fullmatch(r"[0-9]{1,5}", value) or not minimum <= int(value) <= maximum:
                        raise ValueError(f"Table {name} is outside the supported whole-number range")
                    out.append(f' {name}="{value}"')
            if attrs.get("scope") in {"row", "col", "rowgroup", "colgroup"}:
                out.append(f' scope="{attrs["scope"]}"')
            if attrs.get("headers"):
                headers = " ".join(self.prefix + part for part in attrs["headers"].split())
                out.append(f' headers="{_text(headers)}"')
        return "".join(out)

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        self.tags += 1
        if self.tags > MAX_TAGS:
            raise ValueError("Syllabus exceeds the 20,000-tag reading limit")
        if len(self.frames) >= MAX_DEPTH:
            raise ValueError("Syllabus exceeds the 256-level nesting limit")
        # HTML discards later duplicate attributes. Preserve the first value,
        # including link identity, instead of dict() silently choosing the last.
        attrs: dict[str, str | None] = {}
        for name, value in attributes:
            attrs.setdefault(name, value)
        closing = ""
        block = False
        if not self.suppressed:
            if tag in _SUPPRESS:
                self._omission(tag, attrs)
                block = True
            elif tag == "a":
                raw = attrs.get("href")
                if raw is None:
                    self.parts.append("<span>")
                    closing = "</span>"
                else:
                    safe, note = self._destination(raw)
                    if safe:
                        self.parts.append(
                            f'<a href="{_text(safe)}" rel="noopener noreferrer" '
                            'referrerpolicy="no-referrer">'
                        )
                        closing = "</a>" + note
                    else:
                        self.parts.append("<span>")
                        closing = "</span>" + note
            elif tag in _PASSIVE:
                extra = self._attributes(tag, attrs)
                if tag == "table":
                    self.parts.append('<div class="table-wrap">')
                self.parts.append(f"<{tag}{extra}>")
                if tag not in _VOID:
                    closing = f"</{tag}>" + ("</div>" if tag == "table" else "")
            elif tag in _RESOURCE or tag not in {"html", "head", "body"}:
                self._omission(tag, attrs)
        if tag not in _VOID:
            self.frames.append((tag, closing, block))
            if block:
                self.suppressed += 1

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.frames) - 1, -1, -1):
            if self.frames[index][0] == tag:
                while len(self.frames) > index:
                    _, closing, block = self.frames.pop()
                    self.parts.append(closing)
                    if block:
                        self.suppressed -= 1
                break

    def handle_data(self, data: str) -> None:
        if not self.suppressed:
            self.parts.append(_text(data))

    def finish(self) -> str:
        self.close()
        while self.frames:
            _, closing, _ = self.frames.pop()
            self.parts.append(closing)
        return "".join(self.parts)


def build_syllabus_packet(
    api: CanvasAPI,
    course_ids: Sequence[int | str],
    *,
    captured_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Collect every selected course before returning one complete HTML packet."""
    selected = _course_ids(course_ids)
    base = api.client.base_url
    if not isinstance(base, str) or not _safe_url(base):
        raise ValueError("Configured Canvas base URL must be an HTTP(S) URL without credentials")
    stamp = captured_at or datetime.now(UTC)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("Capture time must include a timezone")
    timestamp = stamp.astimezone(UTC).isoformat(timespec="seconds")
    total = 0
    sections = []
    navigation = []
    statuses = []
    for course_id in selected:
        course = api.get_course(course_id)
        if not isinstance(course, dict):
            raise TypeError(f"Course {course_id} did not return a course object")
        returned_id = course.get("id")
        try:
            matches = _course_ids([returned_id]) == [course_id]
        except (ValueError, TypeError):
            matches = False
        if not matches:
            raise ValueError(f"Returned course identity does not match selected course {course_id}")
        name = _metadata(course, "name")
        code = _metadata(course, "course_code")
        raw_name = course.get("name")
        heading = raw_name if isinstance(raw_name, str) and raw_name else f"Course {course_id}"
        course_url = urljoin(base.rstrip("/") + "/", f"/courses/{course_id}/assignments/syllabus")
        body = course.get("syllabus_body", _MISSING)
        source = ""
        if body is _MISSING:
            state = "not_supplied"
            reading = '<p class="status">Syllabus body not supplied by Canvas. Its contents are unknown.</p>'
        elif body is None:
            state = "unavailable"
            reading = '<p class="status">Syllabus body unavailable (null). Its contents are unknown.</p>'
        elif isinstance(body, str):
            body_bytes = body.encode("utf-8")
            if len(body_bytes) > MAX_BODY_BYTES:
                raise ValueError(f"Course {course_id} syllabus exceeds the 512 KiB source limit")
            total += len(body_bytes)
            if total > MAX_TOTAL_BODY_BYTES:
                raise ValueError("Selected syllabi exceed the 2 MiB combined source limit")
            digest = hashlib.sha256(body_bytes).hexdigest()
            encoded = base64.b64encode(body_bytes).decode("ascii")
            source = (
                '<details class="packet-source"><summary>Supplied HTML source and exact text download</summary>'
                '<p>This escaped preview is inert. Browsers can normalize control characters when displaying '
                'or copying it; the text download preserves the exact UTF-8 bytes supplied in syllabus_body.</p>'
                f'<p><a href="data:text/plain;base64,{encoded}" download="course-{course_id}-syllabus-source.txt">'
                'Download supplied syllabus HTML as a text file</a></p>'
                f'<p class="small">Source: {len(body_bytes)} bytes · SHA-256 {_text(digest)}</p>'
                f'<pre class="source">{_text(body)}</pre></details>'
            )
            if body == "":
                state = "empty"
                reading = '<p class="status">Canvas supplied an explicitly empty syllabus body (zero bytes).</p>'
            else:
                state = "supplied"
                renderer = _ReadingHTML(course_url, course_id)
                try:
                    renderer.feed(body)
                    projection = renderer.finish()
                except AssertionError as error:
                    # HTMLParser uses AssertionError for unknown marked
                    # declarations. Keep malformed source inside CLI refusal.
                    raise ValueError(f"Course {course_id} contains unsupported HTML markup") from error
                reading = (
                    '<p class="status">Syllabus HTML supplied. The reading projection follows.</p>'
                    f'<div class="syllabus">{projection}</div>'
                )
                if not projection.strip():
                    reading += '<p class="notice">The supplied HTML has no projected text. This is not an explicitly empty source.</p>'
        else:
            raise TypeError(f"Course {course_id} syllabus_body must be HTML text, null, or absent")
        navigation.append(f'<li><a href="#course-{course_id}">{_text(heading)}</a> · Course {course_id}</li>')
        statuses.append({"course_id": course_id, "status": state})
        sections.append(
            f'<section class="course" id="course-{course_id}" data-course-id="{course_id}" '
            f'data-syllabus-status="{state}"><h2>{_text(heading)}</h2>'
            '<dl class="meta">'
            f'<dt>Course ID</dt><dd>{course_id}</dd>'
            f'<dt>Returned name</dt><dd>{_text(name)}</dd>'
            f'<dt>Course code</dt><dd>{_text(code)}</dd>'
            f'<dt>Configured course link</dt><dd><a href="{_text(course_url)}" '
            f'rel="noopener noreferrer" referrerpolicy="no-referrer">{_text(course_url)}</a></dd>'
            '</dl>' + reading + source +
            '<p class="top-link"><a href="#packet-top">Back to courses</a></p></section>'
        )
    document = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
        '<meta name="referrer" content="no-referrer"><title>Syllabus reading packet</title>'
        f'<style>{_CSS}</style></head><body><main id="packet-top">'
        '<header class="packet-header"><p class="eyebrow">CanvasPilot · Saved reading</p>'
        '<h1>Syllabus reading packet</h1>'
        f'<p>{len(selected)} selected course{"s" if len(selected) != 1 else ""} · Saved {_text(timestamp)}</p>'
        f'<p class="small">Configured Canvas base URL: {_text(base)}</p></header>'
        '<aside class="notice"><strong>What this packet contains</strong>'
        '<p>These are sequential course reads, not a simultaneous snapshot or a promise that policies are current. '
        'Read the supplied text, headings, lists and tables below. Source styling and interactive behavior are not retained; '
        'malformed or unsupported HTML can look different. An omitted-resource marker is not the resource itself.</p>'
        '<p>Images, media, frames and linked files are not downloaded or embedded. Their supplied descriptions and destinations '
        'are shown where available. Follow an online link to read information that exists only there; Canvas may require sign-in. '
        'Canvas’s separately generated course-summary assignments and events are not included in syllabus_body.</p>'
        '<p>Course identity matches the requested ID. The configured URL supplies link context, not a verified response origin: '
        'the unchanged client can use a broker or redirects. Returned names may be your Canvas nicknames.</p>'
        '<p>Open or print this file without CanvasPilot or a network connection. Source previews and text-download controls '
        'remain on screen and are left out of print.</p></aside>'
        '<nav aria-label="Selected courses"><h2>Courses in this packet</h2><ol>' +
        "".join(navigation) + '</ol></nav>' + "".join(sections) +
        '<footer class="packet-footer">Saved by CanvasPilot. Only explicit navigation leaves this local reading file.</footer>'
        '</main></body></html>\n'
    ).encode("utf-8")
    if len(document) > MAX_PACKET_BYTES:
        raise ValueError("Rendered packet exceeds the 32 MiB output limit")
    return document, {
        "course_ids": selected, "course_count": len(selected), "syllabus_statuses": statuses,
        "captured_at": timestamp, "source_body_bytes": total, "output_bytes": len(document),
    }


def write_syllabus_packet(path: Path, content: bytes) -> None:
    """Publish complete bytes under a new name, preserving all existing entries."""
    # Follow the calendar export's same-directory hard-link publication. Never
    # fall back to rename/replace on a filesystem that cannot provide this rule.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="." + path.name + ".", suffix=".tmp", dir=path.parent, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink()
