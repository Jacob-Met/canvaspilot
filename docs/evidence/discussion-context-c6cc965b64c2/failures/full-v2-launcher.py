from pathlib import Path
import hashlib, json, os, subprocess, sys, time
root = Path("/dev/shm/c6cc965b64c2-canvas-discussion/candidate")
out = Path("/dev/c6cc965b64c2-canvas-discussion-tmp")
out.mkdir(parents=True, exist_ok=True)
(out / "tmp").mkdir(exist_ok=True)
def inventory():
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
before = inventory()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(root / "src"), TMPDIR=str(out / "tmp"), CANVAS_DISCUSSION_TEST_RECEIPTS=str(out / "final-native-records"))
command = [sys.executable, "-B", "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", "--basetemp=" + str(out / "pytest-final")]
started = time.time()
result = subprocess.run(command, cwd=root, env=env, text=True, capture_output=True, timeout=240)
after = inventory()
receipt = {"schema": "canvas-discussion-native-pytest-v2", "python": sys.executable, "command": command, "cwd": str(root), "tmpdir": env["TMPDIR"], "started_unix": started, "elapsed_seconds": time.time() - started, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "source_before": before, "source_after": after, "source_unchanged": before == after}
raw = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode()
destination = out / "evidence/candidate-full-v2-receipt.json"
destination.write_bytes(raw)
(out / "evidence/candidate-full-v2.stdout").write_text(result.stdout)
(out / "evidence/candidate-full-v2.stderr").write_text(result.stderr)
print(json.dumps({"path": str(destination), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "elapsed_seconds": receipt["elapsed_seconds"], "returncode": result.returncode, "source_unchanged": before == after, "source_file_count": len(before), "stdout_tail": result.stdout[-7000:], "stderr_tail": result.stderr[-2000:]}), flush=True)
sys.exit(result.returncode)
