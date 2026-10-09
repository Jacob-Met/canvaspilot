"""Correct the reviewer's source-inverse list/bytes join; do not rerun CLI controls."""
from pathlib import Path
import ast,hashlib,json,difflib
root=Path("/dev/shm/integration-69570d292200-canvas-pages-v1")
author=Path("/home/jacob/evaluation-69570d292200/canvas-pages-6d2bd132-9mie48yb")
source=root/"receive-pages.py"
text=source.read_text()
old='reverse=b"".join(b[j:k] for tag,i,l,j,k in opcodes if tag=="equal")'
new='reverse=b"".join(line for tag,i,l,j,k in opcodes if tag=="equal" for line in b[j:k])'
assert text.count(old)==1
corrected=text.replace(old,new)
tree=ast.parse(corrected)
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ("tree_hash","source_fence")]
assert len(selected)==2
pins=json.loads((author/"evidence/product-tree.json").read_text())
base=json.loads((author/"evidence/base-tree.json").read_text())
ns={"hashlib":hashlib,"difflib":difflib,"SOURCE":author/"candidate","BASE":Path("/home/jacob/canvas-attempt-69570d292200/original"),
"basemap":{p["path"]:p for p in base["tree"] if p["type"]!="tree"},
"pinmap":{p["path"]:p for p in pins["tree"] if p["type"]!="tree"},
"R":{"product_tree":"6d2bd132c4e8de5735cfeeb15ef2db35bcbbf608"},
"maintained":{"src/canvaspilot/cli.py","README.md","tests/test_pages_cli.py","docs/pages-cli.md"}}
exec(compile(ast.Module(body=selected,type_ignores=[]),"<corrected-reviewer-source-proof>","exec"),ns)
detail=ns["source_fence"]()
r={"result":"PASS","detail":detail,"original_program_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
"correction":{"before":old,"after":new,"reason":"Original reviewer attempted joining list slices as bytes; flatten equal byte-lines instead.","product_changes":False,"CLI_rerun":False,"original_overall_result":"FAIL retained"}}
(root/"source-proof-correction.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps(r))
