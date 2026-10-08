"""Independent replay of author's later-page shape question, at frozen PR35."""
import unittest

from test_link_context_receiving import BASE, GOOD, PATH, server_for

from canvaspilot import client as cm
from canvaspilot import session_broker as broker


class TerminalPageShapeReceiving(unittest.TestCase):
    def test_later_terminal_page_cannot_turn_a_collection_into_an_object(self):
        for label, json_value, text in (
            ('object', {'error': 'authored application failure'}, None),
            ('html', None, '<html>authored reauthentication</html>'),
            ('empty', None, ''),
        ):
            with self.subTest(shape=label), server_for(f'<{GOOD}>; rel="next"') as calls:
                original = broker._call.side_effect

                def browser(job, original=original, json_value=json_value, text=text):
                    response = original(job)
                    if len(calls) == 2:
                        response['response']['json'] = json_value
                        response['response']['text'] = text
                    return response

                broker._call.side_effect = browser
                with cm.CanvasClient(token='') as client, \
                        self.assertRaisesRegex(RuntimeError, 'non-list|collection|shape|list'):
                    client.get_paginated(PATH)
                self.assertEqual(len(calls), 2)

    def test_first_terminal_object_preserves_single_resource_compatibility(self):
        with server_for('') as calls:
            original = broker._call.side_effect

            def browser(job):
                response = original(job)
                response['response']['json'] = {'id': 42, 'name': 'Authored single course'}
                return response

            broker._call.side_effect = browser
            with cm.CanvasClient(base_url=BASE, token='') as client:
                self.assertEqual(client.get_paginated('/api/v1/courses/42'), [
                    {'id': 42, 'name': 'Authored single course'},
                ])
            self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
