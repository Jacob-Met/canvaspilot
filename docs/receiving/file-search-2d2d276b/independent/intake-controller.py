from pathlib import Path
import subprocess,hashlib,json,tarfile,io,datetime,os
out=Path("/home/jacob/hamon-ultra-2d2d276b-canvas-file-search-independent")
source=Path("/home/jacob/hamon-ultra-2d2d276b-canvas-file-search/source")
contract=source.parent/"contract-v2.md"
rev="56a72a2e2cee5ec04671d12ebe5bc2484afb8026"
tree="a07c3e941219ff80968e1ff20528a63541bb7400"
sha=lambda b:hashlib.sha256(b).hexdigest()
def enc(d):return (json.dumps(d,ensure_ascii=False,indent=2)+"\n").encode()
def put(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
def git(*args):return subprocess.check_output(["git","-C",str(source),*args])
assert source.stat().st_uid==os.getuid()==0,"Use actual source owner; do not change safe.directory"
assert not out.exists(),"Existing independent namespace requires reconciliation"
raw_contract=contract.read_bytes()
assert sha(raw_contract)=="34c12b41e1f9824a1b7da1f5173bf3f5efa8f02094f560f16b35fd02a4479e57"
assert git("rev-parse",rev+"^{tree}").decode().strip()==tree
rows=git("ls-tree","-r","-l","-z",rev,"src/canvaspilot","pyproject.toml").split(b"\0")
items=[]
for row in rows:
 if not row:continue
 left,name=row.split(b"\t",1); mode,kind,blob,size=left.decode().split()
 assert kind=="blob" and mode in ("100644","100755")
 items.append({"path":name.decode(),"mode":mode,"git_blob":blob,"bytes":int(size)})
assert sum(x["bytes"] for x in items)<12*1024*1024
archive=git("archive","--format=tar",rev,"src/canvaspilot","pyproject.toml")
out.mkdir()
with tarfile.open(fileobj=io.BytesIO(archive),mode="r:") as tf:
 for m in tf.getmembers():
  if m.isdir():continue
  assert m.isfile() and not m.name.startswith("/") and ".." not in Path(m.name).parts
  put(out/"baseline"/m.name,tf.extractfile(m).read())
pins={}
for item in items:
 data=(out/"baseline"/item["path"]).read_bytes()
 assert len(data)==item["bytes"]
 assert hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==item["git_blob"]
 pins[item["path"]]={**item,"sha256":sha(data)}
put(out/"contract-v2.md",raw_contract)
receipt={"schema":"hamon.canvas.file-search.independent-intake.v1","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"reviewer":"hamon-ultra-20261008-1657-2d2d276b/root","source":str(source),"base":rev,"tree":tree,"contract_sha256":sha(raw_contract),"baseline":str(out/"baseline"),"runtime":"/home/jacob/canvaspilot-enrollments-env-65ae877160f6/bin/python","candidate_read":False,"frozen_runtime_files":len(pins),"runtime_bytes":sum(x["bytes"] for x in items),"source_pins":pins,"prior_read_attempt":{"kind":"read-only git dubious-ownership refusal","pid":3359003,"effects":0,"resolved":"Re-read as existing root source owner through established sudo; no permission or safe.directory changes"}}
put(out/"intake.json",enc(receipt));put(out/"intake-controller.py",Path(__file__).read_bytes())
claim={"schema":"hamon.external_contribution.v1","worker_id":"hamon-ultra-20261008-1657-2d2d276b/root","actor":"chatgpt:2d2d276bbccc:root","state":"independent_canvas_file_search_receiving_reserved_before_candidate_exposure","repository":"Jacob-Met/canvaspilot","base":rev,"tree":tree,"owned_root":str(out),"author_claim":"/srv/hamon-estate/coord/hamon-ultra-2d2d276b-canvas-file-search.json","contract":str(out/"contract-v2.md"),"contract_sha256":sha(raw_contract),"source_candidate_read":False,"scope":"Independent model/CLI/real loopback client receiving of exact frozen file-search contract; no author source edits","native_goal_or_lease_claimed":False,"boundaries":["No LA7 calls","No GitHub Actions or source publication in this receiving phase","No real Canvas, account, browser, model, credential or existing profile changes","Private loopback server, source copy, HOME/profile/tmp only","Preserve prior source and failed attempts"]}
put(Path("/srv/hamon-estate/coord/hamon-ultra-2d2d276b-canvas-file-search-independent.json"),enc(claim))
print(json.dumps({"root":str(out),"intake_sha256":sha((out/"intake.json").read_bytes()),"files":len(pins),"bytes":receipt["runtime_bytes"],"candidate_read":False,"contract_sha256":sha(raw_contract)}))
