from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, subprocess, sys, xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
EARLIER = HERE.parent / 'current-review-20261008'
PYTHON = Path('/workspace/scratch/20b27c2ea29e/workers/runtime-integration/product-discovery/canvaspilot/venv/bin/python')

def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}

def main():
    harness = EARLIER / 'test_independent_rubric_brief.py'
    if hashlib.sha256(harness.read_bytes()).hexdigest() != '0d4f352f81c0c2a39415df9effdf4ffc0318e7f6dd21a6876e459233f28d8a0b':
        raise ValueError('independent harness changed')
    output = HERE / 'qualification'
    output.mkdir()
    tmp = HERE / 'tmp'
    tmp.mkdir()
    before = {kind: hashes(HERE / kind) for kind in ('baseline', 'candidate')}
    runs = []
    for kind in ('baseline', 'candidate'):
        root = HERE / kind
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(tmp), PYTHONPATH=str(root / 'src'))
        xmlpath = output / ('full-' + kind + '.xml')
        command = [str(PYTHON), '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                   '--basetemp', str(tmp / ('pytest-' + kind)), '--junitxml', str(xmlpath)]
        started = datetime.now(timezone.utc).isoformat()
        proc = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
        log = proc.stdout + proc.stderr
        (output / ('full-' + kind + '.log')).write_text(log)
        suites = list(ET.parse(xmlpath).getroot().iter('testsuite')) if xmlpath.exists() else []
        counts = {k: sum(int(s.attrib.get(k, '0')) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
        runs.append({'kind': kind, 'suite': 'complete-current-pytest', 'mode': 'normal', 'command': command,
            'cwd': str(root), 'started_utc': started, 'exit_code': proc.returncode, 'counts': counts,
            'log': 'full-' + kind + '.log', 'junit': 'full-' + kind + '.xml'})
        print(json.dumps(runs[-1]), flush=True)
    for kind in ('baseline', 'candidate'):
        for mode, flags in [('normal', []), ('optimized', ['-O'])]:
            target = output / (kind + '-' + mode)
            command = [str(PYTHON), '-B', *flags, str(harness), '--source', str(HERE / kind), '--output', str(target)]
            started = datetime.now(timezone.utc).isoformat()
            proc = subprocess.run(command, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(tmp)), capture_output=True, text=True)
            public = target / 'public-outputs.json'
            old_public = EARLIER / (kind + '-' + mode) / 'public-outputs.json'
            receipt = json.loads((target / 'receipt.json').read_text())
            runs.append({'kind': kind, 'suite': 'unchanged-independent-public-receiver', 'mode': mode,
                'command': command, 'started_utc': started, 'exit_code': proc.returncode,
                'stdout': proc.stdout, 'stderr': proc.stderr, 'receipt': receipt,
                'raw_log': (target / 'results.log').read_text(),
                'public_output_sha256': hashlib.sha256(public.read_bytes()).hexdigest(),
                'public_output_identical_to_original': public.read_bytes() == old_public.read_bytes(),
                'original_public_output': '../independent-review/' + kind + '-' + mode + '/public-outputs.json'})
            print(json.dumps({'kind': kind, 'mode': mode, 'suite': 'independent-public', 'exit_code': proc.returncode,
                'methods': receipt['methods'], 'passed_methods': receipt['passed_methods'],
                'failed_methods': len(receipt['failed_methods']), 'failure_entries': receipt['failure_entries'],
                'error_entries': receipt['error_entries'], 'skips': receipt['skips'],
                'public_outputs_identical': runs[-1]['public_output_identical_to_original']}), flush=True)
    command = [str(PYTHON), '-B', '-m', 'ruff', 'check', '--no-cache', 'src', 'tests', 'scripts', '--output-format', 'json']
    proc = subprocess.run(command, cwd=HERE / 'candidate', env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(tmp)), capture_output=True, text=True)
    runs.append({'kind': 'candidate', 'suite': 'repository-lint', 'command': command,
                 'exit_code': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr})
    print(json.dumps(runs[-1]), flush=True)
    after = {kind: hashes(HERE / kind) for kind in ('baseline', 'candidate')}
    expected = lambda r: 1 if r['kind'] == 'baseline' and r['suite'] == 'unchanged-independent-public-receiver' else 0
    result = {'schema': 'canvas-sync-rubric-current-receiving-v1', 'source_before': before, 'source_after': after,
        'source_unchanged': before == after, 'runs': runs,
        'composition': json.loads((HERE / 'composition-final.json').read_text()),
        'successful': before == after and all(r['exit_code'] == expected(r) for r in runs)}
    (output / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'successful': result['successful'], 'source_unchanged': result['source_unchanged'], 'runs': len(runs)}))
    return 0 if result['successful'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
