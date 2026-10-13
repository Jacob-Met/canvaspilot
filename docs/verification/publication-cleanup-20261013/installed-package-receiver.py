"""Receive an installed CanvasPilot wheel with real dependencies and fictional local output."""
from __future__ import annotations
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import socket
import subprocess
import sys
import zipfile

work = Path(sys.argv[1]).resolve()
manifest_path = Path(sys.argv[2]).resolve()
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
source = work / "source"
environment = work / "venv"
python = environment / "bin/python"
evidence = work / "evidence"
run_dir = work / "consumer"
run_dir.mkdir(exist_ok=True)
evidence.mkdir(exist_ok=True)
temp_dir = work / "temp"
temp_dir.mkdir(exist_ok=True)
env = {"PATH": str(environment / "bin") + ":/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
       "TMPDIR": str(temp_dir), "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_CONFIG_FILE": os.devnull}
receipt = {
    "scope": "Normal isolated wheel installation and maintained writer tests with real dependencies",
    "source_commit": manifest["commit"], "source_tree": manifest["tree"],
    "device_id": "d55b2499-5e82-4805-819a-d0d7ddea1efe",
    "host": socket.gethostname(), "uid": os.getuid(), "platform": platform.platform(),
    "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "work": str(work), "source": str(source), "environment": str(environment),
    "dependency_environment_origin": manifest["dependency_environment_origin"],
    "commands": [], "checks": [], "limitations": [
        "Runtime dependencies and hatchling were freshly resolved from PyPI as recorded wheels; optional browser/dev extras were not installed.",
        "No live Canvas, credentials, browser, session broker, or MCP transport was used.",
        "No replay of the earlier 554 or 284 assertion courses or historical issue 111 consumer.",
        "Qualified on this macOS arm64 environment and exact recorded dependency versions only."
    ],
}
def digest(data):
    return hashlib.sha256(data).hexdigest()
def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
def check(name, condition, details=None):
    receipt["checks"].append({"name": name, "passed": bool(condition), "details": details})
    if not condition:
        raise AssertionError(name)
