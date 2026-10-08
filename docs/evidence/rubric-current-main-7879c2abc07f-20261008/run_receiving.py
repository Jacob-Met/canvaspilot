"""Execute only the authorized frozen-source receiving gates."""
import argparse, hashlib, json, os, signal, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path("/dev/shm/canvaspilot-rubric-receiving-7879c2abc07f")
PYTHON = "/workspace/scratch/20b27c2ea29e/workers/runtime-integration/product-discovery/canvaspilot/venv/bin/python"
FLOOR = 16 * 1024 * 1024
def now():
    return datetime.now(timezone.utc).isoformat()
def free():
    s = os.statvfs(ROOT)
    return s.f_bavail * s.f_frsize
def sha(data):
    return hashlib.sha256(data).hexdigest()
def sources():
    m = json.loads((ROOT / "evidence/source-input-manifest.json").read_text())
    for row in m["files"]:
        data = (ROOT / row["path"]).read_bytes()
        if len(data) != row["bytes"] or sha(data) != row["sha256"]:
            raise RuntimeError("Frozen source mismatch: " + row["path"])
    return {"files_verified": len(m["files"]), "source_only_tree": m["source_only_tree"]}
def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("baseline", "candidate", "independent-normal", "independent-optimized", "lint"))
    stage = p.parse_args().stage
    evidence = ROOT / "evidence"
    destination = evidence / (stage + "-run.json")
    if destination.exists() or (evidence / (stage + "-run.log")).exists():
        raise RuntimeError("Preserve existing receiving attempt: " + stage)
    source = ROOT / ("baseline" if stage == "baseline" else "candidate")
    stage_tmp = ROOT / "tmp" / stage
    started = now()
    receipt = {"schema": "canvas.current.rubric.runtime.v1", "stage": stage, "started_utc": started,
               "source_root": str(source), "free_start_bytes": free(), "floor_bytes": FLOOR,
               "source_before": sources(), "production_changes": False}
    fixed = {
        "guard/sitecustomize.py": "5ebd74bc5ec19db0e1560311d402931dd252f4785f34d2a6daae83727096edd4",
        "harness/test_independent_rubric_brief.py": "0d4f352f81c0c2a39415df9effdf4ffc0318e7f6dd21a6876e459233f28d8a0b",
        "harness/assignment-fixture.json": "b0185efda8933d88cd209d7162e39bcc5f825421d25f0c790126dac37c11ab08",
    }
    for path, expected in fixed.items():
        if sha((ROOT / path).read_bytes()) != expected:
            raise RuntimeError("Receiving input mismatch: " + path)
    receipt["receiver_input_sha256"] = fixed
    if receipt["free_start_bytes"] < FLOOR:
        receipt.update(status="storage_preflight_stop", exit_code=75, completed_utc=now(), source_after=sources())
        destination.write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt), flush=True)
        return 75
    stage_tmp.mkdir(exist_ok=False)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("CANVAS_") and k.lower() not in ("http_proxy", "https_proxy", "all_proxy", "no_proxy")
           and k not in ("PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME", "PYTHONPYCACHEPREFIX")}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               PYTHONPATH=str(ROOT / "guard") + os.pathsep + str(source / "src"),
               RECEIVING_SOURCE_ROOT=str(source), CANVAS_PROFILE=str(stage_tmp / "unused-profile"),
               TMPDIR=str(stage_tmp), TMP=str(stage_tmp), TEMP=str(stage_tmp),
               NO_PROXY="127.0.0.1,localhost,::1")
    cmd = [PYTHON, "-B"]
    xml_path = evidence / (stage + ".xml")
    if stage in ("baseline", "candidate"):
        cmd += ["-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", str(stage_tmp / "pytest"),
                "--junitxml", str(xml_path)]
    elif stage.startswith("independent"):
        if stage.endswith("optimized"):
            cmd += ["-O"]
        cmd += [str(ROOT / "harness/test_independent_rubric_brief.py"), "--source", str(source),
                "--output", str(evidence / stage)]
    else:
        cmd += ["-m", "ruff", "check", "--no-cache", "src", "tests", "scripts"]
    receipt["command"] = cmd
    receipt["working_directory"] = str(source)
    min_free = receipt["free_start_bytes"]
    stopped = None
    log_path = evidence / (stage + "-run.log")
    with log_path.open("x") as log:
        proc = subprocess.Popen(cmd, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        receipt["pid"] = proc.pid
        print(json.dumps({"event": "started", "stage": stage, "pid": proc.pid, "source": str(source),
                          "free_bytes": min_free, "time_utc": now()}), flush=True)
        deadline = time.monotonic() + 240
        while proc.poll() is None:
            available = free()
            min_free = min(min_free, available)
            if available < FLOOR or time.monotonic() > deadline:
                stopped = "storage_floor" if available < FLOOR else "timeout"
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                break
            time.sleep(0.2)
        actual_exit = proc.wait()
    receipt.update(actual_subprocess_exit_code=actual_exit, stop_reason=stopped,
                   minimum_free_bytes=min_free, free_end_bytes=free(), completed_utc=now(),
                   source_after=sources(), log_sha256=sha(log_path.read_bytes()), log_bytes=log_path.stat().st_size)
    accepted = actual_exit == 0 and stopped is None
    if stage in ("baseline", "candidate") and xml_path.exists():
        suites = ET.parse(xml_path).getroot()
        cases = list(suites.iter("testcase"))
        ids = sorted(t.get("classname", "") + "::" + t.get("name", "") for t in cases)
        counts = {name: len(list(suites.iter(name))) for name in ("failure", "error", "skipped")}
        expected = 257 if stage == "baseline" else 323
        receipt["pytest"] = {"tests": len(cases), "expected_tests": expected, **counts,
                             "test_ids": ids, "xml_sha256": sha(xml_path.read_bytes())}
        accepted = accepted and len(cases) == expected and not any(counts.values())
        if stage == "candidate":
            baseline = json.loads((evidence / "baseline-run.json").read_text())["pytest"]["test_ids"]
            receipt["pytest"]["baseline_ids_preserved"] = set(baseline).issubset(ids)
            receipt["pytest"]["additional_ids"] = sorted(set(ids) - set(baseline))
            accepted = accepted and set(baseline).issubset(ids) and len(set(ids) - set(baseline)) == 66
    elif stage.startswith("independent") and (evidence / stage / "receipt.json").exists():
        independent = json.loads((evidence / stage / "receipt.json").read_text())
        receipt["independent"] = {k: independent[k] for k in ("methods", "passed_methods", "failed_methods",
            "failure_entries", "error_entries", "skips", "public_invocations_captured", "source_unchanged", "successful")}
        outputs = evidence / stage / "public-outputs.json"
        receipt["public_outputs_sha256"] = sha(outputs.read_bytes())
        accepted = accepted and independent["successful"] and independent["methods"] == 20 and independent["passed_methods"] == 20 and independent["public_invocations_captured"] == 111 and independent["source_unchanged"]
        if stage.endswith("optimized"):
            normal = evidence / "independent-normal/public-outputs.json"
            receipt["same_public_output_as_normal"] = outputs.read_bytes() == normal.read_bytes()
            accepted = accepted and receipt["same_public_output_as_normal"]
    receipt["status"] = "accepted" if accepted else ("storage_stop" if stopped == "storage_floor" else "not_accepted")
    receipt["exit_code"] = 0 if accepted else (75 if stopped == "storage_floor" else 1)
    destination.write_text(json.dumps(receipt, indent=2) + "\n")
    compact = {k: receipt[k] for k in ("stage", "status", "actual_subprocess_exit_code", "stop_reason",
        "minimum_free_bytes", "free_end_bytes", "completed_utc", "log_sha256")}
    if "pytest" in receipt:
        compact["pytest"] = {k:v for k,v in receipt["pytest"].items() if k not in ("test_ids", "additional_ids")}
    if "independent" in receipt:
        compact["independent"] = receipt["independent"]
    print(json.dumps(compact), flush=True)
    print(log_path.read_text()[-5000:], flush=True)
    return receipt["exit_code"]
if __name__ == "__main__":
    raise SystemExit(main())
