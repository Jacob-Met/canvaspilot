from __future__ import annotations
from pathlib import Path
import base64, hashlib, json, sys
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parent
packet=json.loads((ROOT/'current-primary.json').read_text())
SOURCE=ROOT/'source'
def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
pins=[]
for entry in packet['sources']:
    if not entry['path'].endswith('.py'):
        continue
    data=base64.b64decode(entry['content'])
    assert blob(data)==entry['sha'],entry['path']
    path=SOURCE/Path(entry['path']).relative_to('src')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    pins.append({'path':entry['path'],'git_blob':entry['sha']})
init=Path('/workspace/scratch/0ee86eaeaf8d/production/canvaspilot/src/canvaspilot/__init__.py').read_bytes()
assert blob(init)=='74a7a6087bf81fd7c75c15769b30408039618e0f'
(SOURCE/'canvaspilot/__init__.py').write_bytes(init)
pins.append({'path':'src/canvaspilot/__init__.py','git_blob':blob(init)})
sys.path.insert(0,str(SOURCE))
import httpx
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient
BASE='https://canvas.example.test'
NEXT=BASE+'/api/v1/announcements?cursor=after%2B50&per_page=50'
rows=[{'id':i,'title':f'Notice {i}','posted_at':'2026-10-08T12:00:00Z','context_code':'course_7' if i%2 else 'course_9','message':'<p>'+('x'*410)+f' {i} &amp; details</p>','html_url':BASE+f'/courses/7/discussion_topics/{i}'} for i in range(1,62)]
params=[('active_only',True),('per_page',50),('context_codes[]','course_7'),('context_codes[]','course_9'),('start_date','2026-10-01')]
def client_for(*,later_error=False,terminal=False):
    requests=[]
    def respond(request):
        assert request.method=='GET'
        assert request.url.host=='canvas.example.test'
        assert request.url.path=='/api/v1/announcements'
        requests.append(str(request.url))
        if request.url.params.get('cursor'):
            if later_error:
                return httpx.Response(403,json={'error':'fixture refuses continuation'})
            return httpx.Response(200,json=rows[50:])
        if terminal:
            return httpx.Response(200,json=rows[:1])
        return httpx.Response(200,json=rows[:50],headers={'Link':f'<{NEXT}>; rel="next"'})
    client=CanvasClient(base_url=BASE,token='offline-fixture-token',profile=ROOT/'unused-fixture-profile')
    client._http=httpx.Client(base_url=BASE,transport=httpx.MockTransport(respond))
    return client,requests
cases=[]
for detail in ['compact','full']:
    client,requests=client_for()
    with client:
        actual=CanvasAPI(client).list_announcements([7,9],start_date='2026-10-01',detail=detail)
    cases.append({'name':detail+'_returns_complete_paginated_announcements','passed':len(actual)==61,'expected_count':61,'actual_count':len(actual),'actual_ids':[a['id'] for a in actual],'requests':requests,'first_message_chars':len(actual[0]['message_text'])})
client,requests=client_for()
with client:
    actual=client.get_paginated('/api/v1/announcements',params=params)
cases.append({'name':'existing_client_follows_identical_continuation','passed':[a['id'] for a in actual]==list(range(1,62)) and requests[1]==NEXT,'actual_count':len(actual),'requests':requests})
client,requests=client_for(later_error=True)
api_error=None
with client:
    try:
        actual=CanvasAPI(client).list_announcements([7,9],start_date='2026-10-01')
    except CanvasAuthError as exc:
        api_error=type(exc).__name__
cases.append({'name':'announcement_api_propagates_later_page_auth_failure','passed':api_error=='CanvasAuthError','observed_error':api_error,'returned_count':None if api_error else len(actual),'requests':requests})
client,requests=client_for(later_error=True)
direct_error=None
with client:
    try:
        client.get_paginated('/api/v1/announcements',params=params)
    except CanvasAuthError as exc:
        direct_error=type(exc).__name__
cases.append({'name':'existing_paginator_refuses_later_page_auth_failure','passed':direct_error=='CanvasAuthError','observed_error':direct_error,'requests':requests})
client,requests=client_for(terminal=True)
with client:
    actual=CanvasAPI(client).list_announcements([7,9],start_date='2026-10-01')
cases.append({'name':'terminal_single_page_is_unchanged','passed':len(actual)==1 and actual[0]['id']==1 and len(requests)==1,'requests':requests})
for entry in pins:
    assert blob((SOURCE/Path(entry['path']).relative_to('src')).read_bytes())==entry['git_blob']
receipt={'decision':'confirmed_native_baseline_defect' if any(not c['passed'] for c in cases) else 'all_contracts_pass','repo':packet['repo'],'main':packet['main'],'source_pins':pins,'python':sys.version,'httpx':httpx.__version__,'network':'No socket or browser requests. Actual CanvasClient used an httpx.MockTransport with synthetic data and dummy token. No account or environment credential was read for authentication.','cases':cases,'source_unchanged':True,'official_contract_url':'https://canvas.instructure.com/doc/api/announcements.html','official_contract':'The endpoint returns a paginated list for the requested courses and date range.','ownership':'Read-only investigation only; no claim, product edit, or external post.'}
text=json.dumps(receipt,indent=2)+'\n'
(ROOT/'baseline-receiving.json').write_text(text)
print(text)
raise SystemExit(0 if all(c['passed'] for c in cases) else 1)
