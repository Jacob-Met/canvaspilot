from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, json, os, subprocess, sys

HERE = Path(__file__).resolve().parent
OWNER = Path('/dev/shm/ultra-20b27c2e-runtime-integration-canvaspilot')
PYTHON = Path('/workspace/scratch/20b27c2ea29e/workers/runtime-integration/product-discovery/canvaspilot/venv/bin/python')

def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def members(path):
    tree = ast.parse(path.read_text())
    out = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = ast.dump(node, include_attributes=False)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[node.name + '.' + child.name] = ast.dump(child, include_attributes=False)
    return out

def main():
    primary = json.loads((HERE / 'primary-tree.json').read_text())
    if primary.get('truncated') or primary['sha'] != '5d3b9b7b8f3cca5f3940f31e020ad4310078dd70':
        raise ValueError('primary tree mismatch')
    entries = [x for x in primary['tree'] if x['type'] == 'blob']
    if len(entries) != 42:
        raise ValueError('incomplete baseline')
    pins = json.loads((OWNER / 'receiving-source-pins.json').read_text())
    changed = {x['path']: x for x in pins['files']}
    if len(changed) != 6:
        raise ValueError('owner scope changed')
    verified = []
    for item in entries:
        p = item['path']
        before, after = (OWNER / 'baseline' / p).read_bytes(), (OWNER / 'candidate' / p).read_bytes()
        if blob(before) != item['sha']:
            raise ValueError('primary baseline mismatch: ' + p)
        expected = changed.get(p, {}).get('git_blob', item['sha'])
        if blob(after) != expected:
            raise ValueError('candidate composition mismatch: ' + p)
        verified.append({'path': p, 'baseline_git_blob': blob(before), 'candidate_git_blob': blob(after),
                         'candidate_sha256': hashlib.sha256(after).hexdigest()})
    for p, item in changed.items():
        data = (OWNER / 'candidate' / p).read_bytes()
        if blob(data) != item['git_blob'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('frozen candidate mismatch: ' + p)
    if changed['src/canvaspilot/api.py']['sha256'] != 'e35290d0899a88cd5fe03178218b2d7e9f8318cb800a09c18180efef33a1150c':
        raise ValueError('unexpected API pin')
    before_ast = members(OWNER / 'baseline/src/canvaspilot/api.py')
    after_ast = members(OWNER / 'candidate/src/canvaspilot/api.py')
    changed_ast = [k for k in before_ast if before_ast[k] != after_ast.get(k)]
    added_ast = sorted(set(after_ast) - set(before_ast))
    if sorted(changed_ast) != ['CanvasAPI.assignment_brief', 'CanvasAPI.get_assignment'] or added_ast != ['_brief_rubric']:
        raise ValueError('unowned API member changed')
    source_receipt = {'baseline_commit': pins['baseline_commit'], 'primary_tree': primary['sha'],
        'verified_baseline_blobs': len(verified), 'candidate_delta': pins['files'],
        'unowned_baseline_blobs_preserved': sum(x['path'] not in changed for x in entries),
        'changed_api_members': changed_ast, 'added_api_members': added_ast,
        'unowned_api_members_identical': True, 'files': verified}
    (HERE / 'independent-source-verification.json').write_text(json.dumps(source_receipt, indent=2) + '\n')
    temp = HERE / 'tmp'
    temp.mkdir(exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(temp))
    runs = []
    for mode, flags in [('normal', []), ('optimized', ['-O'])]:
        for kind in ('baseline', 'candidate'):
            out = HERE / (kind + '-' + mode)
            command = [str(PYTHON), '-B', *flags, str(HERE / 'test_independent_rubric_brief.py'),
                       '--source', str(OWNER / kind), '--output', str(out)]
            started = datetime.now(timezone.utc).isoformat()
            proc = subprocess.run(command, capture_output=True, text=True, env=env)
            result = {'kind': kind, 'mode': mode, 'command': command, 'started_utc': started,
                      'exit_code': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}
            runs.append(result)
            print(json.dumps(result), flush=True)
    report = {'schema': 'independent-canvas-receiving-review-v1', 'runs': runs,
              'source_verification': source_receipt,
              'test_sha256': hashlib.sha256((HERE / 'test_independent_rubric_brief.py').read_bytes()).hexdigest(),
              'fixture_sha256': hashlib.sha256((HERE / 'assignment-fixture.json').read_bytes()).hexdigest()}
    (HERE / 'review-runs.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if all(r['exit_code'] == (1 if r['kind'] == 'baseline' else 0) for r in runs) else 1

if __name__ == '__main__':
    raise SystemExit(main())
