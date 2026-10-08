"""Independent current-parent receiving through native token and broker CLI paths."""
import argparse
from copy import deepcopy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from urllib.parse import parse_qs, urlsplit

SUPPORT_SHA = '27b2851617939bdce42549cb5a0de2e663f66b7ceea6ee53e6ff24b88ec6089b'
REFUSAL = 'Canvas provider mismatch: selected browser page is not the configured school [authored independent refusal]'


def pin(b):
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()}


def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


class AuthoredBroker:
    """Wire fixture only: no broker process, browser, or account is started."""
    def __init__(self, directory):
        self.directory = directory
        directory.mkdir()
        self.assignment, self.submission = SUPPORT.authored_feedback()
        self.requests, self.commands = [], []
        self.refuse = False

    def __enter__(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def respond(self, status, payload, record):
                body = SUPPORT.pretty(payload)
                record.update(response_status=status, response=pin(body))
                outer.requests.append(record)
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                record = {'method': 'GET', 'path': self.path,
                          'authorization_header_present': self.headers.get('Authorization') is not None}
                if self.path != '/health':
                    self.respond(404, {'outside_authored_contract': True}, record)
                    return
                # Deliberately no Link pagination or provider capability fields.
                self.respond(200, {'ok': True, 'base_url': outer.url}, record)

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                payload = json.loads(body)
                record = {'method': 'POST', 'path': self.path, 'payload': payload,
                          'authorization_header_present': self.headers.get('Authorization') is not None}
                parts = urlsplit(payload.get('path', ''))
                valid = (self.path == '/fetch' and payload.get('op') == 'fetch'
                         and payload.get('method') == 'GET' and payload.get('body') is None
                         and parts.path in {SUPPORT.ASSIGNMENT_PATH, SUPPORT.SUBMISSION_PATH}
                         and not parts.scheme and not parts.netloc)
                if not valid:
                    self.respond(405, {'ok': False, 'error': 'outside authored read-only contract'}, record)
                    return
                if outer.refuse:
                    self.respond(200, {'ok': False, 'error': REFUSAL}, record)
                    return
                data = outer.assignment if parts.path == SUPPORT.ASSIGNMENT_PATH else outer.submission
                # Deliberately no response.headers: these are singular resource reads.
                self.respond(200, {'ok': True, 'response': {'status': 200, 'json': data, 'text': None}}, record)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.url = 'http://127.0.0.1:' + str(self.server.server_address[1])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        save(self.directory / 'authored-data.json', {'assignment': self.assignment, 'submission': self.submission,
             'health_fields': ['ok', 'base_url'], 'response_fields': ['status', 'json', 'text'], 'refusal': REFUSAL})
        return self

    def cli(self, source, operation, out=None):
        command = [sys.executable, '-B', *(['-O'] if sys.flags.optimize else []), '-m', 'canvaspilot.cli',
                   operation, SUPPORT.COURSE, SUPPORT.ASSIGNMENT, '--base-url', self.url,
                   '--token', '', '--profile', str(self.directory / 'unused-profile')]
        if out is not None:
            command += ['--out', str(out)]
        env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'PYTHONPATH': str(source / 'src') + ':' + str(SUPPORT.DEPS),
               'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONIOENCODING': 'utf-8',
               'CANVAS_SESSION_PORT': str(self.server.server_address[1])}
        first = len(self.requests)
        start = time.monotonic()
        result = subprocess.run(command, cwd=source, env=env, capture_output=True, text=True, timeout=30)
        row = {'command': command, 'cwd': str(source), 'returncode': result.returncode,
               'elapsed_seconds': time.monotonic() - start, 'stdout': result.stdout, 'stderr': result.stderr,
               'requests': deepcopy(self.requests[first:])}
        if out is not None and out.is_file():
            row['output_file'] = pin(out.read_bytes())
        self.commands.append(row)
        save(self.directory / ('command-%02d.json' % len(self.commands)), row)
        return row

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        save(self.directory / 'requests.json', self.requests)
        save(self.directory / 'commands.json', self.commands)


