import json,hashlib,subprocess,sys,os,time,importlib.metadata
from pathlib import Path
r=Path(__file__).parent;s=r/'source'
baseline=json.loads((r/'evidence/baseline-v2-process.json').read_text(encoding='utf-8'));assert baseline['exit']==0
m=json.loads((r/'evidence/intake-receipt.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256((s/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in m['source_projection'])
files=json.loads((r/'candidate.json').read_text(encoding='utf-8'))
for f in files:
 p=s/f['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(f['content'].encode('utf-8'))
pins={f['path']:hashlib.sha256((s/f['path']).read_bytes()).hexdigest() for f in files}
env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(s/'src'),str(r/'dependencies')]);env['PYTHONDONTWRITEBYTECODE']='1'
start=time.time()
p=subprocess.run([sys.executable,'-X','utf8','-B','-m','pytest','-q','-p','no:cacheprovider','tests/test_file_search.py','tests/test_file_search_cli.py','--junitxml='+str(r/'evidence/candidate-v1.xml')],cwd=s,env=env,text=True,capture_output=True,timeout=120)
(r/'evidence/candidate-v1.stdout').write_text(p.stdout,encoding='utf-8');(r/'evidence/candidate-v1.stderr').write_text(p.stderr,encoding='utf-8')
unowned=[x for x in m['source_projection'] if x['path'] not in ['README.md','src/canvaspilot/cli.py']]
out={'exit':p.returncode,'seconds':time.time()-start,'product_pins':pins,'all_product_inputs_unchanged':all(hashlib.sha256((s/k).read_bytes()).hexdigest()==v for k,v in pins.items()),'unowned_input_count':len(unowned),'all_unowned_inputs_unchanged':all(hashlib.sha256((s/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in unowned),'stdout':p.stdout,'stderr':p.stderr}
(r/'evidence/candidate-v1.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))
