from pathlib import Path
import ast, difflib, hashlib, json, shutil
root=Path("/dev/shm/c6cc965b64c2-canvas-discussion")
baseline=root/"baseline"
old_candidate=root/"candidate"
inputs=root/"qualification/current39d-inputs"
destination=root/"candidate-current39d"
assert not destination.exists()
shutil.copytree(baseline,destination)
for p in inputs.rglob("*"):
    if p.is_file():
        d=destination/p.relative_to(inputs)
        d.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,d)
current_before={str(p.relative_to(destination)):p.read_bytes() for p in destination.rglob("*") if p.is_file()}
owned=json.loads("[\"src/canvaspilot/api.py\",\"src/canvaspilot/cli.py\",\"src/canvaspilot/mcp_server.py\",\"src/canvaspilot/bundle.py\",\"src/canvaspilot/discussion_thread.py\",\"tests/test_discussion_thread.py\",\"tests/test_discussion_thread_native.py\",\"docs/DISCUSSIONS.md\",\"README.md\"]")
notes=[]
for name in owned:
    new=(old_candidate/name).read_text()
    previous=baseline/name
    d=destination/name
    if not previous.exists():
        d.parent.mkdir(parents=True,exist_ok=True)
        d.write_text(new,encoding="utf-8")
        continue
    old=previous.read_text()
    current=d.read_text()
    a=old.splitlines(True)
    b=new.splitlines(True)
    operations=[item for item in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if item[0]!="equal"]
    for kind,i,j,k,l in reversed(operations):
        before="".join(a[i:j])
        after="".join(b[k:l])
        if name=="README.md" and "**36 MCP tools**" in before:
            assert current.count("**37 MCP tools**")==1
            current=current.replace("**37 MCP tools**","**38 MCP tools**",1)
            notes.append({"path":name,"kind":"current owner count plus one","before":"37 MCP tools","after":"38 MCP tools"})
        elif kind=="replace":
            assert current.count(before)==1,(name,before)
            current=current.replace(before,after,1)
            notes.append({"path":name,"kind":kind,"before":before,"after":after})
        elif kind=="insert":
            anchor=None
            for count in range(1,13):
                context="".join(a[i:i+count])
                if context and current.count(context)==1:
                    anchor=context
                    break
            assert anchor is not None,(name,i)
            current=current.replace(anchor,after+anchor,1)
            notes.append({"path":name,"kind":kind,"next_context":anchor,"inserted":after})
        else:
            raise AssertionError((name,kind))
    d.write_text(current,encoding="utf-8")
def functions(raw):
    answer={}
    def visit(items,prefix=""):
        for item in items:
            if isinstance(item,ast.ClassDef):
                visit(item.body,prefix+item.name+".")
            elif isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)):
                answer[prefix+item.name]=ast.dump(item,include_attributes=False)
    visit(ast.parse(raw).body)
    return answer
function_proof={}
for name,new_function in (("src/canvaspilot/api.py","CanvasAPI.discussion_thread"),("src/canvaspilot/mcp_server.py","canvas_discussion_thread")):
    before=functions(current_before[name].decode())
    after=functions((destination/name).read_text())
    assert set(after)-set(before)=={new_function}
    assert all(after[key]==value for key,value in before.items())
    old=functions((old_candidate/name).read_text())
    assert after[new_function]==old[new_function]
    function_proof[name]={"owner_functions_preserved":len(before),"new_function_ast_matches_frozen_79a2":True}
assert (destination/"src/canvaspilot/discussion_thread.py").read_bytes()==(old_candidate/"src/canvaspilot/discussion_thread.py").read_bytes()
for name,raw in current_before.items():
    if name not in owned:
        assert (destination/name).read_bytes()==raw,name
def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()
pins=[{"path":name,"bytes":len((destination/name).read_bytes()),"sha256":hashlib.sha256((destination/name).read_bytes()).hexdigest(),"git_blob":git_blob((destination/name).read_bytes())} for name in owned]
proof={"schema":"canvas-discussion-current39d-composition-v1","base_commit":"39d835c8becb04d81b65c90d1491d2d3a2727ffe","base_tree":"53b67d3f06b4c780e508325ec42b2b435ec57e97","prior_qualified_base":"79a2f2b2cbb7e74128d731cf096c7e86f1942d4b","source_root":str(destination),"current_original_files":len(current_before),"all_unowned_current_inputs_exact":True,"new_module_and_functions_unchanged":True,"owner_functions":function_proof,"source_pins":pins,"seam_changes":notes,"classification":"Additive assignment submission metadata and self-submission history. Existing raw discussion/client/session/broker/dependencies/CI unchanged."}
raw=(json.dumps(proof,ensure_ascii=False,indent=2)+"\n").encode()
(root/"qualification/current39d-composition.json").write_bytes(raw)
print(json.dumps({"source_root":str(destination),"proof_sha256":hashlib.sha256(raw).hexdigest(),"source_pins":pins,"owner_functions":function_proof,"current_original_files":len(current_before)}))
