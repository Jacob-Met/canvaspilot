import sys,json,hashlib,contextlib,io
from pathlib import Path
from unittest.mock import patch
r=Path(__file__).parent;s=r/'source';sys.path.insert(0,str(s/'src'))
import httpx
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.cli import main
rows=[{'id':11,'display_name':'Straße NOTES.pdf','filename':'notes.pdf','size':0,'content-type':'application/pdf','url':'https://unfollowed.invalid/a'},None,{'id':11,'display_name':None,'filename':'Résumé 📚.txt','size':2**60}]
requests=[]
def handle(q):
 requests.append({'method':q.method,'url':str(q.url)});return httpx.Response(200,json=rows,request=q)
c=CanvasClient(base_url='https://synthetic.invalid',token='synthetic-not-a-secret',profile=r/'unused-profile');c._http=httpx.Client(base_url=c.base_url,transport=httpx.MockTransport(handle))
out=CanvasAPI(c).list_files('42');c.close()
assert len(out)==2 and out[0]['size']==0 and out[1]['id']==11 and out[1]['size']==2**60
stdout=io.StringIO();stderr=io.StringIO();created=[]
def forbidden(*a,**kw):created.append(True);raise AssertionError('unexpected client')
with patch('canvaspilot.client.CanvasClient',forbidden),contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
 try:main(['find-files','42','--text','notes'])
 except SystemExit as e:status=e.code
assert status==2 and not created and not stdout.getvalue()
m=json.loads((r/'evidence/intake-receipt.json').read_text(encoding='utf-8'));assert all(hashlib.sha256((s/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in m['source_projection'])
receipt={'missing_command':{'exit':status,'stdout':stdout.getvalue(),'stderr':stderr.getvalue(),'client_constructions':len(created)},'actual_unchanged_reader':{'requests':requests,'raw_rows':rows,'normalized_rows':out,'client_closed':c._http is None},'inputs_unchanged':35,'profile_exists':(r/'unused-profile').exists(),'transport':'native HTTPX MockTransport with actual unchanged client/API; no network or account'}
(r/'evidence/baseline.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps({'baseline_passed':True,'missing_command_exit':status,'normalized_rows':len(out),'requests':len(requests),'inputs_unchanged':35}))
