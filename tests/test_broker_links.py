"""Canvas continuation contract through the real local broker HTTP handler.

Only the browser worker is replaced. Authored responses follow Canvas's current
public pagination contract: page size is not guaranteed, and rel=next URLs are
opaque. No school account, external request or Canvas write is involved.
"""
from __future__ import annotations

import copy
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from canvaspilot import client as client_mod
from canvaspilot import session_broker
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient

BASE = 'https://fixture.instructure.com'
PATH = '/api/v1/courses/42/assignments'
NEXT = BASE + PATH + '?cursor=a%2Bb%3D&include%5B%5D=submission&include%5B%5D=rubric'


@pytest.fixture
def receiver(monkeypatch):
    calls = []
    response = {'handler': lambda job: {'status': 200, 'json': [], 'headers': {'link': ''}}}

    def browser(job):
        calls.append(copy.deepcopy(job))
        return {'ok': True, 'response': response['handler'](job)}

    monkeypatch.setattr(session_broker, '_call', browser)
    monkeypatch.setattr(session_broker.STATE, 'read_only', True)
    monkeypatch.setattr(session_broker.STATE, 'base_url', BASE)
    server = ThreadingHTTPServer(('127.0.0.1', 0), session_broker.Handler)
    monkeypatch.setattr(client_mod, 'BROKER_PORT', server.server_address[1])
    thread = threading.Thread(target=server.serve_forever,
                              kwargs={'poll_interval': 0.01}, daemon=True)
    thread.start()
    try:
        yield calls, response
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def page(rows, next_url=None, *, spelling='link'):
    return {'status': 200, 'json': rows,
            'headers': {spelling: f'<{next_url}>; rel="next"' if next_url else ''}}


def test_assignment_list_follows_short_page_and_exact_opaque_link(receiver):
    calls, response = receiver
    rows = [{'id': n, 'name': f'Assignment {n}'} for n in range(1, 4)]

    def canvas(job):
        if 'cursor=' in job['path']:
            assert job['path'] == NEXT
            return page(rows[1:])
        return page(rows[:1], NEXT, spelling='LiNk')

    response['handler'] = canvas
    with CanvasAPI(CanvasClient(base_url=BASE, token='')) as api:
        result = api.list_assignments(42)
    assert [row['id'] for row in result] == [1, 2, 3]
    assert len(calls) == 2
    assert parse_qs(urlsplit(calls[0]['path']).query)['include[]'] == ['submission']
    assert calls[1]['path'] == NEXT


def test_full_terminal_page_does_not_invent_another_request(receiver):
    calls, response = receiver
    rows = [{'id': n} for n in range(50)]

    def canvas(job):
        if len(calls) > 1:
            return {'status': 400, 'json': {'error': 'numeric continuation is not supported'},
                    'headers': {'link': ''}}
        return page(rows)

    response['handler'] = canvas
    with CanvasClient(base_url=BASE, token='') as client:
        assert client.get_paginated(PATH) == rows
    assert len(calls) == 1


def test_repeated_continuation_refuses_partial_success(receiver):
    calls, response = receiver
    response['handler'] = lambda job: page([{'id': len(calls)}], NEXT)
    with (CanvasClient(base_url=BASE, token='') as client,
          pytest.raises(RuntimeError, match='repeat|cycle')):
        client.get_paginated(PATH)
    assert len(calls) == 2


def test_foreign_continuation_is_refused_before_browser_dispatch(receiver):
    calls, response = receiver
    response['handler'] = lambda job: page([{'id': 1}], 'https://other.invalid/api/v1/courses')
    with (CanvasClient(base_url=BASE, token='') as client,
          pytest.raises(RuntimeError, match='origin')):
        client.get_paginated(PATH)
    assert len(calls) == 1


def test_ordinary_request_keeps_its_decoded_response(receiver):
    calls, response = receiver
    row = {'id': 42, 'name': 'Authored course'}
    response['handler'] = lambda job: page(row, NEXT)
    with CanvasClient(base_url=BASE, token='') as client:
        assert client.request('GET', '/api/v1/courses/42') == row
    assert len(calls) == 1


