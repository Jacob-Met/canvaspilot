"""Call the public saved-report renderer once for each frozen fictional input."""
import argparse, base64, datetime, hashlib, importlib.util, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
def ident(p):
    b=p.read_bytes();s=p.stat()
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'mode':s.st_mode,'mtime_ns':str(s.st_mtime_ns),'inode':str(s.st_ino)}
def inv(p): return {str(q.relative_to(p)):ident(q) for q in sorted(p.rglob('*')) if q.is_file()}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--source-blob',required=True);ap.add_argument('--fixtures',required=True);ap.add_argument('--criteria',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    src=Path(a.source).resolve();fixtures=Path(a.fixtures).resolve();criteria=Path(a.criteria).resolve();out=Path(a.output).resolve()
    if out.exists(): raise RuntimeError('Output must be new')
    before={'source':inv(src.parent),'fixtures':inv(fixtures),'criteria':ident(criteria),'observer':ident(Path(__file__))}
    if ident(src)['git_blob']!=a.source_blob:raise RuntimeError('source pin mismatch')
    rules=json.loads(criteria.read_text(encoding='utf-8'));out.mkdir(parents=True)
    receipt={'source_blob':a.source_blob,'python':sys.version,'before':before,'checks':[],'outputs':{},'scope':'Public renderer only; no API, client, authentication, grade reader or CLI call.'}
    def check(name,actual,expected):
        receipt['checks'].append({'name':name,'actual':actual,'expected':expected})
        if actual!=expected:raise RuntimeError(name)
    try:
        spec=importlib.util.spec_from_file_location('frozen_grade_export',src);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        for name in ('mixed','hidden'):
            report=json.loads((fixtures/(name+'.json')).read_text(encoding='utf-8'))
            payload=(json.dumps(report,ensure_ascii=True,allow_nan=False,indent=2)+'\n').encode('ascii')
            html, metadata=mod.render_grade_review_report(report,generated_at=datetime.datetime.fromisoformat(rules['generated_at']))
            check(name+' json hash',metadata['json_sha256'],hashlib.sha256(payload).hexdigest())
            check(name+' encoded JSON present',base64.b64encode(payload).decode() in html.decode(),True)
            check(name+' groups',metadata['groups_returned'],5);check(name+' assignments',metadata['assignments_returned'],10)
            p=out/(name+'.html');p.open('xb').write(html);receipt['outputs'][name]={'html':ident(p),'render_metadata':metadata}
        receipt['passed']=True
    except Exception as e:receipt.update(passed=False,error=repr(e))
    finally:
        after={'source':inv(src.parent),'fixtures':inv(fixtures),'criteria':ident(criteria),'observer':ident(Path(__file__))};receipt['after']=after;receipt['conserved']=after==before
        if not receipt['conserved']:receipt['passed']=False
        (out/'receiving.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':receipt['passed'],'checks':len(receipt['checks']),'source_blob':a.source_blob,'outputs':receipt['outputs']}))
    return 0 if receipt['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
