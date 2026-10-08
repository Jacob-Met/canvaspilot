"""One native export checks the newly imported API dependency; no suite replay."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}


def check(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser()
    for name in ['source', 'support', 'prior-html', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    support_file = args.support / 'receiving_support.py'
    check(pin(support_file.read_bytes())['sha256'] == '27b2851617939bdce42549cb5a0de2e663f66b7ceea6ee53e6ff24b88ec6089b',
          'original independent support drift')
    spec = importlib.util.spec_from_file_location('receiving_support', support_file)
    support = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = support
    spec.loader.exec_module(support)
    before = {p.relative_to(args.source).as_posix(): pin(p.read_bytes())
              for p in sorted((args.source / 'src/canvaspilot').glob('*.py'))}
    check(len(before) == 14, 'expected the current fourteen native modules')
    check(before['src/canvaspilot/api.py']['git_blob'] == '8de750525055991ca470fb4881d0368a07631818', 'API import context drift')
    check(before['src/canvaspilot/assignment_submission.py']['git_blob'] == '95b1f19927e4eecf99fc852325737c3cfe86cd0d', 'new dependency drift')
    check(before['src/canvaspilot/cli.py']['sha256'] == '223654cbd53c539b327dfb7399ed01953381044f387c205bb1a7eb21f6c1808f', 'CLI drift')
    check(before['src/canvaspilot/feedback_export.py']['sha256'] == 'a0db41dca9cce28c9fb7594c88ea6dc103b0f3104d5ba4d061bd93aaed92a714', 'formatter drift')
    (args.output / 'source-before.json').write_bytes(support.pretty(before))
    prior_raw = args.prior_html.read_bytes()
    check(pin(prior_raw)['sha256'] == '27ae70511395b7412359bdedd17baf0f5f499ef3550da104d5e6e882ce847e78', 'qualified prior actual export drift')
    start = time.monotonic()
    assignment, submission = support.authored_feedback()
    out = args.output / 'feedback.html'
    with support.LocalCanvas(assignment, submission, args.output / 'wire') as local:
        command = local.cli(args.source, 'export-feedback', out=out)
    check(command['returncode'] == 0, 'current import-context export failed: ' + command['stderr'])
    check(len(local.commands) == 1 and len(local.requests) == 2, 'expected one command and exactly two requests')
    check([row['path'] for row in local.requests] == [support.ASSIGNMENT_PATH, support.SUBMISSION_PATH], 'feedback read routes changed')
    check(all(row['method'] == 'GET' and row['synthetic_authorization_matches'] for row in local.requests), 'unexpected request')
    raw = out.read_bytes()
    check(json.loads(command['stdout'])['sha256'] == pin(raw)['sha256'], 'actual file receipt mismatch')
    old_doc, new_doc = support.OfflineDocument(prior_raw), support.OfflineDocument(raw)
    old_fields, new_fields = old_doc.fields(), new_doc.fields()
    old_stamp, new_stamp = old_fields.pop('captured_at'), new_fields.pop('captured_at')
    check(old_fields == new_fields, 'received feedback fields changed across import context')
    check(old_doc.text().count(old_stamp) == new_doc.text().count(new_stamp) == 1, 'ambiguous capture-time normalization')
    check(old_doc.text().replace(old_stamp, '[capture-time]') == new_doc.text().replace(new_stamp, '[capture-time]'),
          'visible feedback changed across import context')
    check(new_fields['submission.score'] == '0' and new_fields['submission.missing'] == 'Not returned', 'zero/unknown changed')
    check(not new_doc.elements('script'), 'literal feedback became script markup')
    after = {p.relative_to(args.source).as_posix(): pin(p.read_bytes())
             for p in sorted((args.source / 'src/canvaspilot').glob('*.py'))}
    check(before == after, 'native source changed during the command')
    (args.output / 'source-after.json').write_bytes(support.pretty(after))
    report = {'schema': 'independent-current0d-feedback-import.v1', 'passed': True,
              'parent': '0d1898544a90079e2dcc7ceb3fa4bc6bca88a2bc',
              'tree': 'de9fca025ebe325807bd53cd9b7f3b6be50c6d19',
              'mode': 'optimized' if sys.flags.optimize else 'normal',
              'actual_cli_processes': 1, 'actual_loopback_GETs': 2, 'actual_html_files': 1,
              'native_source_files': 14, 'source_before_after_identical': True,
              'all_visible_feedback_equal_except_capture_time': True,
              'new_assignment_list_helper_behavior_tested': False,
              'prior_actual_export': pin(prior_raw), 'actual_export': pin(raw),
              'elapsed_seconds': time.monotonic() - start, 'python': sys.version,
              'probe': pin(Path(__file__).read_bytes()), 'support': pin(support_file.read_bytes()),
              'browser_allocations': 0, 'actual_broker_processes': 0, 'github_writes': 0, 'live_accounts': 0}
    (args.output / 'result.json').write_bytes(support.pretty(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
