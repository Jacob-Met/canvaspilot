"""Actual public MCP/CLI composition on the unchanged read-only broker Handler."""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

parser=argparse.ArgumentParser()
parser.add_argument("--source",type=Path,required=True)
parser.add_argument("--manifest",type=Path,required=True)
parser.add_argument("--output",type=Path,required=True)
args=parser.parse_args()
source=args.source.resolve()
output=args.output.resolve()
output.mkdir(parents=True,exist_ok=False)
manifest=json.loads(args.manifest.read_text())
def verify():
    for row in manifest["files"]:
        assert hashlib.sha256((source/row["path"]).read_bytes()).hexdigest()==row["sha256"],row["path"]
verify()
for name in ("CANVAS_API_TOKEN","HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","NO_PROXY","http_proxy","https_proxy","all_proxy","no_proxy"):
    os.environ.pop(name,None)
os.environ.update(CANVAS_BASE_URL="https://canvas.fixture.invalid",CANVAS_PROFILE=str(output/"unused-profile"),CANVAS_SESSION_PORT="0",PYTHONPATH=str(source/"src"),PYTHONDONTWRITEBYTECODE="1")
sys.path[:0]=[str(source/"src"),str(source/"tests")]
from folder_http_fixture import FolderHTTPFixture, FolderBrokerFixture
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

metadata=FolderHTTPFixture()
metadata.overrides.update({
    "/api/v1/courses":(200,[{"id":42,"name":"Synthetic course 42"},{"id":77,"name":"Synthetic course 77"}]),
    "/api/v1/courses/42/assignments":(200,[
        {"id":4201,"name":"Later 42","due_at":"2026-11-20T12:00:00Z"},
        {"id":4202,"name":"Nearest 42","due_at":"2026-11-10T12:00:00Z"},
    ]),
    "/api/v1/courses/77/assignments":(200,[{"id":7701,"name":"Nearest overall","due_at":"2026-11-01T12:00:00Z"}]),
    "/api/v1/courses/42/modules":(200,[{"id":7,"name":"Synthetic module","items_count":2,"state":"locked","items_url":"https://must-not-follow.invalid/items"}]),
    "/api/v1/courses/42/modules/7/items":(200,[{"id":7101,"title":"Read instructions","type":"Page"},{"id":7102,"title":"Preparation","type":"Quiz"}]),
})
broker=FolderBrokerFixture(metadata)
os.environ.update(CANVAS_SESSION_PORT=str(broker.server.server_port),HTTP_PROXY=metadata.url,HTTPS_PROXY=metadata.url,ALL_PROXY=metadata.url,NO_PROXY="[::1]")
actions=[]
def record(name,**detail):
    actions.append({"name":name,"passed":True,**detail})
def decode(result):
    wire=result.model_dump(by_alias=True)
    text="".join(x["text"] for x in wire["content"] if x["type"]=="text")
    return wire.get("isError",False),text
async def mcp_journey():
    params=StdioServerParameters(command=sys.executable,args=["-m","canvaspilot.cli","mcp"],env=dict(os.environ))
    with (output/"mcp-stderr.log").open("w") as errors:
        async with stdio_client(params,errlog=errors) as (read,write),ClientSession(read,write,read_timeout_seconds=10) as session:
            await session.initialize()
            catalog={x.name:x.model_dump(by_alias=True) for x in (await session.list_tools()).tools}
            assert catalog["canvas_browse_files"]["inputSchema"]["properties"]["per_page"]["type"]=="integer"
            assert catalog["canvas_sync_summary"]["inputSchema"]["properties"]["limit_courses"]["exclusiveMinimum"]==0
            assert catalog["canvas_browse_files"]["annotations"]["readOnlyHint"] is True
            failed,text=decode(await session.call_tool("canvas_list_modules",{"course_id":"42","detail":"full"}))
            modules=json.loads(text)
            assert not failed and [x["id"] for x in modules[0]["items"]]==[7101,7102]
            assert modules[0]["state"]=="locked"
            record("mcp_module_items_fallback",item_ids=[7101,7102])
            failed,text=decode(await session.call_tool("canvas_sync_summary",{"limit_courses":2,"limit_assignments_per_course":1}))
            sync=json.loads(text)
            assert not failed and [x["id"] for x in sync["upcoming_assignments"]]==[7701,4202]
            assert sync["course_summaries"][0]["assignments_omitted"]==1
            record("mcp_sync_deadlines_and_counts",assignment_ids=[7701,4202])
            failed,text=decode(await session.call_tool("canvas_browse_files",{"course_id":"42","per_page":2}))
            root=json.loads(text)
            assert not failed and [x["id"] for x in root["folders"]["items"]]==[110,120]
            failed,text=decode(await session.call_tool("canvas_browse_files",{"course_id":"42","folder_id":"110","files_page":2,"per_page":2}))
            selected=json.loads(text)
            assert not failed and [x["id"] for x in selected["files"]["items"]]==[2003]
            assert selected["files"]["has_more"] is None
            assert all("url" not in x and "body" not in x for x in selected["files"]["items"])
            record("mcp_folder_root_selection_and_page",folder_id=110,file_ids=[2003])
            before=len(broker.jobs)
            for name,arguments in (("canvas_sync_summary",{"limit_courses":True}),("canvas_browse_files",{"course_id":"42","per_page":True})):
                failed,_=decode(await session.call_tool(name,arguments))
                assert failed
            assert len(broker.jobs)==before
            record("mcp_both_strict_argument_schemas_refuse_before_io")
def cli(arguments,name):
    child=subprocess.run([sys.executable,"-m","canvaspilot.cli",*arguments],capture_output=True,text=True,env=dict(os.environ),timeout=20)
    (output/(name+".stdout.json")).write_text(child.stdout)
    (output/(name+".stderr.log")).write_text(child.stderr)
    assert child.returncode==0,child.stderr
    return json.loads(child.stdout)
try:
    asyncio.run(mcp_journey())
    sync=cli(["sync","--limit-courses","2","--limit-assignments-per-course","1"],"cli-sync")
    assert [x["id"] for x in sync["upcoming_assignments"]]==[7701,4202]
    assert sync["course_summaries"][0]["assignments_omitted"]==1
    record("public_cli_sync_preserves_current_deadline_selection",assignment_ids=[7701,4202])
    selected=cli(["browse-files","42","--folder-id","110","--files-page","2","--per-page","2"],"cli-folder")
    assert [x["id"] for x in selected["files"]["items"]]==[2003]
    record("public_cli_folder_navigation_coexists",file_ids=[2003])
    assert metadata.requests==[]
    assert all(x["method"]=="GET" and x["body"] is None for x in broker.jobs)
    assert not (output/"unused-profile").exists()
finally:
    broker.close()
    metadata.close()
verify()
receipt={"schema":"canvaspilot.folder-current-public-composition.v1","received_at":datetime.now(timezone.utc).isoformat(),"source":str(source),"parent":manifest["parent"],"source_tree":manifest["source_tree"],"source_files_verified":len(manifest["files"]),"source_unchanged":True,"python":sys.version,"actions":actions,"broker_jobs":broker.jobs,"proxy_requests":metadata.requests,"read_only_handler":True,"transport":"actual CLI subprocess and MCP stdio -> CanvasAPI/CanvasClient -> actual loopback broker Handler; authored browser-queue responses only","proxy_environment":"HTTP/HTTPS/ALL_PROXY point to own loopback metadata trap; NO_PROXY=[::1]","script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(output/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"passed":True,"actions":len(actions),"broker_jobs":len(broker.jobs),"proxy_requests":len(metadata.requests),"source_tree":manifest["source_tree"]}))
