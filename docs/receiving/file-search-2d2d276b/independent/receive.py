"""Independent contract receiver: real CanvasPilot CLI/client plus model invariants."""
from __future__ import annotations
import base64, copy, datetime, hashlib, http.server, importlib, json, os, pathlib
import subprocess, sys, threading, time, traceback, urllib.parse, socket

ROOT=pathlib.Path(__file__).resolve().parent
MODE=sys.argv[1]
SOURCE=pathlib.Path(sys.argv[2]).resolve()
OUT=pathlib.Path(sys.argv[3]).resolve()
assert MODE in ("baseline","candidate")
OUT.mkdir(parents=True,exist_ok=False)
PYTHON=sys.executable
TOKEN="synthetic-receiver-token-2d2d276b"
sha=lambda b:hashlib.sha256(b).hexdigest()
jbytes=lambda x:(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+"\n").encode()
def source_pins():
    return {str(p.relative_to(SOURCE)):{"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())}
            for p in sorted(SOURCE.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
BEFORE=source_pins()
assert BEFORE
sys.path.insert(0,str(SOURCE/"src"))
GROUPS=[]
INVOCATIONS=[]

RAW_A={"id":0,"display_name":"Straße [lab]","filename":"STRASSE.pdf","size":0,
       "url":"https://never-open.invalid/file?literal=<script>","content-type":"text/plain"}
RAW_B={"id":0,"display_name":None,"filename":"strasse-notes.md","size":4}
RAW_77={"id":7,"display_name":"Unrelated","filename":None}
PROJECTED_A={"id":0,"display_name":"Straße [lab]","filename":"STRASSE.pdf","size":0,
             "updated_at":None,"url":RAW_A["url"],"content_type":"text/plain"}
PROJECTED_B={"id":0,"display_name":None,"filename":"strasse-notes.md","size":4,
             "updated_at":None,"url":None,"content_type":None}
PROJECTED_77={"id":7,"display_name":"Unrelated","filename":None,"size":None,
              "updated_at":None,"url":None,"content_type":None}

class Fixture:
    def __init__(self):
        fixture=self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self): self.reply(405,{"error":"receiver forbids writes"})
            def do_GET(self):
                fixture.requests.append({"method":"GET","path":self.path,
                    "synthetic_auth":self.headers.get("Authorization")=="Bearer "+TOKEN})
                parts=urllib.parse.urlsplit(self.path);q=urllib.parse.parse_qs(parts.query)
                if self.headers.get("Authorization")!="Bearer "+TOKEN:
                    return self.reply(401,{"error":"synthetic token required"})
                if parts.path=="/api/v1/courses/42/files":
                    if fixture.mode=="first_auth": return self.reply(401,{"error":"synthetic denied"})
                    if fixture.mode=="oversized": return self.reply(200,[RAW_A]*2001)
                    if fixture.mode=="foreign_link":
                        return self.reply(200,[RAW_A],'<http://127.0.0.1:1/foreign>; rel="next"')
                    if fixture.mode=="cycle":
                        return self.reply(200,[RAW_A],'<'+fixture.base+'/api/v1/courses/42/files?cursor=loop>; rel="next"')
                    if "cursor" not in q:
                        return self.reply(200,[RAW_A,17],'<'+fixture.base+'/api/v1/courses/42/files?cursor=opaque%2Bnext&keep=1&keep=2>; rel="next"')
                    assert q=={"cursor":["opaque+next"],"keep":["1","2"]},q
                    if fixture.mode=="late_http": return self.reply(503,{"error":"synthetic later-page failure"})
                    if fixture.mode=="late_nonlist": return self.reply(200,{"not":"a list"})
                    if fixture.mode=="late_json": return self.reply(200,b"{")
                    return self.reply(200,[RAW_B,RAW_A])
                if parts.path=="/api/v1/courses/77/files": return self.reply(200,[RAW_77,{}])
                if parts.path=="/api/v1/courses/88/files": return self.reply(200,[])
                return self.reply(404,{"error":"no fixture route"})
            def reply(self,status,body,link=None):
                if self.command!="GET":
                    fixture.requests.append({"method":self.command,"path":self.path,"synthetic_auth":False})
                data=body if isinstance(body,bytes) else json.dumps(body,ensure_ascii=False,allow_nan=False).encode()
                self.send_response(status)
                self.send_header("Content-Type","application/json; charset=utf-8")
                self.send_header("Content-Length",str(len(data)))
                self.send_header("Connection","close")
                if link:self.send_header("Link",link)
                self.end_headers();self.wfile.write(data)
        self.server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
        self.server.daemon_threads=True
        self.base="http://127.0.0.1:"+str(self.server.server_port)
        self.requests=[];self.mode="success"
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join(3)
        assert not self.thread.is_alive(),"Owned HTTP listener thread did not drain"

SERVER=Fixture()
PARENT_BLOCKED=[]
def forbid_parent_connection(*args,**kwargs):
    PARENT_BLOCKED.append("outbound socket or DNS requested in model receiver")
    raise RuntimeError("Independent model receiving permits no outbound connection")
socket.socket.connect=forbid_parent_connection
socket.getaddrinfo=forbid_parent_connection
def cli(arguments,mode="success",level=17):
    SERVER.mode=mode;SERVER.requests=[]
    case=OUT/("cli-%03d"%(len(INVOCATIONS)+1));case.mkdir()
    home=case/"home";home.mkdir()
    temp=case/"tmp";temp.mkdir()
    env=os.environ.copy()
    for key in list(env):
        if key.upper() in ("HTTP_PROXY","HTTPS_PROXY","ALL_PROXY") or key.startswith("CANVAS"):
            env.pop(key,None)
    env.update({"HOME":str(home),"USERPROFILE":str(home),"TMPDIR":str(temp),"TMP":str(temp),"TEMP":str(temp),
                "XDG_CACHE_HOME":str(home/"cache"),"PYTHONDONTWRITEBYTECODE":"1",
                "PYTHONPATH":str(SOURCE/"src"),"CANVAS_API_TOKEN":TOKEN,"CANVAS_BASE_URL":SERVER.base,
                "CANVAS_PROFILE":str(home/"profile"),"NO_PROXY":"127.0.0.1",
                "RECEIVER_LOOPBACK_PORT":str(SERVER.server.server_port),"RECEIVER_META":str(case/"lifecycle.json"),
                "RECEIVER_LOG_LEVEL":str(level)})
    cmd=[PYTHON,"-B",str(ROOT/"cli-child.py"),*arguments,"--base-url",SERVER.base,"--token",TOKEN,"--profile",str(home/"profile")]
    done=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=18)
    (case/"stdout.bin").write_bytes(done.stdout);(case/"stderr.bin").write_bytes(done.stderr)
    metadata=json.loads((case/"lifecycle.json").read_bytes())
    record={"case":case.name,"arguments":arguments,"scenario":mode,"returncode":done.returncode,
            "stdout_bytes":len(done.stdout),"stdout_sha256":sha(done.stdout),
            "stderr_bytes":len(done.stderr),"stderr_sha256":sha(done.stderr),
            "requests":copy.deepcopy(SERVER.requests),"lifecycle":metadata}
    (case/"receipt.json").write_bytes(jbytes(record));INVOCATIONS.append(record)
    assert metadata["blocked"]==[],metadata
    assert metadata["source_modules"]
    assert all(value.startswith(str(SOURCE/"src")+"/") for value in metadata["source_modules"].values()),metadata["source_modules"]
    assert all(x["method"]=="GET" and x["synthetic_auth"] for x in SERVER.requests),SERVER.requests
    assert metadata["logger_before"]==metadata["logger_after"]==level,metadata
    return done,metadata,copy.deepcopy(SERVER.requests)

def expected_cli():
    return {"query":"STRASSE","match_rule":"unicode_casefold_substring",
      "searched_fields":["display_name","filename"],"source":"CanvasAPI.list_files","content_searched":False,
      "courses":[
        {"course_id":"42","returned_files":3,"searched_files":3,"matched_files":3,
         "unavailable_names":[{"source_position":2,"fields":{"display_name":"null"}}],
         "matches":[{"source_position":1,"matched_fields":["display_name","filename"],"file":PROJECTED_A},
                    {"source_position":2,"matched_fields":["filename"],"file":PROJECTED_B},
                    {"source_position":3,"matched_fields":["display_name","filename"],"file":PROJECTED_A}]},
        {"course_id":"77","returned_files":2,"searched_files":1,"matched_files":0,
         "unavailable_names":[{"source_position":1,"fields":{"filename":"null"}},
                              {"source_position":2,"fields":{"display_name":"null","filename":"null"}}],"matches":[]},
        {"course_id":"88","returned_files":0,"searched_files":0,"matched_files":0,"unavailable_names":[],"matches":[]}],
      "totals":{"courses":3,"returned_files":5,"searched_files":4,"matched_files":3,"rows_with_unavailable_names":3}}

def cli_success():
    done,meta,requests=cli(["find-files","042","77","88","--text","STRASSE"])
    assert done.returncode==0,(done.returncode,done.stderr.decode())
    assert not done.stderr,done.stderr
    assert json.loads(done.stdout)==expected_cli(),done.stdout.decode()
    assert done.stdout==(json.dumps(expected_cli(),indent=2,allow_nan=False)+"\n").encode()
    assert meta["client_created"]==meta["client_closed"]==1,meta
    assert len(requests)==4,requests
    assert [urllib.parse.urlsplit(x["path"]).path for x in requests]==[
        "/api/v1/courses/42/files","/api/v1/courses/42/files","/api/v1/courses/77/files","/api/v1/courses/88/files"]
    assert requests[1]["path"]=="/api/v1/courses/42/files?cursor=opaque%2Bnext&keep=1&keep=2"
    (OUT/"accepted-success.stdout.bin").write_bytes(done.stdout)
    return {"normalized_rows":5,"matches":3,"requests":4,"duplicate_occurrences_preserved":True}

def legacy_control():
    done,meta,requests=cli(["files","42"])
    assert done.returncode==0,(done.returncode,done.stderr.decode())
    assert json.loads(done.stdout)==[PROJECTED_A,PROJECTED_B,PROJECTED_A]
    assert meta["client_created"]==meta["client_closed"]==1
    assert len(requests)==2
    (OUT/"legacy-files.stdout.bin").write_bytes(done.stdout)
    original=ROOT/"baseline-run"/"legacy-files.stdout.bin"
    if MODE=="candidate" and original.exists():assert done.stdout==original.read_bytes()
    return {"rows":3,"requests":2,"ordinary_files_continuity":True}

class API:
    def __init__(self,rows):self.rows=rows;self.calls=[]
    def list_files(self,course):
        self.calls.append(course);value=self.rows[course]
        if isinstance(value,BaseException):raise value
        return value
    def __getattr__(self,name):raise AssertionError("Uncontracted API access: "+name)
def helper():return importlib.import_module("canvaspilot.file_search")
def must_fail(call,kind=ValueError):
    try:call()
    except kind as exc:return exc
    raise AssertionError("Expected "+kind.__name__)

def admission():
    h=helper()
    assert h.validate_request(("001",2)," lab ")==(["1","2"]," lab ")
    assert h.validate_request(list(range(1,11)),"q")==([str(x) for x in range(1,11)],"q")
    assert h.validate_request(["9"*20],"é"*256)==(["9"*20],"é"*256)
    assert h.validate_request([int("9"*20)],"雪"*170+"é")==(["9"*20],"雪"*170+"é")
    bad_ids=[[],(),list(range(1,12)),["1"]*11,["01",1],["0"],[0],[True],[False],["-1"],["+1"],[" 1"],["1 "],
             ["١"],["１"],["1.0"],[1.0],[None],["1"*21],"1",{"1"},(x for x in ["1"])]
    for ids in bad_ids:
        api=API({})
        must_fail(lambda: h.find_files(api,ids,"lab"))
        assert api.calls==[]
    for text in (""," \t\n","\u00a0",None,17,b"lab","\ud800","雪"*171,"a"*513):
        api=API({})
        must_fail(lambda: h.find_files(api,["1"],text))
        assert api.calls==[]
    return {"invalid_selections":len(bad_ids),"invalid_texts":9,"accepted_UTF8_bytes":512}

def exact_model():
    h=helper()
    row={"id":7,"display_name":"Straße [LAB] notes","filename":"STRASSE [lab].PDF","size":0,
         "url":"https://never-open.invalid/?literal=<script>","extra":{"raw":"e\u0301","values":[False,None,0]}}
    rows=[row,{"id":7,"display_name":None,"filename":"strasse.md","size":0},
          {"id":8,"display_name":"Moss","filename":""},
          {"id":False,"display_name":88,"meta":{"literal":"STRASSE"}},
          {"id":9,"display_name":"","filename":None},copy.deepcopy(row)]
    original=copy.deepcopy(rows);api=API({"77":[],"42":rows})
    got=h.find_files(api,["077",42],"STRASSE")
    assert api.calls==["77","42"] and rows==original
    empty={"course_id":"77","returned_files":0,"searched_files":0,"matched_files":0,"unavailable_names":[],"matches":[]}
    second={"course_id":"42","returned_files":6,"searched_files":5,"matched_files":3,
            "unavailable_names":[{"source_position":2,"fields":{"display_name":"null"}},
              {"source_position":4,"fields":{"display_name":"unsupported_type","filename":"missing"}},
              {"source_position":5,"fields":{"filename":"null"}}],
            "matches":[{"source_position":1,"matched_fields":["display_name","filename"],"file":rows[0]},
                       {"source_position":2,"matched_fields":["filename"],"file":rows[1]},
                       {"source_position":6,"matched_fields":["display_name","filename"],"file":rows[5]}]}
    expected={"query":"STRASSE","match_rule":"unicode_casefold_substring","searched_fields":["display_name","filename"],
              "source":"CanvasAPI.list_files","content_searched":False,"courses":[empty,second],
              "totals":{"courses":2,"returned_files":6,"searched_files":5,"matched_files":3,"rows_with_unavailable_names":3}}
    assert got==expected,got
    return {"complete_objects_preserved":True,"positions":[1,2,6],"unknown_name_rows":3}

def literals():
    h=helper()
    cases=[
      ([{"display_name":"abc","filename":"def"}],"cd",[]),
      ([{"display_name":"a*b[0].pdf","filename":""},{"display_name":"ab0.pdf","filename":""}],"*b[0]",[1]),
      ([{"display_name":"lab","filename":""},{"display_name":" lab ","filename":""},{"display_name":"LAB ","filename":""}]," lab ",[2]),
      ([{"display_name":"café","filename":""},{"display_name":"cafe\u0301","filename":""}],"café",[1]),
      ([{"display_name":["STRASSE"],"filename":"different"},{"display_name":"x","filename":17}],"STRASSE",[]),
      ([{"display_name":"雪研究.PDF","filename":"Δ"}],"雪研究",[1])]
    for rows,query,positions in cases:
        api=API({"1":rows});before=copy.deepcopy(rows)
        result=h.find_files(api,["1"],query)
        assert result["query"]==query
        assert [x["source_position"] for x in result["courses"][0]["matches"]]==positions
        assert rows==before
    return {"literal_cases":len(cases)}

def transport_identity():
    h=helper()
    class ReadFailure(RuntimeError):pass
    error=ReadFailure("synthetic second-course failure")
    rows=[{"display_name":"lab","filename":""}];api=API({"1":rows,"2":error,"3":[]})
    observed=must_fail(lambda:h.find_files(api,["1","2","3"],"lab"),ReadFailure)
    assert observed is error and api.calls==["1","2"]
    return {"same_exception_propagated":True,"later_course_unread":True}

def schema():
    h=helper()
    malformed=[None,{},(),["bad"],[None],[17]]
    malformed += [[{"display_name":"n","meta":value}] for value in
                  (float("nan"),float("inf"),b"bytes",{"x"},object(),{1:"wrong key"},{"nested":{False:1}},"\ud800",{"\ud800":1})]
    cycle={"display_name":"n"};cycle["cycle"]=cycle;malformed.append([cycle])
    for rows in malformed:
        api=API({"1":rows,"2":[]})
        must_fail(lambda:h.find_files(api,["1","2"],"n"))
        assert api.calls==["1"]
    return {"schema_refusals":len(malformed)}

def row_limits():
    h=helper();r={"display_name":"needle","filename":""}
    api=API({"1":[r]*2000,"2":[r]*2000,"3":[r]*1000})
    result=h.find_files(api,["1","2","3"],"needle")
    assert result["totals"]["returned_files"]==result["totals"]["matched_files"]==5000
    assert result["courses"][2]["matches"][-1]["source_position"]==1000
    for mapping,courses,expected in [
        ({"1":[r]*2001,"2":[]},["1","2"],["1"]),
        ({"1":[r]*2000,"2":[r]*2000,"3":[r]*1001,"4":[]},["1","2","3","4"],["1","2","3"])]:
        api=API(mapping);must_fail(lambda:h.find_files(api,courses,"needle"))
        assert api.calls==expected,api.calls
    return {"per_course_inclusive":2000,"total_inclusive":5000,"over_limit_stops_later_reads":True}

def byte_limits():
    h=helper();limit=8*1024*1024
    blank={"display_name":"needle","payload":""}
    overhead=len(json.dumps(blank,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode())
    half=limit//2;space=half-overhead
    row={"display_name":"needle","payload":"é"*(space//2)+("z" if space%2 else "")}
    assert len(json.dumps(row,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode())==half
    api=API({"1":[row],"2":[row]})
    result=h.find_files(api,["1","2"],"needle")
    assert result["totals"]["matched_files"]==2 and result["courses"][1]["matches"][0]["file"]==row
    del result
    api=API({"1":[row],"2":[row],"3":[{"display_name":"x"}],"4":[]})
    must_fail(lambda:h.find_files(api,["1","2","3","4"],"needle"))
    assert api.calls==["1","2","3"]
    oversized={"display_name":"needle","payload":"z"*(limit-overhead+1)}
    api=API({"1":[oversized],"2":[]})
    must_fail(lambda:h.find_files(api,["1","2"],"needle"))
    assert api.calls==["1"]
    return {"combined_UTF8_bytes_inclusive":limit,"larger_and_accumulated_rows_refused":True}

def cli_invalid():
    cases=[["find-files","01","1","--text","lab"],["find-files","0","--text","lab"],
           ["find-files","١","--text","lab"],["find-files","1"*21,"--text","lab"],
           ["find-files","1","--text"," \t"],["find-files","1","--text","雪"*171]]
    for argv in cases:
        done,meta,requests=cli(argv)
        assert done.returncode==2 and not done.stdout and done.stderr
        assert meta["client_created"]==meta["client_closed"]==0 and requests==[]
    return {"argument_refusals_before_constructor":len(cases)}

def cli_error(scenario):
    done,meta,requests=cli(["find-files","42","77","--text","STRASSE"],mode=scenario,level=0)
    assert done.returncode==1 and not done.stdout,(done.returncode,done.stdout,done.stderr)
    error=json.loads(done.stderr)
    assert set(error)=={"ok","error","message"} and error["ok"] is False
    assert isinstance(error["error"],str) and error["error"] and isinstance(error["message"],str)
    assert meta["client_created"]==meta["client_closed"]==1
    assert requests and all("/courses/42/files" in r["path"] for r in requests)
    return {"error_class":error["error"],"requests":len(requests),"no_partial_stdout":True}

def determinism():
    original=(OUT/"accepted-success.stdout.bin").read_bytes()
    done,meta,requests=cli(["find-files","042","77","88","--text","STRASSE"])
    assert done.returncode==0 and done.stdout==original and done.stderr==b""
    assert meta["client_created"]==meta["client_closed"]==1
    return {"repeated_stdout_sha256":sha(original)}

def group(name,fn):
    start=time.monotonic()
    try:
        details=fn()
        row={"name":name,"passed":True,"details":details}
    except Exception as exc:
        row={"name":name,"passed":False,"error":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    row["seconds"]=round(time.monotonic()-start,6);GROUPS.append(row)
    print(json.dumps({"group":name,"passed":row["passed"]}),flush=True)

try:
    group("Real CLI selected-course pagination and exact report",cli_success)
    group("Existing files command continuity",legacy_control)
    if MODE=="candidate":
        for name,fn in [("Input validation before effects",admission),("Exact model rows and missing-name semantics",exact_model),
                        ("Literal and Unicode matching",literals),("Original read exception identity",transport_identity),
                        ("Whole schema refusal",schema),("Inclusive row budgets",row_limits),
                        ("Combined strict UTF8 byte budget",byte_limits),("CLI argument admission before constructor",cli_invalid)]:
            group(name,fn)
        for scenario in ("first_auth","late_http","late_nonlist","late_json","foreign_link","cycle","oversized"):
            group("CLI whole-result refusal: "+scenario,lambda scenario=scenario:cli_error(scenario))
        group("Deterministic CLI bytes",determinism)
finally:
    SERVER.close()
    after=source_pins()
    preserved=after==BEFORE
    receipt={"schema":"hamon.canvas.file-search.independent-receiving.v1",
      "at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"mode":MODE,"source":str(SOURCE),
      "runtime":sys.version,"python":sys.executable,"oracle_sha256":sha(pathlib.Path(__file__).read_bytes()),
      "child_driver_sha256":sha((ROOT/"cli-child.py").read_bytes()),
      "contract_sha256":sha((ROOT/"contract-v2.md").read_bytes()),
      "groups":GROUPS,"passed":sum(x["passed"] for x in GROUPS),"failed":sum(not x["passed"] for x in GROUPS),
      "invocations":INVOCATIONS,"source_pins":BEFORE,"source_unchanged":preserved,
      "owned_listener_closed":True,"parent_network_rejections":PARENT_BLOCKED,"live_Canvas_browser_model_or_account":False,
      "socket_policy":"Child real CLI execution permits only exact private loopback fixture port; DNS/connect rejections are receiving failures",
      "state":"accepted" if MODE=="candidate" and all(x["passed"] for x in GROUPS) and preserved and not PARENT_BLOCKED else
        "baseline_feature_absent_healthy_existing_control" if MODE=="baseline" and len(GROUPS)==2 and not GROUPS[0]["passed"] and GROUPS[1]["passed"] and preserved else "not_accepted"}
    (OUT/"receipt.json").write_bytes(jbytes(receipt))
    print(json.dumps({"receipt":str(OUT/"receipt.json"),"sha256":sha((OUT/"receipt.json").read_bytes()),
                     "state":receipt["state"],"passed":receipt["passed"],"failed":receipt["failed"],
                     "source_unchanged":preserved}),flush=True)
raise SystemExit(0 if receipt["state"] in ("accepted","baseline_feature_absent_healthy_existing_control") else 1)
