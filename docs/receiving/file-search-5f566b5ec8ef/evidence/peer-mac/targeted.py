from pathlib import Path
import sys,json,hashlib,datetime,copy
root=Path("D:/HAMON/canvas-file-search-5f566b5ec8ef")
sys.path[:0]=[str(root/"source/src"),str(root/"dependencies")]
from canvaspilot.file_search import search_course_files,validate_selection
from canvaspilot.api import CanvasAPI
paths=[root/"source/src/canvaspilot"/p for p in ["file_search.py","cli.py","api.py"]]
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
results=[]
def check(name,fn):
    try: fn();results.append({"name":name,"passed":True})
    except Exception as e:results.append({"name":name,"passed":False,"error":repr(e)})
class API:
    def __init__(self,rows):self.rows=rows;self.calls=[]
    def list_files(self,course):
        self.calls.append(course)
        return self.rows
def observations(rows,q):
    return search_course_files(API(rows),["01"],q)["courses"][0]["observations"]
def known_partial():
    row={"display_name":"Straße","filename":None,"id":9007199254740993}
    o=observations([row],"SS")[0]
    assert o["match"] is True and o["matched_fields"]==["display_name"]
    assert o["unavailable_fields"]==["filename"] and o["source"]["id"]==9007199254740993
check("Known casefold match remains true despite unavailable second name; large integer exact",known_partial)
def canonical():
    o=observations([{"display_name":None,"filename":"cafe\u0301"}],"é")[0]
    assert o["match"] is None and o["matched_fields"]==[] and o["unavailable_fields"]==["display_name"]
check("Canonically equivalent accents are not silently normalized and partial nonmatch stays unknown",canonical)
def fields():
    o=observations([{"display_name":"ab","filename":"cd"}],"bc")[0]
    assert o["match"] is False and o["unavailable_fields"]==[]
check("Name fields are searched separately, never concatenated",fields)
def whitespace():
    rows=[{"display_name":"A","filename":""},{"display_name":" A ","filename":None}]
    r=search_course_files(API(rows),[1]," a ")
    assert r["query"]==" a " and r["counts"]==dict(returned=2,matched=1,nonmatching=1,unknown=0)
    assert [o["source"] for o in r["courses"][0]["observations"]]==rows
check("Query and source whitespace preserved with empty known fields",whitespace)
def duplicates():
    rows=[{"id":7,"display_name":"I\u0307","filename":"","extra":{"null":None,"false":False,"zero":0,"list":["甲",123]}},
          {"id":7,"display_name":"i","filename":None}]
    old=copy.deepcopy(rows);r=search_course_files(API(rows),[1],"İ")
    o=r["courses"][0]["observations"]
    assert [x["source_index"] for x in o]==[0,1] and [x["match"] for x in o]==[True,None]
    assert [x["source"] for x in o]==old
    rows[0]["extra"]["list"][0]="MUTATED"; rows.reverse()
    assert [x["source"] for x in o]==old
check("Duplicate occurrences and unknown JSON fields remain exact and deeply detached",duplicates)
def preflight():
    for courses,q in [(["01",1],"x"),([True],"x"),([1],"\ud800"),([1],"😀"*128+"x")]:
        api=API([])
        try:search_course_files(api,courses,q)
        except (ValueError,UnicodeError):pass
        else:raise AssertionError("accepted invalid selection")
        assert api.calls==[]
    ids,q=validate_selection([1],"😀"*128)
    assert ids==["1"] and q=="😀"*128
check("Alias/type/UTF8 admission precedes every read, exact512 bytes accepted",preflight)
def normalized():
    class Client:
        def __init__(self):self.paths=[]
        def get_paginated(self,path):
            self.paths.append(path)
            return [None,False,"raw omitted",{"id":1,"display_name":"SS","unknown":"not projected","content-type":"","content_type":"fallback"},
                    {"id":1,"filename":"Straße","url":"https://example.invalid/do-not-follow","size":0}]
    c=Client();r=search_course_files(CanvasAPI(c),["001"],"ss")
    o=r["courses"][0]["observations"]
    assert c.paths==["/api/v1/courses/1/files"] and len(o)==2
    assert [x["match"] for x in o]==[True,True] and "unknown" not in o[0]["source"]
    assert o[0]["source"]["filename"] is None and o[0]["source"]["content_type"]=="fallback"
    assert o[1]["source"]["size"]==0 and o[1]["source"]["url"]=="https://example.invalid/do-not-follow"
    assert "projection" in r["scope"] and "No file URL was followed" in r["scope"]
check("Actual unchanged CanvasAPI projection drops raw nonobjects and keeps truthful observed metadata",normalized)
def late_error():
    class Failing:
        def __init__(self):self.calls=[]
        def list_files(self,c):
            self.calls.append(c)
            if c=="2":raise RuntimeError("later course unavailable")
            return [{"display_name":"x","filename":""}]
    a=Failing()
    try:search_course_files(a,["1","2","3"],"x")
    except RuntimeError as e:assert str(e)=="later course unavailable"
    else:raise AssertionError("Returned partial success")
    assert a.calls==["1","2"]
check("Later course error refuses complete result and stops remaining reads",late_error)
def invalid_names():
    for value in [False,0,[],{}]:
        try:observations([{"display_name":value,"filename":"match"}],"match")
        except ValueError:pass
        else:raise AssertionError("Invalid known name admitted")
check("Invalid scalar/container name never hides behind other matching field",invalid_names)
after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
assert before==after
report={"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_before":before,"source_after":after,
        "checks":results,"passed":sum(x["passed"] for x in results),"total":len(results),
        "scope":"Independent contract-first helper and actual unchanged CanvasAPI projection; authored in-memory responses, no client/profile/provider call, owner tests unread.",
        "blind_cases_sha256":hashlib.sha256((root/"evidence/peer-mac/contract-cases.json").read_bytes()).hexdigest()}
p=root/"evidence/peer-mac/targeted-result.json"
with p.open("x",encoding="utf-8",newline="") as f:json.dump(report,f,indent=2);f.write("\n")
print(json.dumps(report,ensure_ascii=True))
sys.exit(0 if report["passed"]==report["total"] else 1)
