"""Independent receiving of native Canvas pages/page CLI; synthetic loopback only."""
from pathlib import Path
import base64, contextlib, difflib, hashlib, io, json, logging, os, subprocess, sys, threading, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

AUTHOR=Path("/home/jacob/evaluation-69570d292200/canvas-pages-6d2bd132-9mie48yb")
SOURCE=AUTHOR/"candidate"
BASE=Path("/home/jacob/canvas-attempt-69570d292200/original")
OWN=Path(__file__).resolve().parent
PROFILE=OWN/"unused-profile"
def sha(b): return hashlib.sha256(b).hexdigest()
def git_blob(b):return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def write_json(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n")
R={"result":"RUNNING","source_base":"56a72a2e2cee5ec04671d12ebe5bc2484afb8026","product_tree":"6d2bd132c4e8de5735cfeeb15ef2db35bcbbf608","python":sys.version,"program_sha256":sha(Path(__file__).read_bytes()),"groups":[],"commands":[],"requests":[]}
pins=json.loads((AUTHOR/"evidence/product-tree.json").read_text())
base_pins=json.loads((AUTHOR/"evidence/base-tree.json").read_text())
pinmap={p["path"]:p for p in pins["tree"] if p["type"]!="tree"}
basemap={p["path"]:p for p in base_pins["tree"] if p["type"]!="tree"}
maintained={"src/canvaspilot/cli.py","README.md","tests/test_pages_cli.py","docs/pages-cli.md"}
def native_manifest():
 out={}
 for root,label in [(BASE,"base"),(SOURCE,"candidate")]:
  out[label]={}
  for p in sorted(root.rglob("*")):
   if not p.is_file() or "__pycache__" in p.parts or ".pytest_cache" in p.parts:continue
   relative=p.relative_to(root).as_posix()
   if relative not in (basemap if label=="base" else pinmap):continue
   b=p.read_bytes();expected=(basemap if label=="base" else pinmap)[relative]
   assert git_blob(b)==expected["sha"],(label,relative)
   out[label][relative]={"bytes":len(b),"sha256":sha(b),"blob":git_blob(b)}
 return out
R["source_before"]=native_manifest()
def group(name,fn):
 try:R["groups"].append({"name":name,"result":"PASS","detail":fn()})
 except Exception as e:R["groups"].append({"name":name,"result":"FAIL","error":str(e),"traceback":traceback.format_exc()})
 write_json(OWN/"receiving.json",R)
 print(name+": "+R["groups"][-1]["result"],flush=True)

def tree_hash(entries):
 root={}
 for p in entries:
  parts=p["path"].split("/");d=root
  for part in parts[:-1]:d=d.setdefault(part,{})
  d[parts[-1]]=(p["mode"],p["sha"])
 def encode(d):
  data=b""
  for name,v in sorted(d.items(),key=lambda x:(x[0]+("/" if isinstance(x[1],dict) else "")).encode()):
   if isinstance(v,dict):mode,obj="40000",encode(v)
   else:mode,obj=v
   data+=mode.encode()+b" "+name.encode()+b"\0"+bytes.fromhex(obj)
  return hashlib.sha1(b"tree "+str(len(data)).encode()+b"\0"+data).hexdigest()
 return encode(root)
def source_fence():
 assert tree_hash(list(basemap.values()))=="a07c3e941219ff80968e1ff20528a63541bb7400"
 assert tree_hash(list(pinmap.values()))==R["product_tree"]
 differences={p for p in set(basemap)|set(pinmap) if basemap.get(p)!=pinmap.get(p)}
 assert differences==maintained,differences
 unchanged=sorted(set(basemap)-maintained)
 assert len(unchanged)==1614
 insertion_proofs={}
 for relative in ("src/canvaspilot/cli.py","README.md"):
  a=(BASE/relative).read_bytes().splitlines(keepends=True)
  b=(SOURCE/relative).read_bytes().splitlines(keepends=True)
  opcodes=difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_opcodes()
  assert all(tag in ("equal","insert") for tag,*_ in opcodes),(relative,opcodes)
  reverse=b"".join(b[j:k] for tag,i,l,j,k in opcodes if tag=="equal")
  assert reverse==b"".join(a)
  insertion_proofs[relative]={"inserted_lines":sum(k-j for tag,i,l,j,k in opcodes if tag=="insert"),"original_reconstructed_byte_exact":True}
 return {"base_leaves":len(basemap),"product_leaves":len(pinmap),"unrelated_exact":len(unchanged),"changed":sorted(differences),"both_git_tree_hashes_independently_recomputed":True,"insertions":insertion_proofs}
group("source_scope_and_whole_tree_identity",source_fence)

STATE={"mode":"list-ok"}
FIRST=[{"url":"percent%2F ?# \u6e2c\u5b9a","title":"Literal \u6e2c\u5b9a","published":False,"updated_at":None,"front_page":0,"ignored":{"x":1}},17,{"url":"next","title":None,"published":None,"front_page":False}]
SECOND=[{"url":"page_id:00170","title":"","published":True,"updated_at":"future","front_page":None}]
BODY={"url":"returned%2F","title":"<literal>","body":"<p>A &lt;canvas&gt; &amp; \u6e2c\u5b9a</p>","published":False,"unknown":7}
def projected(rows):return [{k:p.get(k) for k in ("url","title","published","updated_at","front_page")} for p in rows if isinstance(p,dict)]
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  R["requests"].append({"method":"GET","target":self.path,"mode":STATE["mode"]})
  mode=STATE["mode"];status=200;headers={}
  if self.path.startswith("/api/v1/courses/42/pages?"):
   if "cursor=two" in self.path:
    if mode=="list-fail":status=503;payload={"error":"synthetic second page failure"}
    else:payload=SECOND
   elif mode=="list-empty":payload=[]
   else:
    payload=FIRST
    headers["Link"]='<'+ORIGIN+'/api/v1/courses/42/pages?cursor=two%2Fopaque&flag=1>; rel="next"'
  elif self.path.startswith("/api/v1/courses/42/pages/"):
   if mode=="page-malformed":payload=["wrong-shape",{"body":"must not pass"}]
   elif mode=="page-missing":payload={"url":"missing","title":None,"published":False}
   elif mode=="page-empty":payload={"url":"empty","body":"","published":None}
   else:payload=BODY
  else:status=404;payload={"unexpected":self.path}
  content=json.dumps(payload,ensure_ascii=False).encode()
  self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8")
  self.send_header("Content-Length",str(len(content)))
  for k,v in headers.items():self.send_header(k,v)
  self.end_headers();self.wfile.write(content)
server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
ORIGIN="http://127.0.0.1:"+str(server.server_port)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
env=os.environ.copy()
env.update({"PYTHONPATH":str(SOURCE/"src"),"PYTHONDONTWRITEBYTECODE":"1","TMPDIR":str(OWN)})
COMMON=["--base-url",ORIGIN,"--token","REVIEW_SYNTHETIC","--profile",str(PROFILE)]
def command(name,args,status=0,common=True,full=False):
 start=len(R["requests"])
 argv=[sys.executable,"-B","-m","canvaspilot.cli",*args,*(COMMON if common else [])]
 if full:
  with open("/dev/full","wb") as sink:done=subprocess.run(argv,env=env,cwd=OWN,stdout=sink,stderr=subprocess.PIPE,timeout=30)
  stdout=b""
 else:
  done=subprocess.run(argv,env=env,cwd=OWN,capture_output=True,timeout=30);stdout=done.stdout
 (OWN/(name+".stdout")).write_bytes(stdout);(OWN/(name+".stderr")).write_bytes(done.stderr)
 row={"name":name,"args":args,"exit":done.returncode,"stdout_bytes":len(stdout),"stdout_sha256":sha(stdout),"stderr_bytes":len(done.stderr),"stderr_sha256":sha(done.stderr),"requests":R["requests"][start:],"stdout_sink":"/dev/full" if full else "capture"}
 R["commands"].append(row)
 assert done.returncode==status if status is not None else done.returncode!=0,(name,done.returncode,stdout,done.stderr)
 return stdout,done.stderr,row

def admission():
 before=len(R["requests"])
 for label,args,expected in [
  ("pages-help",["pages","--help"],0),
  ("page-help",["page","--help"],0),
  ("zero-course",["pages","0"],2),
  ("missing-locator",["page","42"],2),
  ("literal-path",["page","42","chapter/one"],2),
  ("surrounding-space",["page","42"," intro"],2),
  ("zero-page-id",["page","42","page_id:000"],2)]:
  stdout,stderr,row=command(label,args,expected,common=expected!=0)
  if expected:assert stdout==b"",(label,stdout)
  else:assert b"usage:" in stdout.lower()
 assert len(R["requests"])==before
 assert not PROFILE.exists()
 return {"commands":7,"HTTP_requests":0,"profile_created":False}
group("help_and_rejected_admission_before_transport",admission)

def list_complete():
 STATE["mode"]="list-ok"
 stdout,stderr,row=command("pages-complete",["pages","42"])
 assert json.loads(stdout)==projected(FIRST+SECOND)
 assert stderr==b"",stderr
 targets=[x["target"] for x in row["requests"]]
 assert targets==["/api/v1/courses/42/pages?per_page=50","/api/v1/courses/42/pages?cursor=two%2Fopaque&flag=1"],targets
 return {"requests":targets,"rows":json.loads(stdout),"non_object_row_filter":"unchanged"}
group("complete_pagination_projection_and_opaque_cursor",list_complete)

def literal_page():
 STATE["mode"]="page-normal"
 locator="percent%2F ?# \u6e2c\u5b9a"
 stdout,stderr,row=command("page-literal",["page","42",locator])
 value=json.loads(stdout)
 assert value=={"url":"returned%2F","title":"<literal>","body_html":BODY["body"],"body_text":"A <canvas> & \u6e2c\u5b9a","published":False},value
 assert stderr==b""
 expected="/api/v1/courses/42/pages/"+quote(locator,safe="")+"?per_page=50"
 assert [x["target"] for x in row["requests"]]==[expected],row
 stdout,stderr,idrow=command("page-numeric-id",["page","00042","page_id:00170"])
 assert json.loads(stdout)==value and stderr==b""
 assert [x["target"] for x in idrow["requests"]]==["/api/v1/courses/42/pages/page_id%3A170?per_page=50"]
 return {"literal_target":expected,"id_target":idrow["requests"][0]["target"],"projection":value}
group("literal_locator_and_numeric_id_request_identity",literal_page)

def body_distinction():
 outputs={}
 for mode in ("page-missing","page-empty"):
  STATE["mode"]=mode
  stdout,stderr,row=command(mode,["page","42","chosen"])
  outputs[mode]=json.loads(stdout)
  assert stderr==b"" and len(row["requests"])==1
 assert outputs["page-missing"]["body_html"] is None
 assert outputs["page-empty"]["body_html"]==""
 assert outputs["page-missing"]["body_text"]==outputs["page-empty"]["body_text"]==""
 return outputs
group("missing_and_empty_html_preserve_api_distinction",body_distinction)

sys.path.insert(0,str(SOURCE/"src"))
from canvaspilot import cli, client
OriginalClient=client.CanvasClient
clients=[]
class ObservedClient(OriginalClient):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);clients.append(self);self.closed_observation=None
 def close(self):
  existing=self._http
  super().close()
  self.closed_observation={"actual_http_created":existing is not None,"actual_http_closed":existing.is_closed if existing else None,"released":self._http is None}
