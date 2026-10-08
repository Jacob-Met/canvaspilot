"""Independent actual-API receiving for CanvasPilot's offline grade export."""
from __future__ import annotations
import base64,copy,hashlib,json,os,pathlib,shutil,sys,threading
from datetime import UTC,datetime
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import parse_qs,urlsplit

ROOT=pathlib.Path(__file__).resolve().parent
PRODUCER=pathlib.Path("/home/jacob/canvaspilot-grade-review-export-926c3dc2605e")
SNAP=ROOT/"source"
SNAP.mkdir(exist_ok=False)
source_hashes={}
for p in sorted((PRODUCER/"src").rglob("*")):
    if p.is_file() and "__pycache__" not in p.parts:
        rel=p.relative_to(PRODUCER)
        raw=p.read_bytes(); target=SNAP/rel
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        source_hashes[str(rel)]=hashlib.sha256(raw).hexdigest()
assert source_hashes["src/canvaspilot/grade_review_export.py"]=="7d8df22447642cb5ac2588b144c18b3b2dde14ab7ca4b7fc085b17d60eb874be"
assert all(hashlib.sha256((PRODUCER/p).read_bytes()).hexdigest()==h for p,h in source_hashes.items())
sys.dont_write_bytecode=True
sys.path.insert(0,str(SNAP/"src"))
os.environ["NO_PROXY"]="127.0.0.1,localhost"
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.grade_review import GradeReviewError
from canvaspilot.grade_review_export import build_grade_review_report,render_grade_review_report

OUT=ROOT/"observations";OUT.mkdir()
CHECKS=[];RECORDS=[]
def check(name,value):
    if not value: raise AssertionError(name)
    CHECKS.append(name)

def sample():
    assignments=[
        {"id":201,"name":"Zero & empty <img src=x onerror=alert(1)>","points_possible":0,
         "due_at":None,"submission":{"assignment_id":201,"user_id":91,"score":0,"grade":"",
         "entered_score":0,"attempt":0,"grade_matches_current_submission":True,
         "missing":False,"excused":False,"late":False}},
        {"id":202,"name":"Posting withheld","points_possible":100,
         "submission":{"assignment_id":202,"user_id":91,"score":9117,"grade":"HIDDEN_POSTING_SENTINEL",
         "entered_score":9917,"entered_grade":"HIDDEN_ENTERED_SENTINEL","points_deducted":81,
         "posted_at":None,"missing":False}},
        {"id":203,"name":"Visibility withheld","points_possible":100,
         "submission":{"assignment_id":203,"user_id":91,"score":8229,"grade":"HIDDEN_VISIBILITY_SENTINEL",
         "assignment_visible":False,"posted_at":"2026-10-03T12:30:00Z","grade_matches_current_submission":False}},
        {"id":204,"name":"Older attempt","points_possible":40,"omit_from_final_grade":True,
         "submission":{"assignment_id":204,"user_id":91,"score":135.75,"grade":"A > maximum",
         "entered_score":137.5,"points_deducted":1.75,"attempt":3,"excused":True,"late":True,
         "grade_matches_current_submission":False,"workflow_state":"submitted"}},
        {"id":205,"name":"Submission absent","due_at":"","html_url":"javascript:alert('not-a-link')"},
        {"id":206,"name":"Submission null","submission":None},
        {"id":207,"name":"Submission empty","submission":{}},
        {"id":208,"name":"Explicit unavailable","submission":{"score":None,"grade":None,
         "attempt":None,"missing":None,"late":None,"excused":None}},
        {"id":209,"name":"Invalid values remain unknown","submission":{"score":True,"grade":"kept",
         "attempt":-1,"missing":"no","late":0}},
    ]
    for a in assignments:a.update(course_id="00084",assignment_group_id="0005")
    return {
        "profile":{"id":"00091","name":"Authored caller"},
        "course":{"id":"00084","name":"Matrix \x00 <script>alert('text')</script> & \ud800",
          "course_code":"","hide_final_grades":False,"apply_assignment_group_weights":True,
          "has_grading_periods":True,"unposted_final_grade":"HIDDEN_COURSE_SENTINEL",
          "enrollments":[
            {"type":"teacher","role":"TeacherEnrollment","user_id":91,"computed_current_score":-7,
             "computed_final_score":0,"computed_current_grade":"","unposted_current_score":919191},
            {"type":"student","role":"StudentEnrollment","user_id":"00091","computed_current_score":112.75,
             "computed_final_score":0,"computed_current_grade":None,"computed_final_grade":"",
             "current_period_computed_current_score":104.125,"current_period_computed_final_score":None,
             "override_score":929292},
            {"type":"observer","role":"ObserverEnrollment","user_id":91,"computed_current_score":None,
             "computed_final_score":True},
          ],
          "grading_periods":[{"id":"009","title":"Period \x1f \ud801","weight":120.25,"start_date":""}]},
        "groups":[
          {"id":"0005","name":"","position":7,"group_weight":150.25,
           "rules":{"drop_lowest":3,"drop_highest":1,"never_drop":["00201",204]},
           "assignments":assignments},
          {"id":8,"name":"Empty list","group_weight":0,"rules":{},"assignments":[]},
          {"id":14,"name":"Unknown list","rules":None},
          {"id":19,"name":"Null list","assignments":None},
        ]
    }

