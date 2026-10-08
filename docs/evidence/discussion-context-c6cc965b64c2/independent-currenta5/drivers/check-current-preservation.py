
import ast,hashlib,json,pathlib
current=pathlib.Path("/dev/shm/c6cc965b64c2-canvas-discussion/candidate-currenta5")
prior=pathlib.Path("/dev/shm/c6cc965b64c2-canvas-discussion/candidate-current39d")
proof_path=pathlib.Path("/dev/shm/c6cc965b64c2-canvas-discussion/qualification/currenta5-composition.json")
pbytes=proof_path.read_bytes()
assert hashlib.sha256(pbytes).hexdigest()=="4d873fbd07fc0f07e8a349e350d6d257b210d14430f05c8b3292f6d255f031cd"
seams=json.loads(pbytes)["seam_changes"]
primary=json.loads("{\"src/canvaspilot/api.py\":\"73e47f1354fc5bab44e9f030c5bf5d29c12d065f\",\"src/canvaspilot/cli.py\":\"545ec52f31b694a351e9a41a68e52a34c49db532\",\"src/canvaspilot/mcp_server.py\":\"a35800c496fcab6f28dd11fca0fedfc944be46c7\",\"src/canvaspilot/bundle.py\":\"23badab9d8ea96b4ed30fb2b5f32f773c910c7f9\",\"README.md\":\"4a61c3a5c4b219ec3aaa6cf3b64f19338856ca1f\"}")
out={}
for path,expected in primary.items():
 text=(current/path).read_text();recovered=text
 for s in reversed([s for s in seams if s["path"]==path]):
  if s["kind"]=="insert":
   assert recovered.count(s["inserted"])==1,path
   recovered=recovered.replace(s["inserted"],"",1)
  else:
   assert s["kind"] in ["replace","current owner count plus one"],s
   assert recovered.count(s["after"])==1,path
   recovered=recovered.replace(s["after"],s["before"],1)
 b=recovered.encode()
 blob=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
 assert blob==expected,(path,blob,expected)
 out[path]={"candidate_sha256":hashlib.sha256(text.encode()).hexdigest(),"recovered_current_main_blob":blob,"base_bytes_recovered_exactly":True}
def defs(text):
 return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(text)) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
function_matches={}
for path,names in {
 "src/canvaspilot/api.py":["get_discussion","discussion_thread","__init__","close"],
 "src/canvaspilot/mcp_server.py":["_get_api","canvas_discussion_thread","canvas_get_discussion","main"],
}.items():
 a,b=defs((prior/path).read_text()),defs((current/path).read_text())
 assert all(a[n]==b[n] for n in names),(path,names)
 function_matches[path]=names
unchanged=[]
for path in ["src/canvaspilot/discussion_thread.py","src/canvaspilot/client.py","src/canvaspilot/session_broker.py","src/canvaspilot/__init__.py","pyproject.toml",".github/workflows/ci.yml","tests/test_discussion_thread.py","tests/test_discussion_thread_native.py","docs/DISCUSSIONS.md"]:
 a=(prior/path).read_bytes();b=(current/path).read_bytes()
 assert a==b,path
 unchanged.append({"path":path,"sha256":hashlib.sha256(b).hexdigest()})
print(json.dumps({"schema":"canvas-independent-currenta5-composition-v1","base_commit":"a5ce672e5b3580c1f52e13c49eefee830f11346c","base_tree":"0661a7005e577864cb87bc41e0e715409c92ee76","accepted_prior_base":"39d835c8becb04d81b65c90d1491d2d3a2727ffe","source_root":str(current),"recovered_owned_files":out,"unchanged_relevant_function_asts":function_matches,"unchanged_source_files":unchanged}))
