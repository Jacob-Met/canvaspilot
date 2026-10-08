import argparse, hashlib, importlib.metadata, json, platform, sys
from pathlib import Path
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description="Verify both pinned source trees and record the receiving runtime.")
parser.add_argument("--output",type=Path,default=root/"actual-runtime-receipt.json")
args=parser.parse_args()
verified=[]
for kind in ("head","base"):
    manifest=json.loads((root/(kind+"-source-manifest.json")).read_text())
    rows=[]
    for item in manifest["files"]:
        data=(root/kind/item["path"]).read_bytes()
        actual=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
        if actual != item["sha"]:
            raise RuntimeError("Source changed: "+kind+"/"+item["path"])
        rows.append({"path":item["path"],"git_blob":actual,"sha256":hashlib.sha256(data).hexdigest()})
    verified.append({"source":kind,"files":rows})
receipt={"schema":"canvaspilot.proxy-receiving-runtime.v1","python":sys.version,"platform":platform.platform(),"dependencies":dict(sorted((d.metadata["Name"],d.version) for d in importlib.metadata.distributions())),"verified_source_sets":verified,"scripts_sha256":{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ("native_broker_fixture.py","review_broker_proxy.py")}}
args.output.write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"source_sets":len(verified),"verified_files":sum(len(s["files"]) for s in verified),"python":receipt["python"],"httpx":receipt["dependencies"]["httpx"],"mcp":receipt["dependencies"]["mcp"]}))
