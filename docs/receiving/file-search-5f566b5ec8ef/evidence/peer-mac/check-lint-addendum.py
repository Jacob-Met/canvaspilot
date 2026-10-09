from pathlib import Path
import json,hashlib,datetime
r=Path("D:/HAMON/canvas-file-search-5f566b5ec8ef");p=r/"source/src/canvaspilot/file_search.py"
b=p.read_bytes();assert hashlib.sha256(b).hexdigest()=="36a1d4a886129f44d1ba147265bbe54c433b7abdabe0f0d75ef1a495ab6eac2f"
t=b.decode()
pairs=[
('totals = {"returned": 0, "matched": 0, "nonmatching": 0, "unknown": 0}','totals = dict(returned=0, matched=0, nonmatching=0, unknown=0)'),
('counts = {"returned": len(rows), "matched": 0, "nonmatching": 0, "unknown": 0}','counts = dict(returned=len(rows), matched=0, nonmatching=0, unknown=0)'),
('except Exception as error:  # noqa: BLE001 — structured command boundary, no automatic retry','except Exception as error:')]
for new,old in pairs:assert t.count(new)==1;t=t.replace(new,old)
assert hashlib.sha256(t.encode()).hexdigest()=="c453e2855f32e67180e0a922130cd4c206f5613fb73a7e4cb76481072ff3712a"
prior=r/"evidence/peer-mac/independent-review.json"
receipt={"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"parentReviewSha256":hashlib.sha256(prior.read_bytes()).hexdigest(),"decision":"source-only acceptance extends to lint-only final module","finalModuleSha256":hashlib.sha256(b).hexdigest(),"inverseSha256":hashlib.sha256(t.encode()).hexdigest(),"findings":"Two equivalent dict-constructor replacements preserve insertion order and evaluated values; one comment explains existing broad command boundary without changing it. Independent inverse of exactly those three spans recovers previously received entire module byte-for-byte. Complete70-line provided diff also contains only three equivalent combined test context managers.","execution":"No peer9 replay, no model/CLI/browser/build operation.","sourceUnchanged":p.read_bytes()==b}
out=r/"evidence/peer-mac/lint-only-addendum.json"
with out.open("x",encoding="utf-8",newline="") as f:json.dump(receipt,f,indent=2);f.write("\n")
print(json.dumps({"path":str(out),"sha256":hashlib.sha256(out.read_bytes()).hexdigest()}))
