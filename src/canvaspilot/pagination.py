"""Canvas's opaque Link continuation contract for collection reads."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

import httpx


class CanvasPaginationError(RuntimeError):
    """The requested collection could not be read completely."""


def with_query(path: str, params: dict[str, Any] | list[tuple[str, Any]] | None) -> str:
    """Match native HTTPX query encoding, including arrays and empty values."""
    if not params:
        return path
    query = str(httpx.QueryParams(params))
    if not query:
        return path
    return f"{path}{'&' if '?' in path else '?'}{query}"


def _origin(url: SplitResult) -> tuple[str, str | None, int | None]:
    default_port = {"https": 443, "http": 80}.get(url.scheme.lower())
    return url.scheme.lower(), url.hostname, url.port if url.port is not None else default_port


def broker_path(url: str, base_url: str) -> str:
    """Keep pagination on the configured Canvas origin without broker navigation.

    Canvas documents absolute continuation URLs. Root-relative URLs are also
    accepted, but no continuation may change scheme/host/port or carry userinfo.
    The query remains opaque: never decode, increment, or rebuild its cursor.
    """
    try:
        if not isinstance(url, str) or not url or any(ord(c) <= 32 for c in url):
            raise ValueError
        if "\\" in url or "#" in url:
            raise ValueError
        parsed, base = urlsplit(url), urlsplit(base_url)
        if base.scheme not in ("http", "https") or not base.hostname:
            raise ValueError
        if parsed.username is not None or parsed.password is not None:
            raise ValueError
        if parsed.scheme or parsed.netloc:
            if not parsed.scheme or _origin(parsed) != _origin(base):
                raise ValueError
        elif not url.startswith("/") or url.startswith("//"):
            raise ValueError
        if parsed.path.startswith("//"):
            raise ValueError
        return urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    except ValueError:
        # Do not expose opaque cursors, query tokens, or foreign URLs in errors.
        raise CanvasPaginationError(
            "Canvas pagination requires a valid URL on the configured Canvas origin."
        ) from None


def _split_fields(value: str, separator: str) -> list[str]:
    """Split only outside quoted parameters and the URI's angle brackets."""
    fields, start = [], 0
    quoted = bracketed = escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
        elif quoted and char == "\\":
            escaped = True
        elif char == '"' and not bracketed:
            quoted = not quoted
        elif not quoted:
            if char == "<":
                if bracketed:
                    raise CanvasPaginationError("Malformed Canvas pagination Link header.")
                bracketed = True
            elif char == ">":
                if not bracketed:
                    raise CanvasPaginationError("Malformed Canvas pagination Link header.")
                bracketed = False
            elif char == separator and not bracketed:
                fields.append(value[start:index].strip())
                start = index + 1
    if quoted or bracketed or escaped:
        raise CanvasPaginationError("Malformed Canvas pagination Link header.")
    fields.append(value[start:].strip())
    return fields


# Parameter and relation grammar contributed by estate-86776bb3cdb8, commit
# 246602b0edac3092ef957e391702815702451e2c, independently received against this
# parser. RFC 8288 section 3 defines token/quoted values and relation syntax.
_LINK_TOKEN = r"[!#$%&'*+.^_`|~0-9A-Za-z-]+"
_LINK_VALUE = rf'(?:"(?:[^"\\]|\\.)*"|{_LINK_TOKEN})'
_PARAMETER = re.compile(rf"({_LINK_TOKEN})(?:\s*=\s*({_LINK_VALUE}))?")
_RELATION = re.compile(
    r"(?:[A-Za-z][A-Za-z0-9.-]*|"
    r"[A-Za-z][A-Za-z0-9+.-]*:(?:[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=-]|%[0-9A-Fa-f]{2})*)"
)


def next_link(header: str | None) -> str | None:
    """Find one exact ``next`` relation without splitting an opaque URI's commas."""
    if header is None or header == "":
        return None
    if not isinstance(header, str) or any(ord(c) < 32 for c in header):
        raise CanvasPaginationError("Malformed Canvas pagination Link header.")
    following: list[str] = []
    for field in _split_fields(header, ","):
        if not field.startswith("<") or ">" not in field:
            raise CanvasPaginationError("Malformed Canvas pagination Link header.")
        target, parameters = field[1:].split(">", 1)
        if not target or (parameters.strip() and not parameters.lstrip().startswith(";")):
            raise CanvasPaginationError("Malformed Canvas pagination Link header.")
        relations: list[str] = []
        for parameter in _split_fields(parameters, ";")[1:]:
            match = _PARAMETER.fullmatch(parameter)
            if match is None:
                raise CanvasPaginationError("Malformed Canvas pagination Link parameter.")
            name, value = match.groups()
            if name.lower() == "anchor":
                # An anchor changes the linked resource's context (RFC 8288
                # section 3.2). It cannot be ignored while following the link.
                raise CanvasPaginationError("Canvas pagination Link has an unsupported anchor context.")
            if name.lower() != "rel":
                continue
            if value is None or relations:
                raise CanvasPaginationError("Malformed Canvas pagination Link relation.")
            if value.startswith('"'):
                value = re.sub(r"\\(.)", r"\1", value[1:-1])
            relations = [item.lower() for item in value.split(" ") if item]
            if not relations or any(_RELATION.fullmatch(item) is None for item in relations):
                raise CanvasPaginationError("Malformed Canvas pagination Link relation.")
        if not relations:
            raise CanvasPaginationError("Canvas pagination Link has no relation; collection incomplete.")
        if "next" in relations:
            following.append(target)
    if len(following) > 1:
        raise CanvasPaginationError("Canvas pagination returned more than one next link.")
    return following[0] if following else None
