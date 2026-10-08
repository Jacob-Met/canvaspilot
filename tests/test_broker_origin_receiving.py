"""Receive the broker's configured school origin through actual loopback HTTP.

The scenario comes from PR35 (estate-ac386303dce2). These independent tests
reuse the root-authored production Handler/queue receiver with fictional data.
No broker metadata format, real profile, credential or provider is introduced.
"""

from __future__ import annotations

import pytest
from test_broker_http_receiving import ASSIGNMENTS, ORIGIN, envelope, running_broker

from canvaspilot import client as client_module
from canvaspilot import session_broker as broker_module
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.pagination import CanvasPaginationError

NEXT_PATH = ASSIGNMENTS + "?cursor=school%2fopaque&include[]=submission"


def school_pages(_job, index):
    if index == 1:
        return envelope([{"id": 1}], f'<{ORIGIN}{NEXT_PATH}>; rel="next"')
    return envelope([{"id": 2}])


def test_default_client_follows_the_school_configured_in_the_running_broker(monkeypatch):
    monkeypatch.delenv("CANVAS_BASE_URL", raising=False)
    with running_broker(monkeypatch, school_pages) as (_api, requests):
        with CanvasAPI(CanvasClient(token="", timeout=3)) as api:
            assert api.client.base_url == client_module.DEFAULT_BASE
            assert api.client.base_url != ORIGIN
            rows = api.list_assignments(17)
        assert [row["id"] for row in rows] == [1, 2]
        assert len(requests) == 2
        assert requests[1]["path"] == NEXT_PATH
        assert all(job["method"] == "GET" for job in requests)


def test_matching_explicit_client_origin_keeps_the_existing_result(monkeypatch):
    with running_broker(monkeypatch, school_pages) as (api, requests):
        assert [row["id"] for row in api.list_assignments(17)] == [1, 2]
        assert requests[1]["path"] == NEXT_PATH


@pytest.mark.parametrize("invalid_origin", [
    None,
    "",
    0,
    [],
    {},
    "receiving-fixture.instructure.com",
    "ftp://receiving-fixture.instructure.com",
    "https://user:fixture-password@receiving-fixture.instructure.com",
    ORIGIN + "/#fixture-fragment",
    ORIGIN + ":bad",
    ORIGIN + "\\@other-fixture.invalid",
    ORIGIN + "\n",
])
def test_invalid_advertised_origin_is_refused_before_any_fetch(monkeypatch, invalid_origin):
    with running_broker(monkeypatch, lambda _job, _index: envelope([{"id": 1}])) as (api, requests):
        # The actual production Handler serializes this through GET /health.
        broker_module.STATE.base_url = invalid_origin
        with pytest.raises(CanvasPaginationError) as error:
            api.list_assignments(17)
        assert requests == []
        assert "fixture-password" not in str(error.value)
        assert "fixture-fragment" not in str(error.value)


def test_absent_health_origin_retains_explicit_client_configuration(monkeypatch):
    health = client_module.broker_health

    def older_health():
        result = health()
        result.pop("base_url")
        return result

    with running_broker(monkeypatch, school_pages) as (api, requests):
        monkeypatch.setattr(client_module, "broker_health", older_health)
        assert [row["id"] for row in api.list_assignments(17)] == [1, 2]
        assert requests[1]["path"] == NEXT_PATH