class Fixture:
    def __init__(self,data):
        self.data=data;self.requests=[];owner=self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                p=urlsplit(self.path);query=parse_qs(p.query)
                owner.requests.append({"method":"GET","path":p.path,"query":query})
                status=200;headers={}
                if self.headers.get("Authorization")!="Bearer receiving-fictional-token":
                    status=401;body={"error":"fixture authorization required"}
                elif p.path=="/api/v1/users/self/profile":body=owner.data["profile"]
                elif p.path=="/api/v1/courses/84":body=owner.data["course"]
                elif p.path=="/api/v1/courses/84/assignment_groups":
                    if query.get("cursor")==["page-two"]:body=owner.data["groups"][2:]
                    else:
                        body=owner.data["groups"][:2]
                        headers["Link"]=f'<{owner.base_url}{p.path}?cursor=page-two>; rel="next"'
                else:status=404;body={"error":"unmapped fixture route"}
                raw=json.dumps(copy.deepcopy(body),ensure_ascii=True,allow_nan=False).encode("ascii")
                self.send_response(status);self.send_header("Content-Type","application/json")
                self.send_header("Content-Length",str(len(raw)))
                for k,v in headers.items():self.send_header(k,v)
                self.end_headers();self.wfile.write(raw)
            def log_message(self,*args):pass
        self.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        self.base_url=f"http://127.0.0.1:{self.server.server_port}"
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join(5)

class CountingAPI(CanvasAPI):
    def __init__(self,client):super().__init__(client);self.reviews=0
    def grade_review(self,cid):
        self.reviews+=1
        return super().grade_review(cid)

class Node:
    def __init__(self,tag,attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
    def text(self):return "".join(x if isinstance(x,str) else x.text() for x in self.children)
    def all(self,pred):
        found=[self] if pred(self) else []
        for x in self.children:
            if isinstance(x,Node):found.extend(x.all(pred))
        return found

class Document(HTMLParser):
    def __init__(self,raw):
        super().__init__(convert_charrefs=True);self.root=Node("root");self.stack=[self.root];self.feed(raw)
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs);self.stack[-1].children.append(n)
        if tag not in {"meta","br","hr","img","input","link","source","wbr"}:self.stack.append(n)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:self.stack=self.stack[:i];break
    def handle_data(self,data):self.stack[-1].children.append(data)

