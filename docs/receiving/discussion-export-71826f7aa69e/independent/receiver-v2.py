"""Independent black-box discussion export receiving; authored before candidate."""
from __future__ import annotations
import argparse, base64, copy, hashlib, json, os, pathlib, subprocess, sys, threading, time
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

def sha(data): return hashlib.sha256(data).hexdigest()
def gblob(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def fingerprint(path):
    st=path.lstat()
    return {"inode":st.st_ino,"device":st.st_dev,"mode":st.st_mode,"mtime_ns":st.st_mtime_ns,
            "bytes":path.read_bytes().hex() if path.is_file() and not path.is_symlink() else None,
            "link":os.readlink(path) if path.is_symlink() else None}
class Document(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags=[]; self.downloads=[]; self.ids=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs); self.tags.append((tag,a))
        if a.get("id"): self.ids.append(a["id"])
        if tag=="a" and a.get("download"): self.downloads.append(a)
def decode_document(content):
    doc=Document(); doc.feed(content.decode("utf-8")); doc.close()
    links=[a for a in doc.downloads if a.get("id")=="download-report"]
    assert len(links)==1, "One explicit normalized-report download"
    link=links[0]
    assert link["download"]=="discussion-thread.json"
    prefix="data:application/json;base64,"
    assert link["href"].startswith(prefix)
    payload=base64.b64decode(link["href"][len(prefix):],validate=True)
    assert len(doc.ids)==len(set(doc.ids)), "Generated document IDs must be unique"
    forbidden={"script","iframe","object","embed","form","img","link","base","svg","audio","video"}
    assert not [tag for tag,a in doc.tags if tag in forbidden], "Passive HTML only"
    for tag,a in doc.tags:
        assert not any(k.lower().startswith("on") for k in a), "No event handler attributes"
        assert "src" not in a and "srcset" not in a, "No remote resource source"
        if "href" in a:
            assert a["href"].startswith("#") or a is link or a["href"]==link["href"], "Only internal/local-download links"
    return json.loads(payload), payload

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True,type=pathlib.Path)
    parser.add_argument("--fixtures",required=True,type=pathlib.Path)
    parser.add_argument("--out",required=True,type=pathlib.Path)
    a=parser.parse_args()
    source=a.source.resolve(); out=a.out.resolve()
    free=os.statvfs(out.parent).f_bavail*os.statvfs(out.parent).f_frsize
    if free<32*1024*1024: raise SystemExit("Need32MiB free before independent receiving")
    out.mkdir(exist_ok=False)
    fixtures=json.loads(a.fixtures.read_text())
    sys.path.insert(0,str(source/"src"))
    from canvaspilot.discussion_thread import build_discussion_thread
    report_file=source/"src/canvaspilot/discussion_thread.py"
    assert gblob(report_file.read_bytes())=="2ed658fcf5cee996a02115742935716f1d039e25"
    original=copy.deepcopy(fixtures)
    full=build_discussion_thread(fixtures["topic"],fixtures["view"])
    unread=build_discussion_thread(fixtures["topic"],fixtures["view"],unread_only=True)
    e=fixtures["expected"]
    assert [r["path"] for r in full["entries"]]==e["all_paths"]
    assert [r["entry"]["id"] for r in full["entries"]]==e["all_entry_ids"]
    assert [r["path"] for r in unread["entries"]]==e["unread_paths"]
    assert [r["path"] for r in unread["entries"] if r["context_only"]]==e["context_only_paths"]
    assert full["counts"]=={"observed_entries":8,"returned_entries":8,"known_unread_entries":2,"unknown_read_state_entries":2}
    assert unread["counts"]=={"observed_entries":8,"returned_entries":3,"known_unread_entries":2,"unknown_read_state_entries":2}
    assert full["unmatched_unread_entries"]==[999]
    assert full["entries"][1]["message_text"] is None and full["entries"][1]["author"] is None
    assert full["entries"][4]["author"] is None
    assert all(full["entries"][i]["read_state"]=="unknown" for i in (5,6))
    assert full["entries"][2]["author"]["id"]=="3"
    assert full["entries"][3]["parent_path"] is None and full["entries"][3]["entry"]["parent_id"]==101
    assert fixtures==original
    (out/"oracle-full.json").write_text(json.dumps(full,ensure_ascii=True,indent=2)+"\n")
    (out/"oracle-unread.json").write_text(json.dumps(unread,ensure_ascii=True,indent=2)+"\n")
    state={"fixture":copy.deepcopy(fixtures),"requests":[],"topic_status":200,"race":None}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            path=urlsplit(self.path).path
            state["requests"].append({"method":"GET","path":path,"query":urlsplit(self.path).query})
            topic="/api/v1/courses/42/discussion_topics/71"
            if path==topic:
                status=state["topic_status"]; data=state["fixture"]["topic"] if status==200 else {"error":"synthetic unavailable"}
            elif path==topic+"/view":
                status=200; data=state["fixture"]["view"]
                if state["race"]:
                    state["race"].write_bytes(b"RACE WINNER MUST SURVIVE")
                    state["race"]=None
            else:
                status=404; data={"error":"unexpected synthetic route"}
            body=json.dumps(data,ensure_ascii=True).encode()
            self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers()
            self.wfile.write(body)
        def forbidden(self):
            state["requests"].append({"method":self.command,"path":self.path})
            self.send_response(405); self.end_headers()
        do_POST=forbidden; do_PUT=forbidden; do_PATCH=forbidden; do_DELETE=forbidden
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    env=os.environ.copy()
    for key in ("CANVAS_BASE_URL","CANVAS_API_TOKEN","CANVAS_PROFILE_DIR","HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"):
        env.pop(key,None)
    env.update({"PYTHONPATH":str(source/"src"),"PYTHONDONTWRITEBYTECODE":"1","PYTHONNOUSERSITE":"1","NO_PROXY":"127.0.0.1,localhost"})
    records=[]
    names=("src/canvaspilot/discussion_thread.py","src/canvaspilot/api.py","src/canvaspilot/cli.py",
           "src/canvaspilot/discussion_export.py","src/canvaspilot/page_export.py","src/canvaspilot/client.py")
    pins={name:{"sha256":sha((source/name).read_bytes()),"git_blob":gblob((source/name).read_bytes())} for name in names}
    result={"schema":"canvaspilot.discussion-export.independent-cli.v1","state":"running","source":str(source),"python":sys.version,
            "started":time.time(),"source_before":pins,"cases":records,"browser_executed":False}
    def run(name,*,fixture=None,focus=False,expect=None,target=None,status=200,requests=2,race=False):
        state["fixture"]=copy.deepcopy(fixture or fixtures); state["topic_status"]=status; state["requests"]=[]
        dest=target or out/(name+".html"); state["race"]=dest if race else None
        cmd=[sys.executable,"-B","-m","canvaspilot.cli","export-discussion","42","71","--out",str(dest),
             "--base-url",f"http://127.0.0.1:{server.server_port}","--token","synthetic-owned-fixture"]
        if focus: cmd.append("--unread-only")
        cp=subprocess.run(cmd,cwd=source,env=env,capture_output=True,timeout=30)
        (out/(name+".stdout")).write_bytes(cp.stdout); (out/(name+".stderr")).write_bytes(cp.stderr)
        row={"case":name,"argv":cmd,"returncode":cp.returncode,"requests":copy.deepcopy(state["requests"]),
             "stdout_sha256":sha(cp.stdout),"stderr_sha256":sha(cp.stderr),"output":str(dest)}
        records.append(row)
        assert len(state["requests"])==requests,(name,state["requests"])
        assert all(x["method"]=="GET" and not x["query"] for x in state["requests"])
        if requests:
            assert state["requests"][0]["path"]=="/api/v1/courses/42/discussion_topics/71"
            if requests==2: assert state["requests"][1]["path"]=="/api/v1/courses/42/discussion_topics/71/view"
        if expect is None:
            assert cp.returncode!=0 and not cp.stdout.strip(),(name,cp.returncode,cp.stdout)
            assert not dest.exists() or target is not None or race
            row["accepted_refusal"]=True
        else:
            assert cp.returncode==0,(name,cp.stderr.decode(errors="replace"))
            metadata=json.loads(cp.stdout); assert metadata["ok"] is True
            content=dest.read_bytes(); decoded,payload=decode_document(content)
            assert decoded==expect, "Complete normalized report equality"
            assert metadata["html_bytes"]==len(content) and metadata["sha256"]==sha(content)
            assert metadata["json_bytes"]==len(payload) and metadata["json_sha256"]==sha(payload)
            assert metadata["course_id"]=="42" and metadata["topic_id"]=="71"
            assert metadata["selection"]==expect["selection"] and metadata["entries_included"]==len(expect["entries"])
            generated=datetime.fromisoformat(metadata["generated_at"].replace("Z","+00:00"))
            assert generated.tzinfo is not None, "Creation timestamp must identify its timezone"
            assert abs(generated.timestamp()-time.time())<120, "Creation timestamp is the local export event"
            row.update({"html_bytes":len(content),"html_sha256":sha(content),"json_bytes":len(payload),"json_sha256":sha(payload),"metadata":metadata})
        return dest
    try:
        run("full",expect=full)
        run("unread",focus=True,expect=unread)
        empty=copy.deepcopy(fixtures); empty["view"]["unread_entries"]=[]
        run("empty-unread",fixture=empty,focus=True,expect=build_discussion_thread(empty["topic"],empty["view"],unread_only=True))
        missing=copy.deepcopy(fixtures); del missing["view"]["unread_entries"]
        run("missing-unread-refused",fixture=missing,focus=True)
        ambiguous=copy.deepcopy(fixtures); ambiguous["view"]["unread_entries"]=[106]
        run("ambiguous-unread-refused",fixture=ambiguous,focus=True)
        malformed=copy.deepcopy(fixtures); malformed["view"]["view"]={"not":"a tree"}
        run("malformed-view-refused",fixture=malformed)
        run("topic-unavailable",status=503,requests=1)
        sentinel=out/"existing.html"; sentinel.write_bytes(b"ORIGINAL KEEP")
        before=fingerprint(sentinel); run("existing-refused",target=sentinel,requests=0); assert fingerprint(sentinel)==before
        directory=out/"existing-directory"; directory.mkdir(); before=fingerprint(directory)
        run("directory-refused",target=directory,requests=0); assert fingerprint(directory)==before
        symlink=out/"existing-link"; symlink.symlink_to(sentinel)
        before=fingerprint(symlink); original_file=fingerprint(sentinel)
        run("symlink-refused",target=symlink,requests=0); assert fingerprint(symlink)==before and fingerprint(sentinel)==original_file
        dangling=out/"dangling-link"; dangling.symlink_to(out/"absent-link-target")
        before=fingerprint(dangling); run("dangling-refused",target=dangling,requests=0); assert fingerprint(dangling)==before and not (out/"absent-link-target").exists()
        run("missing-parent",target=out/"absent-parent"/"report.html")
        assert not (out/"absent-parent").exists()
        race=out/"race-target.html"; run("race-refused",target=race,race=True)
        assert race.read_bytes()==b"RACE WINNER MUST SURVIVE"
        huge=copy.deepcopy(fixtures); huge["topic"]["message"]="x"*(4*1024*1024)
        run("oversized-report-refused",fixture=huge)
        assert fixtures==original
        result["state"]="passed"
    except BaseException as error:
        result["state"]="failed"; result["error"]=repr(error); raise
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
        after={name:{"sha256":sha((source/name).read_bytes()),"git_blob":gblob((source/name).read_bytes())} for name in names}
        result["source_after"]=after; result["source_unchanged"]=after==pins; result["finished"]=time.time()
        if after!=pins: result["state"]="failed"
        (out/"receiving.json").write_text(json.dumps(result,ensure_ascii=True,indent=2)+"\n")
        print(json.dumps({"state":result["state"],"cases":len(records),"source_unchanged":after==pins,"receipt":str(out/"receiving.json")}))
    assert result["state"]=="passed"
if __name__=="__main__": main()
