from pathlib import Path
import subprocess,json,os,datetime,hashlib
R=Path(__file__).resolve().parents[3]
E=R/'docs/receiving/calendar-events-65ae877160f6'
PY='/home/jacob/canvaspilot-enrollments-env-65ae877160f6/bin/python'
env={'PATH':os.defpath,'PYTHONPATH':str(R/'src'),'PYTHONDONTWRITEBYTECODE':'1','LANG':'C.UTF-8'}
commands=[('existing-cli-regressions',[PY,'-B','-m','pytest','-q',str(R/'tests/test_enrollments_cli.py'),str(R/'tests/test_course_agenda_process.py'),'-k','not registered_mcp']),('changed-file-lint',[PY,'-B','-m','ruff','check',str(R/'src/canvaspilot/cli.py'),str(R/'tests/test_calendar_events_cli.py')])]
records=[]
for name,argv in commands:
 rec={'name':name,'argv':argv,'started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':'started'};records.append(rec);(E/'regression-gates.json').write_text(json.dumps(records,indent=2)+'\n')
 try:
  p=subprocess.run(argv,cwd=R,env=env,capture_output=True,text=True,timeout=240)
  rec.update(state='completed',exit=p.returncode,stdout=p.stdout,stderr=p.stderr,ended=datetime.datetime.now(datetime.timezone.utc).isoformat())
 except subprocess.TimeoutExpired as ex:
  rec.update(state='timeout',stdout=str(ex.stdout),stderr=str(ex.stderr))
 (E/'regression-gates.json').write_text(json.dumps(records,indent=2)+'\n')
 print(json.dumps(rec),flush=True)
