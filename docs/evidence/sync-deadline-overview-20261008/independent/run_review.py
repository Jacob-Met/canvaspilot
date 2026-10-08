"""Capture a bounded independent fixture run and exact source hashes."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


root = Path(__file__).resolve().parent
source = Path(sys.argv[1]).resolve()
label = sys.argv[2]
tests = sys.argv[3:]
probe = root / "test_independent_sync.py"
runtime = Path("/workspace/scratch/3dab0b9d2ce9/canvaspilot-product/test-env/bin/python")
out = root / "evidence" / label
out.mkdir(parents=True, exist_ok=False)


def pin(path):
    content = path.read_bytes()
    return {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


def source_pins():
    return {str(path.relative_to(source)): pin(path) for path in sorted((source / "src").rglob("*.py"))}


before = source_pins()
cmd = [str(runtime), "-B", str(probe), *tests]
env = {
    "PATH": "/usr/bin:/bin",
    "PYTHONPATH": str(source / "src"),
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "LC_ALL": "C.UTF-8",
}
started = datetime.now(timezone.utc).isoformat()
process = subprocess.run(cmd, cwd=root, env=env, capture_output=True, timeout=40)
ended = datetime.now(timezone.utc).isoformat()
(out / "stdout.log").write_bytes(process.stdout)
(out / "stderr.log").write_bytes(process.stderr)
after = source_pins()
receipt = {
    "label": label,
    "started_utc": started,
    "ended_utc": ended,
    "source_root": str(source),
    "argv": cmd,
    "environment": env,
    "exit_code": process.returncode,
    "probe": pin(probe),
    "driver": pin(Path(__file__)),
    "runtime_executable": str(runtime.resolve()),
    "runtime_sha256": pin(runtime.resolve()),
    "source_before": before,
    "source_after": after,
    "source_unchanged": before == after,
    "stdout": pin(out / "stdout.log"),
    "stderr": pin(out / "stderr.log"),
    "boundary": "Authored CanvasClient fixture data only. Socket connect, broker access, profile/default lookups guarded; no network install or account operations.",
}
(out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"label": label, "exit_code": process.returncode, "source_unchanged": before == after, "stdout": process.stdout.decode(), "stderr": process.stderr.decode()}, indent=2))
sys.exit(0 if before == after else 3)