class CurrentReceiving(unittest.TestCase):
    def test_current_token_reader_and_export_preserve_projection_and_existing_file(self):
        directory = ARGS.output / 'token'
        directory.mkdir()
        assignment, submission = SUPPORT.authored_feedback()
        with SUPPORT.LocalCanvas(assignment, submission, directory / 'wire') as local:
            old = local.cli(ARGS.before_source, 'feedback')
            new = local.cli(ARGS.source, 'feedback')
            self.assertEqual(old['returncode'], 0, old['stderr'])
            self.assertEqual(new['returncode'], 0, new['stderr'])
            before, after = json.loads(old['stdout']), json.loads(new['stdout'])
            self.assertEqual(before, after)
            self.assertEqual(after['submission_comments'], submission['submission_comments'])
            out = directory / 'feedback.html'
            export = local.cli(ARGS.source, 'export-feedback', out=out)
            self.assertEqual(export['returncode'], 0, export['stderr'])
            raw = out.read_bytes()
            self.assertEqual(json.loads(export['stdout'])['sha256'], pin(raw)['sha256'])
            fields = SUPPORT.OfflineDocument(raw).fields()
            self.assertEqual(fields['submission.score'], '0')
            self.assertEqual(fields['submission.missing'], 'Not returned')
            self.assertEqual(fields['submission.attempt'], '7')
            self.assertIs(after['submission']['grade_matches_current_submission'], False)
            self.assertEqual(len(local.requests), 6)
            self.assertEqual([x['path'] for x in local.requests],
                             [SUPPORT.ASSIGNMENT_PATH, SUPPORT.SUBMISSION_PATH] * 3)
            refused = local.cli(ARGS.source, 'export-feedback', out=out)
            self.assertEqual(refused['returncode'], 1)
            self.assertEqual(refused['stdout'], '')
            self.assertEqual(SUPPORT.terminal_json(refused['stderr'])['error'], 'FileExistsError')
            self.assertEqual(refused['requests'], [])
            self.assertEqual(out.read_bytes(), raw)
            self.assertEqual(len(local.requests), 6)

    def test_current_broker_single_reads_need_no_collection_metadata_and_refusal_is_retained(self):
        directory = ARGS.output / 'broker'
        directory.mkdir()
        with AuthoredBroker(directory / 'wire') as broker:
            old = broker.cli(ARGS.before_source, 'feedback')
            new = broker.cli(ARGS.source, 'feedback')
            self.assertEqual(old['returncode'], 0, old['stderr'])
            self.assertEqual(new['returncode'], 0, new['stderr'])
            self.assertEqual(json.loads(old['stdout']), json.loads(new['stdout']))
            self.assertEqual(json.loads(new['stdout'])['submission_comments'], broker.submission['submission_comments'])
            out = directory / 'feedback.html'
            export = broker.cli(ARGS.source, 'export-feedback', out)
            self.assertEqual(export['returncode'], 0, export['stderr'])
            raw = out.read_bytes()
            self.assertEqual(json.loads(export['stdout'])['sha256'], pin(raw)['sha256'])
            fields = SUPPORT.OfflineDocument(raw).fields()
            self.assertEqual(fields['submission.score'], '0')
            self.assertEqual(fields['submission.missing'], 'Not returned')
            self.assertEqual(fields['submission.attempt'], '7')
            for command in broker.commands:
                self.assertEqual([x['path'] for x in command['requests']], ['/health', '/fetch'] * 2)
                fetches = [x for x in command['requests'] if x['path'] == '/fetch']
                self.assertEqual([urlsplit(x['payload']['path']).path for x in fetches],
                                 [SUPPORT.ASSIGNMENT_PATH, SUPPORT.SUBMISSION_PATH])
                self.assertEqual(parse_qs(urlsplit(fetches[1]['payload']['path']).query),
                                 {'per_page': ['50'], 'include[]': ['submission_comments', 'rubric_assessment']})
                self.assertTrue(all(x['payload']['method'] == 'GET' for x in fetches))
            broker.refuse = True
            refused_out = directory / 'refused.html'
            refused = broker.cli(ARGS.source, 'export-feedback', refused_out)
            self.assertEqual(refused['returncode'], 1)
            self.assertEqual(refused['stdout'], '')
            error = SUPPORT.terminal_json(refused['stderr'])
            self.assertEqual(error, {'ok': False, 'error': 'CanvasAuthError', 'message': REFUSAL})
            self.assertFalse(refused_out.exists())
            self.assertEqual([x['path'] for x in refused['requests']], ['/health', '/fetch'])
            self.assertTrue(all(not x['authorization_header_present'] for x in broker.requests))
        self.assertEqual(sorted(x.name for x in directory.iterdir()), ['feedback.html', 'wire'])


def main():
    global ARGS, SUPPORT
    parser = argparse.ArgumentParser()
    for name in ['source', 'before-source', 'old-review', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    ARGS = parser.parse_args()
    ARGS.output.mkdir(parents=True)
    support = ARGS.old_review / 'receiving_support.py'
    if pin(support.read_bytes())['sha256'] != SUPPORT_SHA:
        raise RuntimeError('original independent support drift')
    spec = importlib.util.spec_from_file_location('receiving_support', support)
    SUPPORT = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = SUPPORT
    spec.loader.exec_module(SUPPORT)

    def sources():
        return {name: {p.relative_to(root).as_posix(): pin(p.read_bytes()) for p in sorted((root / 'src/canvaspilot').glob('*.py'))}
                for name, root in [('before', ARGS.before_source), ('candidate', ARGS.source)]}

    before = sources()
    save(ARGS.output / 'source-before.json', before)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CurrentReceiving))
    after = sources()
    save(ARGS.output / 'source-after.json', after)
    if before != after:
        raise RuntimeError('private source changed during receiving')
    commands = []
    for file in sorted(ARGS.output.glob('*/wire/commands.json')):
        commands.extend(json.loads(file.read_text()))
    requests = [r for command in commands for r in command['requests']]
    save(ARGS.output / 'result.json', {'schema': 'independent-current79-feedback.v1', 'parent': '79a2f2b2cbb7e74128d731cf096c7e86f1942d4b',
         'tree': '0114a6230c473c1ee1d01b99c7121c754b781d54', 'tests': result.testsRun,
         'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped),
         'success': result.wasSuccessful(), 'source_before_after_identical': True,
         'private_runtime_files': sum(len(x) for x in before.values()), 'commands': len(commands),
         'HTTP_GETs': sum(x['method'] == 'GET' for x in requests), 'HTTP_POSTs_to_authored_broker_only': sum(x['method'] == 'POST' for x in requests),
         'synthetic_broker_GET_intents': sum(x.get('payload', {}).get('method') == 'GET' for x in requests),
         'actual_new_html_files': len(list(ARGS.output.glob('*/feedback.html'))),
         'browser_allocations': 0, 'actual_broker_processes': 0, 'live_accounts': 0, 'github_writes': 0,
         'probe': pin(Path(__file__).read_bytes()), 'support': pin(support.read_bytes()), 'python': sys.version})
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
