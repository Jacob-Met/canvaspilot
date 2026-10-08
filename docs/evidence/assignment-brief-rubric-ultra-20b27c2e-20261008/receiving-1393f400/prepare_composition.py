from pathlib import Path
import difflib, hashlib, json, shutil, subprocess

HERE = Path(__file__).resolve().parent
OLD = Path('/dev/shm/ultra-20b27c2e-runtime-integration-canvaspilot')

def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def main():
    primary = json.loads((HERE / 'primary-inputs.json').read_text())
    fetched = primary['files'] + json.loads((HERE / 'primary-additions.json').read_text())
    fetched = {f['path']: f for f in fetched}
    baseline, candidate = HERE / 'baseline', HERE / 'candidate'
    baseline.mkdir()
    verified = []
    for item in primary['tree']['tree']:
        if item['type'] != 'blob':
            continue
        path = item['path']
        if path in fetched:
            data = fetched[path]['content'].encode()
            if blob(data) != item['sha'] and data.endswith(b'\n') and blob(data[:-1]) == item['sha']:
                data = data[:-1]
        else:
            data = (OLD / 'baseline' / path).read_bytes()
        if blob(data) != item['sha']:
            raise ValueError('current primary Git blob mismatch: ' + path)
        out = baseline / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        out.chmod(int(item['mode'], 8) & 0o777)
        verified.append({'path': path, 'git_blob': item['sha'], 'mode': item['mode'],
                         'sha256': hashlib.sha256(data).hexdigest()})
    if len(verified) != 63:
        raise ValueError('current baseline incomplete')
    shutil.copytree(baseline, candidate)
    pins = json.loads((OLD / 'receiving-source-pins.json').read_text())
    patch_lines = []
    proposals = []
    proposal_root = HERE / 'native-proposals'
    for f in pins['files']:
        path = f['path']
        accepted = (OLD / 'candidate' / path).read_bytes()
        if blob(accepted) != f['git_blob']:
            raise ValueError('accepted source changed: ' + path)
        previous = OLD / 'baseline' / path
        before = previous.read_text() if previous.exists() else ''
        patch_lines.extend(difflib.unified_diff(before.splitlines(True), accepted.decode().splitlines(True),
            fromfile='a/' + path if previous.exists() else '/dev/null', tofile='b/' + path))
        dest = proposal_root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if previous.exists():
            command = ['git', 'merge-file', '-p', str(baseline / path), str(previous), str(OLD / 'candidate' / path)]
            proc = subprocess.run(command, capture_output=True)
            dest.write_bytes(proc.stdout)
            proposals.append({'path': path, 'command': command, 'exit_code': proc.returncode,
                              'stderr': proc.stderr.decode(), 'proposal': str(dest)})
        else:
            dest.write_bytes(accepted)
            proposals.append({'path': path, 'exit_code': 0, 'proposal': str(dest), 'additive': True})
    patch = HERE / 'accepted-rubric.patch'
    patch.write_text(''.join(patch_lines))
    command = ['git', 'apply', '--check', str(patch)]
    dry = subprocess.run(command, cwd=candidate, capture_output=True, text=True)
    report = {'baseline_commit': primary['commit']['sha'], 'baseline_tree': primary['commit']['tree']['sha'],
              'baseline_verified': verified, 'accepted_delta_paths': [f['path'] for f in pins['files']],
              'original_delta_check': {'command': command, 'exit_code': dry.returncode,
                                       'stdout': dry.stdout, 'stderr': dry.stderr},
              'native_three_way_proposals': proposals}
    (HERE / 'composition-initial.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'baseline_blobs': len(verified), 'patch_check': report['original_delta_check'],
                      'proposals': [{'path': r['path'], 'exit_code': r['exit_code']} for r in proposals]}))

if __name__ == '__main__':
    main()
