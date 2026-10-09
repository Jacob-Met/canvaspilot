import sys,subprocess,json,os,importlib.metadata,time
from pathlib import Path
r=Path(__file__).parent
original={'python':sys.version,'mcp':importlib.metadata.version('mcp'),'failure':'baseline import failed before product execution: no mcp.server.mcpserver','original_source_unchanged':True}
(r/'evidence/baseline-environment-failure.json').write_text(json.dumps(original,indent=2)+'\n',encoding='utf-8')
d=r/'dependencies';assert not d.exists()
env=os.environ.copy();env['PIP_INDEX_URL']='https://pypi.org/simple';env['PIP_DISABLE_PIP_VERSION_CHECK']='1'
start=time.time();p=subprocess.run([sys.executable,'-m','pip','install','--no-cache-dir','--target',str(d),'mcp==2.3.0'],env=env,text=True,capture_output=True,timeout=300)
(r/'evidence/dependency-install.stdout').write_text(p.stdout,encoding='utf-8');(r/'evidence/dependency-install.stderr').write_text(p.stderr,encoding='utf-8')
out={'exit':p.returncode,'seconds':time.time()-start,'original':original,'target':str(d),'command':'private target mcp==2.3.0 from standard PyPI, no shared environment edits','stdout_bytes':len(p.stdout.encode()),'stderr_bytes':len(p.stderr.encode())};(r/'evidence/dependency-install.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))
