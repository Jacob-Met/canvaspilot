import subprocess,sys,os,json,time
from pathlib import Path
r=Path(__file__).parent
env=os.environ.copy();env['PYTHONPATH']=str(r/'dependencies');env['PYTHONDONTWRITEBYTECODE']='1'
p=subprocess.run([sys.executable,'-X','utf8','-B',str(r/'baseline.py')],env=env,text=True,capture_output=True,timeout=60)
(r/'evidence/baseline-v2.stdout').write_text(p.stdout,encoding='utf-8');(r/'evidence/baseline-v2.stderr').write_text(p.stderr,encoding='utf-8')
out={'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'environment_phase':'private mcp2.3.0 satisfies unchanged project dependency range; original system1.29.1 import failure preserved','source_edits_before_baseline':0}
(r/'evidence/baseline-v2-process.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))