STAMP=datetime(2026,10,8,16,0,tzinfo=UTC)
def receive(name,data):
    raw_before=json.dumps(data,ensure_ascii=True,allow_nan=False)
    fixture=Fixture(data)
    try:
        with CountingAPI(CanvasClient(base_url=fixture.base_url,token="receiving-fictional-token",profile=ROOT/"unused-profile")) as api:
            report=api.grade_review("00084")
            before=copy.deepcopy(report)
            content,meta=build_grade_review_report(api,84,generated_at=STAMP)
            check(name+": build invokes current grade API once",api.reviews==2)
        doc=Document(content.decode("utf-8")).root
        links=doc.all(lambda n:n.tag=="a")
        downloads=[n for n in links if n.attrs.get("download")=="course-grade-review.json"]
        check(name+": one JSON download",len(downloads)==1)
        href=downloads[0].attrs["href"]
        check(name+": static local data download",href.startswith("data:application/json;base64,"))
        payload=base64.b64decode(href.split(",",1)[1],validate=True)
        recovered=json.loads(payload)
        check(name+": download equals actual normalized API",recovered==report)
        check(name+": normalized original unchanged",report==before)
        check(name+": raw supplied records unchanged",json.dumps(data,ensure_ascii=True,allow_nan=False)==raw_before)
        check(name+": accurate digest",meta["json_sha256"]==hashlib.sha256(payload).hexdigest())
        check(name+": no active payload elements",not doc.all(lambda n:n.tag in {"script","img","iframe","object","embed","form","input","link"}))
        check(name+": no event attributes",not doc.all(lambda n:any(a.lower().startswith("on") for a in n.attrs)))
        check(name+": links all local",all(n.attrs.get("href","").startswith(("#","data:application/json;base64,")) for n in links))
        check(name+": no known hidden grade recovery",all(token not in json.dumps(recovered) and token not in doc.text() for token in ["HIDDEN_POSTING_SENTINEL","HIDDEN_ENTERED_SENTINEL","HIDDEN_VISIBILITY_SENTINEL","HIDDEN_COURSE_SENTINEL"]))
        check(name+": read-only actual HTTP route",len(fixture.requests)==8 and {x["method"] for x in fixture.requests}=={"GET"})
        check(name+": actual pagination forwarded",fixture.requests[2]["query"].get("include[]")==["assignments","submission"] and fixture.requests[3]["query"]=={"cursor":["page-two"]})
        check(name+": completeness stays unknown",recovered["collection_complete"] is None)
        check(name+": no user-session profile",not (ROOT/"unused-profile").exists())
        (OUT/f"{name}.html").write_bytes(content);(OUT/f"{name}.json").write_bytes(payload)
        RECORDS.append({"case":name,"api_grade_review_calls":api.reviews,"http_requests":fixture.requests,
                        "html_sha256":hashlib.sha256(content).hexdigest(),"json_sha256":hashlib.sha256(payload).hexdigest(),"metadata":meta})
        return report,doc,content
    finally:fixture.close()

rich,richdoc,richhtml=receive("rich",sample())
enrollments=richdoc.all(lambda n:n.tag=="article" and n.attrs.get("class")=="enrollment")
check("three separate enrollments preserved",len(enrollments)==3)
for i,role in enumerate(["TeacherEnrollment","StudentEnrollment","ObserverEnrollment"]):
    check(role+" remains attached to its enrollment",role in enrollments[i].text())
check("teacher first does not select or replace student",rich["enrollments"][0]["reported_totals"]["computed_current_score"]==-7 and rich["enrollments"][1]["reported_totals"]["computed_current_score"]==112.75)
check("over100 retained without arithmetic",rich["enrollments"][1]["reported_totals"]["current_period_computed_current_score"]==104.125)
check("raw identity spelling preserved",rich["authenticated_user_id"]=="00091" and rich["course"]["id"]=="00084")
check("normalized enrollment keys preserve reader order",list(rich["enrollments"][1]["reported_totals"])==["computed_current_score","computed_final_score","computed_current_grade","computed_final_grade","current_period_computed_current_score","current_period_computed_final_score"])
groups=rich["assignment_groups"]
check("group order and original identifiers preserved",[g["id"] for g in groups]==["0005",8,14,19])
check("no weighting or drop selection",groups[0]["group_weight"]==150.25 and groups[0]["rules"]=={"drop_lowest":3,"drop_highest":1,"never_drop":["00201",204]})
check("absent null empty assignment collections distinct",[g["assignments_state"] for g in groups]==["returned","returned","not_returned","null"] and groups[1]["assignments"]==[] and groups[2]["assignments"] is None and groups[3]["assignments"] is None)
assignments=groups[0]["assignments"]
check("assignment count without dropped-work inference",len(assignments)==9 and rich["counts"]["assignments_returned"]==9)
fields=[a["submission"]["fields"] if a["submission"] is not None else None for a in assignments]
check("zero and empty grade and zero attempt exact",fields[0]["score"]==0 and type(fields[0]["score"]) is int and fields[0]["grade"]=="" and fields[0]["attempt"]==0)
check("false flags retained",all(fields[0][k] is False for k in ["missing","late","excused"]))
check("hidden posting and visibility boundaries retained",assignments[1]["submission"]["grade_visibility"]=="not_posted" and assignments[2]["submission"]["grade_visibility"]=="assignment_not_visible")
check("hidden grades absent from normalized fields",not ({"grade","score","entered_grade","entered_score","points_deducted"} & fields[1].keys()) and not ({"grade","score","entered_grade","entered_score","points_deducted"} & fields[2].keys()))
check("latest-attempt mismatch retains reported score without promotion",fields[3]["score"]==135.75 and fields[3]["grade_matches_current_submission"] is False and "Do not treat it as the grade for the latest attempt." in richdoc.text())
check("submission absent null empty are distinct",assignments[4]["submission_state"]=="not_returned" and assignments[5]["submission_state"]=="null" and fields[6]=={})
check("unknown applicability stays unknown","Whether the grade matches the current submission is unknown." in richdoc.text())
check("explicit nulls remain null",all(fields[7][k] is None for k in ["score","grade","attempt","missing","late","excused"]))
check("invalid values remain omitted with warnings","score" not in fields[8] and "attempt" not in fields[8] and "missing" not in fields[8] and fields[8]["grade"]=="kept" and len(rich["warnings"])>=5)
check("visible control and surrogate characters safe","\\u0000" in richdoc.text() and "\\ud800" in richdoc.text())
check("escaped original malicious title remains data","<script>alert('text')</script>" in richdoc.text())
check("malicious source URL remains text","javascript:alert('not-a-link')" in richdoc.text())

