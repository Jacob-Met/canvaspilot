"""Compare explicitly saved syllabus-source bytes without Canvas or HTML parsing.

Portable invocation: python syllabus_source_compare.py BEFORE AFTER --out NEW.txt
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import unicodedata

SCHEMA = "canvaspilot.syllabus-source-comparison.v1"
MAX_SOURCE_BYTES = 512 * 1024
MAX_LINES = 4096
MAX_REPORT_BYTES = 32 * 1024 * 1024
CONTEXT_LINES = 3
ENDINGS = ("LF", "CRLF", "CR", "NONE")


def _source(raw: bytes, label: str) -> tuple[list[tuple[str, str]], dict]:
    if type(raw) is not bytes:
        raise TypeError(f"{label}: source must be bytes")
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError(f"{label}: source exceeds 512 KiB")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label}: source is not valid UTF-8") from exc
    lines: list[tuple[str, str]] = []
    start = 0
    for match in re.finditer(r"\r\n|\r|\n", text):
        ending = {"\n": "LF", "\r\n": "CRLF", "\r": "CR"}[match.group()]
        lines.append((text[start:match.start()], ending))
        start = match.end()
        if len(lines) > MAX_LINES:
            raise ValueError(f"{label}: source exceeds 4096 physical lines")
    if start < len(text):
        lines.append((text[start:], "NONE"))
    if len(lines) > MAX_LINES:
        raise ValueError(f"{label}: source exceeds 4096 physical lines")
    counts = dict.fromkeys(ENDINGS, 0)
    for _, ending in lines:
        counts[ending] += 1
    return lines, {
        "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        "lines": len(lines), "leading_bom": raw.startswith(b"\xef\xbb\xbf"),
        "endings": counts,
    }


def compare_sources(before: bytes, after: bytes) -> dict:
    """Return exact line occurrences and grouped changes; never normalize inputs."""
    left, left_info = _source(before, "before")
    right, right_info = _source(after, "after")
    result = {
        "schema": SCHEMA, "status": "identical" if before == after else "different",
        "context_lines": CONTEXT_LINES, "before": left_info, "after": right_info,
        "hunks": [],
    }
    if before == after:
        return result
    matcher = difflib.SequenceMatcher(None, left, right, autojunk=False)
    for group in matcher.get_grouped_opcodes(CONTEXT_LINES):
        operations = []
        for tag, i, j, k, m in group:
            operations.append({
                "tag": tag, "before_start": i, "before_end": j,
                "after_start": k, "after_end": m,
                "before_lines": [{"text": t, "ending": e} for t, e in left[i:j]],
                "after_lines": [{"text": t, "ending": e} for t, e in right[k:m]],
            })
        result["hunks"].append({
            "before_start": group[0][1], "before_end": group[-1][2],
            "after_start": group[0][3], "after_end": group[-1][4],
            "operations": operations,
        })
    return result


def quote_display(value: str) -> str:
    """Reversible JSON quoting with controls and Unicode format marks escaped."""
    quoted = json.dumps(value, ensure_ascii=False)
    return "".join(
        json.dumps(char, ensure_ascii=True)[1:-1]
        if 0x7F <= ord(char) <= 0x9F
        or unicodedata.category(char) in ("Cf", "Cs")
        or char in ("\u2028", "\u2029")
        else char
        for char in quoted
    )


def render_report(result: dict, before_label: str, after_label: str) -> bytes:
    """Render the comparison as bounded, readable UTF-8 plain text."""
    chunks: list[bytes] = []
    total = 0

    def line(text: str = "") -> None:
        nonlocal total
        chunk = (text + "\n").encode("utf-8")
        total += len(chunk)
        if total > MAX_REPORT_BYTES:
            raise ValueError("report exceeds 32 MiB")
        chunks.append(chunk)

    line("CanvasPilot — saved syllabus source comparison")
    line("Source-only review: differences do not establish a changed policy or meaning.")
    line("Selected filenames and hashes do not prove origin, authenticity, capture time,")
    line("same-course identity, or current policy. No HTML is parsed or rendered.")
    line("This is a diff with context, not a complete source archive. Preserve both inputs;")
    line("omitted unchanged lines remain only in those inputs.")
    line()
    for key, label in (("before", before_label), ("after", after_label)):
        info = result[key]
        line(f"{key.capitalize()} source: {quote_display(label)}")
        line(f"  Bytes: {info['bytes']}; SHA-256: {info['sha256']}")
        line(f"  Source lines: {info['lines']}; leading BOM: {str(info['leading_bom']).lower()}")
        line("  Endings: " + ", ".join(f"{name}={info['endings'][name]}" for name in ENDINGS))
    line()
    line("Result: source bytes are identical." if result["status"] == "identical"
         else "Result: source bytes differ.")
    line("Hunk ranges are zero-based, end-exclusive source-line positions.")
    line("B/A labels are one-based original line occurrences; ending=NONE means no terminator.")
    line("Quoted text uses reversible JSON escapes for controls and format characters.")
    line("Line alignment uses three context lines; it is not a unique edit explanation.")
    for number, hunk in enumerate(result["hunks"], 1):
        line()
        line(f"Hunk {number}: before [{hunk['before_start']}, {hunk['before_end']}); "
             f"after [{hunk['after_start']}, {hunk['after_end']})")
        for operation in hunk["operations"]:
            if operation["tag"] == "equal":
                for offset, record in enumerate(operation["before_lines"]):
                    line(f"  B{operation['before_start'] + offset + 1} "
                         f"A{operation['after_start'] + offset + 1} "
                         f"{quote_display(record['text'])} ending={record['ending']}")
                continue
            for key, prefix in (("before", "- B"), ("after", "+ A")):
                for offset, record in enumerate(operation[f"{key}_lines"]):
                    line(f"{prefix}{operation[f'{key}_start'] + offset + 1} "
                         f"{quote_display(record['text'])} ending={record['ending']}")
    return b"".join(chunks)


def _identity(info: os.stat_result) -> tuple:
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns


def read_source(path: str, label: str) -> bytes:
    """Read a bounded regular file and refuse observed changes or selected links."""
    selected = os.lstat(path)
    if not stat.S_ISREG(selected.st_mode):
        raise ValueError(f"{label}: selected input must be a regular file, not a symlink")
    if selected.st_size > MAX_SOURCE_BYTES:
        raise ValueError(f"{label}: source exceeds 512 KiB")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as source:
        opened = os.fstat(source.fileno())
        if not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(selected):
            raise ValueError(f"{label}: selected input changed before reading")
        raw = source.read(MAX_SOURCE_BYTES + 1)
        completed = os.fstat(source.fileno())
    current = os.lstat(path)
    if (_identity(opened) != _identity(completed)
            or _identity(completed) != _identity(current) or len(raw) != completed.st_size):
        raise ValueError(f"{label}: selected input changed while reading")
    return raw


def publish_report(destination: str, data: bytes) -> list[str]:
    """Publish a complete new file exclusively, with no overwrite fallback."""
    if os.path.lexists(destination):
        raise FileExistsError("destination already exists")
    parent = Path(destination).parent
    descriptor, temporary = tempfile.mkstemp(prefix=".cp-sc-", dir=parent)
    published = False
    warnings = []
    try:
        with os.fdopen(descriptor, "wb") as staging:
            staging.write(data)
            staging.flush()
        os.link(temporary, destination)
        published = True
    finally:
        try:
            os.unlink(temporary)
        except OSError as exc:
            if published:
                warnings.append(f"report published; staging cleanup failed: {exc}")
            else:
                raise OSError(f"report not published; staging cleanup failed: {exc}") from exc
    return warnings


def _json_line(stream, value: dict) -> None:
    stream.write(json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n")
    stream.flush()


def _silence_failed_stream(name: str) -> None:
    # Avoid another buffered flush failure during ordinary interpreter shutdown.
    try:
        setattr(sys, name, open(os.devnull, "w", encoding="ascii"))
    except OSError:
        pass


def _failure(kind: str, message: str) -> int:
    try:
        _json_line(sys.stderr, {"ok": False, "error": {"kind": kind, "message": message}})
    except (OSError, UnicodeError):
        _silence_failed_stream("stderr")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", help="explicit saved source-text file")
    parser.add_argument("after", help="explicit saved source-text file")
    parser.add_argument("--out", required=True, help="new UTF-8 plain-text report (never overwritten)")
    args = parser.parse_args(argv)
    sources = []
    for label in ("before", "after"):
        try:
            sources.append(read_source(getattr(args, label), label))
        except (OSError, ValueError) as exc:
            return _failure("input", f"{label}: {exc}")
    try:
        result = compare_sources(*sources)
    except (TypeError, ValueError) as exc:
        return _failure("input", str(exc))
    try:
        report = render_report(result, args.before, args.after)
    except (ValueError, UnicodeError) as exc:
        return _failure("comparison", str(exc))
    try:
        warnings = publish_report(args.out, report)
    except (OSError, ValueError) as exc:
        return _failure("output", str(exc))
    receipt = {
        "ok": True, "schema": SCHEMA, "output": args.out, "status": result["status"],
        "before": {key: result["before"][key] for key in ("bytes", "sha256", "lines")},
        "after": {key: result["after"][key] for key in ("bytes", "sha256", "lines")},
        "hunks": len(result["hunks"]), "report_bytes": len(report), "warnings": warnings,
    }
    try:
        _json_line(sys.stdout, receipt)
    except (OSError, UnicodeError) as exc:
        _silence_failed_stream("stdout")
        return _failure("output", f"report published; receipt undelivered: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
