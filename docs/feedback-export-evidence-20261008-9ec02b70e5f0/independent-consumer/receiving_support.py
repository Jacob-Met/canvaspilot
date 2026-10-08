"""Independent offline HTML consumer and real loopback native-CLI transport."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit

COURSE = '77'
ASSIGNMENT = '314'
ASSIGNMENT_PATH = f'/api/v1/courses/{COURSE}/assignments/{ASSIGNMENT}'
SUBMISSION_PATH = ASSIGNMENT_PATH + '/submissions/self'
DEPS = Path('/dev/shm/hamon-afe225d6c6be-product/canvas-deps')
AUTHORED_TOKEN = 'independent-local-fixture-only'


def fingerprint(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}


def pretty(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def authored_feedback():
    return (
        {'id': 314, 'course_id': 77, 'name': 'Δοκιμή · 研究 <draft> & feedback',
         'html_url': 'https://canvas.invalid/courses/77/assignments/314',
         'due_at': None, 'points_possible': 0, 'use_rubric_for_grading': False,
         'rubric_settings': {'id': 891, 'points_possible': 47.25,
                             'hide_points': False, 'hide_score_total': False,
                             'hide_outcome_results': False},
         'rubric': [{'id': 'k-outcome', 'description': 'Outcome evidence Ω',
                     'long_description': 'Demonstrate the stated connection.',
                     'points': 8.75, 'learning_outcome_id': 610,
                     'ratings': [{'id': 'rating-zero', 'description': 'Still developing',
                                  'points': 0}]},
                    {'id': 'k-unknown', 'description': 'Unassessed criterion 未',
                     'points': None}]},
        {'id': 801, 'assignment_id': 314, 'user_id': 909,
         'attempt': 7, 'workflow_state': 'graded', 'score': 0, 'grade': '0',
         'grade_matches_current_submission': False, 'grader_id': 202,
         'graded_at': '2026-10-01T10:02:03Z', 'submitted_at': '2026-10-02T12:00:00Z',
         'posted_at': None, 'excused': False, 'late': False, 'missing': None,
         'rubric_assessment': {'k-outcome': {'points': 0,
                                'comments': 'Keep the claimed outcome visible.',
                                'rating_id': 'rating-zero'},
                               'orphan-criterion': {'points': 2.125,
                                'comments': 'An unjoined assessment stays unjoined.'}},
         'submission_comments': [
             {'id': 71, 'author_id': 202, 'author_name': 'Kai <learner> & Ω',
              'created_at': '2026-10-03T15:16:17Z',
              'comment': 'Literal <script>window.INJECTED=1</script> & 日本語\nSecond line.',
              'author': {'id': 203, 'display_name': 'Nested supplied name 研',
                         'role': 'student'}},
             {'id': 72, 'author': {'id': 204, 'display_name': 'Only nested author β'},
              'comment': '', 'media_comment': {'display_name': 'Spoken response 日本語',
                                              'url': 'https://media.invalid/voice.ogg'},
              'attachments': [{'display_name': 'voice <literal>.ogg',
                               'url': 'https://media.invalid/voice.ogg'}]},
             {'id': 73, 'comment': 'No author supplied for this separate comment.'},
         ]}
    )


@dataclass
class Element:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    parent: 'Element | None' = None

    def text(self):
        if self.tag in {'script', 'style'}:
            return ''
        return ''.join(x if isinstance(x, str) else x.text() for x in self.children)

    def descendants(self, tag=None):
        for child in self.children:
            if isinstance(child, Element):
                if tag is None or child.tag == tag:
                    yield child
                yield from child.descendants(tag)


class OfflineDocument(HTMLParser):
    """Read actual document structure without importing a formatter helper."""
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
            'param', 'source', 'track', 'wbr'}

    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.document = Element('document')
        self.stack = [self.document]
        self.feed(raw.decode('utf-8', errors='strict'))
        self.close()

    def handle_starttag(self, tag, attrs):
        element = Element(tag, dict(attrs), parent=self.stack[-1])
        self.stack[-1].children.append(element)
        if tag not in self.VOID:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, text):
        self.stack[-1].children.append(text)

    def text(self):
        return self.document.text()

    def elements(self, tag=None):
        return list(self.document.descendants(tag))

    def definitions(self, within=None):
        node = within or self.document
        result = []
        for dl in node.descendants('dl'):
            key = None
            for child in dl.children:
                if isinstance(child, Element) and child.tag == 'dt':
                    key = child.text().strip()
                elif isinstance(child, Element) and child.tag == 'dd' and key is not None:
                    result.append((key, child.text().strip()))
        return result

    def tables(self):
        return [[[(cell.tag, cell.text().strip()) for cell in row.children
                  if isinstance(cell, Element) and cell.tag in {'th', 'td'}]
                 for row in table.descendants('tr')]
                for table in self.document.descendants('table')]

    def fields(self):
        values = {}
        for element in self.elements('dd'):
            key = element.attrs.get('data-field')
            if key:
                if key in values:
                    raise ValueError('duplicate semantic field: ' + key)
                values[key] = element.text().strip()
        return values

    def by_id(self, identity):
        matches = [element for element in self.elements() if element.attrs.get('id') == identity]
        if len(matches) != 1:
            raise ValueError('missing or duplicate element ID: ' + identity)
        return matches[0]


class LocalCanvas:
    def __init__(self, assignment, submission, receipts, *, responses=None, before_response=None):
        self.assignment = deepcopy(assignment)
        self.submission = deepcopy(submission)
        self.receipts = Path(receipts)
        self.receipts.mkdir(parents=True, exist_ok=False)
        self.requests = []
        self.responses = responses or {}
        self.before_response = before_response
        self.commands = []

    def __enter__(self):
        local = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                parts = urlsplit(self.path)
                record = {'method': 'GET', 'path': parts.path,
                          'query': parse_qs(parts.query),
                          'synthetic_authorization_matches': self.headers.get('Authorization') == 'Bearer ' + AUTHORED_TOKEN}
                local.requests.append(record)
                if local.before_response is not None:
                    local.before_response(parts.path)
                if parts.path in local.responses:
                    status, body, content_type = local.responses[parts.path]
                elif parts.path == ASSIGNMENT_PATH:
                    status, body, content_type = 200, pretty(local.assignment), 'application/json; charset=utf-8'
                elif parts.path == SUBMISSION_PATH:
                    status, body, content_type = 200, pretty(local.submission), 'application/json; charset=utf-8'
                else:
                    status, body, content_type = 404, b'{"error":"outside authored routes"}', 'application/json'
                record['response_status'] = status
                record['response'] = fingerprint(body)
                self.send_response(status)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def reject_write(self):
                local.requests.append({'method': self.command, 'path': self.path})
                self.send_error(405, 'read-only authored server')

            do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = reject_write

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.server.server_address[1])
        (self.receipts / 'authored-responses.json').write_bytes(pretty({'assignment': self.assignment, 'submission': self.submission}))
        return self

    def cli(self, source, operation, *, out=None):
        sequence = len(self.commands) + 1
        command = [sys.executable, '-B', *(['-O'] if sys.flags.optimize else []),
                   '-m', 'canvaspilot.cli', operation, COURSE, ASSIGNMENT,
                   '--base-url', self.url, '--token', AUTHORED_TOKEN,
                   '--profile', str(self.receipts / 'unused-profile')]
        if out is not None:
            command.extend(['--out', str(out)])
        env = {'PATH': '/usr/local/bin:/usr/bin:/bin',
               'PYTHONPATH': str(Path(source) / 'src') + ':' + str(DEPS),
               'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONIOENCODING': 'utf-8',
               'NO_PROXY': '127.0.0.1', 'no_proxy': '127.0.0.1'}
        prior_requests = len(self.requests)
        started = datetime.now(timezone.utc).isoformat()
        clock = time.monotonic()
        process = subprocess.run(command, cwd=source, env=env, capture_output=True,
                                 encoding='utf-8', errors='strict', timeout=30)
        record = {'command': command, 'cwd': str(source), 'started_at_utc': started,
                  'elapsed_seconds': time.monotonic() - clock, 'returncode': process.returncode,
                  'stdout': process.stdout, 'stderr': process.stderr,
                  'requests': deepcopy(self.requests[prior_requests:])}
        if out is not None and Path(out).is_file() and not Path(out).is_symlink():
            raw = Path(out).read_bytes()
            record['output_file'] = fingerprint(raw)
            (self.receipts / f'command-{sequence:02d}.html').write_bytes(raw)
        self.commands.append(record)
        (self.receipts / f'command-{sequence:02d}.json').write_bytes(pretty(record))
        return record

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        (self.receipts / 'requests.json').write_bytes(pretty(self.requests))
        (self.receipts / 'commands.json').write_bytes(pretty(self.commands))


def terminal_json(stream):
    """CLI HTTP diagnostics precede its terminal structured error on stderr."""
    for line in reversed(stream.splitlines()):
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError('no terminal JSON object')
