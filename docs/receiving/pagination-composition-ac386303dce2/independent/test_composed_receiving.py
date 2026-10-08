"""Independent composition controls through authored PAT and real broker HTTP.

Every Canvas response is authored here. Token requests use the production
_ensure_http constructor with an injected HTTPX transport; broker requests use
the unchanged production Handler with its browser queue boundary authored.
No school account, browser profile, environment token, or live Canvas endpoint
is read. The review token is deliberately synthetic.
"""

from __future__ import annotations

import contextlib
import copy
from http.server import ThreadingHTTPServer
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urljoin

import httpx

from canvaspilot import client as cm
from canvaspilot import session_broker as broker


BASE = "https://composition-campus.instructure.com"
PATH = "/api/v1/courses/42/assignments"
NEXT = BASE + PATH + "?cursor=%2f%2F,a;b&include%5B%5D=one&include%5B%5D=two&empty=&literal=+"
SIMPLE_NEXT = BASE + PATH + "?cursor=second"
SYNTHETIC_TOKEN = "independent-review-not-a-credential"


@contextlib.contextmanager
def transport(mode, pages):
    """Yield one actual client and its observed outbound Canvas requests."""
    queued = copy.deepcopy(list(pages))
    calls = []

    def response_for(url):
        calls.append({"url": url})
        if not queued:
            raise AssertionError("request after the authored terminal boundary")
        return queued.pop(0)

    if mode == "token":
        real_client = httpx.Client

        def receiving(request):
            data, link = response_for(str(request.url))
            return httpx.Response(200, json=data, headers={"link": link})

        def client_factory(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(receiving)
            kwargs["trust_env"] = False
            return real_client(*args, **kwargs)

        with patch.object(cm.httpx, "Client", side_effect=client_factory), \
                patch.object(cm, "broker_health", side_effect=AssertionError("PAT consulted broker")):
            with cm.CanvasClient(base_url=BASE, token=SYNTHETIC_TOKEN, timeout=3) as client:
                yield client, calls
        return

    if mode != "broker":
        raise ValueError("unknown authored transport")

    def browser(job):
        data, link = response_for(urljoin(BASE + "/", job["path"]))
        return {"ok": True, "response": {
            "status": 200, "json": data, "headers": {"link": link},
        }}

    with patch.object(broker, "_call", side_effect=browser), \
            patch.object(broker.STATE, "base_url", BASE), \
            patch.object(broker.STATE, "read_only", True), \
            patch.object(broker.Handler, "log_message", lambda *args: None):
        server = ThreadingHTTPServer(("127.0.0.1", 0), broker.Handler)
        thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True,
        )
        thread.start()
        try:
            with patch.object(cm, "BROKER_PORT", server.server_address[1]):
                with cm.CanvasClient(base_url=BASE, token="", timeout=3) as client:
                    yield client, calls
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)
            if thread.is_alive():
                raise RuntimeError("authored broker HTTP thread did not close")


class ComposedReceiving(unittest.TestCase):
    def test_context_exclusion_is_independent_of_order_and_transport(self):
        anchored = '<https://other.invalid/list?cursor=canary>; rel="next"; AnChOr="/other-context"'
        applicable = f'<{NEXT}>; title="opaque, query; remains"; rel="alternate NEXT"'
        for mode in ("token", "broker"):
            for entries in ((anchored, applicable), (applicable, anchored)):
                with self.subTest(mode=mode, anchored_first=entries[0] == anchored):
                    pages = [([{"id": 1}], ", ".join(entries)), ([{"id": 2}], "")]
                    with transport(mode, pages) as (client, calls):
                        self.assertEqual(client.get_paginated(PATH), [{"id": 1}, {"id": 2}])
                        self.assertEqual(len(calls), 2)
                        self.assertEqual(calls[1]["url"], NEXT)

    def test_malformed_metadata_after_a_valid_page_never_returns_a_prefix(self):
        malformed = (
            f"<{BASE + PATH}?cursor=unclassified>",
            f'<{BASE + PATH}?cursor=unclassified>; rel="https://relations.invalid/bad%qq"',
        )
        for mode in ("token", "broker"):
            for header in malformed:
                with self.subTest(mode=mode, header=header):
                    pages = [([{"id": 1}], f'<{SIMPLE_NEXT}>; rel="next"'), ([{"id": 2}], header)]
                    with transport(mode, pages) as (client, calls):
                        with self.assertRaises(cm.CanvasPaginationError):
                            client.get_paginated(PATH)
                        self.assertEqual(len(calls), 2)

    def test_terminal_mapping_compatibility_does_not_admit_a_later_mapping(self):
        mapping = {"id": 9, "kind": "single-object"}
        for mode in ("token", "broker"):
            with self.subTest(mode=mode, position="first"):
                with transport(mode, [(mapping, "")]) as (client, calls):
                    self.assertEqual(client.get_paginated(PATH), [mapping])
                    self.assertEqual(len(calls), 1)
            with self.subTest(mode=mode, position="later"):
                pages = [([{"id": 1}], f'<{SIMPLE_NEXT}>; rel="next"'), (mapping, "")]
                with transport(mode, pages) as (client, calls):
                    with self.assertRaises(cm.CanvasPaginationError):
                        client.get_paginated(PATH)
                    self.assertEqual(len(calls), 2)

    def test_initial_pat_target_admission_precedes_any_http_dispatch(self):
        invalid = (
            "//other.invalid/api/v1/assignments",
            PATH + "#private-fragment",
            PATH + "?cursor=back\\slash",
            BASE + ":not-a-port" + PATH,
            PATH + "?cursor=control\nvalue",
        )
        for path in invalid:
            with self.subTest(path=path):
                with transport("token", [([{"id": 1}], "")]) as (client, calls):
                    with self.assertRaises(cm.CanvasPaginationError):
                        client.get_paginated(path)
                    self.assertEqual(calls, [])

    def test_nonboolean_broker_capability_cannot_assert_collection_completeness(self):
        for capability in (False, "true", 1, None):
            with self.subTest(capability=capability):
                with transport("broker", [([{"id": 1}], "")]) as (client, calls):
                    health = {"ok": True, "base_url": BASE, "link_pagination": capability}
                    with patch.object(cm, "broker_health", return_value=health):
                        with self.assertRaisesRegex(cm.CanvasPaginationError, "metadata|restart|[Ll]ink|incomplete"):
                            client.get_paginated(PATH)
                        self.assertEqual(calls, [])
                        self.assertEqual(client.request("GET", PATH), [{"id": 1}])
                        self.assertEqual(len(calls), 1)

    def test_first_query_filters_and_opaque_continuation_have_the_same_wire_contract(self):
        path = BASE + PATH + "?cursor=first%2f&tag=one&tag=two"
        filters = {"search_term": "rain + snow", "include[]": ["submission", "visibility"], "published": False}
        before = copy.deepcopy(filters)
        expected_first = path + "&" + str(httpx.QueryParams({**filters, "per_page": 50}))
        pages = [([], f'<{NEXT}>; rel="next"'), ([{"id": 2}], "")]
        for mode in ("token", "broker"):
            with self.subTest(mode=mode):
                with transport(mode, pages) as (client, calls):
                    self.assertEqual(client.get_paginated(path, params=filters), [{"id": 2}])
                    self.assertEqual(filters, before)
                    self.assertEqual([call["url"] for call in calls], [expected_first, NEXT])


if __name__ == "__main__":
    unittest.main(verbosity=2)
