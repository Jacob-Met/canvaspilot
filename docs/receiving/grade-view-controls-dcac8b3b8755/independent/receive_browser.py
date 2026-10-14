"""Original-first saved grade-view browser receiving; no API/reader/build calls."""
import argparse, base64, hashlib, json, os, platform, sys, tempfile, time, traceback
from pathlib import Path
from playwright.sync_api import sync_playwright

def ident(p):
    b=p.read_bytes();s=p.stat()
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'mode':s.st_mode,'mtime_ns':str(s.st_mtime_ns),'inode':str(s.st_ino)}
def inv(root):return {p.relative_to(root).as_posix():ident(p) for p in sorted(root.rglob('*')) if p.is_file()}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',required=True);ap.add_argument('--output',required=True);ap.add_argument('--mode',choices=['original','candidate'],required=True);ap.add_argument('--chrome',required=True);ap.add_argument('--baseline');a=ap.parse_args()
    src=Path(a.inputs).resolve();out=Path(a.output).resolve()
    if out.exists():raise RuntimeError('output must be new')
    out.mkdir(parents=True);temp=out/'process-temp';temp.mkdir();downloads=out/'browser-downloads';downloads.mkdir()
    os.environ['TEMP']=os.environ['TMP']=str(temp);tempfile.tempdir=str(temp)
    before=inv(src);criteria=json.loads((src/'criteria.json').read_text(encoding='utf-8'));source=json.loads((src/'source.json').read_text(encoding='utf-8'));prod=json.loads((src/'producer.json').read_text(encoding='utf-8'))
    baseline=None
    if a.baseline:baseline=json.loads(Path(a.baseline).read_text(encoding='utf-8'))
    result={'mode':a.mode,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source':source,'runtime':{'python':sys.version,'host':platform.node(),'user':os.environ.get('USERNAME'),'chrome':a.chrome},'checks':[],'before':before,'fixed':{},'downloads':[],'requests':[],'page_errors':[],'snapshots':[],'scope':'Saved HTML only; managed closure, print-media visibility, no browser OS-exit or physical print claim.'}
    pw=browser=context=nojs=None;passed=False
    def check(name,actual,expected):
        result['checks'].append({'name':name,'actual':actual,'expected':expected})
        if actual!=expected:raise RuntimeError(name)
    def ids(page):return page.locator('.assignment').evaluate_all('(xs)=>xs.filter(x=>getComputedStyle(x).display!=="none").map(x=>x.id)')
    def fixed(page):return page.evaluate('''() => ({cards:[...document.querySelectorAll('.assignment')].map(x=>({id:x.id,text:x.textContent})),groups:[...document.querySelectorAll('section.group')].map(x=>({id:x.id,title:x.querySelector('h2').textContent,facts:x.querySelector(':scope > .facts').textContent})),totals:document.querySelector('[aria-labelledby="totals-title"]').textContent,context:document.querySelector('[aria-labelledby="scope-title"]').textContent})''')
    def install_events(ctx):
        ctx.on('request',lambda r:result['requests'].append(r.url))
        ctx.route('http://**/*',lambda r:r.abort());ctx.route('https://**/*',lambda r:r.abort())
        ctx.on('page',lambda p:p.on('pageerror',lambda e:result['page_errors'].append(str(e))))
    def download(page,name,report):
        expected=(json.dumps(report,ensure_ascii=True,allow_nan=False,indent=2)+'\n').encode('ascii')
        with page.expect_download(timeout=15000) as info:page.locator('#download-report').click()
        dl=info.value;check(name+' suggested filename',dl.suggested_filename,'course-grade-review.json');check(name+' download failure',dl.failure(),None)
        target=out/(name+'.json');dl.save_as(str(target));check(name+' saved payload',target.read_bytes()==expected,True)
        check(name+' displayed sha',page.locator('#json-sha256').text_content(),hashlib.sha256(expected).hexdigest());result['downloads'].append({'name':name,**ident(target)})
    try:
        check('producer passed',prod['passed'],True);check('producer custody',prod['conserved'],True)
        check('source producer bind',prod['source_blob'],source['exporter_blob']);check('actual exporter',ident(src/'grade_review_export.py')['git_blob'],source['exporter_blob'])
        for name in ('mixed','hidden'):
            check(name+' page bytes',ident(src/(name+'.html'))['sha256'],prod['outputs'][name]['html']['sha256'])
        if a.mode=='candidate':
            check('original baseline passed',baseline['passed'],True);check('baseline mode',baseline['mode'],'original')
            check('same frozen criteria',before['criteria.json']['git_blob'],baseline['before']['criteria.json']['git_blob'])
        pw=sync_playwright().start();browser=pw.chromium.launch(executable_path=a.chrome,headless=True,downloads_path=str(downloads),env={**os.environ,'TEMP':str(temp),'TMP':str(temp)},args=['--no-first-run','--no-default-browser-check','--disable-background-networking'])
        result['runtime']['browser_version']=browser.version
        context=browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True,java_script_enabled=True);install_events(context);storage_before=context.storage_state();page=context.new_page()
        for name in ('mixed','hidden'):
            report=json.loads((src/(name+'.json')).read_text(encoding='utf-8'));page.goto((src/(name+'.html')).as_uri(),wait_until='load',timeout=30000)
            full=fixed(page);result['fixed'][name]=full
            check(name+' all assignment IDs',ids(page),criteria['all_cards']);check(name+' full group identities',page.locator('section.group').evaluate_all('(xs)=>xs.map(x=>x.id)'),criteria['group_ids'])
            check(name+' initial closed details',page.locator('.assignment details').evaluate_all('(xs)=>xs.map(x=>x.open)'),[False]*10)
            check(name+' inert literal markup',page.locator('.assignment h3 b').count(),0)
            check(name+' no inferred missing status',page.locator('#assignment-0-3').text_content().find('No grade or missing-work status is inferred.')>=0,True)
            check(name+' withheld visibility notices',page.locator('.assignment').filter(has_text='Withheld by the reader').count(),2)
            check(name+' stale warning',page.locator('#assignment-0-2').text_content().find('does not match the current submission')>=0,True)
            check(name+' unknown list states',all(s in page.locator('body').text_content() for s in ['Canvas returned null','Not returned by Canvas','empty assignment list']),True)
            if a.mode=='original':check(name+' no controls',page.locator('#grade-view-controls').count(),0)
            else:
                check(name+' complete static content unchanged',full,baseline['fixed'][name])
                check(name+' controls visible',page.locator('#grade-view-controls').is_visible(),True)
                check(name+' labels', [page.get_by_label(x,exact=True).count() for x in ['Find returned assignments','Returned group','Canvas reported flag']],[1,1,1])
            if name=='mixed':
                page.locator('#assignment-0-2 summary').click();check('manual disclosure opened',page.locator('#assignment-0-2 details').evaluate('(x)=>x.open'),True)
                if a.mode=='candidate':
                    for case in criteria['cases']:
                        page.locator('#grade-search').fill(case['search']);page.locator('#grade-group').select_option(case['group']);page.locator('#grade-flag').select_option(case['flag'])
                        check(case['name']+' visible order',ids(page),case['expected'])
                        check(case['name']+' visible count',page.locator('#grade-view-count').text_content(),'Showing %d of 10 returned assignment cards.'%len(case['expected']))
                        check(case['name']+' no match',page.locator('#grade-no-match').is_visible(),not bool(case['expected']))
                        check(case['name']+' disclosure retained',page.locator('#assignment-0-2 details').evaluate('(x)=>x.open'),True)
                        check(case['name']+' fixed content retained',fixed(page),full)
                    download(page,'mixed-filtered',report)
                    page.emulate_media(media='print');check('print restores all cards',ids(page),criteria['all_cards']);check('print controls suppressed',page.locator('#grade-view-controls').is_visible(),False)
                    check('print closed detail content visible',page.locator('#assignment-0-0 details > h4').first.is_visible(),True)
                    page.emulate_media(media='screen');check('screen filter restored after print',ids(page),[])
                    page.set_viewport_size({'width':390,'height':844});page.locator('#grade-search').focus()
                    focused=[]
                    for _ in range(5):
                        page.keyboard.press('Tab');label=page.evaluate('document.activeElement.id');focused.append(label)
                        if label=='grade-reset':break
                    check('native Tab reaches reset',focused[-1],'grade-reset');page.keyboard.press('Enter');check('keyboard reset restores all',ids(page),criteria['all_cards'])
                    check('reset retains disclosure',page.locator('#assignment-0-2 details').evaluate('(x)=>x.open'),True)
                    check('reset empty controls',[page.locator('#grade-search').input_value(),page.locator('#grade-group').input_value(),page.locator('#grade-flag').input_value()],['','',''])
                else:
                    page.emulate_media(media='print');check('original print all cards',ids(page),criteria['all_cards']);check('original closed detail printable',page.locator('#assignment-0-0 details > h4').first.is_visible(),True);page.emulate_media(media='screen');page.set_viewport_size({'width':390,'height':844})
                check('390 no document overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'),True)
                page.screenshot(path=str(out/'mixed-390.png'));download(page,'mixed-390',report)
                page.set_viewport_size({'width':1280,'height':900});page.screenshot(path=str(out/'mixed-desktop.png'))
            else:
                check('hidden course notice',page.locator('[aria-labelledby="totals-title"]').text_content().find('reader withheld enrollment totals')>=0,True)
                download(page,'hidden',report)
            check(name+' storage unchanged',context.storage_state(),storage_before)
        nojs=browser.new_context(viewport={'width':390,'height':844},java_script_enabled=False,accept_downloads=True);install_events(nojs);np=nojs.new_page()
        for name in ('mixed','hidden'):
            np.goto((src/(name+'.html')).as_uri(),wait_until='load');check(name+' noJS full cards',ids(np),criteria['all_cards']);check(name+' noJS controls unusable absent',np.locator('#grade-view-controls').is_visible(),False)
            check(name+' noJS full content',fixed(np),result['fixed'][name]);check(name+' noJS no overflow',np.evaluate('document.documentElement.scrollWidth<=innerWidth'),True)
        check('no external HTTP requests',[x for x in result['requests'] if x.startswith(('http:','https:'))],[]);check('no page errors',result['page_errors'],[])
        passed=True
    except Exception as e:result['error']=repr(e);result['traceback']=traceback.format_exc()
    finally:
        for name,obj in [('nojs_context',nojs),('context',context)]:
            if obj:
                try:obj.close();result[name+'_closed']=True
                except Exception as e:result[name+'_close_error']=repr(e);passed=False
        if browser:
            try:browser.close();result['managed_browser_disconnected']=not browser.is_connected();passed=passed and result['managed_browser_disconnected']
            except Exception as e:result['browser_close_error']=repr(e);passed=False
        if pw:
            try:pw.stop();result['playwright_stopped']=True
            except Exception as e:result['playwright_stop_error']=repr(e);passed=False
        result['after']=inv(src);result['source_inputs_preserved']=result['after']==before;passed=passed and result['source_inputs_preserved']
        result['passed']=passed;result['artifacts']={p.name:ident(p) for p in sorted(out.iterdir()) if p.is_file()}
        (out/'receiving.json').write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':passed,'mode':a.mode,'checks':len(result['checks']),'downloads':len(result['downloads']),'managed_browser_disconnected':result.get('managed_browser_disconnected'),'output':str(out)}))
    return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
