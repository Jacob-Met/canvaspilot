"""A passive offline packet for one unchanged Canvas inbox conversation."""

from __future__ import annotations

import base64
import hashlib
import html
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from canvaspilot.api import CanvasAPI

MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_HTML_BYTES = 16 * 1024 * 1024
_MISSING = object()

_STYLE = """
:root { color-scheme: light; font: 16px/1.6 system-ui, sans-serif; color: #21323d; background: #f0f4f5; }
* { box-sizing: border-box; }
body { margin: 0; }
main { max-width: 960px; margin: auto; padding: 36px 24px 64px; }
h1, h2, h3, p { margin-top: 0; }
h1 { font-size: clamp(1.9rem, 5vw, 2.8rem); line-height: 1.15; }
h2 { font-size: 1.35rem; line-height: 1.35; }
h3 { font-size: 1.1rem; line-height: 1.4; }
header, .panel, .message { margin-bottom: 24px; }
.eyebrow { color: #375665; font-size: .9rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.panel, .message { background: white; border: 1px solid #cad8de; border-radius: 12px; padding: 24px; }
.notice { border-left: 4px solid #517986; background: #e3edf0; padding: 12px 16px; }
.muted, footer { color: #48616d; }
.facts { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); margin: 0; }
.facts dt, .facts dd { min-width: 0; margin: 0; padding: 8px 10px; border-bottom: 1px solid #e3e9ec; }
.facts dt { color: #3a5665; font-weight: 600; }
.value, .message-body { white-space: pre-wrap; overflow-wrap: anywhere; }
.message-body { font-size: 1.05rem; margin: 14px 0 22px; }
.subject { font-size: 1.25rem; }
.context { margin-bottom: 16px; }
summary { cursor: pointer; color: #3a5665; font-weight: 600; margin-bottom: 10px; }
h1, h2, h3, p, li, dt, dd, a, code { overflow-wrap: anywhere; }
code { font: .88rem/1.5 ui-monospace, SFMono-Regular, Consolas, monospace; }
.participants { padding-left: 24px; }
.participants > li { margin-bottom: 20px; padding-left: 6px; }
a { color: #125781; text-underline-offset: .18em; }
a:focus-visible { outline: 3px solid #125781; outline-offset: 4px; }
.download { display: inline-block; border: 1px solid #125781; border-radius: 6px; padding: 10px 16px; font-weight: 650; }
.back { font-size: .9rem; }
@media (max-width: 540px) {
  main { padding: 22px 12px 36px; }
  .panel, .message { padding: 16px; }
  .facts { grid-template-columns: minmax(0, 1fr); }
  .facts dt { border-bottom: 0; padding-bottom: 0; }
  .facts dd { padding-top: 2px; }
}
@media print {
  :root { background: white; color: black; font-size: 10pt; }
  main { max-width: none; padding: 0; }
  .panel, .message { border-radius: 0; padding: 14px; }
  h2, h3, dt { break-after: avoid; }
  .download, .back, nav { display: none; }
  a { color: black; }
}
"""

_LABELS = {
    "id": "ID",
    "subject": "Subject",
    "workflow_state": "Returned read/archive state",
    "author_id": "Author ID",
    "created_at": "Created at, as returned",
    "last_message_at": "Last message at, as returned",
    "last_authored_message_at": "Last authored message at, as returned",
    "message_count": "Reported message count",
    "name": "Name",
    "full_name": "Full name",
    "short_name": "Short name",
    "participating_user_ids": "Participating user IDs",
}


def _escape(text: str) -> str:
    """Keep unsupported HTML code points visible; JSON retains the source."""
    visible = "".join(
        f"\\u{ord(character):04x}"
        if (ord(character) < 32 and character not in "\n\t")
        or 127 <= ord(character) <= 159
        or 0xD800 <= ord(character) <= 0xDFFF
        else character
        for character in text
    )
    return html.escape(visible, quote=True)


def _validate_json(value: Any) -> None:
    """Refuse Python-only values that JSON serialization would coerce."""
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise TypeError("Conversation source object keys must be strings")
            _validate_json(child)
    elif type(value) is list:
        for child in value:
            _validate_json(child)
    elif value is not None and type(value) not in (str, bool, int, float):
        raise TypeError("Conversation source must contain only decoded JSON values")


def _state(value: Any) -> str:
    if value is _MISSING:
        return "missing"
    if value is None:
        return "null"
    if value == "" and isinstance(value, str):
        return "empty-string"
    if isinstance(value, list) and not value:
        return "empty-list"
    return "value"


def _display(value: Any) -> str:
    state = _state(value)
    if state != "value":
        return {
            "missing": "Not returned",
            "null": "Returned null",
            "empty-string": "Empty string",
            "empty-list": "Empty list",
        }[state]
    if isinstance(value, str):
        return _escape(value)
    return _escape(json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2))