def cleanup_recovery():
 client.CanvasClient=ObservedClient
 http_log=logging.getLogger("httpx")
 previous=http_log.level
 http_log.setLevel(17)
 results=[]
 try:
  for mode,args,expected,error in [
   ("list-fail",["pages","42"],1,"HTTPStatusError"),
   ("list-ok",["pages","42"],0,None),
   ("page-malformed",["page","42","chosen"],1,"AttributeError"),
   ("page-normal",["page","42","chosen"],0,None)]:
   STATE["mode"]=mode;out=io.StringIO();err=io.StringIO();status=0;start=len(R["requests"])
   with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
    try:cli.main([*args,*COMMON])
    except SystemExit as exc:status=exc.code
   assert status==expected,(mode,status,out.getvalue(),err.getvalue())
   assert http_log.level==17
   obs=clients[-1].closed_observation
   assert obs=={"actual_http_created":True,"actual_http_closed":True,"released":True},obs
   if expected:
    assert out.getvalue()==""
    assert json.loads(err.getvalue())["error"]==error
   else:
    assert err.getvalue()==""
    assert json.loads(out.getvalue())==(projected(FIRST+SECOND) if mode=="list-ok" else {"url":"returned%2F","title":"<literal>","body_html":BODY["body"],"body_text":"A <canvas> & \u6e2c\u5b9a","published":False})
   results.append({"mode":mode,"exit":status,"stdout":out.getvalue(),"stderr":err.getvalue(),"requests":R["requests"][start:],"client":obs,"logger_restored_to":http_log.level})
 finally:
  client.CanvasClient=OriginalClient;http_log.setLevel(previous)
 write_json(OWN/"in-process-cleanup.json",results)
 return results
