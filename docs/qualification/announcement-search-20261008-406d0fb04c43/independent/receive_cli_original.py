"""Independent actual-process receiver; frozen before candidate source inspection."""
import base64, fcntl, hashlib, http.server, io, json, os, pathlib, socket, subprocess, sys, threading, time, traceback, tty, urllib.parse, zipfile
PYTHON = "/workspace/scratch/ac386303dce2/runtime-execution/canvaspilot-env/bin/python"
TOKEN = "independent-local-fixture-token"
CHILD = r"""
import hashlib,json,logging,os,sys,traceback
source,meta_fd,port=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
args=json.loads(sys.argv[4]); sys.path.insert(0,source)
seen={"forbidden":[],"writes":[],"connects":[],"calls":[]}
def audit(event,args):
 if event=="open":
  mode=args[1] if len(args)>1 else None; flags=args[2] if len(args)>2 else 0
  writing=(isinstance(mode,str) and any(c in mode for c in "wax+")) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
  if writing:
   seen["writes"].append(str(args[0]));raise RuntimeError("receiver forbids filesystem writes")
 if event=="socket.connect":
  address=args[1];seen["connects"].append(repr(address))
  if not(isinstance(address,tuple) and address[0]=="127.0.0.1" and address[1]==port):
   seen["forbidden"].append([event,repr(address)]);raise RuntimeError("receiver forbids non-fixture connection")
 if event=="socket.getaddrinfo":
  if args[0] not in ("127.0.0.1",None):
   seen["forbidden"].append([event,repr(args)]);raise RuntimeError("receiver forbids non-fixture name lookup")
 if event in ("subprocess.Popen","os.posix_spawn","os.system"):
  seen["forbidden"].append([event,repr(args)]);raise RuntimeError("receiver forbids nested processes")
sys.addaudithook(audit)
def profiler(frame,event,arg):
 if event=="call" and frame.f_globals.get("__name__")=="canvaspilot.client" and frame.f_code.co_name in ("default_profile","default_base_url","__init__"):
  seen["calls"].append(frame.f_code.co_name)
sys.setprofile(profiler)
log=logging.getLogger("httpx");log.setLevel(logging.INFO)
handler=logging.StreamHandler(sys.stderr);handler.setFormatter(logging.Formatter("UNSUPPRESSED_HTTPX:%(message)s"));log.addHandler(handler)
code=0
try:
 from canvaspilot.cli import main
 main(args)
except SystemExit as e:
 code=e.code if isinstance(e.code,int) else (0 if e.code is None else 1)
except BaseException:
 traceback.print_exc();code=99
finally:
 sys.setprofile(None)
 seen["logger_level"]=log.level
 seen["modules"]={k:getattr(v,"__file__",None) for k,v in sys.modules.items() if k=="canvaspilot" or k.startswith("canvaspilot.")}
 os.write(meta_fd,json.dumps(seen,ensure_ascii=False).encode());os.close(meta_fd)
raise SystemExit(code)
"""
LONG = "x"*480 + " tail ROOM CHANGE ζ"
def row(i,title,text,course="course_42",posted=None,url=None):
 return {"id":i,"title":title,"message":text,"context_code":course,"posted_at":posted,"html_url":url,"ignored_extra":"not a normalized reader field"}
raw = [
 row(8,"ROOM CHANGE","<p>"+LONG+"</p>",posted="2026-10-07T12:00:00Z",url="https://canvas.invalid/courses/42/discussion_topics/8"),
 row(0,"room","change",course="course_77",posted=0),
 row(None,"Straße","<p>STRASSE e\u0301</p>"),
 row(9,"café","unrelated"),
 row(10,"cafe\u0301","e\u0301"),
 row(11,"a.b [room]","<p>axb [ROOM] a&amp;b</p>"),
 row(42,42,"plain"),
 None,
 row(12,None,"<p>prefix ROOM CHANGE suffix</p>",course="course_77"),
 row(13,"ΟΣ","<p>ος</p>"),
 row(14,"room change",None),
 row(15,{"room":"change"},"<p>none</p>")
]
raw[7]=dict(raw[0])
texts=[LONG,"change","STRASSE e\u0301","unrelated","e\u0301","axb [ROOM] a&b","plain",LONG,"prefix ROOM CHANGE suffix","ος","","none"]
EXPECTED=[{k:r[k] for k in ("id","title","posted_at","context_code","html_url")} | {"message_text":text} for r,text in zip(raw,texts)]
QUERY_CASES=[
 ("tail-order-duplicates","room change",[(0,["title","message_text"]),(7,["title","message_text"]),(8,["message_text"]),(10,["title"])]),
 ("unicode-full-casefold","STRASSE",[(2,["title","message_text"])]),
 ("no-unicode-normalization","café",[(3,["title"])]),
 ("literal-dot","a.b",[(5,["title"])]),
 ("literal-brackets","[room]",[(5,["title","message_text"])]),
 ("significant-query-spaces"," room change ",[(0,["message_text"]),(7,["message_text"]),(8,["message_text"])]),
 ("no-query-whitespace-normalization","room\nchange",[]),
 ("no-nontext-coercion","42",[]),
 ("greek-final-sigma-casefold","οσ",[(9,["title","message_text"])]),
 ("no-match-is-success","definitely absent",[])
]
state={"mode":"normal","requests":[]}
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_GET(self):
  parsed=urllib.parse.urlsplit(self.path);q=urllib.parse.parse_qs(parsed.query,keep_blank_values=True)
  state["requests"].append({"method":"GET","path":parsed.path,"query":q,"authorization":self.headers.get("Authorization")})
  page=q.get("page",["1"])[0];mode=state["mode"];status=200;link=None
  if parsed.path!="/api/v1/announcements": status=404;data={"error":"unexpected fixture endpoint"}
  elif mode=="auth":status=401;data={"errors":[{"message":"authored unauthorized"}]}
  elif mode=="later503" and page=="2":status=503;data={"errors":[{"message":"authored page-two unavailable"}]}
  elif mode=="empty":data=[]
  elif page=="1":data=raw[:6]+[None];link=f'<http://127.0.0.1:{self.server.server_port}/api/v1/announcements?page=2>; rel="next"'
  else:
   data=raw[6:]+[42,"noise"]
   if mode=="loop":link=f'<http://127.0.0.1:{self.server.server_port}/api/v1/announcements?page=2>; rel="next"'
  b=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)))
  if link:self.send_header("Link",link)
  self.end_headers();self.wfile.write(b)
 def do_POST(self):
  state["requests"].append({"method":"POST","path":self.path});self.send_error(405)
