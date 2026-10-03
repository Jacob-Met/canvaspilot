"""Regression: session-broker get_paginated must return ALL pages, not just the first.

The broker's /fetch returns {status, json, text} with no response headers, so
Link: rel=next following is impossible on the broker path. The client must use
Canvas explicit pagination (?page=N&per_page=M). A fake broker emulates a
235-row collection; the pre-fix code returned only the first 50.
"""

from __future__ import annotations

import pytest

from canvaspilot import client as client_mod
from canvaspilot.client import CanvasClient

DATASET = [{"id": i, "name": f"Course {i}"} for i in range(1, 236)]  # 5 pages @50


def make_fake_broker(rows, calls):
    def fake_broker_fetch(method, path, *, params=None, **kwargs):
        p = dict(params or [])
        page = int(p.get("page", 1))
        per_page = int(p.get("per_page", 50))
        calls.append((page, per_page))
        start = (page - 1) * per_page
        return rows[start : start + per_page]

    return fake_broker_fetch


@pytest.fixture
def broker_mode(monkeypatch):
    calls: list[tuple[int, int]] = []

    def fake_health():
        return {"ok": True}

    monkeypatch.setattr(client_mod, "broker_health", fake_health)
    monkeypatch.setattr(client_mod, "broker_fetch", make_fake_broker(DATASET, calls))
    return calls


def _broker_client():
    return CanvasClient(base_url="https://canvas.example.test", token=None)


def test_broker_path_collects_all_pages(broker_mode):
    client = _broker_client()
    rows = client.get_paginated("/api/v1/courses")
    assert len(rows) == len(DATASET)
    assert rows[0]["id"] == 1 and rows[-1]["id"] == 235
    assert [page for page, _ in broker_mode] == [1, 2, 3, 4, 5]


def test_broker_path_exact_multiple_requests_final_empty_page(broker_mode):
    calls: list[tuple[int, int]] = []
    monkeypatch_rows = DATASET[:100]
    from canvaspilot import client as cm

    cm.broker_fetch = make_fake_broker(monkeypatch_rows, calls)
    client = _broker_client()
    rows = client.get_paginated("/api/v1/courses")
    assert len(rows) == 100
    assert [page for page, _ in calls] == [1, 2, 3]  # pages 50,50 then empty


def test_broker_path_list_params_form(broker_mode, monkeypatch):
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        client_mod, "broker_fetch", make_fake_broker(DATASET, calls)
    )
    client = _broker_client()
    rows = client.get_paginated(
        "/api/v1/courses", params=[("enrollment_state", "active")]
    )
    assert len(rows) == len(DATASET)
    assert any(page == 5 for page, _ in calls)


def test_broker_path_non_list_response(broker_mode, monkeypatch):
    monkeypatch.setattr(
        client_mod,
        "broker_fetch",
        lambda *a, **k: {"id": 7, "name": "Single"},
    )
    client = _broker_client()
    assert client.get_paginated("/api/v1/users/self") == [
        {"id": 7, "name": "Single"}
    ]
