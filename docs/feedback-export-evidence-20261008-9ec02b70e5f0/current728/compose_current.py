
import ast,difflib,hashlib,json,os,pathlib,sys
incoming=json.loads(sys.argv[1]);root=pathlib.Path('/dev/shm/estate-9ec02b70e5f0/lead/canvas-current728');root.mkdir(exist_ok=False)
old=root.parent/'canvas-current17';repo=root/'repo';published=root/'published'
def pin(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def put(p,b):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def insertions(a,b,count):
 aa=a.splitlines(keepends=True);bb=b.splitlines(keepends=True);ops=difflib.SequenceMatcher(None,aa,bb,autojunk=False).get_opcodes();changes=[x for x in ops if x[0]!='equal']
 assert len(changes)==count and all(x[0]=='insert' for x in changes)
 assert b''.join(b''.join(bb[k:l]) for tag,i,j,k,l in ops if tag=='equal')==a
 return [{'position':i,'block':b''.join(bb[k:l]),'pin':pin(b''.join(bb[k:l]))} for tag,i,j,k,l in changes]
oldpins=json.loads((old/'candidate-pins.json').read_bytes());proof={'parent':'728d2d8b67b6f0812956fecdeeb50e25ee32e979','tree':'7a659089347c983e79106b505e63981f91986507','independently_qualified_parent':'17d63dc43fde30efd8d3454ef09b1d1a8c5bcd0d','source_only_composition':True,'native_execution':False,'full_repository_CI':'Final PR head must pass the existing CI workflow before integration','incoming_additions':{},'export_insertions':{}}
for row in oldpins['files']:
 if row['path'] in [x['path'] for x in incoming]:continue
 p=repo/row['path'];p.parent.mkdir(parents=True,exist_ok=True);os.link(old/'repo'/row['path'],p)
for x in incoming:
 path=x['path'];native=x['content'].encode();assert pin(native)['git_blob']==x['git_blob']
 put(published/path,native)
 prior=(old/'published'/path).read_bytes();qualified=(old/'repo'/path).read_bytes()
 native_add=insertions(prior,native,2 if path=='README.md' else 4)
 proof['incoming_additions'][path]=[{'pin':z['pin'],'block':z['block'].decode()} for z in native_add]
 own=insertions(prior,qualified,1 if path=='README.md' else 2);lines=prior.splitlines(keepends=True);candidate=native;records=[]
 for z in reversed(own):
  assert native.count(z['block'])==0
  for n in range(1,len(lines)-z['position']+1):
   anchor=b''.join(lines[z['position']:z['position']+n])
   if anchor and candidate.count(anchor)==1:break
  else:raise ValueError('No unique native insertion anchor')
  candidate=candidate.replace(anchor,z['block']+anchor,1);records.append({'block':z['block'].decode(),'pin':z['pin'],'anchor_lines':n,'anchor_sha256':hashlib.sha256(anchor).hexdigest()})
 recovered=candidate
 for z in own:
  assert recovered.count(z['block'])==1;recovered=recovered.replace(z['block'],b'',1)
 assert recovered==native
 own_final=insertions(native,candidate,1 if path=='README.md' else 2)
 assert [z['block'] for z in own_final]==[z['block'] for z in own]
 if path.endswith('.py'):ast.parse(candidate)
 put(repo/path,candidate);proof['export_insertions'][path]={'complete_native_before':pin(native),'candidate':pin(candidate),'inverse_exact':True,'blocks':list(reversed(records))}
pins={'parent':proof['parent'],'tree':proof['tree'],'source_root':str(repo),'files':[{'path':x['path'],**pin((repo/x['path']).read_bytes())} for x in oldpins['files']]}
for name,obj in [('candidate-pins.json',pins),('composition.json',proof)]:put(root/name,(json.dumps(obj,indent=2,ensure_ascii=False)+'\n').encode())
out=[]
for name in ['candidate-pins.json','composition.json','repo/README.md','repo/src/canvaspilot/cli.py']:
 p=root/name;b=p.read_bytes();out.append({'path':name,'source_path':str(p),**pin(b),'content':b.decode()})
print(json.dumps(out,ensure_ascii=False))
