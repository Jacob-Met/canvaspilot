import ast,hashlib,json
from pathlib import Path
root=Path("/dev/shm/hamon-31a349052b90/canvas-assignment-submission-31a349052b90")
own=root.parent/"engine-canvas-review"
old=root/"current-base"; current=root/"parent-79a2"; prior=root/"publish-candidate"; final=root/"publish-79a2"
def pin(p):
 b=p.read_bytes(); return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()}
m=json.loads((root/"integration/parent-79a2-materialization.json").read_text())
for i in m["source_files"]:
 p=pin(current/i["path"]); assert all(p[k]==i[k] for k in p),i["path"]
features=json.loads((own/"source-verification.json").read_text())["final_source_files"]
for i in features:
 path=i["path"]; assert (prior/path).read_bytes()==(final/path).read_bytes(); p=pin(final/path); assert all(p[k]==i[k] for k in p)
client="src/canvaspilot/client.py"; broker="src/canvaspilot/session_broker.py"; cli="src/canvaspilot/cli.py"
assert (old/client).read_bytes()==(final/client).read_bytes()
assert pin(final/client)["git_blob"]=="1db4b1135305f7e410025ae7937f9a6cd349f020"
def top(s,n):
 return ast.get_source_segment(s,next(x for x in ast.parse(s).body if getattr(x,"name",None)==n))
a=(old/broker).read_text(); b=(final/broker).read_text(); added='                    "provider_origin_checks": True,\n'
assert (current/broker).read_bytes()==(final/broker).read_bytes()
assert pin(final/broker)["git_blob"]=="cc706d5860489ec37cb2cf7f0b1cb4eee33b664f"
assert top(b,"Handler").count(added)==1
assert top(b,"Handler").replace(added,"")==top(a,"Handler")
assert top(b,"_call")==top(a,"_call")
assert top(b,"_BrokerState")==top(a,"_BrokerState")
c=(final/client).read_text(); assert "provider_origin_checks" not in c
assert 'if health:' in c and 'health.get("link_pagination") is not True' in c and 'origin=health.get("base_url") or self.base_url' in c
a=(old/cli).read_text(); b=(final/cli).read_text()
assert (current/cli).read_bytes()==(final/cli).read_bytes()
assert pin(final/cli)["git_blob"]=="9b8eec6ea177d0fe69e3cb7776af185d2e7ad4a5"
imports="            from canvaspilot.client import CanvasAuthError, CanvasPaginationError\n"
catch="            except (CanvasAuthError, CanvasPaginationError, httpx.HTTPError, ValueError, TypeError, OSError) as error:\n"
assert b.count(imports)==b.count(catch)==1
assert b.replace(imports,imports.replace(", CanvasPaginationError","")).replace(catch,catch.replace(", CanvasPaginationError",""))==a
assert pin(own/"independent-session-receiving.tar.gz")["sha256"]=="792e183779aa81f2927d28f27e53d0f811ca1970a4f82a79f11314e68b2e1dbe"
r={"reviewer":"/root/engine_execution","accepted":True,"review_kind":"Independent static source binding; historical native attribution preserved","parent":m["parent"],"parent_tree":m["tree"],"parent_native_inputs_verified":len(m["source_files"]),"feature_files":features,"unchanged_client":pin(final/client),"current_broker":pin(final/broker),"current_cli":pin(final/cli),"independent_remote_blob_reads":{broker:"cc706d5860489ec37cb2cf7f0b1cb4eee33b664f",cli:"9b8eec6ea177d0fe69e3cb7776af185d2e7ad4a5"},"handler_exact_except_one_added_health_boolean":True,"broker_call_and_state_definitions_byte_exact":True,"client_does_not_read_new_health_key":True,"cli_exact_except_export_calendar_import_and_exception_tuple":True,"six_feature_blobs_unchanged":True,"historical_native_parent":"ca2318fe7c56d2e4ec1b363ff8a945ab78bf4a0c","historical_native_cli_processes":4,"additional_native_executions":0,"native_repeat_needed":False,"reason":"The exercised assignment projection, pagination, Handler POST/serialization and CLI branch remain unchanged. The only exercised-source delta adds a health key ignored by the unchanged client. New provider-origin enforcement lives beyond the explicitly synthetic browser-terminal _call seam; repeating that receiver would not qualify changed browser routing.","limits":["No native run is attributed to parent79a2 by this static receipt.","Browser/provider-origin behavior belongs to PR45 owner receiving and hosted gates.","No whole-broker or whole-CLI identity claim.","Ordinary published-head CI and final-parent integration remain with the owner."],"historical_appendix_sha256":"792e183779aa81f2927d28f27e53d0f811ca1970a4f82a79f11314e68b2e1dbe"}
print(json.dumps(r,indent=2))
