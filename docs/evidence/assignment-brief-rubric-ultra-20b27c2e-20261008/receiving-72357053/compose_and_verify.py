from pathlib import Path
import ast, difflib, hashlib, json, shutil, subprocess

HERE = Path(__file__).resolve().parent
PREVIOUS = Path('/workspace/scratch/20b27c2ea29e/workers/memory-improvement/canvas-review/receiving-1393f400')

def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def spans(path):
    source = path.read_text()
    out = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = ast.get_source_segment(source, node)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[node.name + '.' + item.name] = ast.get_source_segment(source, item)
    return out

def main():
    primary = json.loads((HERE / 'primary-inputs.json').read_text())
    fetched = {f['path']: f for f in primary['files']}
    product_doc = json.loads((HERE / 'primary-product-doc.json').read_text())
    fetched[product_doc['path']] = product_doc
    tree = {f['path']: f for f in primary['tree']['tree'] if f['type'] == 'blob'}
    if len(tree) != 123 or primary['tree'].get('truncated'):
        raise ValueError('incomplete current primary tree')
    baseline, candidate = HERE / 'baseline', HERE / 'candidate'
    baseline.mkdir()
    verified, deferred = [], []
    for path, item in tree.items():
        if path in fetched:
            data = fetched[path]['content'].encode()
            if blob(data) != item['sha'] and data.endswith(b'\n') and blob(data[:-1]) == item['sha']:
                data = data[:-1]
        elif (PREVIOUS / 'baseline' / path).exists():
            data = (PREVIOUS / 'baseline' / path).read_bytes()
        else:
            if not path.startswith('docs/evidence/'):
                raise ValueError('missing applicable current file: ' + path)
            deferred.append({'path': path, 'git_blob': item['sha'], 'mode': item['mode']})
            continue
        if blob(data) != item['sha']:
            raise ValueError('current primary blob mismatch: ' + path)
        dest = baseline / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        dest.chmod(int(item['mode'], 8) & 0o777)
        verified.append({'path': path, 'git_blob': item['sha'], 'sha256': hashlib.sha256(data).hexdigest(), 'mode': item['mode']})
    if len(verified) != 67 or len(deferred) != 56:
        raise ValueError('unexpected closure size')
    shutil.copytree(baseline, candidate)
    accepted = json.loads((PREVIOUS / 'receiving-source-updates.json').read_text())['files']
    lines = []
    for f in accepted:
        data = Path(f['local_path']).read_bytes()
        if blob(data) != f['git_blob_sha'] or hashlib.sha256(data).hexdigest() != f['sha256']:
            raise ValueError('previously accepted source changed: ' + f['repo_path'])
        path = f['repo_path']
        oldpath = PREVIOUS / 'baseline' / path
        before = oldpath.read_text() if oldpath.exists() else ''
        lines.extend(difflib.unified_diff(before.splitlines(True), data.decode().splitlines(True),
            fromfile='a/' + path if oldpath.exists() else '/dev/null', tofile='b/' + path))
    patch = HERE / 'accepted-rubric.patch'
    patch.write_text(''.join(lines))
    command = ['git', 'apply', '--check', str(patch)]
    dry = subprocess.run(command, cwd=candidate, capture_output=True, text=True)
    initial = {'command': command, 'exit_code': dry.returncode, 'stdout': dry.stdout, 'stderr': dry.stderr}
    (HERE / 'patch-check.json').write_text(json.dumps(initial, indent=2) + '\n')
    if dry.returncode:
        print(json.dumps(initial))
        return 1
    applied = subprocess.run(['git', 'apply', str(patch)], cwd=candidate, capture_output=True, text=True)
    if applied.returncode:
        raise ValueError('native patch application failed: ' + applied.stderr)
    current_api = spans(baseline / 'src/canvaspilot/api.py')
    accepted_api = spans(PREVIOUS / 'candidate/src/canvaspilot/api.py')
    composed_api = spans(candidate / 'src/canvaspilot/api.py')
    owned = ['_brief_rubric', 'CanvasAPI.get_assignment', 'CanvasAPI.assignment_brief']
    if any(composed_api.get(k) != accepted_api[k] for k in owned):
        raise ValueError('accepted rubric span changed')
    untouched = sorted(set(current_api) - set(owned))
    if any(composed_api.get(k) != current_api[k] for k in untouched) or set(composed_api) - set(current_api) != {'_brief_rubric'}:
        raise ValueError('unowned API span changed')
    cur = ast.parse((baseline / 'src/canvaspilot/api.py').read_text())
    cmp = ast.parse((candidate / 'src/canvaspilot/api.py').read_text())
    cmp.body = [n for n in cmp.body if not (isinstance(n, ast.FunctionDef) and n.name == '_brief_rubric')
                and not (isinstance(n, ast.ImportFrom) and n.module in ('copy', 'math'))]
    cur_class = next(n for n in cur.body if isinstance(n, ast.ClassDef) and n.name == 'CanvasAPI')
    cmp_class = next(n for n in cmp.body if isinstance(n, ast.ClassDef) and n.name == 'CanvasAPI')
    replace = {n.name: n for n in cur_class.body if isinstance(n, ast.FunctionDef) and n.name in ('get_assignment', 'assignment_brief')}
    cmp_class.body = [replace.get(n.name, n) if isinstance(n, ast.FunctionDef) else n for n in cmp_class.body]
    if ast.dump(cmp, include_attributes=False) != ast.dump(cur, include_attributes=False):
        raise ValueError('unowned API structure changed')
    for path, marker in [('src/canvaspilot/cli.py', 'brief = sub.add_parser('),
                         ('src/canvaspilot/mcp_server.py', '@mcp.tool(description="Digested assignment brief:')]:
        oldline = next(l for l in (PREVIOUS / 'baseline' / path).read_text().splitlines(True) if marker in l)
        newline = next(l for l in (PREVIOUS / 'candidate' / path).read_text().splitlines(True) if marker in l)
        output = (candidate / path).read_text()
        if output.count(newline) != 1 or output.replace(newline, oldline) != (baseline / path).read_text():
            raise ValueError('unowned CLI/MCP source changed: ' + path)
    # Reversing the exact six-path delta must recover the complete local current receiver.
    reverse = HERE / 'reverse-check'
    shutil.copytree(candidate, reverse)
    proc = subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=reverse, capture_output=True, text=True)
    reverse_files = {str(p.relative_to(reverse)): blob(p.read_bytes()) for p in reverse.rglob('*') if p.is_file()}
    current_files = {str(p.relative_to(baseline)): blob(p.read_bytes()) for p in baseline.rglob('*') if p.is_file()}
    if proc.returncode or reverse_files != current_files:
        raise ValueError('reverse delta does not restore exact current files: ' + proc.stderr)
    scope = {f['repo_path'] for f in accepted}
    unowned = [f for f in verified if f['path'] not in scope]
    for f in unowned:
        if blob((candidate / f['path']).read_bytes()) != f['git_blob']:
            raise ValueError('unowned source changed: ' + f['path'])
    updates = []
    for path in sorted(scope):
        data = (candidate / path).read_bytes()
        updates.append({'repo_path': path, 'local_path': str(candidate / path), 'mode': '100644', 'type': 'blob',
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'git_blob_sha': blob(data),
            'original_git_blob': tree.get(path, {}).get('sha')})
    report = {'baseline_commit': primary['commit']['sha'], 'baseline_tree': primary['commit']['tree']['sha'],
        'primary_tree_leaves_pinned': 123, 'materialized_baseline_files': 67, 'materialized_candidate_files': 69,
        'materialized_unowned_files_verified_unchanged': len(unowned), 'unmaterialized_unexecuted_owner_evidence_leaves': deferred,
        'all_unowned_base_leaves_to_preserve_at_git_composition': 119, 'materialized_primary_files': verified,
        'native_patch_check': initial, 'native_patch_applied_without_manual_resolution': True,
        'all_materialized_current_files_restored_by_reverse_delta': True,
        'rubric_spans_identical_to_accepted_f113': owned, 'all_unowned_api_spans_unchanged': untouched,
        'unowned_api_structure_unchanged': True, 'CLI_MCP_only_accepted_rubric_line_changes': True,
        'files': updates}
    (HERE / 'composition.json').write_text(json.dumps(report, indent=2) + '\n')
    (HERE / 'source-updates.json').write_text(json.dumps({'repository': 'Jacob-Met/CanvasPilot', 'base_branch': 'main',
        'receiving_base': report['baseline_commit'], 'files': updates}, indent=2) + '\n')
    print(json.dumps({'base': report['baseline_commit'], 'tree': report['baseline_tree'], 'materialized': len(verified),
        'deferred_evidence': len(deferred), 'unowned_materialized_preserved': len(unowned), 'reverse_delta_exact': True,
        'source_updates': [{'path': f['repo_path'], 'sha256': f['sha256'], 'git_blob': f['git_blob_sha']} for f in updates]}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
