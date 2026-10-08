"""Explicit new receiving policy, superseding the recorded legacy fallback control.

The former eight-method acceptance remains valid for e208's narrower contract.
Combined collection retrieval requires metadata proving completion. An older
broker remains usable for an ordinary non-paginated request.
"""
import unittest

from test_link_context_receiving import PATH, server_for

from canvaspilot import client as cm


class LegacyMetadataPolicy(unittest.TestCase):
    def test_collection_requires_actionable_metadata_or_restart_error(self):
        with server_for('', old_broker=True) as calls:
            with (cm.CanvasClient(token='') as client,
                  self.assertRaisesRegex(RuntimeError, 'metadata|restart|[Ll]ink|incomplete')):
                client.get_paginated(PATH)
            self.assertLessEqual(len(calls), 1)

    def test_ordinary_decoded_request_keeps_old_broker_compatibility(self):
        with server_for('', old_broker=True) as calls:
            with cm.CanvasClient(token='') as client:
                self.assertEqual(client.request('GET', PATH), [{'id': 1, 'course_id': 42}])
            self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
