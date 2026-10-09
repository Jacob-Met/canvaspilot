from pathlib import Path
import ast,hashlib,json
root=Path("D:/HAMON/canvas-file-search-5f566b5ec8ef");s=root/"source/src/canvaspilot"
for name in ["file_search.py","cli.py","api.py"]:
 b=(s/name).read_bytes(); print(name,hashlib.sha256(b).hexdigest())
 t=b.decode()
 if name=="cli.py":
  ls=t.splitlines(); indices=set()
  for i,l in enumerate(ls):
   if "find-files" in l or "file_search" in l: indices.update(range(max(0,i-4),min(len(ls),i+10)))
  print("\n".join(str(i+1)+":"+ls[i] for i in sorted(indices)))
 if name=="api.py":
  for node in ast.walk(ast.parse(t)):
   if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name=="list_files":print(ast.get_source_segment(t,node))
