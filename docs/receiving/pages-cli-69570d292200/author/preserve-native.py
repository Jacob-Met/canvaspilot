import datetime, hashlib, json, pathlib, shutil, subprocess, tempfile
src=pathlib.Path('/dev/shm/evaluation-69570d292200-canvas-pages')
parent=pathlib.Path('/home/jacob/evaluation-69570d292200')
assert shutil.disk_usage('/home/jacob').free>128*1024*1024
parent.mkdir(exist_ok=True)
files=[p for p in src.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
assert sum(p.stat().st_size for p in files)<4*1024*1024
dst=pathlib.Path(tempfile.mkdtemp(prefix='canvas-pages-6d2bd132-',dir=parent))
pins=[]
for p in files:
 rel=p.relative_to(src);b=p.read_bytes();q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
 assert q.read_bytes()==b
 pins.append({'path':rel.as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'gitBlob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()})
(dst/'manifest.json').write_text(json.dumps({'files':sorted(pins,key=lambda x:x['path']),'canonicalProductTree':'6d2bd132c4e8de5735cfeeb15ef2db35bcbbf608','copiedBytes':sum(x['bytes'] for x in pins),'boundary':'Native isolated Git custody, no remote/ref/Actions'},indent=2)+'\n')
def git(*args):
 p=subprocess.run(['git',*args],cwd=dst,capture_output=True,text=True,check=True);return p.stdout.strip()
git('init','--template=','-q')
git('add','.')
git('-c','user.name=HAMON external evaluation contributor','-c','user.email=69570d292200-evaluation@localhost','commit','-q','-m','Preserve native Canvas page reader and qualification')
head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}');assert git('status','--porcelain')==''
for item in pins:
 assert git('hash-object',item['path'])==item['gitBlob']
receipt={'nativeRoot':str(dst),'nativeCommit':head,'nativeTree':tree,'canonicalProductTree':'6d2bd132c4e8de5735cfeeb15ef2db35bcbbf608','files':len(pins),'bytes':sum(x['bytes'] for x in pins),'clean':True,'at':datetime.datetime.now(datetime.UTC).isoformat(),'freeBytes':shutil.disk_usage('/home/jacob').free}
(parent/'canvas-pages-custody.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