def reverse_fields(value):
    if isinstance(value,dict):return {k:reverse_fields(value[k]) for k in reversed(value)}
    if isinstance(value,list):return [reverse_fields(x) for x in value]
    return value
_,_,reordered=receive("field-order",reverse_fields(sample()))
check("raw field-order changes cannot change normalized export",reordered==richhtml)
hidden=sample();hidden["course"]["hide_final_grades"]=True
h,hd,_=receive("hidden-totals",hidden)
check("all enrollment totals withheld when course hides grades",all(e["reported_totals"]=={} for e in h["enrollments"]))
check("hidden-total explanation is present","The reader withheld enrollment totals." in hd.text())
for key,label in [("enrollments","enrollment"),("grading_periods","period")]:
    for variant in ["absent","null","empty"]:
        data=sample()
        if variant=="absent":data["course"].pop(key)
        else:data["course"][key]=None if variant=="null" else []
        r,doc,_=receive(label+"-"+variant,data)
        expected_state={"absent":"not_returned","null":"null","empty":"returned"}[variant]
        check(label+" "+variant+" remains explicit",r[key+"_state"]==expected_state and r[key]==([] if variant=="empty" else None))
empty=sample();empty["groups"]=[]
er,ed,_=receive("no-groups",empty)
check("empty groups do not establish course absence","This does not establish that the course has none." in ed.text() and er["counts"]["groups_returned"]==0)

for name,mutate in [
    ("restricted-course",lambda d:d["course"].update(access_restricted_by_date=True)),
    ("mismatched-user",lambda d:d["course"]["enrollments"][0].update(user_id=999)),
    ("invalid-visibility",lambda d:d["groups"][0]["assignments"][0]["submission"].update(assignment_visible="false")),
]:
    data=sample();mutate(data);fixture=Fixture(data)
    try:
        with CountingAPI(CanvasClient(base_url=fixture.base_url,token="receiving-fictional-token",profile=ROOT/"unused-profile")) as api:
            try:build_grade_review_report(api,84,generated_at=STAMP)
            except GradeReviewError as exc:
                check(name+": error is not rendered as a report",api.reviews==1)
                RECORDS.append({"case":name,"error_type":type(exc).__name__,"error":str(exc),"http_requests":fixture.requests})
            else:raise AssertionError(name+" unexpectedly exported")
    finally:fixture.close()

check("producer source unchanged during receiving",all(hashlib.sha256((PRODUCER/p).read_bytes()).hexdigest()==h for p,h in source_hashes.items()))
receipt={"schema":"hamon.canvaspilot_grade_export_receiving.v1","receiver":"chatgpt-926c3dc2605e/runtime_execution",
 "verdict":"qualified","cases":len(RECORDS),"checks":CHECKS,"source_sha256":source_hashes,
 "renderer_sha256":source_hashes["src/canvaspilot/grade_review_export.py"],"records":RECORDS,
 "boundary":"Actual CanvasAPI/CanvasClient HTTPX normalization and native renderer; independent fictional HTTP source",
 "production_source_modified":False,"live_canvas_called":False,"browser_print_download_review":"Owned by production_execution; not duplicated"}
(OUT/"receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
print(json.dumps({"verdict":receipt["verdict"],"cases":len(RECORDS),"checks":len(CHECKS),"receipt_sha256":hashlib.sha256((OUT/"receipt.json").read_bytes()).hexdigest()}))
