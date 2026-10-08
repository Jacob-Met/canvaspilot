"""Complete fixture qualification, exporting receipts before /dev is reset."""
from __future__ import annotations
import base64
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import zlib

ROOT = Path("/dev/shm/c6cc965b64c2-canvas-discussion/candidate")
OUT = Path("/dev/c6cc965b64c2-canvas-discussion-tmp")
PERSIST = ROOT.parent / "qualification"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "tmp").mkdir(exist_ok=True)
(OUT / "evidence").mkdir(exist_ok=True)

def inventory():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}

before = inventory()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT / "src"),
           TMPDIR=str(OUT / "tmp"), CANVAS_DISCUSSION_TEST_RECEIPTS=str(OUT / "final-native-records"))
runs = []
commands = [
    ("ruff", [sys.executable, "-B", "-m", "ruff", "check", "--no-cache", "src", "tests", "scripts"]),
    ("pytest", [sys.executable, "-B", "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider",
                "--basetemp=" + str(OUT / "pytest-final")]),
]
for name, command in commands:
    started = time.time()
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=240, check=False)
    runs.append({"name": name, "command": command, "started_unix": started,
                 "elapsed_seconds": time.time() - started, "returncode": completed.returncode,
                 "stdout": completed.stdout, "stderr": completed.stderr})
after = inventory()
files = []
for p in sorted((OUT / "final-native-records").glob("*.json")):
    raw = p.read_bytes()
    files.append({"path": "native-records/" + p.name, "encoding": "utf-8",
                  "content": raw.decode(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
packet = {
    "schema": "canvas-discussion-native-gate-v3",
    "base_commit": "79a2f2b2cbb7e74128d731cf096c7e86f1942d4b",
    "python": sys.executable, "python_version": platform.python_version(),
    "dependencies": {name: importlib.metadata.version(name) for name in ("pytest", "ruff", "httpx", "mcp", "pydantic")},
    "cwd": str(ROOT), "temporary_root": str(OUT),
    "tmpfs_lifetime": "The /dev mount is private to this exec invocation. Every evidence byte is exported here before exit.",
    "runs": runs, "source_before": before, "source_after": after, "source_unchanged": before == after, "files": files,
}
raw = (json.dumps(packet, ensure_ascii=False, indent=2) + "\n").encode()
compressed = zlib.compress(raw, 9)
envelope = {"schema": "canvas-discussion-native-gate-v3-envelope", "encoding": "zlib-base64",
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "compressed_bytes": len(compressed), "data": base64.b64encode(compressed).decode(),
            "summary": {"source_unchanged": before == after, "source_file_count": len(before),
                        "native_record_files": len(files), "runs": [
                            {"name": r["name"], "returncode": r["returncode"], "elapsed_seconds": r["elapsed_seconds"],
                             "stdout_tail": r["stdout"][-3500:], "stderr_tail": r["stderr"][-1500:]} for r in runs]}}
persist_error = None
try:
    PERSIST.mkdir(exist_ok=True)
    (PERSIST / "native-gate-v3.json").write_bytes(raw)
    for item in files:
        p = PERSIST / item["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(item["content"], encoding="utf-8")
except OSError as error:
    persist_error = f"{type(error).__name__}: {error}"
envelope["persistent_copy_error"] = persist_error
print(json.dumps(envelope), flush=True)
sys.exit(0 if before == after and all(r["returncode"] == 0 for r in runs) else 1)
