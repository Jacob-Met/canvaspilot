"""Capture an offline HTML packet through the actual privately installed console entry point."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, urlsplit, parse_qs
import datetime
import hashlib
import json
import os
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/quiz-receiving/offline-capture"
OUT.mkdir()
fixture_path = ROOT / "source/tests/fixtures/page_packet.json"
fixture_bytes = fixture_path.read_bytes()
fixture = json.loads(fixture_bytes)
(OUT / "authored-fixture.json").write_bytes(fixture_bytes)
routes = {"/api/v1/courses/42": fixture["course"]}
routes.update({f"/api/v1/courses/42/pages/{quote(locator, safe='')}": page
               for locator, page in fixture["pages"].items()})
requests = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path)
        requests.append({"method": self.command, "path": path.path, "query": parse_qs(path.query),
                         "authored_token": self.headers.get("Authorization") == "Bearer authored-page-packet-token"})
        row = routes.get(path.path)
        payload = json.dumps(row if row is not None else {"error": "unrequested fixture route"},
                             ensure_ascii=False).encode()
        self.send_response(200 if row is not None else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base_url = f"http://127.0.0.1:{server.server_port}"
output = OUT / "reading.html"
selection = ["intro", "7", "page_id:7"]
command = [str(ROOT / "venv/bin/canvaspilot"), "export-pages", "42", *selection,
           "--base-url", base_url, "--token", "authored-page-packet-token",
           "--profile", str(OUT / "unused-authored-profile"), "--out", str(output)]
env = {key: value for key, value in os.environ.items()
       if not key.startswith(("CANVAS_", "CANVASPILOT_", "PYTEST_"))
       and key not in ("PYTHONPATH", "VIRTUAL_ENV") and not key.lower().endswith("_proxy")}
env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
           TMPDIR=str(ROOT / "temp"), NO_PROXY="127.0.0.1,localhost")
record = {"utc": datetime.datetime.now(datetime.UTC).isoformat(), "command": command,
          "selection": selection, "base_url": base_url, "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
          "network_scope": "Authored GET-only loopback HTTP server; no Canvas account or broker",
          "output": str(output)}
try:
    process = subprocess.run(command, cwd=ROOT / "temp", env=env, text=True, capture_output=True, timeout=60)
    print(json.dumps({"console_exit_before_receipt": process.returncode, "stdout_tail": process.stdout[-2500:], "stderr_tail": process.stderr[-1000:]}), flush=True)
    (OUT / "console.stdout").write_text(process.stdout)
    (OUT / "console.stderr").write_text(process.stderr)
    record["exit_code"] = process.returncode
    record["requests"] = requests
    assert process.returncode == 0, process.stderr
    report = json.loads(process.stdout)
    record["console_report"] = report
    content = output.read_bytes()
    assert report["ok"] is True and report["output"] == str(output)
    assert [row["requested"] for row in report["pages"]] == selection
    assert [row["page_id"] for row in report["pages"]] == [9007199254740993, 8, 7]
    assert report["sha256"] == hashlib.sha256(content).hexdigest()
    assert report["bytes"] == len(content)
    assert [row["path"] for row in requests] == ["/api/v1/courses/42", *[
        f"/api/v1/courses/42/pages/{quote(locator, safe='')}" for locator in selection]]
    assert all(row["method"] == "GET" and row["authored_token"] for row in requests)
    assert fixture_path.read_bytes() == fixture_bytes
    assert not (OUT / "unused-authored-profile").exists()
    assert not list(OUT.glob(".canvaspilot-pages-*.tmp"))
    record["passed"] = True
    record["output_sha256"] = hashlib.sha256(content).hexdigest()
    record["output_bytes"] = len(content)
except BaseException as error:
    record["passed"] = False
    record["error"] = f"{type(error).__name__}: {error}"
    raise
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
    record["fixture_unchanged"] = fixture_path.read_bytes() == fixture_bytes
    record["server_closed"] = not thread.is_alive()
    (OUT / "capture.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"passed": record["passed"], "output_sha256": record["output_sha256"],
                  "output_bytes": record["output_bytes"],
                  "capture_sha256": hashlib.sha256((OUT / "capture.json").read_bytes()).hexdigest()}))

old_dir=ROOT/"evidence/offline-browser"
old_record=json.loads((old_dir/"capture.json").read_text())
old_content=(old_dir/"reading.html").read_bytes()
new_content=output.read_bytes()
assert hashlib.sha256(old_content).hexdigest()=="c9511af4f33ab4931a5b828131a82e625610ac4b5fd5eafbb8f30d8cb8c68aba"
normalizations=[
 (record["base_url"],old_record["base_url"],"configured authored loopback fixture origin"),
 (record["console_report"]["generated_at"],old_record["console_report"]["generated_at"],"generated timestamp")
]
normalized=new_content
counts=[]
for fresh,old,label in normalizations:
 assert fresh not in fixture_bytes.decode()
 count=normalized.count(fresh.encode())
 assert count>0
 counts.append({"field":label,"new":fresh,"old":old,"occurrences":count})
 normalized=normalized.replace(fresh.encode(),old.encode())
equal=normalized==old_content
receipt={"utc":datetime.datetime.now(datetime.UTC).isoformat(),
 "source_commit":"0ef6b368ba9a21bfb93e8a513ad12a19e232219a",
 "installed_wheel_sha256":"d5fc2e444fc867a688f2c71173ef06c04251accc497498d5bbe439329be187ee",
 "page_module_sha256":"8800e959ee620438273c3291fd24c51b9ed567430b28093cd3f8bef52bff5015",
 "old_browser_receipt_sha256":hashlib.sha256((old_dir/"browser-first/browser.json").read_bytes()).hexdigest(),
 "new_capture_sha256":hashlib.sha256((OUT/"capture.json").read_bytes()).hexdigest(),
 "new_packet_sha256":hashlib.sha256(new_content).hexdigest(),
 "old_packet_sha256":hashlib.sha256(old_content).hexdigest(),
 "normalizations":counts,"all_other_bytes_identical":equal,
 "browser_rerun":False,"claim":"The latest installed console produced the previously browser-qualified packet bytes after replacing only the two explicitly recorded fixture-dependent fields."}
print(json.dumps(receipt),flush=True)
(OUT/"canonical-output-equality.json").write_text(json.dumps(receipt,indent=2)+"\n")
assert equal