def command(name, argv, cwd=run_dir):
    completed = subprocess.run([str(item) for item in argv], cwd=cwd, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    for label, data in (("stdout", completed.stdout), ("stderr", completed.stderr)):
        (evidence / f"{name}.{label}").write_bytes(data)
    record = {"name": name, "argv": [str(item) for item in argv], "cwd": str(cwd),
              "returncode": completed.returncode,
              "stdout": completed.stdout.decode("utf-8", "replace"),
              "stderr": completed.stderr.decode("utf-8", "replace"),
              "stdout_sha256": digest(completed.stdout), "stderr_sha256": digest(completed.stderr)}
    receipt["commands"].append(record)
    return completed

try:
    check("review directory belongs to current user", work.stat().st_uid == os.getuid() == 1000)
    actual_source = {}
    for item in manifest["files"]:
        raw = (source / item["path"]).read_bytes()
        check("source blob " + item["path"], git_blob(raw) == item["sha"])
        actual_source[item["path"]] = {"bytes": len(raw), "git_blob": git_blob(raw), "sha256": digest(raw)}
    receipt["source_files"] = actual_source
    build = command("build-wheel", [python, "-I", "-B", "-m", "hatchling", "build", "-t", "wheel",
                                   "-d", evidence / "wheels"], source)
    check("wheel build exits successfully", build.returncode == 0)
    wheels = list((evidence / "wheels").glob("*.whl"))
    check("one wheel produced", len(wheels) == 1)
    wheel = wheels[0]
    receipt["wheel"] = {"name": wheel.name, "bytes": wheel.stat().st_size, "sha256": digest(wheel.read_bytes())}
    package_files = {p: row for p, row in actual_source.items() if p.startswith("src/canvaspilot/")}
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        expected = {p.removeprefix("src/") for p in package_files}
        check("wheel includes every pinned package source and asset", expected.issubset(names))
        for path, expected_row in package_files.items():
            check("wheel bytes " + path, digest(archive.read(path.removeprefix("src/"))) == expected_row["sha256"])
    install = command("install-wheel", [python, "-I", "-B", "-m", "pip", "install", "--no-cache-dir",
                                       "--disable-pip-version-check", "--no-index", "--no-deps",
                                       "--force-reinstall", "--report", evidence / "wheel-install.json", wheel])
    check("offline isolated wheel install exits successfully", install.returncode == 0)
    inspection_code = r'''
import importlib, importlib.metadata as metadata, json, pathlib, site, sys
from packaging.requirements import Requirement
from packaging.markers import default_environment
wanted = ("canvaspilot", "canvaspilot.client", "canvaspilot.api", "canvaspilot.cli",
          "canvaspilot.calendar_export", "canvaspilot.grade_review_export", "canvaspilot.module_progress_export",
          "httpx", "mcp", "pydantic")
loaded = {name: str(pathlib.Path(importlib.import_module(name).__file__).resolve()) for name in wanted}
dists = list(metadata.distributions())
versions = {d.metadata["Name"]: d.version for d in dists}
problems = []
marker_env = default_environment()
marker_env["extra"] = ""
for dist in dists:
    for text in dist.requires or []:
        req = Requirement(text)
        if req.marker is not None and not req.marker.evaluate(marker_env):
            continue
        try:
            actual = metadata.version(req.name)
        except metadata.PackageNotFoundError:
            problems.append({"distribution": dist.metadata["Name"], "requires": text, "missing": req.name})
            continue
        if actual not in req.specifier:
            problems.append({"distribution": dist.metadata["Name"], "requires": text, "actual": actual})
canvas = metadata.distribution("canvaspilot")
print(json.dumps({
    "python": sys.version, "executable": sys.executable, "prefix": sys.prefix, "base_prefix": sys.base_prefix,
    "sys_path": sys.path, "site_packages": site.getsitepackages(), "modules": loaded, "versions": versions,
    "dependency_problems": problems, "canvaspilot_requires": canvas.requires,
    "canvaspilot_entrypoints": [{"name": e.name, "value": e.value, "group": e.group} for e in canvas.entry_points],
    "direct_url": canvas.read_text("direct_url.json"),
}, indent=2, sort_keys=True))
'''
    inspected = command("installed-imports", [python, "-I", "-B", "-c", inspection_code])
    check("normal installed package and dependency imports succeed", inspected.returncode == 0)
    inspection = json.loads(inspected.stdout)
    receipt["installed_environment"] = inspection
    check("interpreter prefix is isolated review environment", Path(inspection["prefix"]).resolve() == environment)
    check("installed dependency requirements are consistent", not inspection["dependency_problems"], inspection["dependency_problems"])
    check("module imports use private site-packages",
          all(Path(p).is_relative_to(environment) for p in inspection["modules"].values()))
    check("source checkout is absent from normal interpreter path",
          all(not Path(p).is_relative_to(source) for p in inspection["sys_path"] if p))
    installed_root = Path(inspection["modules"]["canvaspilot"]).parent
    for path, row in package_files.items():
        installed = installed_root / path.removeprefix("src/canvaspilot/")
        check("installed bytes " + path, digest(installed.read_bytes()) == row["sha256"])
    entry = environment / "bin/canvaspilot"
    check("installed console entrypoint uses private interpreter",
          entry.read_text(encoding="utf-8").splitlines()[0] == "#!" + str(python))
    console_help = command("console-help", [entry, "--help"])
    module_help = command("module-help", [python, "-I", "-B", "-m", "canvaspilot.cli", "--help"])
    for label, result in (("console", console_help), ("module", module_help)):
        check(label + " help exits successfully", result.returncode == 0 and not result.stderr)
        check(label + " exposes all three export consumers",
              all(name in result.stdout for name in (b"export-calendar", b"export-grade-review", b"export-module-progress")))
    check("console and module help agree", console_help.stdout == module_help.stdout)
    demo_path = run_dir / "synthetic-review.json"
    demo = command("offline-demo", [python, "-I", "-B", "-m", "canvaspilot.offline_demo", "--out", demo_path])
    check("built-in offline demonstration writes local JSON successfully", demo.returncode == 0 and not demo.stderr)
    demo_raw = demo_path.read_bytes()
    demo_payload = json.loads(demo_raw)
    check("demonstration remains explicitly synthetic and account-free",
          demo_payload["mode"] == "synthetic_offline_example" and
          demo_payload["network_required"] is False and demo_payload["account_required"] is False)
    check("demonstration receives its two fictional assignment briefs", len(demo_payload["assignment_briefs"]) == 2)
    receipt["offline_demo"] = {"path": str(demo_path), "bytes": len(demo_raw), "sha256": digest(demo_raw),
                               "mode": demo_payload["mode"], "course_count": len(demo_payload["courses"]),
                               "assignment_briefs": len(demo_payload["assignment_briefs"])}
    again = command("offline-demo-existing-path", [python, "-I", "-B", "-m", "canvaspilot.offline_demo", "--out", demo_path])
    check("demonstration preserves existing output", again.returncode == 2 and demo_path.read_bytes() == demo_raw)
    tests = command("maintained-writer-tests", [python, "-I", "-B", "-m", "unittest", "discover",
                    "-s", source / "tests", "-p", "test_calendar_publication_cleanup.py", "-v"])
    log = (tests.stdout + tests.stderr).decode("utf-8")
    check("seven maintained writer tests pass with real package imports",
          tests.returncode == 0 and "Ran 7 tests" in log and re.search(r"\nOK\s*$", log) is not None)
    receipt["maintained_tests"] = {"run": 7, "failures": 0, "errors": 0,
                                  "test_git_blob": actual_source["tests/test_calendar_publication_cleanup.py"]["git_blob"],
                                  "import_stubs": False}
    for path, row in actual_source.items():
        check("pinned source unchanged after build and tests " + path, digest((source / path).read_bytes()) == row["sha256"])
    check("installed writer unchanged after tests",
          digest((installed_root / "calendar_export.py").read_bytes()) == actual_source["src/canvaspilot/calendar_export.py"]["sha256"])
    receipt["environment_preparation_sha256"] = digest((evidence / "environment-preparation.json").read_bytes())
    receipt["dependency_install_report_sha256"] = digest((evidence / "dependency-install.json").read_bytes())
    receipt["installation_target"] = str(environment)
    receipt["existing_environment_used"] = False
    receipt["status"] = "passed"
except BaseException as error:
    receipt["status"] = "failed"
    receipt["failure"] = {"type": type(error).__name__, "message": str(error)}
    raise
finally:
    receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    output = evidence / "installed-package-receipt.json"
    output.write_bytes(data)
    print(json.dumps({"status": receipt.get("status"), "receipt": str(output), "receipt_sha256": digest(data),
                      "checks": len(receipt["checks"]), "failed_checks": [x["name"] for x in receipt["checks"] if not x["passed"]]}))
