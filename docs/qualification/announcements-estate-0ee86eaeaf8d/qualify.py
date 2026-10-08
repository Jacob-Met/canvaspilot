"""Run the current native source image without modifying a shared runtime."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

WORK = Path(__file__).resolve().parent
CANDIDATE = WORK / "candidate"
PYTHON = "/workspace/scratch/3dab0b9d2ce9/canvaspilot-product/test-env/bin/python"


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def pins():
    return {
        str(path.relative_to(CANDIDATE)): {
            "git_blob": git_blob(path.read_bytes()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(CANDIDATE.rglob("*")) if path.is_file()
    }


before = pins()
receipt = {
    "repository": "Jacob-Met/canvaspilot",
    "base": "72357053a1629c349f700030013559fa6d8130f2",
    "python": PYTHON,
    "source_before": before,
    "commands": [],
}
with tempfile.TemporaryDirectory(prefix="canvas-announcements-", dir="/dev") as temp:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(CANDIDATE / "src"), TMPDIR=temp)
    commands = [
        ("focused", [PYTHON, "-B", "-m", "pytest", "tests/test_announcements_pagination.py", "-p", "no:cacheprovider", "-q"]),
        ("full", [PYTHON, "-B", "-m", "pytest", "-p", "no:cacheprovider", "--basetemp", str(Path(temp) / "pytest"), "-q"]),
        ("ruff", [PYTHON, "-B", "-m", "ruff", "check", "src", "tests", "scripts", "--no-cache"]),
    ]
    for name, command in commands:
        started = time.monotonic()
        result = subprocess.run(command, cwd=CANDIDATE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=240)
        log = WORK / f"{name}.log"
        log.write_text(result.stdout)
        record = {"name": name, "command": command, "cwd": str(CANDIDATE), "exit": result.returncode,
                  "seconds": round(time.monotonic() - started, 3), "log": log.name,
                  "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
                  "tail": result.stdout.splitlines()[-8:]}
        receipt["commands"].append(record)
        print(json.dumps(record), flush=True)
        if result.returncode:
            break
receipt["source_after"] = pins()
receipt["source_unchanged_by_validation"] = before == receipt["source_after"]
(WORK / "qualification.json").write_text(json.dumps(receipt, indent=2) + "\n")
assert receipt["source_unchanged_by_validation"]
raise SystemExit(0 if len(receipt["commands"]) == 3 and all(c["exit"] == 0 for c in receipt["commands"]) else 1)
