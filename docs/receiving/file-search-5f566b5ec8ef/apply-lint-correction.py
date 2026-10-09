import subprocess,sys,os,json,hashlib,time,shutil
from pathlib import Path
r=Path(__file__).parent;s=r/'source';initial=json.loads((r/'evidence/candidate-v1.json').read_text(encoding='utf-8'))['product_pins']
assert all(hashlib.sha256((s/k).read_bytes()).hexdigest()==v for k,v in initial.items())
subprocess.run(['git','-C',str(s),'add','--',*initial],check=True,capture_output=True)
subprocess.run(['git','-C',str(s),'commit','-m','Add explicit course file name search with native receiving'],check=True,capture_output=True)
old=subprocess.check_output(['git','-C',str(s),'rev-parse','HEAD'],text=True).strip()
for f in json.loads((r/'lint-correction.json').read_text(encoding='utf-8')):
 p=s/f['path'];(r/'evidence'/('pre-lint-'+p.name)).write_bytes(p.read_bytes());p.write_bytes(f['content'].encode('utf-8'))
diff=subprocess.check_output(['git','-C',str(s),'diff','--','src/canvaspilot/file_search.py','tests/test_file_search.py'],text=True)
(r/'evidence/lint-correction.diff').write_text(diff,encoding='utf-8')
env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(s/'src'),str(r/'dependencies'),str(r/'lint-tools')]);env['PYTHONDONTWRITEBYTECODE']='1'
runs=[]
for name,args in [('lint',['-m','ruff','check','--no-cache','src/canvaspilot/file_search.py','src/canvaspilot/cli.py','tests/test_file_search.py','tests/test_file_search_cli.py']),('tests',['-m','pytest','-q','-p','no:cacheprovider','tests/test_file_search.py','tests/test_file_search_cli.py','--junitxml='+str(r/'evidence/candidate-v2.xml')])]:
 start=time.time();p=subprocess.run([sys.executable,'-X','utf8','-B',*args],cwd=s,env=env,text=True,capture_output=True,timeout=120)
 (r/'evidence'/('candidate-v2-'+name+'.stdout')).write_text(p.stdout,encoding='utf-8');(r/'evidence'/('candidate-v2-'+name+'.stderr')).write_text(p.stderr,encoding='utf-8')
 runs.append({'name':name,'exit':p.returncode,'seconds':time.time()-start,'stdout':p.stdout,'stderr':p.stderr})
pins={k:hashlib.sha256((s/k).read_bytes()).hexdigest() for k in initial}
out={'original_product_head':old,'runs':runs,'product_pins':pins,'bar_peer_cases_sha256':hashlib.sha256(Path('D:/HAMON/offhand-bar-export-peer-cases-5f566b5ec8ef.json').read_bytes()).hexdigest(),'source_change':'two equivalent dict literals + explanatory command-boundary noqa, three test context compositions; no behavior/transport policy change'}
(r/'evidence/candidate-v2.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))
