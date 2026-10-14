"""Run only the frozen saved-grade view tests against one explicit source."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def identity(path):
    raw = path.read_bytes()
    stat = path.stat()
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
        "mode": str(stat.st_mode),
        "mtime_ns": str(stat.st_mtime_ns),
        "inode": str(stat.st_ino),
    }


def inventory(source, test, driver):
    rows = {str(p): identity(p) for p in sorted(source.parent.rglob("*")) if p.is_file()}
    rows[str(test)] = identity(test)
    rows[str(driver)] = identity(driver)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    driver = Path(__file__).resolve(strict=True)
    test = driver.with_name("test_grade_review_view.py")
    args.output.mkdir(parents=False, exist_ok=False)
    before = inventory(source, test, driver)
    env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "LANG", "TMPDIR") if k in os.environ}
    env["CANVASPILOT_VIEW_TEST_SOURCE"] = str(source)
    command = [sys.executable, "-B", str(test), "-v"]
    started = datetime.now(UTC).isoformat()
    result = subprocess.run(command, env=env, capture_output=True, timeout=30, check=False)
    (args.output / "stdout.txt").write_bytes(result.stdout)
    (args.output / "stderr.txt").write_bytes(result.stderr)
    after = inventory(source, test, driver)
    receipt = {
        "schema": "hamon.canvas-grade-view.author/1",
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "command": command,
        "returncode": result.returncode,
        "stdout": identity(args.output / "stdout.txt"),
        "stderr": identity(args.output / "stderr.txt"),
        "before": before,
        "after": after,
        "source_and_witnesses_preserved": before == after,
        "scope": "Focused standard-library tests of the public renderer; no Canvas transport, browser, CLI service, grade calculation or prior owner course.",
    }
    (args.output / "receiving.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"returncode": result.returncode, "preserved": before == after, "receipt": identity(args.output / "receiving.json")}))
    return 0 if before == after else 2


if __name__ == "__main__":
    raise SystemExit(main())
