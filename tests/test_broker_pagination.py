"""Collection compatibility when the broker carries Canvas's next-link metadata."""

from __future__ import annotations

from urllib.parse import urljoin

import httpx
import pytest

from canvaspilot import client as client_mod
from canvaspilot.client import CanvasClient, CanvasPaginationError

BASE = "https://canvas.example.test"
DATASET = [{"id": i, "name": f"Course {i}"} for i in range(1, 236)]


def make_fake_broker(rows, calls):
    def fake_broker_response(method, path, *, params=None, **kwargs):
        url = httpx.Request(method, urljoin(BASE + "/", path), params=params).url
        page = int(url.params.get("page", 1))
        per_page = int(url.params.get("per_page", 50))
        calls.append((page, per_page))
        start = (page - 1) * per_page
        next_url = url.copy_set_param("page", page + 1)
        return {
            "status": 200,
            "json": rows[start : start + per_page],
            "text": None,
            "url": str(url),
            "link": f'<{next_url}>; rel="next"' if start + per_page < len(rows) else None,
        }

    return fake_broker_response


@pytest.fixture
def broker_mode(monkeypatch):
    calls: list[tuple[int, int]] = []
    monkeypatch.delenv("CANVAS_API_TOKEN", raising=False)
    monkeypatch.setattr(client_mod, "broker_health", lambda: {"ok": True})
    monkeypatch.setattr(client_mod, "_broker_fetch_response", make_fake_broker(DATASET, calls))
    return calls


def _broker_client():
    return CanvasClient(base_url=BASE, token="")


def test_broker_path_collects_all_pages(broker_mode):
    rows = _broker_client().get_paginated("/api/v1/courses")
    assert len(rows) == len(DATASET)
    assert rows[0]["id"] == 1 and rows[-1]["id"] == 235
    assert [page for page, _ in broker_mode] == [1, 2, 3, 4, 5]


def test_broker_path_exact_multiple_stops_at_final_link(broker_mode, monkeypatch):
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(client_mod, "_broker_fetch_response", make_fake_broker(DATASET[:100], calls))
    rows = _broker_client().get_paginated("/api/v1/courses")
    assert len(rows) == 100
    assert [page for page, _ in calls] == [1, 2]


def test_broker_path_list_params_form(broker_mode):
    rows = _broker_client().get_paginated(
        "/api/v1/courses", params=[("enrollment_state", "active")]
    )
    assert len(rows) == len(DATASET)
    assert [page for page, _ in broker_mode] == [1, 2, 3, 4, 5]


def test_broker_path_non_list_response(broker_mode, monkeypatch):
    monkeypatch.setattr(
        client_mod, "_broker_fetch_response",
        lambda *a, **k: {"status": 200, "json": {"id": 7, "name": "Single"}},
    )
    assert _broker_client().get_paginated("/api/v1/users/self") == [{"id": 7, "name": "Single"}]


def test_broker_path_non_list_mid_pagination_kept_not_dropped(broker_mode, monkeypatch):
    calls: list[tuple[int, int]] = []
    fake = make_fake_broker(DATASET, calls)

    def trailing_single(*args, **kwargs):
        response = fake(*args, **kwargs)
        if calls[-1][0] == 3:
            response["json"] = {"id": 999, "name": "Trailing single"}
        return response

    monkeypatch.setattr(client_mod, "_broker_fetch_response", trailing_single)
    rows = _broker_client().get_paginated("/api/v1/courses")
    assert len(rows) == 101
    assert rows[-1] == {"id": 999, "name": "Trailing single"}
    assert [page for page, _ in calls] == [1, 2, 3]


def test_broker_path_40_page_cap_refuses_incomplete_collection(broker_mode, monkeypatch):
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        client_mod, "_broker_fetch_response", make_fake_broker([{"id": i} for i in range(4500)], calls)
    )
    with pytest.raises(CanvasPaginationError, match="40-page.*incomplete"):
        _broker_client().get_paginated("/api/v1/courses", params={"per_page": 100})
    assert calls == [(page, 100) for page in range(1, 41)]
