
import ast,difflib,hashlib,json,os,pathlib
root=pathlib.Path('/dev/shm/estate-9ec02b70e5f0/lead/canvas-current17')
old=root.parent/'canvas-current39';repo=root/'repo';published=root/'published'
def pin(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def put(p,b):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
reserve=root/'native-evidence.reserved';assert reserve.stat().st_size==reserve.stat().st_blocks*512==196608
proof={'receiving_parent':'17d63dc43fde30efd8d3454ef09b1d1a8c5bcd0d','receiving_tree':'9818539d6444ef43a72d6540c2ba3817c758d9c8','qualified_parent':'39d835c8becb04d81b65c90d1491d2d3a2727ffe','insertions':{},'native_changes':{}}
for path,expected in [('README.md',1),('src/canvaspilot/cli.py',2)]:
 prior=(old/'published'/path).read_bytes();qualified=(old/'repo'/path).read_bytes()
 a=prior.splitlines(keepends=True);b=qualified.splitlines(keepends=True)
 ops=[o for o in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if o[0]!='equal']
 assert len(ops)==expected and all(o[0]=='insert' for o in ops)
 incoming=(published/path).read_bytes();candidate=incoming;inserts=[]
 for tag,i,j,k,l in reversed(ops):
  block=b''.join(b[k:l]);assert incoming.count(block)==0
  for n in range(1,len(a)-i+1):
   anchor=b''.join(a[i:i+n])
   if anchor and candidate.count(anchor)==1:break
  else:raise ValueError('No unique complete-line anchor for '+path)
  candidate=candidate.replace(anchor,block+anchor,1)
  inserts.append({'block':block.decode(),'pin':pin(block),'following_anchor_sha256':hashlib.sha256(anchor).hexdigest(),'following_anchor_lines':n})
 recovered=candidate
 for row in inserts:
  block=row['block'].encode();assert recovered.count(block)==1;recovered=recovered.replace(block,b'',1)
 assert recovered==incoming
 put(repo/path,candidate)
 proof['insertions'][path]={'prior_qualified':pin(qualified),'incoming':pin(incoming),'candidate':pin(candidate),'inverse_exact':True,'blocks':list(reversed(inserts))}
def methods(raw):
 s=raw.decode();cls=next(x for x in ast.parse(s).body if isinstance(x,ast.ClassDef) and x.name=='CanvasAPI')
 return {n.name:ast.get_source_segment(s,n).encode() for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
before=(old/'repo/src/canvaspilot/api.py').read_bytes();after=(repo/'src/canvaspilot/api.py').read_bytes()
a,b=methods(before),methods(after)
proof['api']={'prior_method_count':len(a),'current_method_count':len(b),'unchanged':[k for k,v in a.items() if b.get(k)==v],'changed':{k:{'before':v.decode(),'after':b.get(k,b'').decode()} for k,v in a.items() if b.get(k)!=v},'added':{k:v.decode() for k,v in b.items() if k not in a}}
assert set(proof['api']['changed'])=={'list_conversations','get_conversation'}
assert set(proof['api']['added'])=={'discussion_thread','course_agenda'}
assert len(proof['api']['unchanged'])==39
for path in ['README.md','src/canvaspilot/api.py','src/canvaspilot/cli.py','src/canvaspilot/bundle.py','src/canvaspilot/mcp_server.py']:
 previous=(old/'published'/path).read_text();latest=(published/path).read_text()
 proof['native_changes'][path]=''.join(difflib.unified_diff(previous.splitlines(keepends=True),latest.splitlines(keepends=True),fromfile='current39/'+path,tofile='current17/'+path))
p=published/'src/canvaspilot/submission_history.py'
if not p.exists():os.link(repo/'src/canvaspilot/submission_history.py',p)
oldpins=json.loads((old/'candidate-pins.json').read_bytes())
paths=sorted(set([r['path'] for r in oldpins['files']]+['src/canvaspilot/agenda.py','src/canvaspilot/discussion_thread.py']))
pins={'parent':proof['receiving_parent'],'tree':proof['receiving_tree'],'source_root':str(repo),'files':[{'path':p,**pin((repo/p).read_bytes())} for p in paths]}
assert len(pins['files'])==32
for name,obj in [('candidate-pins.json',pins),('composition.json',proof)]:
 put(root/name,(json.dumps(obj,indent=2,ensure_ascii=False)+'\n').encode())
print(json.dumps({'root':str(root),'reserve':{'bytes':reserve.stat().st_size,'allocated':reserve.stat().st_blocks*512},'pins':pin((root/'candidate-pins.json').read_bytes()),'composition':pin((root/'composition.json').read_bytes()),'api':proof['api'],'insertions':proof['insertions'],'source_files':len(paths)},ensure_ascii=False))
