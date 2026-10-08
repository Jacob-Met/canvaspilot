import pathlib,tempfile,json,os,sys,subprocess,hashlib,datetime,shutil
p=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
storage=os.statvfs("/dev")
if storage.f_bavail*storage.f_frsize<8*1024*1024:raise SystemExit("one-shot tmpfs capacity gate; no allocation")
root=pathlib.Path(tempfile.mkdtemp(prefix="hamon-e04-canvas-independent-",dir="/dev"))
os.chmod(root,0o700)
def pin(data):
 return {"bytes":len(data),"git_blob":hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest(),"sha256":hashlib.sha256(data).hexdigest()}
files={}
try:
 for name,text in p["sources"].items():
  f=root/name;f.parent.mkdir(parents=True,exist_ok=True);b=text.encode()
  with f.open("xb") as h:h.write(b)
  if f.read_bytes()!=b:raise RuntimeError("source write/read mismatch")
  files[name]=pin(b)
 old=p["sources"]["candidate-cli.py"]
 for span in p["planner_spans"]:
  if old.count(span)!=1:raise RuntimeError("source span count")
  old=old.replace(span,"",1)
 with (root/"baseline-cli.py").open("xb") as h:h.write(old.encode())
 files["baseline-cli.py"]=pin(old.encode())
 with (root/"receive_child.py").open("x") as h:h.write(p["child"])
 cases=[
  {"name":"baseline-refuses-planner","cli":"baseline-cli.py","argv":["planner"],"data":[],"params":None,"exit":2,"parser":True,"logger_level":0},
  {"name":"offset-window-and-native-payload","argv":["planner","--start-date","2026-12-31T23:59:59-08:00","--end-date","2026-12-31T08:00:00+05:30"],"data":[{"plannable_type":"planner_note","plannable_id":0,"planner_override":{"marked_complete":False,"dismissed":None},"future":{"text":"<em>調査</em>\n\u0000 & value","fraction":0.0}},False,None,0],"params":{"start_date":"2026-12-31T23:59:59-08:00","end_date":"2026-12-31T08:00:00+05:30"},"exit":0,"logger_level":0},
  {"name":"empty-start-retains-native-omission","argv":["planner","--start-date","","--end-date","2026-10-01"],"data":[],"params":{"end_date":"2026-10-01"},"exit":0,"logger_level":10},
  {"name":"first-terminal-zero-retains-native-wrapper","argv":["planner"],"data":0,"params":{},"exit":0,"logger_level":50},
  *[{"name":"typed-"+kind,"argv":["planner"],"data":[{"id":"not-a-success-output"}],"params":{},"exit":1,"error":kind,"logger_level":0} for kind in ("CanvasAuthError","CanvasPaginationError","ValueError","HTTPError")],
  {"name":"missing-date-is-parser-only","argv":["planner","--end-date"],"data":[],"params":None,"exit":2,"parser":True,"logger_level":10},
 ]
 rows=[]
 for case in cases:
  config={**case,"cli":case.get("cli","candidate-cli.py"),"root":str(root)}
  config["argv"]=[*case["argv"],"--base-url","https://independent.invalid","--token","independent-synthetic-token","--profile",str(root/"unused-profile")]
  run=subprocess.run([sys.executable,"-B",str(root/"receive_child.py")],input=json.dumps(config),text=True,capture_output=True,timeout=12,env={"PATH":os.defpath,"PYTHONDONTWRITEBYTECODE":"1","LANG":"C.UTF-8","PYTHONHASHSEED":"0"},cwd=root)
  try:r=json.loads(run.stdout)
  except Exception:rows.append({"name":case["name"],"outer_exit":run.returncode,"harness_error":True,"stdout":run.stdout,"stderr":run.stderr});continue
  checks=[]
  def check(name,value,actual=None):checks.append({"name":name,"pass":bool(value),**({"actual":actual} if actual is not None else {})})
  check("actual child exit",run.returncode==case["exit"],run.returncode)
  check("native exit agrees",r["native_exit"]==case["exit"],r["native_exit"])
  check("no unhandled receiver exception",r["uncaught"] is None,r["uncaught"])
  check("no transport/broker effects",not r["effects"])
  check("no profile creation",not r["profile_exists"])
  check("fixture data unchanged",r["fixture_unchanged"])
  check("logger restored exactly",r["logger_before"]==r["logger_after"],[r["logger_before"],r["logger_after"]])
  check("no HTTPX info output",r["captured_httpx_info"]=="")
  check("wrapper stderr empty",run.stderr=="",run.stderr)
  if case.get("parser"):
   check("parser refusal before client construction",r["constructions"]==[] and r["calls"]==[] and r["closed"]==0)
   check("parser stdout empty",r["stdout"]=="")
  else:
   check("one native client and one close",len(r["constructions"])==1 and r["closed"]==1)
   check("exact existing planner GET and native filters",len(r["calls"])==1 and r["calls"][0]["method"]=="GET" and r["calls"][0]["path"]=="/api/v1/planner/items" and r["calls"][0]["params"]==case["params"] and r["calls"][0]["json_body"] is None)
   check("caller configuration retained",r["constructions"][0]["base_url"]=="https://independent.invalid" and r["constructions"][0]["fixture_token_selected"])
   check("logger was at least warning while reading",r["calls"][0]["logger_level_during"]>=30)
   if case.get("error"):
    parsed=json.loads(r["stderr"])
    check("typed complete error and empty success output",r["stdout"]=="" and parsed=={"ok":False,"error":case["error"],"message":'independent "failure"\nsecond line'})
   else:
    expected=case["data"] if isinstance(case["data"],list) else [case["data"]]
    check("lossless native collection",json.loads(r["stdout"])==expected)
    check("success stderr empty",r["stderr"]=="")
  rows.append({"name":case["name"],"outer_exit":run.returncode,"observation":r,"checks":checks})
 stable={}
 for name,want in files.items():stable[name]=pin((root/name).read_bytes())==want
 result={"date":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"PASS" if all(not r.get("harness_error") and all(c["pass"] for c in r["checks"]) for r in rows) and all(stable.values()) else "FAIL","boundary":"Nine actual Python children compile exact source CLI and use native API/client fixture implementation, with a bare package namespace and strict unavailable-HTTPX/broker tripwires. Native transport/MCP/package bootstrap are not exercised here; the separately observed hosted full-package HTTP tests cover that boundary.","python":sys.version,"source_pins":files,"source_stable":stable,"rows":rows,"totals":{"actual_children":len(rows),"conditions":sum(len(r.get("checks",[])) for r in rows),"failed":sum(sum(not c["pass"] for c in r.get("checks",[])) for r in rows),"harness_errors":sum(bool(r.get("harness_error")) for r in rows)},"fixture_storage":"One ordinary unique mode0700 directory on existing /dev tmpfs. All source setup, children, before/after pins and result capture occur in this one process; no cross-call path persistence is claimed."}
 print(json.dumps(result,ensure_ascii=True))
finally:
 shutil.rmtree(root)