def test_broker_configured_school_origin_works_with_default_client(receiver):
    calls, response = receiver
    response['handler'] = lambda job: page([{'id': len(calls)}], NEXT if len(calls) == 1 else None)
    with CanvasClient(token='') as client:
        assert client.get_paginated(PATH) == [{'id': 1}, {'id': 2}]
    assert len(calls) == 2


@pytest.mark.parametrize('bad', [None, [], {}, {'link': None}, {'link': 12},
                               {'link': '', 'Link': ''}])
def test_supported_broker_requires_complete_link_metadata(receiver, bad):
    calls, response = receiver
    response['handler'] = lambda job: {'status': 200, 'json': [{'id': 1}], 'headers': bad}
    with (CanvasClient(base_url=BASE, token='') as client,
          pytest.raises(RuntimeError, match='Link metadata')):
        client.get_paginated(PATH)
    assert len(calls) == 1


@pytest.mark.parametrize('url', [
    'http://fixture.instructure.com/api/v1/courses',
    'https://fixture.instructure.com:444/api/v1/courses',
    'https://fixture.instructure.com:0/api/v1/courses',
    'https://user@fixture.instructure.com/api/v1/courses',
    '/api/v1/courses?page=2',
    '//fixture.instructure.com/api/v1/courses',
    'https://fixture.instructure.com/api/v1/courses#next',
    'https://fixture.instructure.com:bad/api/v1/courses',
    'https://fixture.instructure.com/api/v1/bad path',
])
def test_ambiguous_or_other_origin_link_never_reaches_browser(receiver, url):
    calls, response = receiver
    response['handler'] = lambda job: page([{'id': 1}], url)
    with (CanvasClient(base_url=BASE, token='') as client,
          pytest.raises(RuntimeError, match='origin')):
        client.get_paginated(PATH)
    assert len(calls) == 1


@pytest.mark.parametrize('last_has_next', [False, True])
def test_page_limit_distinguishes_complete_from_incomplete_traversal(receiver, last_has_next):
    calls, response = receiver

    def canvas(job):
        n = len(calls)
        return page([{'id': n}], BASE + PATH + f'?opaque={n}'
                    if n < 40 or last_has_next else None)

    response['handler'] = canvas
    with CanvasClient(base_url=BASE, token='') as client:
        if last_has_next:
            with pytest.raises(RuntimeError, match='40-page cap'):
                client.get_paginated(PATH)
        else:
            assert client.get_paginated(PATH) == [{'id': n} for n in range(1, 41)]
    assert len(calls) == 40


@pytest.mark.parametrize('status', [401, 503])
def test_later_http_failure_never_returns_prior_pages_as_success(receiver, status):
    calls, response = receiver
    response['handler'] = lambda job: (
        page([{'id': 1}], NEXT) if len(calls) == 1 else
        {'status': status, 'json': {'error': 'authored failure'}, 'headers': {'link': ''}}
    )
    error = RuntimeError if status == 401 else httpx.HTTPStatusError
    with (CanvasClient(base_url=BASE, token='') as client, pytest.raises(error)):
        client.get_paginated(PATH)
    assert len(calls) == 2


def test_single_object_without_continuation_remains_supported(receiver):
    calls, response = receiver
    response['handler'] = lambda job: page({'id': 7})
    with CanvasClient(base_url=BASE, token='') as client:
        assert client.get_paginated('/api/v1/users/self') == [{'id': 7}]
    assert len(calls) == 1


def test_object_with_continuation_is_not_silent_truncation(receiver):
    calls, response = receiver
    response['handler'] = lambda job: page({'items': [{'id': 7}]}, NEXT)
    with (CanvasClient(base_url=BASE, token='') as client,
          pytest.raises(RuntimeError, match='non-list continuing page')):
        client.get_paginated(PATH)
    assert len(calls) == 1


