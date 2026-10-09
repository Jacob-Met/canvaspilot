from pathlib import Path
import json,hashlib,datetime
r=Path("D:/HAMON/canvas-file-search-5f566b5ec8ef/evidence/peer-mac")
p=r/"contract-cases.json";b=p.read_bytes();(r/"contract-cases-initial-js-number.json").write_bytes(b)
t=b.decode().replace('"id": 9007199254740992','"id": 9007199254740993')
assert t!=b.decode()
p.write_text(t,encoding="utf-8",newline="")
out={"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"cases_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"initial_sha256":hashlib.sha256(b).hexdigest(),"correction":"Before any product/test read, preserve initial JS-serialized case and restore intended large integer literal which JS rounded. Actual test will parse with native Python arbitrary precision.","product_or_owner_tests_read":False}
(r/"blind-freeze.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8",newline="")
print(json.dumps(out))
