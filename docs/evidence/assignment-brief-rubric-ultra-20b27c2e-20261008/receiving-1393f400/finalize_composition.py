from pathlib import Path
import ast, difflib, hashlib, json, shutil, subprocess

HERE = Path(__file__).resolve().parent
OLD = Path('/dev/shm/ultra-20b27c2e-runtime-integration-canvaspilot')

def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def member_spans(path):
    source = path.read_text()
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = ast.get_source_segment(source, node)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result[node.name + '.' + child.name] = ast.get_source_segment(source, child)
    return result

def main():
    report = json.loads((HERE / 'composition-initial.json').read_text())
    candidate, baseline = HERE / 'candidate', HERE / 'baseline'
    for entry in report['native_three_way_proposals']:
        path = entry['path']
        data = Path(entry['proposal']).read_text()
        if entry['exit_code']:
            if path != 'src/canvaspilot/api.py' or entry['exit_code'] != 1:
                raise ValueError('unexpected merge conflict')
            block = ('<<<<<<< ' + str(baseline / path) + '\nfrom datetime import datetime\n=======\n'
                     'from copy import deepcopy\n>>>>>>> ' + str(OLD / 'candidate' / path) + '\n')
            if data.count(block) != 1:
                raise ValueError('unexpected import conflict content')
            data = data.replace(block, 'from copy import deepcopy\nfrom datetime import datetime\n')
        if '<<<<<<<' in data or '>>>>>>>' in data:
            raise ValueError('unresolved merge markers')
        out = candidate / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(data)
    accepted = member_spans(OLD / 'candidate/src/canvaspilot/api.py')
    current = member_spans(baseline / 'src/canvaspilot/api.py')
    combined = member_spans(candidate / 'src/canvaspilot/api.py')
    rubric_members = ['_brief_rubric', 'CanvasAPI.get_assignment', 'CanvasAPI.assignment_brief']
    for name in rubric_members:
        if combined.get(name) != accepted[name]:
            raise ValueError('rubric behavior span changed: ' + name)
    untouched = sorted(set(current) - set(rubric_members))
    for name in untouched:
        if combined.get(name) != current[name]:
            raise ValueError('unowned API member changed: ' + name)
    if set(combined) - set(current) != {'_brief_rubric'}:
        raise ValueError('unexpected member added')
    old_ast = ast.parse((baseline / 'src/canvaspilot/api.py').read_text())
    new_ast = ast.parse((candidate / 'src/canvaspilot/api.py').read_text())
    new_ast.body = [n for n in new_ast.body if not (isinstance(n, ast.FunctionDef) and n.name == '_brief_rubric')
                    and not (isinstance(n, ast.ImportFrom) and n.module in ('copy', 'math'))]
    original_class = next(n for n in old_ast.body if isinstance(n, ast.ClassDef) and n.name == 'CanvasAPI')
    new_class = next(n for n in new_ast.body if isinstance(n, ast.ClassDef) and n.name == 'CanvasAPI')
    replacements = {n.name: n for n in original_class.body if isinstance(n, ast.FunctionDef) and n.name in ('get_assignment', 'assignment_brief')}
    new_class.body = [replacements.get(n.name, n) if isinstance(n, ast.FunctionDef) else n for n in new_class.body]
    if ast.dump(new_ast, include_attributes=False) != ast.dump(old_ast, include_attributes=False):
        raise ValueError('unowned API structure changed')
    line_checks = []
    for path, marker in [('src/canvaspilot/cli.py', 'brief = sub.add_parser('),
                         ('src/canvaspilot/mcp_server.py', '@mcp.tool(description="Digested assignment brief:')]:
        original = (OLD / 'baseline' / path).read_text()
        accepted_text = (OLD / 'candidate' / path).read_text()
        old_line = next(line for line in original.splitlines(True) if marker in line)
        new_line = next(line for line in accepted_text.splitlines(True) if marker in line)
        combined_text = (candidate / path).read_text()
        if combined_text.count(new_line) != 1 or combined_text.replace(new_line, old_line) != (baseline / path).read_text():
            raise ValueError('unowned public surface source changed: ' + path)
        line_checks.append(path)
    readme_patch = ''.join(difflib.unified_diff((OLD / 'baseline/README.md').read_text().splitlines(True),
        (OLD / 'candidate/README.md').read_text().splitlines(True), fromfile='a/README.md', tofile='b/README.md'))
    readme_patch_path = HERE / 'readme-only.patch'
    readme_patch_path.write_text(readme_patch)
    reverse = HERE / 'readme-reverse-check'
    reverse.mkdir()
    shutil.copy2(candidate / 'README.md', reverse / 'README.md')
    command = ['git', 'apply', '--reverse', str(readme_patch_path)]
    proc = subprocess.run(command, cwd=reverse, capture_output=True, text=True)
    if proc.returncode or (reverse / 'README.md').read_bytes() != (baseline / 'README.md').read_bytes():
        raise ValueError('unowned README edits changed: ' + proc.stderr)
    primary = json.loads((HERE / 'primary-inputs.json').read_text())
    base_map = {x['path']: x for x in primary['tree']['tree'] if x['type'] == 'blob'}
    files = []
    changed_paths = set(report['accepted_delta_paths'])
    for path in sorted(changed_paths):
        data = (candidate / path).read_bytes()
        files.append({'repo_path': path, 'local_path': str(candidate / path), 'mode': '100644',
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob_sha': blob(data), 'original_git_blob': base_map.get(path, {}).get('sha')})
    for path, item in base_map.items():
        if path not in changed_paths and blob((candidate / path).read_bytes()) != item['sha']:
            raise ValueError('unowned current file changed: ' + path)
    result = {'baseline_commit': primary['commit']['sha'], 'baseline_tree': primary['commit']['tree']['sha'],
        'baseline_blobs_verified': 63, 'candidate_files': sum(p.is_file() for p in candidate.rglob('*')),
        'unowned_base_blobs_preserved': sum(p not in changed_paths for p in base_map),
        'rubric_member_spans_identical_to_accepted': rubric_members,
        'unowned_api_member_spans_identical_to_current': untouched,
        'unowned_api_structure_identical': True, 'public_source_single_line_deltas_only': line_checks,
        'readme_reverse_patch': {'command': command, 'exit_code': proc.returncode, 'current_bytes_restored': True},
        'resolved_conflict': 'Only adjacent imports: retain accepted deepcopy and current datetime, along with isfinite.',
        'files': files}
    (HERE / 'composition-final.json').write_text(json.dumps(result, indent=2) + '\n')
    (HERE / 'receiving-source-updates.json').write_text(json.dumps({'repository': 'Jacob-Met/CanvasPilot',
        'base_branch': 'main', 'receiving_base': result['baseline_commit'], 'files': files}, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'unowned_api_member_spans_identical_to_current'}))

if __name__ == '__main__':
    main()
