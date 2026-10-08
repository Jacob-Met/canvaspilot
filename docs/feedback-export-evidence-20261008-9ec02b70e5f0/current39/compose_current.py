import sys,json,hashlib,difflib,ast
from pathlib import Path
p=json.loads(sys.argv[1]);r=Path('/dev/shm/estate-9ec02b70e5f0/lead/canvas-current39');r.mkdir(exist_ok=True);repo=r/'repo';pub=r/'published'
def sha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
for f in p['pins']:
 b=(Path(p['source_root'])/f['path']).read_bytes();assert len(b)==f['bytes'];assert hashlib.sha256(b).hexdigest()==f['sha256'];assert sha(b)==f['git_blob'];out=repo/f['path'];out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
for f in p['incoming']:
 b=f['content'].encode();assert sha(b)==f['git_blob'];out=pub/f['path'];out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
 if f['path'] not in p['bases']:
  out=repo/f['path'];out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
proof=[]
for name,basepath in p['bases'].items():
 old=Path(basepath).read_bytes().decode();prior=(Path(p['source_root'])/name).read_bytes().decode();new=(pub/name).read_bytes().decode();ol=old.splitlines(keepends=True);pl=prior.splitlines(keepends=True);edits=[]
 for tag,i,j,u,v in difflib.SequenceMatcher(None,ol,pl,autojunk=False).get_opcodes():
  if tag=='equal':continue
  assert tag=='insert',(name,tag);choices=[''.join(ol[max(0,i-width):i]) for width in range(4,41)];choices=[a for a in choices if a and new.count(a)==1];assert choices,(name,'no unique native prefix');anchor=choices[0];addition=''.join(pl[u:v]);assert addition not in new;new=new.replace(anchor,anchor+addition,1);edits.append({'anchor_before':anchor,'inserted':addition})
 assert len(edits)==(1 if name=='README.md' else 2),(name,len(edits));inverse=new
 for e in reversed(edits):inverse=inverse.replace(e['anchor_before']+e['inserted'],e['anchor_before'],1)
 assert inverse==(pub/name).read_bytes().decode();(repo/name).write_bytes(new.encode());proof.append({'path':name,'insertions':edits,'inverse_recovers_complete_incoming':True,'before_git_blob':sha(inverse.encode()),'qualified_git_blob':sha(new.encode())})
rows=[]
for f in sorted(repo.rglob('*')):
 if f.is_file():
  b=f.read_bytes();rows.append({'path':f.relative_to(repo).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':sha(b)})
(rootproof:=r/'composition.json').write_text(json.dumps({'parent':p['parent'],'tree':p['tree'],'source_root':str(repo),'changes':proof},indent=2)+'\n')
(r/'candidate-pins.json').write_text(json.dumps({'parent':p['parent'],'tree':p['tree'],'source_root':str(repo),'files':rows},indent=2)+'\n')
(r/'compose_current.py').write_text(p['recipe'])
(r/'composition-first-failure.json').write_text(json.dumps({'stage':'composition before qualification','exception':'AssertionError: dispatcher prefix matched three places','product_execution':False,'disposition':'derive a longer unique native prefix; all inserted blocks remain unchanged'},indent=2)+'\n')
oldapi=(Path(p['source_root'])/'src/canvaspilot/api.py').read_text();newapi=(repo/'src/canvaspilot/api.py').read_text();print(''.join(difflib.unified_diff(oldapi.splitlines(True),newapi.splitlines(True),fromfile='api0d',tofile='api39')))
print(json.dumps({'source':str(repo),'files':len(rows),'proof':str(rootproof),'pins_sha256':hashlib.sha256((r/'candidate-pins.json').read_bytes()).hexdigest(),'owned':[x for x in rows if x['path'] in ['README.md','src/canvaspilot/cli.py']]}))