def _field(key: str, value: Any) -> str:
    label = _LABELS.get(key, key.replace("_", " ").capitalize())
    return (
        f"<dt>{_escape(label)}</dt>"
        f'<dd class="value" data-field="{_escape(key)}" data-state="{_state(value)}">'
        f"{_display(value)}</dd>"
    )


def _facts(record: dict[str, Any], required: tuple[str, ...], exclude: set[str]) -> str:
    keys = list(required) + [key for key in record if key not in required and key not in exclude]
    return '<dl class="facts">' + "".join(_field(key, record.get(key, _MISSING)) for key in keys) + "</dl>"


def _author_context(message: dict[str, Any], participants: Any) -> str:
    author_id = message.get("author_id", _MISSING)
    matches = []
    if type(author_id) in (int, str, bool, float) and isinstance(participants, list):
        matches = [
            participant for participant in participants
            if isinstance(participant, dict)
            and type(participant.get("id", _MISSING)) is type(author_id)
            and participant.get("id", _MISSING) == author_id
        ]
    if not matches:
        return "Unresolved author: no matching returned participant."
    if len(matches) != 1:
        return "Ambiguous author: multiple returned participants have this ID."
    participant = matches[0]
    for key in ("full_name", "name", "short_name"):
        name = participant.get(key)
        if isinstance(name, str) and name:
            return "Returned participant: " + _escape(name)
    return "Matched returned participant; no usable display name was returned."


def _participants(value: Any) -> str:
    parts = [
        f'<section class="panel" data-field="participants" data-state="{_state(value)}">',
        "<h2>Returned participants</h2>",
    ]
    if isinstance(value, list) and value:
        parts.append('<ol class="participants">')
        for participant in value:
            parts.append("<li>")
            if isinstance(participant, dict):
                parts.append(_facts(participant, ("id", "name"), set()))
            else:
                parts.append('<p class="muted">Returned participant entry is not an object.</p>')
                parts.append('<div class="value">' + _display(participant) + "</div>")
            parts.append("</li>")
        parts.append("</ol>")
    else:
        parts.append('<div class="value">' + _display(value) + "</div>")
        if value is not _MISSING and value is not None and not isinstance(value, list):
            parts.append('<p class="muted">The returned participants value is not a list.</p>')
    parts.append("</section>")
    return "".join(parts)


def _message(value: Any, index: int, participants: Any) -> str:
    parts = [
        f'<article class="message" id="message-{index}">',
        f"<h3>Message {index + 1}</h3>",
    ]
    if isinstance(value, dict):
        parts.append('<p class="muted author-context">' + _author_context(value, participants) + "</p>")
        identity_keys = ("id", "author_id", "created_at")
        identity = {key: value[key] for key in identity_keys if key in value}
        parts.append(_facts(identity, identity_keys, set()))
        body = value.get("body", _MISSING)
        parts.append(
            f'<div class="message-body" data-field="body" data-state="{_state(body)}">'
            + _display(body) + "</div>"
        )
        additional = {key: item for key, item in value.items() if key not in (*identity_keys, "body")}
        if additional:
            parts.append(
                '<details class="context" open><summary>Additional returned message context</summary>'
            )
            parts.append(_facts(additional, (), set()))
            parts.append("</details>")
    else:
        parts.append('<p class="muted">Returned message entry is not an object.</p>')
        parts.append('<div class="value">' + _display(value) + "</div>")
    parts.append('<p class="back"><a href="#top">Back to overview</a></p></article>')
    return "".join(parts)


