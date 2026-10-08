"""One real native export; retain the prior actual export as the CSS counterexample."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ORIGINAL = '3bc3f44f9d8f682fbf8442fed88e05d6148ecbf889e41c941ce65f067f59904b'
SUCCESSOR = 'a0db41dca9cce28c9fb7594c88ea6dc103b0f3104d5ba4d061bd93aaed92a714'
MANIFEST = '79e28c5bc7bc7f8953f0aa560000c655d832954a61fe84ec6c14c7834be3cc4d'
SUPPORT = '27b2851617939bdce42549cb5a0de2e663f66b7ceea6ee53e6ff24b88ec6089b'
FORMATTER = 'src/canvaspilot/feedback_export.py'


def check(value, message):
    if not value:
        raise RuntimeError(message)


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    for name in ['original-review', 'original-source', 'successor-source', 'jsdom', 'node', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    manifest_bytes = (args.original_review / 'candidate-author-manifest.json').read_bytes()
    check(pin(manifest_bytes)['sha256'] == MANIFEST, 'author manifest drift')
    manifest = json.loads(manifest_bytes)

    def source_pins():
        return {x['path']: {'original': pin((args.original_source / x['path']).read_bytes()),
                            'successor': pin((args.successor_source / x['path']).read_bytes())}
                for x in manifest['files']}

    before = source_pins()
    for item in manifest['files']:
        relative = item['path']
        a = (args.original_source / relative).read_bytes()
        b = (args.successor_source / relative).read_bytes()
        check(pin(a)['sha256'] == item['sha256'], 'original source drift: ' + relative)
        if relative == FORMATTER:
            check(pin(a)['sha256'] == ORIGINAL and pin(b)['sha256'] == SUCCESSOR, 'formatter pin mismatch')
            check(a[392:393] == b'+' and b == a[:392] + a[393:], 'not the exact one-byte deletion')
        else:
            check(a == b, 'additional source changed: ' + relative)
    support_path = args.original_review / 'receiving_support.py'
    check(pin(support_path.read_bytes())['sha256'] == SUPPORT, 'independent support drift')
    spec = importlib.util.spec_from_file_location('receiving_support', support_path)
    support = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = support
    spec.loader.exec_module(support)
    runtime_files = json.loads((args.original_review / 'candidate-pins.json').read_text())['files']
    private = args.output / 'repo'
    for item in runtime_files:
        target = private / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((args.successor_source / item['path']).read_bytes())
    private_before = {x['path']: pin((private / x['path']).read_bytes()) for x in runtime_files}
    save(args.output / 'source-before.json', before)
    save(args.output / 'private-before.json', private_before)
    original_html = args.original_review / 'normal/test_zero_prior_attempt_and_existing_reader_remain_truthful/case/command-03.html'
    old_html = args.output / 'predecessor-actual-export.html'
    shutil.copyfile(original_html, old_html)
    assignment, submission = support.authored_feedback()
    new_html = args.output / 'feedback.html'
    with support.LocalCanvas(assignment, submission, args.output / 'native-command') as local:
        command = local.cli(private, 'export-feedback', out=new_html)
    check(command['returncode'] == 0, 'native export failed: ' + command['stderr'])
    check(len(local.commands) == 1 and len(local.requests) == 2, 'expected one CLI process and two GETs')
    check([x['path'] for x in local.requests] == [support.ASSIGNMENT_PATH, support.SUBMISSION_PATH], 'reader routes changed')
    check(all(x['method'] == 'GET' and x['synthetic_authorization_matches'] for x in local.requests), 'unexpected request')
    raw = new_html.read_bytes()
    check(json.loads(command['stdout'])['sha256'] == pin(raw)['sha256'], 'receipt digest mismatch')
    old_fields = support.OfflineDocument(old_html.read_bytes()).fields()
    new_fields = support.OfflineDocument(raw).fields()
    old_fields.pop('captured_at')
    new_fields.pop('captured_at')
    check(old_fields == new_fields, 'Canvas feedback fields changed during the CSS repair')
    node_command = [str(args.node), str(Path(__file__).with_name('verify_exported_selectors.cjs')),
                    str(old_html), str(new_html), str(args.jsdom)]
    result = subprocess.run(node_command, capture_output=True, text=True, timeout=30)
    (args.output / 'selector-stdout.json').write_text(result.stdout, encoding='utf-8')
    (args.output / 'selector-stderr.log').write_text(result.stderr, encoding='utf-8')
    save(args.output / 'selector-process.json', {'command': node_command, 'returncode': result.returncode})
    check(result.returncode == 0, 'selector parser failed: ' + result.stderr)
    parsed = json.loads(result.stdout)
    after = source_pins()
    private_after = {x['path']: pin((private / x['path']).read_bytes()) for x in runtime_files}
    check(before == after and private_before == private_after, 'source changed during receiving')
    save(args.output / 'source-after.json', after)
    save(args.output / 'private-after.json', private_after)
    report = {'schema': 'independent-feedback-css-successor.v1', 'passed': True,
              'parent': manifest['parent'], 'tree': manifest['tree'],
              'original_formatter': ORIGINAL, 'successor_formatter': SUCCESSOR,
              'deletion': {'offset': 392, 'byte': '+', 'before_bytes': 20918, 'after_bytes': 20917},
              'other_received_files_byte_identical': len(manifest['files']) - 1,
              'source_before_after_identical': True, 'private_runtime_files': len(private_before),
              'actual_cli_processes': 1, 'actual_loopback_gets': 2, 'successful_html_files': 1,
              'predecessor_actual_file': pin(old_html.read_bytes()), 'successor_actual_file': pin(raw),
              'semantic_fields_equal_except_capture_timestamp': True,
              'css_selector_count': len(parsed['after']['selectors']),
              'predecessor_invalid_selectors': [x['selector'] for x in parsed['before']['selectors'] if not x['accepted']],
              'successor_invalid_selectors': [x['selector'] for x in parsed['after']['selectors'] if not x['accepted']],
              'elapsed_seconds': time.monotonic() - started, 'python': sys.version,
              'browser_allocations': 0, 'live_accounts': 0, 'github_writes': 0,
              'rendered_print_layout_claim': False, 'current79_parent_qualification': False,
              'probe': pin(Path(__file__).read_bytes()),
              'selector_probe': pin(Path(__file__).with_name('verify_exported_selectors.cjs').read_bytes())}
    save(args.output / 'review.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