def sha(b):return hashlib.sha256(b).hexdigest()
def gitblob(b):return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def main(payload):
 started=time.time();archive=base64.b64decode(payload["archive"]);manifest=payload["manifest"]
 assert sha(archive)==manifest["sourceZip"]["sha256"]
 assert len(archive)==manifest["sourceZip"]["bytes"]
 assert gitblob(archive)==manifest["sourceZip"]["gitBlob"]
 z=zipfile.ZipFile(io.BytesIO(archive));entries=manifest["source"]
 assert len(z.namelist())==len(entries)
 source=[]
 for f in entries:
  name=f["path"].removeprefix("src/");b=z.read(name)
  assert len(b)==f["bytes"] and sha(b)==f["sha256"] and gitblob(b)==f["gitBlob"]
  source.append({"path":f["path"],"sha256":sha(b),"gitBlob":gitblob(b)})
 fd=os.memfd_create("canvas-announcement-independent-source",os.MFD_ALLOW_SEALING)
 os.write(fd,archive);fcntl.fcntl(fd,1033,15);assert fcntl.fcntl(fd,1034)==15
 source_path=f"/proc/self/fd/{fd}"
 server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 base=f"http://127.0.0.1:{server.server_port}";cases=[];checks=0
 def check(value,message):
  nonlocal checks
  checks+=1
  if not value:raise AssertionError(message)
 def invoke(name,args,mode="normal"):
  state["mode"]=mode;state["requests"]=[]
  rd,wr=os.pipe()
  env={"PATH":"/usr/bin:/bin","LANG":"C.UTF-8","PYTHONIOENCODING":"utf-8","PYTHONDONTWRITEBYTECODE":"1"}
  p=subprocess.run([PYTHON,"-I","-B","-c",CHILD,source_path,str(wr),str(server.server_port),json.dumps(args,ensure_ascii=False)],capture_output=True,text=True,env=env,pass_fds=(fd,wr),timeout=20)
  os.close(wr);meta=json.loads(os.read(rd,1_000_000));os.close(rd)
  result={"name":name,"args":args,"mode":mode,"exit":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"meta":meta,"requests":list(state["requests"])}
  cases.append(result)
  check(not meta["forbidden"],name+": forbidden operation")
  check(not meta["writes"],name+": filesystem write")
  check(meta["logger_level"]==20,name+": caller HTTPX logger level not restored")
  check(all(v and v.startswith(source_path+"/canvaspilot/") for v in meta["modules"].values()),name+": donor source imported")
  check(all(r["method"]=="GET" and r["path"]=="/api/v1/announcements" and r["authorization"]=="Bearer "+TOKEN for r in result["requests"]),name+": unexpected HTTP effects")
  return result
 def common(command):return [command,"42","77","42","--base-url",base,"--token",TOKEN,"--profile","/__canvas_receiver_unused_profile__"]
 def success(result):
  check(result["exit"]==0,result["name"]+": not success")
  check(result["stderr"]=="",result["name"]+": stderr contamination")
  data=json.loads(result["stdout"])
  req=result["requests"][0]["query"]
  check(req.get("context_codes[]")==["course_42","course_77","course_42"],result["name"]+": course order/duplicates lost")
  check(req.get("per_page")==["50"] and req.get("active_only")==["true"],result["name"]+": inherited reader query changed")
  return data
 try:
  if payload["variant"]=="baseline":
   r=invoke("new-capability-absent",["find-announcements","42","77","--text","room change"])
   check(r["exit"]==2 and r["stdout"]=="" and not r["requests"],"baseline missing command contract")
   check(not r["meta"]["calls"] and "canvaspilot.client" not in r["meta"]["modules"],"baseline parser had effects")
   r=invoke("inherited-full-reader",common("announcements")+["--detail","full"]);data=success(r)
   check(data==EXPECTED,"baseline full reader does not equal authored full normalized rows")
   check("ROOM CHANGE" in data[0]["message_text"][400:],"baseline tail not actually beyond compact boundary")
   r=invoke("inherited-compact-reader",common("announcements"));data=success(r)
   expected=[dict(x) for x in EXPECTED]
   for x in expected:
    if len(x["message_text"])>400:x["message_text"]=x["message_text"][:400]+"…"
   check(data==expected,"baseline compact reader contract")
   r=invoke("inherited-partial-page-refusal",common("announcements")+["--detail","full"],"later503")
   check(r["exit"]==1 and r["stdout"]=="" and len(r["requests"])==2,"baseline partial output leaked")
   e=json.loads(r["stderr"]);check(e["ok"] is False and set(e)=={"ok","error","message"},"baseline error shape")
  else:
   for n,query,wanted in QUERY_CASES:
    args=common("find-announcements")+["--text",query]
    start="2026-10-01T00:00:00+00:00" if n=="tail-order-duplicates" else None
    if start:args+=["--start-date",start]
    r=invoke(n,args);data=success(r)
    expected={"query":query,"match_mode":"literal_casefold","course_ids":[42,77,42],"start_date":start,"announcements_returned":12,"announcements_matched":len(wanted),"matches":[{"matched_fields":fields,"announcement":EXPECTED[i]} for i,fields in wanted]}
    check(data==expected,n+": exact independent desired result mismatch")
    check(len(r["requests"])==2,n+": complete two-page reader not used")
    check(r["requests"][0]["query"].get("start_date")==([start] if start else None),n+": start date forwarding")
   r=invoke("empty-reader-success",common("find-announcements")+["--text","anything"],"empty");data=success(r)
   check(data=={"query":"anything","match_mode":"literal_casefold","course_ids":[42,77,42],"start_date":None,"announcements_returned":0,"announcements_matched":0,"matches":[]},"empty result shape")
   refusals=[
    ("missing-query",["42"]),
    ("empty-query",["42","--text",""]),
    ("ascii-blank-query",["42","--text"," \t "]),
    ("unicode-blank-query",["42","--text","\u00a0\u2003"]),
    ("zero-course",["0","--text","x"]),
    ("negative-course",["-1","--text","x"]),
    ("nonnumeric-course",["nope","--text","x"]),
    ("missing-course",["--text","x"])
   ]
   for n,args in refusals:
    r=invoke(n,["find-announcements"]+args)
    check(r["exit"]==2 and r["stdout"]=="" and not r["requests"],n+": refusal output or HTTP effects")
    check(not r["meta"]["calls"] and "canvaspilot.client" not in r["meta"]["modules"],n+": client/default effects before admission")
   for mode in ("auth","later503","loop"):
    r=invoke("error-"+mode,common("find-announcements")+["--text","room change"],mode)
    check(r["exit"]==1 and r["stdout"]=="","error-"+mode+": partial success output")
    e=json.loads(r["stderr"]);check(set(e)=={"ok","error","message"} and e["ok"] is False and isinstance(e["error"],str) and bool(e["message"]),"error-"+mode+": structured error")
    check(len(r["requests"])==(1 if mode=="auth" else 2),"error-"+mode+": unexpected traversal")
   r=invoke("unchanged-full-reader-control",common("announcements")+["--detail","full"])
   check(success(r)==EXPECTED,"candidate changed inherited full reader")
  receipt={"schema":"canvaspilot74.independent-receiving.v1","variant":payload["variant"],"accepted":True,"sourceZipSha256":sha(archive),"sourceSeal":fcntl.fcntl(fd,1034),"source":source,"python":sys.version,"cases":cases,"checks":checks,"elapsedSeconds":round(time.time()-started,3),"filesystemWrites":0}
 except BaseException as e:
  receipt={"schema":"canvaspilot74.independent-receiving.v1","variant":payload["variant"],"accepted":False,"sourceZipSha256":sha(archive),"source":source,"cases":cases,"checks":checks,"failure":{"message":str(e),"traceback":traceback.format_exc()},"filesystemWrites":0}
 finally:server.shutdown();server.server_close();os.close(fd)
 return receipt
if __name__=="__main__":
 tty.setraw(sys.stdin.fileno());print("CANVAS_RECEIVER_READY",flush=True)
 buf=b""
 while b"\n" not in buf:buf+=os.read(sys.stdin.fileno(),65536)
 payload=json.loads(buf.split(b"\n",1)[0]);receipt=main(payload)
 print(json.dumps(receipt,ensure_ascii=False),flush=True)
 sys.exit(0 if receipt["accepted"] else 1)
