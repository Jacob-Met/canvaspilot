import sys,os,json,subprocess,threading,time,hashlib
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
r=Path(__file__).parent;s=r/'source';requests=[]
class H(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  requests.append({'method':'GET','path':self.path})
  if self.path.startswith('/api/v1/courses/42/files'):
   if 'cursor=' in self.path:
    rows=[{'id':5,'display_name':None,'filename':'LAB NOTES.txt','size':2**60}]
   else:
    rows=[{'id':5,'display_name':'Lab notes 📚.pdf','filename':'lab.pdf','size':0,'url':'https://do-not-follow.invalid/file'},None]
  elif self.path.startswith('/api/v1/courses/77/files'):
   rows=[{'id':5,'display_name':None,'filename':'other'},{'id':6,'display_name':'','filename':''}]
  elif self.path.startswith('/api/v1/courses/88/files'):
   self.send_response(503);self.end_headers();self.wfile.write(b'synthetic unavailable');return
  else:
   self.send_response(404);self.end_headers();return
  body=json.dumps(rows,ensure_ascii=False).encode('utf-8');self.send_response(200)
  if '/42/' in self.path and 'cursor=' not in self.path:self.send_header('Link',f'<http://127.0.0.1:{self.server.server_port}/api/v1/courses/42/files?cursor=opaque%2B2>; rel="next"')
  self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
server=ThreadingHTTPServer(('127.0.0.1',0),H);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(s/'src'),str(r/'dependencies')]);env['PYTHONDONTWRITEBYTECODE']='1';env['NO_PROXY']='127.0.0.1';env.pop('CANVAS_API_TOKEN',None)
phase=r/'evidence/process-consumer';phase.mkdir();pins=json.loads((r/'evidence/candidate-v1.json').read_text(encoding='utf-8'))['product_pins'];runs=[]
try:
 for label,courses,expected in [('complete',['0042','77'],0),('later-course-error',['42','88'],1),('invalid-selection',['42','042'],1)]:
  before=len(requests);profile=phase/(label+'-unused-profile');argv=[sys.executable,'-X','utf8','-B','-m','canvaspilot.cli','find-files',*courses,'--text','Lab notes','--base-url',f'http://127.0.0.1:{server.server_port}','--token','synthetic-not-an-account','--profile',str(profile)]
  start=time.time();p=subprocess.run(argv,cwd=s,env=env,text=True,capture_output=True,timeout=30)
  (phase/(label+'.stdout')).write_bytes(p.stdout.encode());(phase/(label+'.stderr')).write_bytes(p.stderr.encode())
  assert p.returncode==expected,(label,p.returncode,p.stderr)
  calls=requests[before:];assert not profile.exists()
  if expected==0:
   report=json.loads(p.stdout);assert report['counts']=={'returned':4,'matched':2,'nonmatching':1,'unknown':1};assert report['course_ids']==['42','77'];assert report['courses'][0]['observations'][1]['source']['size']==2**60;assert not p.stderr;assert len(calls)==3
  else:
   assert not p.stdout;assert json.loads(p.stderr)['ok'] is False;assert len(calls)==(0 if label=='invalid-selection' else 3)
  runs.append({'label':label,'exit':p.returncode,'seconds':time.time()-start,'requests':calls,'stdout_sha256':hashlib.sha256(p.stdout.encode()).hexdigest(),'stderr_sha256':hashlib.sha256(p.stderr.encode()).hexdigest(),'profile_created':False})
finally:
 server.shutdown();server.server_close();thread.join()
assert all(hashlib.sha256((s/k).read_bytes()).hexdigest()==v for k,v in pins.items())
out={'passed':len(runs),'runs':runs,'transport':'actual child python -m canvaspilot.cli and unchanged HTTPX client against private loopback HTTP server','product_inputs_unchanged':True,'server_closed':True,'no_provider_or_account_operation':True}
(phase/'receipt.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))
