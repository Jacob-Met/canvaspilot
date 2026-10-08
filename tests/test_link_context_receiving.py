"""Independent HTTP receiving checks for PR35, with authored browser responses."""
import contextlib
import copy
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from canvaspilot import client as cm
from canvaspilot import session_broker as broker

BASE = 'https://review-campus.instructure.com'
PATH = '/api/v1/courses/42/assignments'
GOOD = BASE + PATH + '?opaque=a,b;c%2Bz'
OTHER = BASE + '/api/v1/courses/99/assignments?opaque=other'


@contextlib.contextmanager
def server_for(first_header, *, old_broker=False):
    calls = []

    def browser(job):
        calls.append(copy.deepcopy(job))
        path = job['path']
        if len(calls) == 1:
            data, header = [{'id': 1, 'course_id': 42}], first_header
        elif path == GOOD:
            data, header = [{'id': 2, 'course_id': 42}], ''
        elif path == OTHER:
            data, header = [{'id': 99, 'course_id': 99}], ''
        else:
            raise AssertionError('Unadvertised request: ' + path)
        return {'ok': True, 'response': {'status': 200, 'json': data, 'headers': {'link': header}}}

    with patch.object(broker, '_call', side_effect=browser), \
            patch.object(broker.STATE, 'base_url', BASE), \
            patch.object(broker.STATE, 'read_only', True), \
            patch.object(broker.Handler, 'log_message', lambda *args: None):
        server = ThreadingHTTPServer(('127.0.0.1', 0), broker.Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        thread.start()
        try:
            with patch.object(cm, 'BROKER_PORT', server.server_address[1]):
                if old_broker:
                    with patch.object(cm, 'broker_health', return_value={'ok': True, 'base_url': BASE}):
                        yield calls
                else:
                    yield calls
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)


class LinkContextReceiving(unittest.TestCase):
    def collect(self):
        with cm.CanvasClient(token='') as client:
            return client.get_paginated(PATH)

    def test_registered_next_relation_is_case_insensitive(self):
        for relation in ('NEXT', 'NeXt', 'prev NEXT'):
            with self.subTest(relation=relation), server_for(f'<{GOOD}>; ReL="{relation}"') as calls:
                self.assertEqual([row['id'] for row in self.collect()], [1, 2])
                self.assertEqual(calls[1]['path'], GOOD)

    def test_other_resource_anchor_is_not_current_pagination(self):
        header = f'<{OTHER}>; rel="next"; anchor="{BASE}/api/v1/courses/99/assignments"'
        with server_for(header) as calls:
            self.assertEqual(self.collect(), [{'id': 1, 'course_id': 42}])
            self.assertEqual(len(calls), 1)

    def test_anchored_next_does_not_hide_the_applicable_next(self):
        header = (f'<{OTHER}>; rel="next"; AnChOr="{BASE}/api/v1/courses/99/assignments", '
                  f'<{GOOD}>; rel="next"')
        with server_for(header) as calls:
            self.assertEqual([row['id'] for row in self.collect()], [1, 2])
            self.assertEqual([call['path'] for call in calls[1:]], [GOOD])

    def test_standard_opaque_continuation_preserves_punctuation(self):
        with server_for(f'<{GOOD}>; title="part, two; still same"; rel="next"') as calls:
            self.assertEqual([row['id'] for row in self.collect()], [1, 2])
            self.assertEqual(calls[1]['path'], GOOD)

    def test_other_origin_is_refused_before_dispatch(self):
        with server_for('<https://other.invalid/page>; rel="next"') as calls:
            with self.assertRaisesRegex(RuntimeError, 'origin'):
                self.collect()
            self.assertEqual(len(calls), 1)



if __name__ == '__main__':
    unittest.main(verbosity=2)
