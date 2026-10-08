"""Execute the production in-page fetch in a fresh native Chromium profile.

Opt in with CANVASPILOT_CHROMIUM_BIN. No Playwright driver or school session is
needed: Chromium fetches an authored loopback response and emits its DOM. The
Python client/Handler receiving boundary is independently covered by test_broker_links.
"""
from __future__ import annotations

import ast
import html
import json
import os
import signal
import subprocess
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class ProbeResult(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.text = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'pre' and dict(attrs).get('id') == 'result':
            self.inside = True

    def handle_endtag(self, tag):
        if tag == 'pre':
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.text += data


class BrowserLinkMetadata(unittest.TestCase):
    @unittest.skipUnless('CANVASPILOT_CHROMIUM_BIN' in os.environ,
                         'set CANVASPILOT_CHROMIUM_BIN for native Chromium qualification')
    def test_real_browser_returns_link_only_and_keeps_session_fetch(self):
        binary = os.environ['CANVASPILOT_CHROMIUM_BIN']
        if not binary:
            self.fail('CANVASPILOT_CHROMIUM_BIN is explicitly empty')
        source_path = Path(os.environ.get(
            'CANVASPILOT_BROKER_SOURCE',
            str(Path(__file__).resolve().parents[1] / 'src/canvaspilot/session_broker.py'),
        ))
        tree = ast.parse(source_path.read_text())
        functions = [call.args[0].value for call in ast.walk(tree)
                     if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                     and call.func.attr == 'evaluate' and call.args
                     and isinstance(call.args[0], ast.Constant)
                     and isinstance(call.args[0].value, str)]
        self.assertEqual(1, len(functions), 'identify the exact production fetch expression')
        received = []
        api_rows = [{'id': 17, 'name': 'Authored fixture assignment'}]

        class Provider(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == '/probe':
                    args = {'method': 'GET', 'path': '/api/v1/courses',
                            'headers': {'Accept': 'application/json'}, 'body': None}
                    doc = ('<!doctype html><pre id="result">pending</pre><script>'
                           f'({functions[0]})({json.dumps(args)}).then(value => {{'
                           'document.getElementById("result").textContent=JSON.stringify(value);'
                           '}).catch(error => {'
                           'document.getElementById("result").textContent=JSON.stringify({error:String(error)});'
                           '});</script>')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Set-Cookie', 'canvas_fixture=authored; Path=/; HttpOnly; SameSite=Lax')
                    self.end_headers()
                    self.wfile.write(doc.encode())
                elif self.path == '/api/v1/courses':
                    received.append({'method': 'GET', 'session_present':
                                     'canvas_fixture=authored' in self.headers.get('Cookie', ''),
                                     'accept': self.headers.get('Accept')})
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('LiNk', self.server.next_link)
                    self.send_header('Set-Cookie', 'unrelated_fixture=not-forwarded; Path=/; HttpOnly')
                    self.send_header('X-Unrelated-Fixture', 'not-forwarded')
                    self.end_headers()
                    self.wfile.write(json.dumps(api_rows).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

        server = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
        port = server.server_address[1]
        server.next_link = f'<http://127.0.0.1:{port}/api/v1/courses?opaque=a%2Bb%3D>; rel="next"'
        thread = threading.Thread(target=server.serve_forever,
                                  kwargs={'poll_interval': 0.01}, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(
                prefix='canvaspilot-links-', dir=os.environ.get('CANVASPILOT_CHROMIUM_PROFILE_ROOT'),
            ) as profile:
                command = [binary, '--headless', '--dump-dom', '--virtual-time-budget=3000',
                           '--no-first-run', '--no-default-browser-check',
                           '--disable-background-networking', '--disable-component-update',
                           '--disable-domain-reliability', '--disable-features=MediaRouter,OptimizationHints',
                           '--user-data-dir=' + profile, f'http://127.0.0.1:{port}/probe']
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           text=True, start_new_session=True)
                try:
                    output, errors = process.communicate(timeout=30)
                    self.assertEqual(0, process.returncode, errors[-3000:])
                finally:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    if process.poll() is None:
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait(timeout=3)
            parser = ProbeResult()
            parser.feed(output)
            self.assertNotEqual('pending', parser.text, 'browser fetch must finish')
            result = json.loads(html.unescape(parser.text))
            self.assertEqual(api_rows, result['json'])
            self.assertEqual(200, result['status'])
            self.assertEqual({'link': server.next_link}, result.get('headers'))
            self.assertEqual([{'method': 'GET', 'session_present': True,
                              'accept': 'application/json'}], received)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
