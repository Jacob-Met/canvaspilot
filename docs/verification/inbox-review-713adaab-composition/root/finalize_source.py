README_TEXT = "# Inbox review: composition and receiving supplement\n\nThe independent receiver qualified native source `6b94efe9ff1f117fe4c2f1dfca595003a283d988`, tree `2fbc6ac949bbdc5c3b048f93137197621ed81546`, which receives main `0d1898544a90079e2dcc7ceb3fa4bc6bca88a2bc`. All 14 groups passed, with no skips/errors and all 13 runtime source files unchanged before and after. The complete immutable peer supplement is under `peer/`, including its own manifest, exact successful driver, raw cases, logs, JUnit and source review.\n\nThe receiver used a small private /dev/shm result directory after two /tmp setup stops caused by the current user's tmpfs quota. Both stops occurred before tests. The successful run bound the frozen owner source read-only and retained the same test files and network/profile guards. It exercised actual token HTTP, session envelopes, CLI subprocesses and registered MCP stdio against authored loopback data. Its session fixture models the broker provider response; it does not execute a browser or SSO.\n\nAfter that replay, submission-history PR53 landed as main `39d835c8becb04d81b65c90d1491d2d3a2727ffe`. The final native source composition merges it cleanly. The source-preservation receipt under `root/` checks that the inbox methods, parser/dispatch additions, and MCP metadata remain exactly as qualified, and that all other API/CLI/MCP syntax, README bytes and current-main leaves are preserved. Ruff also passes on that later composition. The full hosted suite on the published head is its subsequent runtime integration gate; the earlier 14-group receipt retains its precise source identity.\n\n`root/` keeps the native Git checkpoints, merge previews, Ruff output and exact source-composition procedure. The original source/negative-run packet at `../inbox-review-713adaab/` remains unchanged, including its peer manifest `988cc00f8c51d6fdeef57b5b77b53e28b4defd1c423b4f65ddba65e7414dfca5`.\n\nThe root inventory hashes every supplement payload except itself. The peer manifest remains byte-identical and inventories only its own peer subtree. Git binds each inventory's own bytes. Neither this supplement nor the original receipts claim live-school receiving, installation, service activation or migration/cutover.\n"
from pathlib import Path
import ast,copy,subprocess,json,hashlib,shutil,os,datetime
repo=Path('/tmp/canvaspilot-inbox-713adaab')
out=Path('/tmp/canvaspilot-inbox-evidence-713adaab/publication')
peer=Path('/dev/shm/canvaspilot-inbox-composition-713adaab')
old='6b94efe9ff1f117fe4c2f1dfca595003a283d988'
main='39d835c8becb04d81b65c90d1491d2d3a2727ffe'
qualified='db32bde55db5080ed7ee856faab5cf1a2b5c949a'
base='ca2318fe7c56d2e4ec1b363ff8a945ab78bf4a0c'
def git(*args):
    return subprocess.run(['git','-C',str(repo),*args],capture_output=True,check=True).stdout
def content(ref,path):
    return git('show',ref+':'+path)
def parsed(ref,name):
    return ast.parse(content(ref,'src/canvaspilot/'+name))
def dump(node):
    return ast.dump(node,include_attributes=False)
def api_methods(tree):
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='CanvasAPI')
    return {n.name:n for n in cls.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in ('list_conversations','get_conversation')}
def without_api(tree):
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='CanvasAPI')
    cls.body=[n for n in cls.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) or n.name not in ('list_conversations','get_conversation')]
    return tree
def tools_for(tree):
    return {n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in ('canvas_list_conversations','canvas_get_conversation')}
def without_metadata(tree):
    for n in tools_for(tree).values():
        n.decorator_list=[]
    return tree
def added_parser(n):
    if isinstance(n,ast.Assign):
        return len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('inbox','conversation')
    if not isinstance(n,ast.Expr) or not isinstance(n.value,ast.Call):
        return False
    c=n.value
    if isinstance(c.func,ast.Name) and c.func.id=='add_common':
        return len(c.args)==1 and isinstance(c.args[0],ast.Name) and c.args[0].id in ('inbox','conversation')
    return isinstance(c.func,ast.Attribute) and isinstance(c.func.value,ast.Name) and c.func.value.id in ('inbox','conversation')
