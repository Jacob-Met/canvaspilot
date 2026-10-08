from pathlib import Path
import argparse, copy, hashlib, http.server, json, os, subprocess, sys, threading, time, traceback
from urllib.parse import parse_qs, urlsplit
from independent_fixture_v1 import COURSE, MODULES, CHOICE_ITEMS, EXPECTED

class WireFixture:
    def __init__(self):
        self.records = []
        self.phase = "complete"
        self.race_target = None
        owner = self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                split = urlsplit(self.path)
                row = {"method": "GET", "path": split.path, "query": parse_qs(split.query),
                       "synthetic_token_matches": self.headers.get("Authorization") == "Bearer independent-local-fixture",
                       "phase": owner.phase}
                owner.records.append(row)
                status = 200
                headers = {}
                if split.path == "/api/v1/courses/731/modules":
                    if parse_qs(split.query).get("page") == ["2"]:
                        if owner.phase == "later-read-failure":
                            status, payload = 503, {"error": "independent later page unavailable"}
                        else:
                            payload = copy.deepcopy(MODULES[2:])
                    else:
                        payload = copy.deepcopy(MODULES[:2])
                        headers["Link"] = '<' + owner.origin + '/api/v1/courses/731/modules?page=2&witness=opaque-continuation>; rel="next"'
                elif split.path == "/api/v1/courses/731/modules/9101/items":
                    payload = copy.deepcopy(CHOICE_ITEMS)
                    if owner.race_target is not None:
                        Path(owner.race_target).write_bytes(b"independent destination appeared during the read\n")
                else:
                    status, payload = 404, {"error": "unregistered independent fixture route"}
                row["status"] = status
                body = json.dumps(payload, ensure_ascii=False).encode()
                row["response_bytes"] = len(body)
                row["response_sha256"] = hashlib.sha256(body).hexdigest()
                row["response_json"] = payload
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)
            def do_POST(self):
                owner.records.append({"method": "POST", "path": self.path})
                self.send_error(405)
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.origin = "http://127.0.0.1:" + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    def __enter__(self):
        self.thread.start()
        return self
    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

def environment(source):
    value = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "TMPDIR") if key in os.environ}
    value.update(PYTHONPATH=str(source / "src"), PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    return value

def command(source, out, server, label, command_args):
    before = len(server.records)
    cmd = [sys.executable, "-s", "-m", "canvaspilot.cli", *command_args,
           "--base-url", server.origin, "--token", "independent-local-fixture",
           "--profile", str(out / "unused-auth-profile")]
    started = time.monotonic()
    result = subprocess.run(cmd, env=environment(source), capture_output=True, timeout=30)
    (out / (label + ".stdout")).write_bytes(result.stdout)
    (out / (label + ".stderr")).write_bytes(result.stderr)
    record = {"label": label, "command": cmd, "exit": result.returncode, "seconds": time.monotonic() - started,
              "stdout_bytes": len(result.stdout), "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
              "stderr_bytes": len(result.stderr), "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
              "wire": copy.deepcopy(server.records[before:])}
    (out / (label + ".json")).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    return result, record

def assert_complete_wire(record):
    assert [(r["method"], r["path"]) for r in record["wire"]] == [
        ("GET", "/api/v1/courses/731/modules"), ("GET", "/api/v1/courses/731/modules"),
        ("GET", "/api/v1/courses/731/modules/9101/items")]
    assert all(r["synthetic_token_matches"] and r["status"] == 200 for r in record["wire"])
    assert record["wire"][0]["query"] == {"include[]": ["items"], "per_page": ["50"]}
    assert record["wire"][1]["query"] == {"page": ["2"], "witness": ["opaque-continuation"]}
    assert record["wire"][2]["query"] == {"per_page": ["50"]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    report = {"purpose": "Freeze one real baseline normalized observation for later independent export receiving",
              "source": str(args.source), "groups": [], "candidate_executed": False}
    try:
        with WireFixture() as server:
            process, receipt = command(args.source, args.out, server, "baseline-module-progress", ["module-progress", "00731"])
            assert process.returncode == 0, process.stderr.decode()
            observation = json.loads(process.stdout)
            assert observation == EXPECTED, {"expected": EXPECTED, "actual": observation}
            assert_complete_wire(receipt)
            (args.out / "NORMALIZED_OBSERVATION.json").write_text(json.dumps(observation, ensure_ascii=False, indent=2) + "\n")
            (args.out / "RAW_FIXTURE.json").write_text(json.dumps({"modules": MODULES, "fallback_items": CHOICE_ITEMS}, ensure_ascii=False, indent=2) + "\n")
            report["groups"].append({"name": "Actual original CLI/client observation matches independent fixed semantics and complete wire path", "pass": True})
    except Exception as error:
        report["groups"].append({"name": "Baseline observation", "pass": False, "error": str(error), "traceback": traceback.format_exc()})
    report["pass"] = all(group["pass"] for group in report["groups"])
    (args.out / "RECEIPT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"pass": report["pass"], "groups": len(report["groups"]), "out": str(args.out)}, indent=2))
    raise SystemExit(0 if report["pass"] else 1)

if __name__ == "__main__":
    main()
