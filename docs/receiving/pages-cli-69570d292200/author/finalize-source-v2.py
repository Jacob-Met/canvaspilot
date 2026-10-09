import difflib, hashlib, json, pathlib, xml.etree.ElementTree as ET
r=pathlib.Path('/dev/shm/evaluation-69570d292200-canvas-pages'); c=r/'candidate';e=r/'evidence';o=pathlib.Path('/home/jacob/canvas-attempt-69570d292200/original')
def need(x,m):
 if not x: raise AssertionError(m)
def obj(t,b): return hashlib.sha1((t+' '+str(len(b))+'\0').encode()+b).hexdigest()
def blob(b): return obj('blob',b)
def tree_hash(rows):
 root={}
 for path,item in rows.items():
  parts=path.split('/');cur=root
  for p in parts[:-1]:cur=cur.setdefault(p,{})
  cur[parts[-1]]=item
 def walk(d):
  a=[]
  for name,v in d.items():
   direct='sha' in v;mode=v['mode'] if direct else '40000';h=v['sha'] if direct else walk(v)
   a.append((name.encode()+(b'' if direct else b'/'),mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(h)))
  return obj('tree',b''.join(v for _,v in sorted(a)))
 return walk(root)
base=json.loads((e/'base-tree.json').read_text()); leaves={x['path']:{k:x[k] for k in ('mode','type','sha')} for x in base['tree'] if x['type']!='tree'}
need(base['sha']=='56a72a2e2cee5ec04671d12ebe5bc2484afb8026','connector requested commit reference')
need(tree_hash(leaves)=='a07c3e941219ff80968e1ff20528a63541bb7400','original full tree from accepted commit metadata')
paths=['src/canvaspilot/cli.py','README.md','tests/test_pages_cli.py','docs/pages-cli.md']
original=json.loads((e/'original-source.json').read_text())
for x in original:
 b=(o/x['path']).read_bytes();need(blob(b)==x['sha'],'original source exact')
 if x['path'] not in paths:need((c/x['path']).read_bytes()==b,'untouched native source')
for path in ['src/canvaspilot/cli.py','README.md']:
 before=(o/path).read_text().splitlines(keepends=True);after=(c/path).read_text().splitlines(keepends=True)
 need(all(tag in ('equal','insert') for tag,*_ in difflib.SequenceMatcher(None,before,after,autojunk=False).get_opcodes()),'only additive source '+path)
delta=[];final=dict(leaves)
for path in paths:
 b=(c/path).read_bytes();pin={'mode':'100644','type':'blob','sha':blob(b)};final[path]=pin;delta.append({'path':path,**pin,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'content':b.decode()})
result=json.loads((e/'candidate-v3.json').read_text())
need(result['candidateUnchanged'] and result['baseSourceUnchanged'],'native preservation receipt')
need(all(x['exit']==0 for x in result['commands']),'native focused tests and ruff')
for x in result['commands']:
 for stream in ['stdout','stderr']:
  need(hashlib.sha256((e/(x['name']+'.'+stream)).read_bytes()).hexdigest()==x[stream+'Sha256'],'raw command log '+x['name'])
tests=list(ET.parse(e/'focused-tests-v3.xml').getroot().iter('testcase'));need(len(tests)==18 and all(not x.findall('failure') and not x.findall('error') and not x.findall('skipped') for x in tests),'18 successful unskipped tests')
need(result['candidateSourceBefore']['src/canvaspilot/cli.py']==json.loads((e/'candidate-v2.json').read_text())['candidateSourceBefore']['src/canvaspilot/cli.py'],'product CLI unchanged after first completed qualification')
proof={'baseCommit':'56a72a2e2cee5ec04671d12ebe5bc2484afb8026','baseTree':tree_hash(leaves),'connectorTreeResponseReference':base['sha'],'productTree':tree_hash(final),'baseLeaves':len(leaves),'productLeaves':len(final),'unrelatedBaseLeavesExact':len(leaves)-2,'maintainedPaths':[{k:v for k,v in x.items() if k!='content'} for x in delta],'nativeOriginalSourceFiles':len(original),'nativeUnchangedFiles':len(original)-2,'focusedTests':18,'focusedRuff':'PASS','productSourceUnchangedAcrossQualification':True,'boundary':'Virtual complete product tree computed from exact accepted tree plus four maintained files; native Git custody is a source/evidence projection. No remote object or ref publication, current-main refresh, live Canvas, build or dependency installation.'}
(e/'source-proof.json').write_text(json.dumps(proof,indent=2)+'\n');(e/'maintained-source-patch.json').write_text(json.dumps(delta,indent=2)+'\n');(e/'product-tree.json').write_text(json.dumps({'sha':tree_hash(final),'tree':[{'path':p,**v} for p,v in sorted(final.items())]},indent=2)+'\n')
print(json.dumps(proof,indent=2))
