import json,hashlib,subprocess
from pathlib import Path
r=Path(__file__).parent;j=json.loads((r/'intake.json').read_text(encoding='utf-8'));s=r/'source'
assert not s.exists();s.mkdir()
manifest=[]
for f in j['files']:
 b=f['content'].encode('utf-8');meta=next(x for x in j['tree']['tree'] if x['path']==f['path'])
 h=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 assert h==f['sha']==meta['sha'],f['path']
 p=s/f['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 manifest.append({'path':f['path'],'git_blob':h,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'mode':meta['mode']})
for args in [['init'],['config','user.name','ChatGPT 5f566b5ec8ef coordination'],['config','user.email','chatgpt-5f566b5ec8ef@local.invalid'],['config','core.autocrlf','false'],['add','.'],['commit','-m','Capture exact CanvasPilot component source for file search']]:
 subprocess.run(['git','-C',str(s),*args],check=True,capture_output=True)
head=subprocess.check_output(['git','-C',str(s),'rev-parse','HEAD'],text=True).strip()
out={'canonical_base':j['base'],'canonical_tree':j['tree']['sha'],'canonical_leaves':sum(x['type']=='blob' for x in j['tree']['tree']),'source_projection':manifest,'local_custody_head':head,'contract_sha256':hashlib.sha256((r/'evidence/implementation-contract.md').read_bytes()).hexdigest(),'scope':'35 exact source/configuration leaves; local component ancestry, not full canonical checkout'}
(r/'evidence/intake-receipt.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='source_projection'}))