def render_conversation_packet(
    source: dict[str, Any], *, generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Render the returned JSON object without normalizing or mutating it."""
    if type(source) is not dict:
        raise ValueError("Conversation response must be a JSON object")
    _validate_json(source)
    payload = (json.dumps(source, ensure_ascii=True, allow_nan=False, separators=(",", ":")) + "\n").encode("ascii")
    if len(payload) > MAX_SOURCE_BYTES:
        raise ValueError("Conversation source JSON exceeds the 4 MiB export limit")
    stamp = generated_at if generated_at is not None else datetime.now(UTC)
    if not isinstance(stamp, datetime) or stamp.utcoffset() is None:
        raise ValueError("generated_at must be a timezone-aware datetime")
    created = stamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
    payload_hash = hashlib.sha256(payload).hexdigest()
    encoded = base64.b64encode(payload).decode("ascii")
    messages = source.get("messages", _MISSING)
    participants = source.get("participants", _MISSING)
    subject = source.get("subject", _MISSING)
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="referrer" content="no-referrer">',
        ('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"),
        "<title>Conversation snapshot — CanvasPilot</title>",
        "<style>", _STYLE, '</style></head><body><main id="top">',
        '<header><p class="eyebrow">CanvasPilot · Saved inbox conversation</p>',
        "<h1>Conversation snapshot</h1>",
        f'<p>Saved <time datetime="{created}">{created}</time></p>',
        ('<p class="notice">This file preserves one returned conversation without marking it read. '
        "It does not refresh or establish that the thread or its history is complete. "
        "Messages and participants retain their returned order; dates below remain as supplied.</p></header>"),
        '<section class="panel"><h2>Subject and conversation context</h2>',
        f'<div class="value subject" data-field="subject" data-state="{_state(subject)}">'
        + _display(subject) + "</div>",
        _facts(source, ("id", "workflow_state", "message_count"), {"subject", "messages", "participants"}),
        "</section>",
        _participants(participants),
        f'<section data-field="messages" data-state="{_state(messages)}"><h2>Returned messages</h2>',
    ]
    if isinstance(messages, list) and messages:
        parts.extend(_message(message, index, participants) for index, message in enumerate(messages))
    else:
        parts.append('<div class="panel value">' + _display(messages) + "</div>")
        if messages is not _MISSING and messages is not None and not isinstance(messages, list):
            parts.append('<p class="muted">The returned messages value is not a list.</p>')
    parts.extend([
        '</section><section class="panel"><h2>Complete source</h2>',
        (f'<p><a class="download" id="download-source" download="conversation.json" '
        f'href="data:application/json;base64,{encoded}">Download complete conversation JSON</a></p>'),
        ('<p class="muted">The download preserves the complete decoded response, including unknown fields, '
        "attachment metadata and forwarded data. It does not preserve HTTP wire formatting. "
        "Attachments are not downloaded. Null, false, zero and empty values remain distinct.</p>"),
        ('<p class="muted">Bodies are displayed as literal text. Line feeds, tabs and ordinary Unicode '
        "remain unstripped. Unsupported control characters, carriage returns and lone surrogates are "
        "shown as \\uXXXX; their original decoded values remain in the JSON download.</p>"),
        f'<p class="muted">JSON SHA-256: <code id="json-sha256">{payload_hash}</code></p>',
        ("</section><footer>Open this file directly in a browser. Use Print for a paper copy or PDF. "
        "The packet has no scripts, external resources, reply form or read-state controls.</footer>"),
        "</main></body></html>\n",
    ])
    content = "".join(parts).encode("utf-8")
    if len(content) > MAX_HTML_BYTES:
        raise ValueError("Rendered conversation HTML exceeds the 16 MiB export limit")
    return content, {
        "conversation_id": source.get("id"),
        "generated_at": created,
        "html_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "json_bytes": len(payload),
        "json_sha256": payload_hash,
    }


def build_conversation_packet(
    api: CanvasAPI, conversation_id: int | str, *, generated_at: datetime | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Read once through the established state-preserving conversation method."""
    source = api.get_conversation(conversation_id)
    content, receipt = render_conversation_packet(source, generated_at=generated_at)
    receipt["requested_conversation_id"] = conversation_id
    return content, receipt


def run_export_conversation(args: Any) -> None:
    """Handle new-file admission before constructing the existing Canvas client."""
    import logging
    import os
    import sys
    from pathlib import Path

    import httpx

    from canvaspilot.api import CanvasAPI
    from canvaspilot.client import (
        CanvasAuthError,
        CanvasClient,
        CanvasPaginationError,
        default_base_url,
        default_profile,
    )
    from canvaspilot.page_export import write_page_packet

    http_log = logging.getLogger("httpx")
    previous_level = http_log.level
    http_log.setLevel(max(http_log.getEffectiveLevel(), logging.WARNING))
    try:
        if os.path.lexists(args.out):
            raise FileExistsError("Output path already exists; choose a new HTML file")
        client = CanvasClient(
            base_url=args.base_url or default_base_url(),
            token=args.token,
            profile=Path(args.profile) if args.profile else default_profile(),
        )
        try:
            content, receipt = build_conversation_packet(CanvasAPI(client), args.conversation_id)
        finally:
            client.close()
        warning = write_page_packet(args.out, content)
    except (CanvasAuthError, CanvasPaginationError, httpx.HTTPError, ValueError, TypeError, OSError, RecursionError) as error:
        print(json.dumps({
            "ok": False, "error": type(error).__name__, "message": str(error),
        }), file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        http_log.setLevel(previous_level)
    result = {"ok": True, "output": str(args.out), **receipt}
    if warning is not None:
        result["cleanup_warning"] = warning
    print(json.dumps(result, indent=2, allow_nan=False))
