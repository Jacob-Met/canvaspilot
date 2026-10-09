"""Read two saved agenda files and print their complete recorded-value comparison."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

if __package__:
    from .agenda_changes import (
        MAX_INPUT_BYTES,
        compare_saved_agendas,
        render_agenda_changes,
    )
else:
    from agenda_changes import (
        MAX_INPUT_BYTES,
        compare_saved_agendas,
        render_agenda_changes,
    )


class Once(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        seen = getattr(namespace, "_seen", set())
        if self.dest in seen:
            parser.error(f"{option_string} may be supplied only once")
        seen.add(self.dest)
        namespace._seen = seen
        setattr(namespace, self.dest, values)


def _read(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("input must be a regular saved file")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            data = source.read(MAX_INPUT_BYTES + 1)
        if len(data) > MAX_INPUT_BYTES:
            raise ValueError("input exceeds the byte limit")
        return data
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path, action=Once)
    parser.add_argument("--after", required=True, type=Path, action=Once)
    parser.add_argument("--format", choices=("text", "json"), default="text", action=Once)
    args = parser.parse_args(argv)
    try:
        result = compare_saved_agendas(_read(args.before), _read(args.after))
        output = render_agenda_changes(result, format=args.format)
        written = sys.stdout.buffer.write(output)
        sys.stdout.buffer.flush()
        if written != len(output):
            raise OSError("output stream accepted fewer bytes than the complete report")
    except (OSError, ValueError, TypeError, RecursionError) as error:
        try:
            sys.stderr.write(json.dumps({"error": str(error)}, ensure_ascii=True) + "\n")
            sys.stderr.flush()
        except OSError:
            pass
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
