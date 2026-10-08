"""Build, install and exercise the exact native CanvasPilot wheel in a private environment."""
from pathlib import Path
import datetime
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"
OUT = Path(__file__).resolve().parent
PYTHON = ROOT / "venv/bin/python"
PROVIDER = Path("/Users/me/hamon-work-ledgerly-566d51f04b31-venv/bin/python")
ENV = {
    key: value for key, value in os.environ.items()
    if not key.startswith(("CANVAS_", "CANVASPILOT_", "PYTEST_", "PIP_"))
    and key not in ("PYTHONPATH", "VIRTUAL_ENV")
}
ENV.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", TMPDIR=str(ROOT / "temp"),
           PIP_CONFIG_FILE=os.devnull, PIP_NO_CACHE_DIR="1", PIP_DISABLE_PIP_VERSION_CHECK="1",
           NO_PROXY="127.0.0.1,localhost")
RECORD = {"utc": datetime.datetime.now(datetime.UTC).isoformat(), "runs": [],
          "environment_is_private": True, "live_installation": False,
          "receiving_base": "0480cbce421bae532e3e909899fc8fb83789e878",
          "prior_full_source_commit": "dbcad81ad35b685299a9f2981fbd509ab8d56f31"}


def save():
    (OUT / "qualification.json").write_text(json.dumps(RECORD, indent=2) + "\n")


def run(name, command, cwd=SOURCE, timeout=300):
    with (OUT / f"{name}.stdout").open("w") as stdout, (OUT / f"{name}.stderr").open("w") as stderr:
        try:
            result = subprocess.run(command, cwd=cwd, env=ENV, stdout=stdout, stderr=stderr, timeout=timeout)
            entry = {"name": name, "command": list(map(str, command)), "exit_code": result.returncode}
        except subprocess.TimeoutExpired:
            entry = {"name": name, "command": list(map(str, command)), "timeout_seconds": timeout}
    RECORD["runs"].append(entry)
    save()
    print(json.dumps(entry), flush=True)
    print((OUT / f"{name}.stdout").read_text()[-3500:], flush=True)
    print((OUT / f"{name}.stderr").read_text()[-1800:], flush=True)
    return entry.get("exit_code") == 0


paths = ["README.md", "docs/page-export.md", "src/canvaspilot/cli.py", "src/canvaspilot/page_export.py",
         "tests/fixtures/page_packet.json", "tests/test_page_export.py", "tests/test_page_export_process.py"]
RECORD["source_sha256"] = {path: hashlib.sha256((SOURCE / path).read_bytes()).hexdigest() for path in paths}
RECORD["source_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SOURCE, text=True).strip()
RECORD["source_tree"] = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=SOURCE, text=True).strip()
save()
wheels = OUT / "wheels"
wheels.mkdir()
if not run("wheel-build", [str(PROVIDER), "-B", "-m", "pip", "--python", str(PYTHON), "wheel",
                           "--no-deps", "--no-build-isolation", "--no-cache-dir", "--wheel-dir", str(wheels),
                           str(SOURCE)]):
    raise SystemExit(1)
wheel_files = list(wheels.glob("*.whl"))
assert len(wheel_files) == 1
wheel = wheel_files[0]
RECORD["wheel"] = {"path": str(wheel), "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                   "bytes": wheel.stat().st_size}
expected_source = {str(p.relative_to(SOURCE / "src")): p.read_bytes()
                   for p in (SOURCE / "src/canvaspilot").rglob("*") if p.is_file()}
with zipfile.ZipFile(wheel) as archive:
    actual_names = {name for name in archive.namelist() if name.startswith("canvaspilot/") and not name.endswith("/")}
    assert actual_names == set(expected_source)
    for name, content in expected_source.items():
        assert archive.read(name) == content
RECORD["all_wheel_package_leaves_match_source"] = len(expected_source)
save()
if not run("wheel-install", [str(PROVIDER), "-B", "-m", "pip", "--python", str(PYTHON), "install",
                             "--force-reinstall", "--no-deps", "--no-compile", "--no-cache-dir", str(wheel)]):
    raise SystemExit(1)
probe = """import canvaspilot,canvaspilot.cli,canvaspilot.page_export,json,sys,importlib.metadata
from pathlib import Path
import hashlib
root=Path(canvaspilot.__file__).parent
print(json.dumps({"python":sys.version,"prefix":sys.prefix,"package_path":str(root),
"cli_path":canvaspilot.cli.__file__,"page_export_path":canvaspilot.page_export.__file__,
"versions":{p:importlib.metadata.version(p) for p in ["canvaspilot","httpx","mcp","pydantic","hatchling","pytest","ruff"]},
"package_sha256":{str(p.relative_to(root.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}},indent=2))
"""
if not run("installed-origin", [str(PYTHON), "-B", "-c", probe], cwd=ROOT / "temp"):
    raise SystemExit(1)
origin = json.loads((OUT / "installed-origin.stdout").read_text())
assert Path(origin["package_path"]).is_relative_to(ROOT / "venv")
assert origin["package_sha256"] == {name: hashlib.sha256(content).hexdigest() for name, content in expected_source.items()}
RECORD["installed_origin"] = origin
RECORD["all_installed_package_leaves_match_wheel_and_source"] = len(expected_source)
save()
print("INSTALLED_SOURCE_READY", flush=True)

# The entire current suite is run against the installed wheel; PYTHONPATH is
# removed, the source layout has no top-level canvaspilot package, and origin
# verification above happens outside the checkout.
suite_ok = run("full-suite", [str(PYTHON), "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                              "--junitxml", str(OUT / "full-suite.xml")])
lint_ok = run("ruff", [str(PYTHON), "-B", "-m", "ruff", "check", "--no-cache", "src", "tests", "scripts"])
assert RECORD["source_sha256"] == {path: hashlib.sha256((SOURCE / path).read_bytes()).hexdigest() for path in paths}
RECORD["full_suite_and_lint_passed"] = suite_ok and lint_ok
RECORD["source_unchanged_during_qualification"] = True
save()
print(json.dumps({"qualified": suite_ok and lint_ok, "receipt_sha256": hashlib.sha256((OUT / "qualification.json").read_bytes()).hexdigest()}), flush=True)
raise SystemExit(0 if suite_ok and lint_ok else 1)
