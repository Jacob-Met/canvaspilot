import subprocess,sys,os,json
from pathlib import Path
r=Path(__file__).parent;s=r/'source';env=os.environ.copy();env['PYTHONPATH']=str(r/'lint-tools')
def run(a):return subprocess.run([sys.executable,'-m','ruff',*a],cwd=s,env=env,text=True,capture_output=True,timeout=30)
q=run(['check','--show-settings','src/canvaspilot/file_search.py'])
(r/'evidence/lint-settings-v1.txt').write_text(q.stdout,encoding='utf-8')
p=run(['check','--config','pyproject.toml','src/canvaspilot/file_search.py','src/canvaspilot/cli.py','tests/test_file_search.py','tests/test_file_search_cli.py','--output-format','json'])
out={'settings_header':q.stdout.splitlines()[:8],'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'configuration':'exact unchanged receiving pyproject.toml explicitly selected; no source/config edit'}
(r/'evidence/lint-v2-explicit-project.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))
