from pathlib import Path
import hashlib,json,subprocess,tarfile,io,datetime,os
root=Path("/home/jacob/hamon-ultra-2d2d276b-canvas-file-search-independent")
source=Path("/home/jacob/hamon-ultra-2d2d276b-canvas-file-search/source")
head="94fb3a02a06b235dc46e25dab5c03012f202eec9";base="56a72a2e2cee5ec04671d12ebe5bc2484afb8026"
tree="721a263dedbb1ad8a2d230eed536cbad35dbe89a"
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(["git","-C",str(source),*a])
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+"\n").encode()
assert not (root/"candidate-source").exists() and not (root/"candidate-run").exists()
freeze=json.loads((root/"oracle-freeze.json").read_bytes())
assert sha((root/"oracle-freeze.json").read_bytes())=="f996d9430ea036fbbeffabd780c97c3dc60ffa6c88b5b369e1a8ed3790193cf6"
for name,pin in freeze["manifest"].items():
 data=(root/name).read_bytes();assert len(data)==pin["bytes"] and sha(data)==pin["sha256"]
assert git("rev-parse",head+"^{tree}").decode().strip()==tree
assert git("rev-parse",head+"^").decode().strip()==base
changed=git("diff","--name-only",base,head).decode().splitlines()
assert changed==["README.md","docs/file-search.md","src/canvaspilot/cli.py","src/canvaspilot/file_search.py","tests/test_file_search.py","tests/test_file_search_cli.py"],changed
alltrees={}
for rev in (base,head):
 leaves={}
 for row in git("ls-tree","-r","-z",rev).split(b"\0"):
  if not row:continue
  meta,name=row.split(b"\t",1);mode,kind,blob=meta.decode().split();leaves[name.decode()]={"mode":mode,"type":kind,"blob":blob}
 alltrees[rev]=leaves
assert len(alltrees[base])==1616 and len(alltrees[head])==1620
preserved=[p for p in alltrees[base] if p not in changed and alltrees[base][p]==alltrees[head].get(p)]
assert len(preserved)==1614
rawfreeze=(source.parent/"source-freeze-01/receipt.json").read_bytes()
assert sha(rawfreeze)=="c7c8fc4478aa061621ef0f2be1df05fed1a42242e579527717031ee82baf68d5"
archive=git("archive","--format=tar",head,"src/canvaspilot","pyproject.toml")
with tarfile.open(fileobj=io.BytesIO(archive),mode="r:") as tf:
 for m in tf.getmembers():
  if m.isdir():continue
  assert m.isfile() and not m.name.startswith("/") and ".." not in Path(m.name).parts
  data=tf.extractfile(m).read()
  expected=alltrees[head][m.name]
  assert hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==expected["blob"]
  put(root/"candidate-source"/m.name,data)
pins={str(p.relative_to(root/"candidate-source")):{"bytes":p.stat().st_size,"sha256":sha(p.read_bytes()),"git_blob":alltrees[head][str(p.relative_to(root/"candidate-source"))]["blob"]}
      for p in sorted((root/"candidate-source").rglob("*")) if p.is_file()}
baseline=json.loads((root/"intake.json").read_bytes())["source_pins"]
for path,pin in baseline.items():
 if path!="src/canvaspilot/cli.py":assert pins[path]["sha256"]==pin["sha256"],path
receipt={"schema":"hamon.canvas.file-search.independent-candidate-intake.v1","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"source":str(source),"head":head,"tree":tree,"base":base,"changed_paths":changed,"baseline_leaves":1616,"candidate_leaves":1620,
"unrelated_base_leaves_preserved":len(preserved),"runtime_package":str(root/"candidate-source"),"runtime_pins":pins,
"oracle_frozen_before_candidate_exposure":True,"oracle_freeze_sha256":sha((root/"oracle-freeze.json").read_bytes()),
"only_changed_existing_runtime_file":"src/canvaspilot/cli.py","new_runtime_module":"src/canvaspilot/file_search.py"}
put(root/"candidate-intake.json",enc(receipt));put(root/"candidate-author-freeze.json",rawfreeze)
put(root/"candidate-intake-controller.py",Path(__file__).read_bytes())
runtime="/home/jacob/canvaspilot-enrollments-env-65ae877160f6/bin/python"
args=[runtime,"-B",str(root/"receive.py"),"candidate",str(root/"candidate-source"),str(root/"candidate-run")]
intent={"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"pid":os.getpid(),"argv":args,"head":head,"tree":tree,"intake_sha256":sha((root/"candidate-intake.json").read_bytes()),"oracle_sha256":sha((root/"receive.py").read_bytes()),"state":"one_independent_receiving_invocation_prepared"}
put(root/"candidate-run-intent.json",enc(intent))
print(json.dumps({"intake":str(root/"candidate-intake.json"),"sha256":intent["intake_sha256"],"runtime_files":len(pins),"unrelated_base_leaves_preserved":len(preserved),"oracle_unchanged":True}),flush=True)
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
os.execv(runtime,args)