class StripDispatch(ast.NodeTransformer):
    def __init__(self):
        self.removed=[]
    def visit_If(self,node):
        self.generic_visit(node)
        t=node.test
        if (isinstance(t,ast.Compare) and dump(t.left)==dump(ast.parse('args.cmd',mode='eval').body)
            and len(t.ops)==1 and isinstance(t.ops[0],ast.In) and len(t.comparators)==1
            and dump(t.comparators[0])==dump(ast.parse('("inbox", "conversation")',mode='eval').body)):
            self.removed.append(dump(ast.Module(body=node.body,type_ignores=[])))
            assert len(node.orelse)==1
            return node.orelse[0]
        return node
def strip_cli(tree):
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    additions=[dump(n) for n in function.body if added_parser(n)]
    assert len(additions)==6
    function.body=[n for n in function.body if not added_parser(n)]
    transform=StripDispatch()
    result=transform.visit(tree)
    assert len(transform.removed)==1
    return result,additions,transform.removed
assert git('rev-parse','HEAD').decode().strip()==old and not git('status','--porcelain=v1')
p=peer/'manifest.json'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='2aa7a08447fb4e29863fdf4610553eb879e23b184373573ed3133ed0346876d4'
manifest=json.loads(p.read_bytes())
for name,item in manifest['files'].items():
    b=(peer/name).read_bytes()
    assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256']
git('merge','--no-ff','-m','Merge submission history while preserving inbox review',main)
composed=git('rev-parse','HEAD').decode().strip()
tree=git('rev-parse','HEAD^{tree}').decode().strip()
assert tree=='428308de0eea2eeaf37772c5892c939a09d553d7'
current_api=parsed(composed,'api.py')
old_methods=api_methods(parsed(qualified,'api.py'))
new_methods=api_methods(copy.deepcopy(current_api))
stripped_cli,parser_nodes,dispatch=strip_cli(parsed(composed,'cli.py'))
_,qualified_parser,qualified_dispatch=strip_cli(parsed(qualified,'cli.py'))
current_tools=tools_for(parsed(composed,'mcp_server.py'))
qualified_tools=tools_for(parsed(qualified,'mcp_server.py'))
section=content(qualified,'README.md')
section=section[section.index(b'## Review your inbox\n'):section.index(b'## Auth modes\n')]
readme=content(composed,'README.md')
changed=git('diff','--name-only',main,composed).decode().splitlines()
checks={
 'owned_API_readers_exactly_match_qualified_source':all(dump(new_methods[k])==dump(old_methods[k]) for k in old_methods),
 'all_other_API_AST_preserved_from_incoming_main':dump(without_api(copy.deepcopy(current_api)))==dump(without_api(parsed(main,'api.py'))),
 'all_other_MCP_AST_preserved_from_incoming_main':dump(without_metadata(parsed(composed,'mcp_server.py')))==dump(without_metadata(parsed(main,'mcp_server.py'))),
 'owned_MCP_metadata_exactly_matches_qualified_source':all([dump(x) for x in current_tools[k].decorator_list]==[dump(x) for x in qualified_tools[k].decorator_list] for k in qualified_tools),
 'all_other_CLI_AST_preserved_from_incoming_main':dump(stripped_cli)==dump(parsed(main,'cli.py')),
 'owned_CLI_additions_exactly_match_qualified_source':parser_nodes==qualified_parser and dispatch==qualified_dispatch,
 'README_preserves_current_main_and_exact_inbox_section':readme.count(section)==1 and readme.replace(section,b'',1)==content(main,'README.md'),
 'only_owned_paths_differ_from_incoming_main':all(p in {'README.md','docs/inbox-review.md','src/canvaspilot/api.py','src/canvaspilot/cli.py','src/canvaspilot/mcp_server.py','tests/test_inbox_review.py'} or p.startswith('docs/verification/inbox-review-713adaab/') for p in changed),
}
assert all(checks.values()),checks
env=dict(os.environ)
env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(repo/'src'))
r=subprocess.run(['/home/jacob/canvaspilot-announcements-3dcb83a1/.venv/bin/python','-B','-m','ruff','check','src','tests','scripts'],cwd=repo,env=env,capture_output=True)
(out/'later-composition-ruff.stdout').write_bytes(r.stdout)
(out/'later-composition-ruff.stderr').write_bytes(r.stderr)
assert r.returncode==0,(r.returncode,r.stdout,r.stderr)
receipt={'schema':'canvaspilot.inbox.later-main-source-preservation.v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'incoming_main':main,'qualified_methods_commit':qualified,'independently_received_composition':old,'native_composed_commit':composed,'native_composed_tree':tree,'checks':checks,'ruff_exit':r.returncode,'runtime_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((repo/'src/canvaspilot').glob('*.py'))},'runtime_gate':'Full hosted tests on the actual published head remain pending; prior native receipts retain their own exact source identities.'}
(out/'later-source-preservation.json').write_text(json.dumps(receipt,indent=2)+'\n')
dest=repo/'docs/verification/inbox-review-713adaab-composition'
dest.mkdir(exist_ok=False)
(dest/'peer').mkdir()
for name in [*manifest['files'],'manifest.json']:
    target=dest/'peer'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(peer/name,target)
