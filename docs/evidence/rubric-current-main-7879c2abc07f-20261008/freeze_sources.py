import ast,copy,datetime,hashlib,json,pathlib,shutil
ROOT=pathlib.Path('/dev/shm/canvaspilot-rubric-receiving-7879c2abc07f')
def digest(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def mapped(name):
 d=json.loads((ROOT/'inputs'/f'{name}-tree.json').read_text())
 return d,{f['path']:f for f in d['leaves']}
def same(a,b):return (a['mode'],a['type'],a['sha'])==(b['mode'],b['type'],b['sha'])
def tree_sha(leaves):
 root={}
 for row in leaves.values():
  node=root;parts=row['path'].split('/')
  for part in parts[:-1]:node=node.setdefault(part,{})
  node[parts[-1]]=(row['mode'],row['sha'])
 def visit(node):
  entries=[]
  for name,value in node.items():
   if isinstance(value,dict):mode,sha='40000',visit(value);order=name.encode()+b'/'
   else:mode,sha=value;order=name.encode()
   entries.append((order,mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(sha)))
  data=b''.join(e[1] for e in sorted(entries))
  return hashlib.sha1(b'tree '+str(len(data)).encode()+b'\0'+data).hexdigest()
 return visit(root)
trees={k:mapped(k) for k in ['current','owner','common']}
for k,(d,m) in trees.items():assert tree_sha(m)==d['sha'],k
current,owner,common=[trees[k][1] for k in ['current','owner','common']]
delta=json.loads((ROOT/'inputs/published-delta.json').read_text())
def hunks(patch):
 result=[]
 for line in patch.splitlines():
  if line.startswith('@@ '):result.append({'before':[],'after':[]})
  elif result and line.startswith((' ','-','+')):
   if line[0] in ' -':result[-1]['before'].append(line[1:])
   if line[0] in ' +':result[-1]['after'].append(line[1:])
 return result
for item in delta:
 path=item['path']
 text=(ROOT/'candidate'/path).read_text()
 for h in reversed(hunks(item['patch'])):
  before='\n'.join(h['after'])+'\n';after='\n'.join(h['before'])+'\n'
  assert text.count(before)==1,path
  text=text.replace(before,after,1)
 assert text.encode()==(ROOT/'baseline'/path).read_bytes(),path
baseline_api=(ROOT/'baseline/src/canvaspilot/api.py').read_text()
candidate_api=(ROOT/'candidate/src/canvaspilot/api.py').read_text()
owner_api=(ROOT/'inputs/published-api-683bc.py').read_text()
def methods(source):
 module=ast.parse(source)
 cls=next(n for n in module.body if isinstance(n,ast.ClassDef) and n.name=='CanvasAPI')
 return module,cls,{n.name:n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
bm,bc,bmethods=methods(baseline_api);cm,cc,cmethods=methods(candidate_api);om,oc,omethods=methods(owner_api)
assert set(bmethods)==set(cmethods)
allowed={'get_assignment','assignment_brief'}
for name in bmethods:
 if name not in allowed:
  assert ast.get_source_segment(baseline_api,bmethods[name])==ast.get_source_segment(candidate_api,cmethods[name]),name
for name in allowed:
 assert ast.get_source_segment(candidate_api,cmethods[name])==ast.get_source_segment(owner_api,omethods[name]),name
ch=next(n for n in cm.body if isinstance(n,ast.FunctionDef) and n.name=='_brief_rubric')
oh=next(n for n in om.body if isinstance(n,ast.FunctionDef) and n.name=='_brief_rubric')
assert ast.get_source_segment(candidate_api,ch)==ast.get_source_segment(owner_api,oh)
normalized=copy.deepcopy(cm)
normalized.body=[n for n in normalized.body if not (isinstance(n,ast.FunctionDef) and n.name=='_brief_rubric') and not (isinstance(n,ast.ImportFrom) and n.module in {'copy','math'})]
nc=next(n for n in normalized.body if isinstance(n,ast.ClassDef) and n.name=='CanvasAPI')
nc.body=[copy.deepcopy(bmethods[n.name]) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in allowed else n for n in nc.body]
assert ast.dump(normalized,include_attributes=False)==ast.dump(bm,include_attributes=False)
rows=[]
for generation in ['baseline','candidate']:
 for p in sorted((ROOT/generation).rglob('*')):
  if not p.is_file():continue
  rel=str(p.relative_to(ROOT/generation));data=p.read_bytes()
  if generation=='baseline':assert blob(data)==current[rel]['sha'],rel
  elif rel not in {d['path'] for d in delta}:
   expected=current.get(rel,owner.get(rel));assert expected and blob(data)==expected['sha'],rel
  rows.append({'path':str(p.relative_to(ROOT)),'repository_path':rel,'generation':generation,'bytes':len(data),'sha256':digest(data),'git_blob':blob(data)})
assert len([r for r in rows if r['generation']=='baseline'])==35
assert len([r for r in rows if r['generation']=='candidate'])==37
added=sorted(set(owner)-set(common))
assert len(added)==58 and not set(added)&set(current)
assert not(set(common)-set(owner))
owner_changed=sorted(p for p in common if not same(common[p],owner[p]))
assert owner_changed==sorted(d['path'] for d in delta)
proposal=copy.deepcopy(current)
for path in added:proposal[path]=copy.deepcopy(owner[path])
for row in rows:
 if row['generation']=='candidate' and row['repository_path'] in owner_changed:
  proposal[row['repository_path']]={**proposal[row['repository_path']],'sha':row['git_blob'],'size':row['bytes']}
assert len(proposal)==347
assert sum(same(current[p],proposal[p]) for p in current)==285
assert all(same(owner[p],proposal[p]) for p in added)
source_manifest={'schema':'canvas.current.rubric.receiving.inputs.v1','time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'current_main':'a03a8637efad8ff22103a0c5018c93f7ecbb7d8d','owner_head':'683bc43de81661f52d9c64f3db00954b52da1205','source_only_tree':tree_sha(proposal),'baseline_files':35,'candidate_files':37,'files':rows}
(ROOT/'evidence/source-input-manifest.json').write_text(json.dumps(source_manifest,indent=2)+'\n')
proof={'schema':'canvas.current.rubric.independent.source.review.v1','time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'public_trees_reconstructed':{k:d['sha'] for k,(d,m) in trees.items()},'source_only_tree':tree_sha(proposal),'prospective_source_leaves':347,'current_preserved_leaves':285,'changed_current_paths':owner_changed,'original_additive_paths_preserved':58,'removed':0,'all_four_deltas_reverse_to_current_exact':True,'API_methods':len(bmethods),'unchanged_API_methods':len(bmethods)-2,'unchanged_entire_API_structure_outside_reviewed_additions':True,'helper_getter_brief_identical_to_published_owner':True,'feedback_method_exact_current':True,'private_guard':{'path':'guard/sitecustomize.py','sha256':digest((ROOT/'guard/sitecustomize.py').read_bytes()),'part_of_source_proposal':False},'source_files_verified':len(rows),'native_receiving_status':'pending','source_branch_writes':False}
(ROOT/'evidence/source-review.json').write_text(json.dumps(proof,indent=2)+'\n')
proposal_doc={'schema':'canvas.current.rubric.source.proposal.v1','kind':'computed source-only tree; no Git object or ref created','prospective_parents':['683bc43de81661f52d9c64f3db00954b52da1205','a03a8637efad8ff22103a0c5018c93f7ecbb7d8d'],'tree':tree_sha(proposal),'leaves':[proposal[p] for p in sorted(proposal)],'materialized_inputs':'evidence/source-input-manifest.json','new_receiving_evidence_included':False}
(ROOT/'SOURCE-PROPOSAL.json').write_text(json.dumps(proposal_doc,indent=2)+'\n')
print(json.dumps({**proof,'changed_blobs':[{k:r[k] for k in ['repository_path','bytes','git_blob','sha256']} for r in rows if r['generation']=='candidate' and r['repository_path'] in owner_changed],'free_bytes':shutil.disk_usage(ROOT).free},indent=2))
