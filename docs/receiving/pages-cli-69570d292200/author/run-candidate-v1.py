import datetime, hashlib, json, os, pathlib, shutil, subprocess
r=pathlib.Path('/dev/shm/evaluation-69570d292200-canvas-pages')
c=r/'candidate'; e=r/'evidence'
assert shutil.disk_usage('/dev/shm').free>128*1024*1024
def inventory(root):
 return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
before=inventory(c)
native=pathlib.Path('/home/jacob/canvaspilot-enrollments-env-65ae877160f6/bin')
env={**os.environ,'PYTHONPATH':str(c/'src'),'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(r)}
commands=[('focused-tests-v1',[str(native/'python'),'-B','-m','pytest','-q','-p','no:cacheprovider','tests/test_pages_cli.py','--junitxml='+str(e/'focused-tests-v1.xml')]),('focused-ruff-v1',[str(native/'ruff'),'check','--no-cache','src/canvaspilot/cli.py','tests/test_pages_cli.py'])]
rows=[]
for name,args in commands:
 started=datetime.datetime.now(datetime.UTC).isoformat()
 p=subprocess.run(args,cwd=c,env=env,capture_output=True,timeout=180)
 (e/(name+'.stdout')).write_bytes(p.stdout);(e/(name+'.stderr')).write_bytes(p.stderr)
 rows.append({'name':name,'argv':args,'cwd':str(c),'started':started,'exit':p.returncode,'stdoutSha256':hashlib.sha256(p.stdout).hexdigest(),'stderrSha256':hashlib.sha256(p.stderr).hexdigest()})
result={'commands':rows,'candidateSourceBefore':before,'candidateUnchanged':before==inventory(c),'baseSourceUnchanged':all(hashlib.sha256((pathlib.Path('/home/jacob/canvas-attempt-69570d292200/original')/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in json.loads((e/'original-source.json').read_text())),'freeBytes':shutil.disk_usage('/dev/shm').free}
(e/'candidate-v1.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='candidateSourceBefore'},indent=2))
