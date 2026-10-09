import pathlib,json,shutil,subprocess,os
src=pathlib.Path('/home/jacob/canvas-attempt-69570d292200/original/src')
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(src)}
exe='/home/jacob/canvaspilot-enrollments-env-65ae877160f6/bin/python'
print(json.dumps({'space':{p:shutil.disk_usage(p).free for p in ['/','/dev/shm']}}))
for args in [['pages','42'],['page','42','course-introduction']]:
 p=subprocess.run([exe,'-B','-m','canvaspilot.cli',*args],env=env,capture_output=True,text=True,timeout=10)
 print(json.dumps({'argv':args,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}))
