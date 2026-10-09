from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess

root = Path("/home/jacob/hamon-ultra-2d2d276b-canvas-file-search")
source = root / "source"
out = root / "qualification-02"
out.mkdir()
python = "/home/jacob/canvaspilot-enrollments-env-65ae877160f6/bin/python"
env = os.environ.copy()
for key in list(env):
    if key.startswith("CANVAS_") or key.upper().endswith("_PROXY"):
        env.pop(key)
env.update({
    "PYTHONPATH": str(source / "src"),
    "PYTHONDONTWRITEBYTECODE": "1",
    "HOME": str(out / "home"),
    "XDG_CONFIG_HOME": str(out / "config"),
    "XDG_CACHE_HOME": str(out / "cache"),
    "NO_PROXY": "127.0.0.1",
})
changed = [
    "src/canvaspilot/file_search.py", "src/canvaspilot/cli.py",
    "tests/test_file_search.py", "tests/test_file_search_cli.py",
    "docs/file-search.md", "README.md",
]
pins = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in changed}
commands = [
    [python, "-B", "-m", "pytest", "-q", "tests/test_file_search.py",
     "tests/test_file_search_cli.py", "tests/test_files_completeness.py",
     "-p", "no:cacheprovider", "--basetemp=" + str(out / "pytest-temp")],
    [python, "-B", "-m", "ruff", "check", "src/canvaspilot/file_search.py",
     "src/canvaspilot/cli.py", "tests/test_file_search.py", "tests/test_file_search_cli.py"],
]
receipt = {
    "state": "running", "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source": str(source), "base": "56a72a2e2cee5ec04671d12ebe5bc2484afb8026",
    "product_pins": pins, "commands": [],
    "boundary": "Private native synthetic HTTP only; no live Canvas/profile/service/Actions/LA7.",
}
path = out / "receipt.json"
path.write_text(json.dumps(receipt, indent=2) + "\n")
for index, command in enumerate(commands):
    item = {"argv": command, "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        result = subprocess.run(command, cwd=source, env=env, capture_output=True, text=True, timeout=120)
        item.update(rc=result.returncode, stdout=result.stdout, stderr=result.stderr)
    except subprocess.TimeoutExpired as error:
        item.update(rc=None, state="bounded_timeout", stdout=str(error.stdout), stderr=str(error.stderr))
    (out / f"command-{index}.stdout").write_text(item["stdout"])
    (out / f"command-{index}.stderr").write_text(item["stderr"])
    item["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt["commands"].append(item)
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"command": index, "rc": item["rc"], "stdout_tail": item["stdout"][-5000:], "stderr_tail": item["stderr"][-1500:]}), flush=True)
receipt["source_pins_unchanged"] = all(hashlib.sha256((source / name).read_bytes()).hexdigest() == sha for name, sha in pins.items())
receipt["state"] = "focused_native_qualification_passed" if all(item["rc"] == 0 for item in receipt["commands"]) and receipt["source_pins_unchanged"] else "qualification_requires_reconciliation"
receipt["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
path.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"state": receipt["state"], "receipt": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}), flush=True)
raise SystemExit(0 if receipt["state"] == "focused_native_qualification_passed" else 1)
