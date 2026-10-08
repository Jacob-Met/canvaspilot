"""Repeat only the interrupted current-source checks; preserve the first run."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"source"
FIRST=ROOT/"evidence/announcements-receiving"
OUT=FIRST/"replay"
OUT.mkdir()
record={"utc":datetime.datetime.now(datetime.UTC).isoformat(),
        "reason":"Prior full suite transcript and summary were incomplete during observed filesystem exhaustion; Ruff had not run.",
        "initial_receipt_sha256":hashlib.sha256((FIRST/"qualification.json").read_bytes()).hexdigest(),
        "free_bytes_before":shutil.disk_usage(ROOT).free,"runs":[]}
assert record["free_bytes_before"]>512*1024*1024
prior=json.loads((FIRST/"qualification.json").read_text())
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=SOURCE,text=True).strip()==prior["source_commit"]
record["source_commit"]=prior["source_commit"]
record["source_tree"]=prior["source_tree"]
record["source_sha256"]=prior["source_sha256"]
for name,digest in record["source_sha256"].items():
 assert hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()==digest
package=Path(prior["installed_origin"]["package_path"])
actual={str(p.relative_to(package.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in package.rglob("*") if p.is_file()}
assert actual==prior["installed_origin"]["package_sha256"]
record["installed_package_sha256"]=actual
record["wheel_sha256"]=prior["wheel"]["sha256"]
record["installed_source_leaf_count"]=len(actual)
env={k:v for k,v in os.environ.items() if not k.startswith(("CANVAS_","CANVASPILOT_","PYTEST_","PIP_")) and k not in ("PYTHONPATH","VIRTUAL_ENV")}
env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONNOUSERSITE="1",TMPDIR=str(ROOT/"temp"),NO_PROXY="127.0.0.1,localhost")
def save():
 temp=OUT/"qualification.tmp"
 temp.write_text(json.dumps(record,indent=2)+"\n")
 os.replace(temp,OUT/"qualification.json")
def run(name,command):
 with (OUT/(name+".stdout")).open("w") as stdout,(OUT/(name+".stderr")).open("w") as stderr:
  try:
   result=subprocess.run(command,cwd=SOURCE,env=env,stdout=stdout,stderr=stderr,timeout=300)
   entry={"name":name,"command":command,"exit_code":result.returncode}
  except subprocess.TimeoutExpired:
   entry={"name":name,"command":command,"timeout_seconds":300}
 record["runs"].append(entry)
 save()
 print(json.dumps(entry),flush=True)
 print((OUT/(name+".stdout")).read_text()[-5000:],flush=True)
 print((OUT/(name+".stderr")).read_text()[-2000:],flush=True)
 return entry.get("exit_code")==0
save()
suite=run("full-suite",[str(ROOT/"venv/bin/python"),"-B","-m","pytest","-q","-p","no:cacheprovider","--junitxml",str(OUT/"full-suite.xml")])
lint=run("ruff",[str(ROOT/"venv/bin/python"),"-B","-m","ruff","check","--no-cache","src","tests","scripts"])
assert record["source_sha256"]=={n:hashlib.sha256((SOURCE/n).read_bytes()).hexdigest() for n in record["source_sha256"]}
record["source_unchanged"]=True
record["free_bytes_after"]=shutil.disk_usage(ROOT).free
record["qualified"]=suite and lint
save()
print(json.dumps({"qualified":record["qualified"],"receipt_sha256":hashlib.sha256((OUT/"qualification.json").read_bytes()).hexdigest()}),flush=True)
sys.exit(0 if suite and lint else 1)
