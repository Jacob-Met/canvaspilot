"""Run the same independent receiver against an explicitly bound source tree."""
from __future__ import annotations

import datetime
import hashlib
import importlib.metadata
import json
import os
import pathlib
import resource
import shutil
import subprocess
import sys
import time

root = pathlib.Path("/tmp/canvaspilot-inbox-independent-713adaab")
stage, source_arg = sys.argv[1:]
assert stage == "composed"
source = pathlib.Path(source_arg).resolve()
assert source.is_dir() and (source / "canvaspilot" / "api.py").is_file()
out = pathlib.Path(os.environ["INBOX_COMPOSED_RESULTS"]).resolve()
assert out == pathlib.Path("/dev/shm/canvaspilot-inbox-composition-713adaab")
assert not out.exists(), "preserve the first replay; use an explicit new receiver revision for repairs"
assert shutil.disk_usage(out.parent).free > 50 * 1024 * 1024
out.mkdir(parents=True, mode=0o700)
budget_probe = out / ".quota-preflight"
try:
    budget_probe.write_bytes(bytes(1024 * 1024))
finally:
    if budget_probe.exists():
        budget_probe.unlink()
driver_text = globals().get("DRIVER_SOURCE") or pathlib.Path(__file__).read_text()
(out / "run_composed_receiving.py").write_text(driver_text)
def pin(path):
    content = path.read_bytes()
    return {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}

def source_pins():
    return {str(path.relative_to(source)): pin(path) for path in sorted(source.rglob("*.py"))}

frozen_commit = "6b94efe9ff1f117fe4c2f1dfca595003a283d988"
source_check = subprocess.run(["git", "-C", str(source.parent), "diff", "--exit-code", frozen_commit, "--", "src"], capture_output=True, check=False)
assert source_check.returncode == 0, "owner runtime differs from frozen commit"
before = source_pins()
receiver_pins = {name: pin(root / name) for name in (
    "test_inbox_receiving.py", "test_fragment_boundary.py", "test_id_admission.py",
    "loopback_guard.py", "base-tool-names.json",
)}
receiver_pins["run_composed_receiving.py"] = pin(out / "run_composed_receiving.py")
env = {key: value for key, value in os.environ.items()
       if not key.startswith("CANVAS_") and not key.lower().endswith("_proxy")}
env.update({
    "INBOX_REVIEW_SOURCE": str(source), "INBOX_REVIEW_RESULT_DIR": str(out / "cases"),
    "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(source), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
})
command = [
    sys.executable, "-B", "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider",
    "-o", "addopts=", "--basetemp", str(out / "tmp"),
    "--junitxml", str(out / "pytest.xml"), str(root / "test_inbox_receiving.py"),
    str(root / "test_fragment_boundary.py"), str(root / "test_id_admission.py"),
]
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
tick = time.monotonic()
process = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=180, check=False)
(out / "stdout.log").write_bytes(process.stdout)
(out / "stderr.log").write_bytes(process.stderr)
after = source_pins()
assert before == after, "candidate source changed during independent receiving"
receipt = {
    "schema": "canvaspilot.inbox.independent_receiving.v1", "stage": stage,
    "reviewer": "chatgpt:/root/mac_execution", "started_utc": started,
    "duration_seconds": round(time.monotonic() - tick, 3), "exit_code": process.returncode,
    "python": sys.version, "executable": sys.executable,
    "dependencies": {name: importlib.metadata.version(name) for name in ("httpx", "mcp", "pytest")},
    "source_root": str(source), "source_git_commit": frozen_commit, "source_before": before, "source_after": after,
    "setup_failure_before_replay": {"location": "/tmp/canvaspilot-inbox-independent-713adaab/composed/src", "error": "OSError 122 during immutable source copy and later /tmp runner write; source preflight and then runner syntax preflight stopped before tests", "tests_executed": False, "partial_file": "canvaspilot/__init__.py, zero bytes", "recovery": "Same-UID private /dev/shm results; frozen owner source bound read-only; no additional source copy."},
    "receiver_sources": receiver_pins, "command": command,
    "evidence": {str(path.relative_to(out)): pin(path) for path in sorted(out.rglob("*")) if path.is_file()},
    "limits": [
        "Authored contract fixtures and real native token/session-envelope, CLI and MCP stdio paths.",
        "No real Canvas, school account, browser, profile, cookies or attachment download.",
        "Only the private loopback provider is admitted by parent and child socket guards.",
        "Session receiving models the broker HTTP envelope; it does not claim Playwright or SSO receiving.",
        "No edits to owner source or borrowed dependency environment; no dependencies installed.",
    ],
}
receipt_path = out / "receipt.json"
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"stage": stage, "exit_code": process.returncode, "source_unchanged": before == after,
                  "receipt": str(receipt_path), "receipt_sha256": pin(receipt_path)["sha256"],
                  "stdout_tail": process.stdout.decode(errors="replace")[-900:],
                  "free_tmp_bytes": shutil.disk_usage(root).free}))
sys.exit(process.returncode)