(dest/'root').mkdir()
for name in ['native-checkpoint.json','native-composition.json','merge-preview-0d189854.json','merge-preview-39d835c8.json','composition-ruff.stdout','composition-ruff.stderr','later-source-preservation.json','later-composition-ruff.stdout','later-composition-ruff.stderr']:
    shutil.copy2(out/name,dest/'root'/name)
for label,commit in [('evidence-checkpoint','4c850261e413af32fb78f4fa389247415f225d1c'),('independently-received-composition',old),('submission-history-composition',composed)]:
    (dest/'root'/(label+'.commit')).write_bytes(git('cat-file','commit',commit))
shutil.copy2(out/'finalize_source.py',dest/'root'/'finalize_source.py')
(dest/'README.md').write_text(README_TEXT,encoding='utf-8')
items=[]
for p in sorted(dest.rglob('*')):
    if p.is_file():
        b=p.read_bytes()
        items.append({'path':str(p.relative_to(dest)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
inventory={'schema':'canvaspilot.inbox.composition-inventory.v1','files':items,'file_count':len(items),'total_bytes':sum(x['bytes'] for x in items),'self_exclusion':'Git binds the final inventory bytes.'}
(dest/'manifest.json').write_text(json.dumps(inventory,indent=2)+'\n')
git('add','--','docs/verification/inbox-review-713adaab-composition')
git('commit','-m','docs: retain inbox composition receiving and source preservation')
assert not git('status','--porcelain=v1')
final={'native_commit':git('rev-parse','HEAD').decode().strip(),'native_tree':git('rev-parse','HEAD^{tree}').decode().strip(),'base_commit':main,'base_tree':git('rev-parse',main+'^{tree}').decode().strip(),'source_commit':composed,'source_tree':tree,'source_unchanged_after_evidence':not git('diff','--name-only',composed,'HEAD','--','src','tests','scripts','README.md','docs/inbox-review.md'),'supplement_files':len(items)+1,'supplement_payload_bytes':inventory['total_bytes'],'supplement_manifest_sha256':hashlib.sha256((dest/'manifest.json').read_bytes()).hexdigest(),'original_peer_manifest_unchanged':hashlib.sha256((repo/'docs/verification/inbox-review-713adaab/peer/manifest.json').read_bytes()).hexdigest()=='988cc00f8c51d6fdeef57b5b77b53e28b4defd1c423b4f65ddba65e7414dfca5','checks':checks,'ruff_exit':r.returncode}
(out/'final-native-checkpoint.json').write_text(json.dumps(final,indent=2)+'\n')
print(json.dumps(final))
