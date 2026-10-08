from pathlib import Path
import hashlib, json, os, subprocess, sys, time
root=Path('/home/jacob/canvaspilot-history-0378a7b6-linux')
proof=root.parent/'canvaspilot-history-0378a7b6-linux-proof'
proof.mkdir(exist_ok=True)
pins={'README.md':'b952f2c4d0f2e632cd4aaa96e430d89338e0eadf','docs/submission-history-export.md':'580ac5db2024e6f692c241eac399ee3b709f53ea','src/canvaspilot/cli.py':'743b1ec2c7157600d5882be55d500d1e38d3a64b','src/canvaspilot/submission_history_export.py':'bc94606454e7d5cb880a5d281716cd7ee0dfb8ac','tests/test_submission_history_export.py':'9a921968e8a3788780ea21689fe6dc17e913e857'}
blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
for name,pin in pins.items():
 p=root/name; b=p.read_bytes()
 if blob(b)!=pin and blob(b+b'\n')==pin: p.write_bytes(b+b'\n')
 assert blob(p.read_bytes())==pin,(name,blob(p.read_bytes()),pin)
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()=='a5e7bec9f93132341e4031de184487310a51daae'
subprocess.run(['git','-C',str(root),'add','--',*pins],check=True)
tree=subprocess.check_output(['git','-C',str(root),'write-tree'],text=True).strip()
assert tree=='bec620b72b9ed59f4d99981e80728a90a880a955',tree
python='/home/jacob/canvaspilot-announcements-3dcb83a1/.venv/bin/python'
env=dict(os.environ,PYTHONPATH=str(root/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
receipt={'started':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source_commit':'6fdb3dc955426da7667e1f4e3844c6741077369f','source_tree':tree,'all_five_git_blobs_exact':True,'python':python,'steps':[]}
for name,args in [('runtime',['-c','import sys,importlib.metadata as m;print(sys.version);print({n:m.version(n) for n in ("pytest","ruff","httpx","mcp","pydantic")})']),('ruff',['-m','ruff','check','src','tests','scripts']),('pytest',['-m','pytest','-q','-o','cache_dir='+str(proof/'pytest-cache')])]:
 with (proof/(name+'.log')).open('w') as log:
  result=subprocess.run([python,*args],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
 receipt['steps'].append({'name':name,'status':result.returncode})
 (proof/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 if result.returncode: sys.exit(result.returncode)
receipt['finished']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
(proof/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
