from pathlib import Path
import base64,json,hashlib,sys
from datetime import datetime
from html.parser import HTMLParser
root,proof=map(Path,sys.argv[1:]);sys.path.insert(0,str(root/'src'))
from canvaspilot.submission_history_export import render_submission_history_report
class Download(HTMLParser):
 href=None
 def handle_starttag(self,tag,attrs):
  values=dict(attrs)
  if tag=='a' and values.get('id')=='download-history':self.href=values['href']
checks=[]
for name,label in [('submission-history.html','full-export'),('unavailable.html','unavailable'),('empty.html','empty')]:
 original=(proof/'candidate'/name).read_bytes();document=Download();document.feed(original.decode('utf-8'));report=json.loads(base64.b64decode(document.href.split(',',1)[1]))
 summary=json.loads((proof/'candidate'/(label+'.stdout.txt')).read_bytes());stamp=datetime.fromisoformat(summary['generated_at'].replace('Z','+00:00'))
 candidate,metadata=render_submission_history_report(report,course_id=summary['requested_course_id'],assignment_id=summary['requested_assignment_id'],generated_at=stamp)
 assert candidate==original,name
 checks.append({'file':name,'bytes':len(original),'sha256':hashlib.sha256(original).hexdigest(),'byte_identical':True})
module=root/'src/canvaspilot/submission_history_export.py';receipt={'source_sha256':hashlib.sha256(module.read_bytes()).hexdigest(),'checks':checks,'source_changes':'Explicit concatenation parentheses (AST-equal), import wrapping, malformed-object TypeError, and intentional-naive-date test lint annotation. No successful output changed.'}
(proof/'lint-byte-equivalence.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt))
