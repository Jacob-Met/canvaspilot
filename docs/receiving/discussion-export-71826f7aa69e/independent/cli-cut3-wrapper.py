import pathlib,subprocess,hashlib,json,os,datetime,time
root=pathlib.Path("/home/jacob/hamon-canvas-discussion-independent-71826f7aa69e")
source=pathlib.Path("/home/jacob/hamon-canvas-discussion-export-71826f7aa69e/source")
required={"receiver-v4.py":"ef22e51d793115120e28d878a4c90e8a0a6d9e89bc335d21ba818e34d5fc02bb","fixtures-v1.json":"458f8d8b3a6fae5da5358fa1f83ed8c3c9b095abb2781e103260082197dbb435"}
for name,digest in required.items(): assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
for name,digest in {"discussion_export.py":"95e8d7078462a60d4d3f1c4bd46b302bb69598563675f44d5d0326edf69d8cde","cli.py":"11215a327e206cef6326c2cfa06feb8e68107dafda0aa835618d83dceac5563f"}.items():
 assert hashlib.sha256((source/"src/canvaspilot"/name).read_bytes()).hexdigest()==digest
assert not os.path.lexists(root/"cli-cut3")
for name in ("cli-cut3-launch.json","cli-cut3.stdout.log","cli-cut3.stderr.log"):assert not os.path.lexists(root/name)
cmd=["/home/jacob/canvaspilot-announcements-3dcb83a1/.venv/bin/python","-B",str(root/"receiver-v4.py"),"--source",str(source),"--fixtures",str(root/"fixtures-v1.json"),"--out",str(root/"cli-cut3"),"--accepted-full",str(root/"cli-cut2")]
receipt={"started":datetime.datetime.now(datetime.timezone.utc).isoformat(),"command":cmd,"adopted_cases":1,"new_cases_planned":13,"product_changed":False,"state":"running"}
(root/"cli-cut3-launch.json").write_text(json.dumps(receipt,indent=2)+"\n")
try:
 with (root/"cli-cut3.stdout.log").open("xb") as so,(root/"cli-cut3.stderr.log").open("xb") as se:
  cp=subprocess.run(cmd,stdout=so,stderr=se,timeout=1800)
 receipt["returncode"]=cp.returncode;receipt["state"]="finished"
except subprocess.TimeoutExpired:
 receipt["state"]="outer_timeout_child_killed_reaped";receipt["returncode"]=None
finally:
 receipt["finished"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
 for name in ("cli-cut3.stdout.log","cli-cut3.stderr.log"):
  b=(root/name).read_bytes();receipt[name]={"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
 (root/"cli-cut3-launch.json").write_text(json.dumps(receipt,indent=2)+"\n")
 print(json.dumps(receipt),flush=True)