def test_initial_selectors_are_preserved_and_not_reapplied_to_next_link(receiver):
    calls, response = receiver
    params = [('include[]', 'a'), ('page', 'opaque-initial'), ('include[]', 'b'),
              ('per_page', 7), ('search_term', 'café + study')]
    before = copy.deepcopy(params)
    response['handler'] = lambda job: page([{'id': len(calls)}], NEXT if len(calls) == 1 else None)
    with CanvasClient(base_url=BASE, token='') as client:
        assert client.get_paginated(PATH, params=params) == [{'id': 1}, {'id': 2}]
    assert parse_qs(urlsplit(calls[0]['path']).query) == {
        'include[]': ['a', 'b'], 'page': ['opaque-initial'], 'per_page': ['7'],
        'search_term': ['café + study'],
    }
    assert calls[1]['path'] == NEXT
    assert params == before


@pytest.mark.parametrize('suffix', ['?cursor=a,b', '?cursor=a;b', '?cursor=a%2Bb%3D&filter=x,y;z'])
def test_opaque_cursor_punctuation_reaches_the_next_request_unchanged(receiver, suffix):
    calls, response = receiver
    continuation = BASE + PATH + suffix
    response['handler'] = lambda job: page([{'id': len(calls)}],
                                           continuation if len(calls) == 1 else None)
    with CanvasClient(base_url=BASE, token='') as client:
        assert client.get_paginated(PATH) == [{'id': 1}, {'id': 2}]
    assert calls[1]['path'] == continuation


def test_link_relations_and_quoted_parameters_do_not_change_continuation(receiver):
    calls, response = receiver

    def canvas(job):
        if len(calls) == 1:
            header = (f'<{BASE + PATH}>; rel="current", <{NEXT}>; title="part, two; <three>"; '
                      'rel="next alternate"; type=application/json')
            return {'status': 200, 'json': [{'id': 1}], 'headers': {'link': header}}
        return page([{'id': 2}])

    response['handler'] = canvas
    with CanvasClient(base_url=BASE, token='') as client:
        assert client.get_paginated(PATH) == [{'id': 1}, {'id': 2}]
    assert calls[1]['path'] == NEXT


@pytest.mark.parametrize('header', [
    'not a Link header',
    '<unclosed; rel="next"',
    f'<{NEXT}>; rel="next",',
    f'<{NEXT}>; rel="next", <{NEXT}>; rel="next"',
    f'<{NEXT}>; rel="next"; rel="prev"',
    f'<{NEXT}>; rel',
    f'<{NEXT}>; rel="next',
])
def test_malformed_or_ambiguous_link_is_not_silent_completion(receiver, header):
    calls, response = receiver
    response['handler'] = lambda job: {'status': 200, 'json': [{'id': 1}],
                                      'headers': {'link': header}}
    with (CanvasClient(base_url=BASE, token='') as client, pytest.raises(RuntimeError)):
        client.get_paginated(PATH)
    assert len(calls) == 1


def test_module_fallback_composes_with_opaque_module_and_item_pages(receiver):
    calls, response = receiver
    modules_path = '/api/v1/courses/42/modules'
    modules_next = BASE + modules_path + '?module_cursor=a%2Bb'
    items_path = modules_path + '/7/items'
    items_next = BASE + items_path + '?item_cursor=x,y;z'

    def canvas(job):
        path = job['path']
        if path == modules_next:
            return page([{'id': 8, 'items_count': 0}])
        if path == items_next:
            return page([{'id': 72, 'title': 'Second item'}])
        if urlsplit(path).path == modules_path:
            return page([{'id': 7, 'name': 'Authored module', 'items_count': 2}], modules_next)
        assert urlsplit(path).path == items_path
        return page([{'id': 71, 'title': 'First item'}], items_next)

    response['handler'] = canvas
    with CanvasAPI(CanvasClient(base_url=BASE, token='')) as api:
        modules = api.list_modules(42, detail='full')
    assert [module['id'] for module in modules] == [7, 8]
    assert [item['id'] for item in modules[0]['items']] == [71, 72]
    assert modules[0]['name'] == 'Authored module'
    assert modules[1]['items'] == []
    assert len(calls) == 4
    assert calls[1]['path'] == modules_next
    assert calls[3]['path'] == items_next