group("second_page_and_schema_failure_then_recovery_with_real_client_cleanup",cleanup_recovery)

def output_failure():
 STATE["mode"]="page-normal"
 stdout,stderr,row=command("stdout-full",["page","42","chosen"],status=None,full=True)
 assert b'"ok": false' in stderr and b'"error": "OSError"' in stderr,stderr
 assert len(row["requests"])==1
 return {"exit":row["exit"],"stderr":stderr.decode(),"actual_gets":1,"claim":"truthful nonzero output failure; no zero-partial-output promise"}
group("actual_native_stdout_device_failure",output_failure)
server.shutdown();server.server_close();thread.join(timeout=3)
R["source_after"]=native_manifest()
assert R["source_before"]==R["source_after"]
assert not PROFILE.exists()
R["source_unchanged"]=True
R["result"]="PASS" if all(g["result"]=="PASS" for g in R["groups"]) else "FAIL"
R["scope"]="Direct reviewer native CLI/process and actual HTTPX loopback observations; no live Canvas, profile, credentials, browser, installed adoption, author-suite replay, dependency/source writes or Actions."
write_json(OWN/"receiving.json",R)
print(json.dumps({"result":R["result"],"groups":len(R["groups"]),"CLI_processes":len(R["commands"]),"actual_GETs":len(R["requests"]),"source_unchanged":True}))
raise SystemExit(0 if R["result"]=="PASS" else 1)
