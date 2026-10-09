import subprocess,sys,os,json,hashlib,time
from pathlib import Path
r=Path(__file__).parent;s=r/'source';target=r/'lint-tools'
assert not target.exists()
env=os.environ.copy();env['PIP_INDEX_URL']='https://pypi.org/simple';env['PIP_DISABLE_PIP_VERSION_CHECK']='1'
start=time.time();p=subprocess.run([sys.executable,'-m','pip','install','--no-cache-dir','--target',str(target),'ruff>=0.4'],env=env,text=True,capture_output=True,timeout=180)
(r/'evidence/lint-install.stdout').write_text(p.stdout,encoding='utf-8');(r/'evidence/lint-install.stderr').write_text(p.stderr,encoding='utf-8')
assert p.returncode==0,p.stderr
env['PYTHONPATH']=str(target);env['PYTHONDONTWRITEBYTECODE']='1'
v=subprocess.run([sys.executable,'-m','ruff','--version'],env=env,text=True,capture_output=True,check=True)
p=subprocess.run([sys.executable,'-m','ruff','check','src/canvaspilot/file_search.py','src/canvaspilot/cli.py','tests/test_file_search.py','tests/test_file_search_cli.py','--output-format','json'],cwd=s,env=env,text=True,capture_output=True,timeout=60)
out={'version':v.stdout.strip(),'exit':p.returncode,'diagnostics':json.loads(p.stdout),'stderr':p.stderr,'elapsed_including_private_setup':time.time()-start,'scope':'four changed Python files, unchanged native declared dev dependency range'}
(r/'evidence/lint-v1.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))
