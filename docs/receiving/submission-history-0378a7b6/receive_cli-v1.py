"""Native CLI receiving with an authored loopback Canvas response, never a school session."""
from __future__ import annotations
import argparse
import base64
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import traceback
from urllib.parse import parse_qs, urlsplit
from html.parser import HTMLParser

parser=argparse.ArgumentParser()
parser.add_argument("mode", choices=["baseline","candidate"])
parser.add_argument("root",type=Path)
parser.add_argument("proof",type=Path)
args=parser.parse_args()
out=args.proof/args.mode
out.mkdir()
sha=lambda data:hashlib.sha256(data).hexdigest()
assignment=json.loads((args.proof/"fixture-assignment.json").read_text(encoding="utf-8"))
submission=json.loads((args.proof/"fixture-submission.json").read_text(encoding="utf-8"))
fixture_hashes={name:sha((args.proof/name).read_bytes()) for name in ["fixture-assignment.json","fixture-submission.json"]}
expected={"assignment":assignment,"current_submission":{k:v for k,v in submission.items() if k not in ("submission_history","submission_comments")},"history":{"returned":True,"records":submission["submission_history"]},"submission_comments":submission["submission_comments"]}
(out/"expected-normalized-report.json").write_text(json.dumps(expected,ensure_ascii=True,indent=2)+"\n",encoding="ascii")
state={"submission":submission,"fail_second":False}
requests=[]
class Fixture(BaseHTTPRequestHandler):
    def log_message(self,*_args): pass
    def do_GET(self):
        parsed=urlsplit(self.path)
        requests.append({"method":"GET","path":parsed.path,"query":parse_qs(parsed.query,keep_blank_values=True)})
        status=200
        if parsed.path=="/api/v1/courses/71/assignments/902":
            value=assignment
        elif parsed.path=="/api/v1/courses/71/assignments/902/submissions/self":
            if state["fail_second"]:status,value=503,{"errors":[{"message":"authored second-read refusal"}]}
            else:value=state["submission"]
        else:status,value=404,{"error":"unexpected fixture route"}
        data=json.dumps(value,ensure_ascii=True).encode("ascii")
        self.send_response(status); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        requests.append({"method":"POST","path":self.path})
        self.send_error(405)
server=ThreadingHTTPServer(("127.0.0.1",0),Fixture)
thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
origin=f"http://127.0.0.1:{server.server_port}"
env={**os.environ,"PYTHONPATH":str(args.root/"src"),"PYTHONUTF8":"1","NO_PROXY":"127.0.0.1,localhost","no_proxy":"127.0.0.1,localhost"}
runs=[]
def run(label,command,extra=None,course="71"):
    requests.clear()
    command_line=[sys.executable,"-c","from canvaspilot.cli import main; main()",command,course,"902","--base-url",origin,"--token","synthetic-history-receiver"]
    if extra:command_line+=extra
    completed=subprocess.run(command_line,cwd=args.root,env=env,capture_output=True,timeout=45)
    (out/(label+".stdout.txt")).write_bytes(completed.stdout)
    (out/(label+".stderr.txt")).write_bytes(completed.stderr)
    item={"label":label,"returncode":completed.returncode,"requests":deepcopy(requests),"stdout_sha256":sha(completed.stdout),"stderr_sha256":sha(completed.stderr)}
    runs.append(item)
    return completed,item
def assert_reads(item):
    assert item["requests"]==[
        {"method":"GET","path":"/api/v1/courses/71/assignments/902","query":{}},
        {"method":"GET","path":"/api/v1/courses/71/assignments/902/submissions/self","query":{"include[]":["submission_history","submission_comments"]}},
    ],item
class Download(HTMLParser):
    href=None
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag=="a" and values.get("id")=="download-history":
            assert self.href is None
            self.href=values.get("href")
def exported_json(file):
    parsed=Download(); parsed.feed(file.read_text(encoding="utf-8"))
    assert parsed.href and parsed.href.startswith("data:application/json;base64,")
    return json.loads(base64.b64decode(parsed.href.split(",",1)[1],validate=True))
checks=[]
receipt={"started":datetime.now(UTC).isoformat(),"mode":args.mode,"source":str(args.root),"head":subprocess.check_output(["git","-C",str(args.root),"rev-parse","HEAD"],text=True).strip(),"source_status":subprocess.check_output(["git","-C",str(args.root),"status","--short"],text=True).strip(),"driver_sha256":sha(Path(__file__).read_bytes()),"fixtures_before":fixture_hashes,"runs":runs,"checks":checks}
try:
    if args.mode=="baseline":
        assert not receipt["source_status"],"Original source must be clean"
        completed,item=run("original-history","submission-history")
        assert completed.returncode==0,completed.stderr
        assert json.loads(completed.stdout)==expected
        assert_reads(item)
        checks.append("Original actual CLI preserves separate current/history/comment JSON through exactly two self GETs")
        target=out/"absent-history.html"
        completed,item=run("missing-export","export-submission-history",["--out",str(target)])
        assert completed.returncode==2 and b"invalid choice" in completed.stderr
        assert not target.exists() and item["requests"]==[]
        checks.append("Original CLI has no export-submission-history command; no report or source request is produced")
    else:
        target=out/"submission-history.html"
        completed,item=run("full-export","export-submission-history",["--out",str(target)])
        assert completed.returncode==0,completed.stderr
        summary=json.loads(completed.stdout)
        assert summary["ok"] is True and summary["sha256"]==sha(target.read_bytes())
        assert_reads(item)
        assert exported_json(target)==expected
        checks.append("Actual candidate CLI publishes exact complete normalized report after two unchanged self GETs")
        sentinel=out/"protected.html"; sentinel.write_bytes(b"existing user file\n")
        completed,item=run("protected-target","export-submission-history",["--out",str(sentinel)])
        assert completed.returncode==1 and json.loads(completed.stderr)["error"]=="FileExistsError"
        assert not completed.stdout and item["requests"]==[] and sentinel.read_bytes()==b"existing user file\n"
        checks.append("Existing output is protected before any provider request")
        for case,returned in [("unavailable",None),("empty",[])]:
            state["submission"]={"attempt":9,"score":0}
            if returned is not None:
                state["submission"]["submission_history"]=[]
                state["submission"]["submission_comments"]=[]
            destination=out/(case+".html")
            completed,item=run(case,"export-submission-history",["--out",str(destination)])
            assert completed.returncode==0,completed.stderr
            assert_reads(item)
            report=exported_json(destination)
            assert report["history"]=={"returned":returned is not None,"records":returned}
            assert report["submission_comments"]==returned
            assert report["current_submission"]=={"attempt":9,"score":0}
        checks.append("Unavailable associations and explicitly returned empty lists remain different in actual files")
        state["submission"]={"submission_history":{"invalid":"container"}}
        refused=out/"malformed.html"
        completed,item=run("malformed-history","export-submission-history",["--out",str(refused)])
        assert completed.returncode==1 and json.loads(completed.stderr)["error"]=="ValueError"
        assert not completed.stdout and not refused.exists()
        assert_reads(item)
        checks.append("Malformed source history refuses the report instead of displaying an empty history")
        state["submission"]=submission;state["fail_second"]=True
        refused=out/"refused.html"
        completed,item=run("second-read-error","export-submission-history",["--out",str(refused)])
        assert completed.returncode==1 and json.loads(completed.stderr)["error"]=="HTTPStatusError"
        assert not completed.stdout and not refused.exists()
        assert_reads(item)
        checks.append("A later read failure creates no partial report")
        state["fail_second"]=False
        refused=out/"invalid-selector.html"
        completed,item=run("invalid-selector","export-submission-history",["--out",str(refused)],course="0")
        assert completed.returncode==1 and json.loads(completed.stderr)["error"]=="ValueError"
        assert not completed.stdout and not refused.exists() and item["requests"]==[]
        checks.append("Invalid original numeric selection fails before any request or report")
    after={name:sha((args.proof/name).read_bytes()) for name in fixture_hashes}
    assert after==fixture_hashes
    receipt.update({"finished":datetime.now(UTC).isoformat(),"fixtures_after":after,"passed":True})
except BaseException:
    receipt.update({"finished":datetime.now(UTC).isoformat(),"passed":False,"error":traceback.format_exc()})
    raise
finally:
    server.shutdown();server.server_close();thread.join(timeout=2)
    (out/"receipt.json").write_text(json.dumps(receipt,ensure_ascii=True,indent=2)+"\n",encoding="ascii")
    print(json.dumps({"mode":args.mode,"passed":receipt.get("passed"),"checks":checks,"receipt":str(out/"receipt.json")}))
