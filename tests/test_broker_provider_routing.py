"""Provider agreement at the broker's actual page-selection/fetch boundary."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from canvaspilot import session_broker as broker

A = "https://school-a.instructure.com"
B = "https://school-b.instructure.com"
PATH = "/api/v1/courses/42/assignments?cursor=a,b;c&empty=&literal=+"


class Page:
    def __init__(self, url, *, after_fetch=None):
        self.url = url
        self.after_fetch = after_fetch
        self.evaluations = []
        self.navigations = []

    def goto(self, url, **kwargs):
        self.navigations.append(url)
        self.url = url

    def title(self):
        return "Authored provider page"

    def evaluate(self, expression, parameters):
        self.evaluations.append((expression, parameters))
        if self.after_fetch:
            self.url = self.after_fetch
        return {"status": 200, "json": [{"id": 1}], "text": None}


def fetch(pages, path=PATH):
    context = SimpleNamespace(pages=pages)
    return broker._run_job(context, {"op": "fetch", "method": "GET", "path": path})


def test_matching_page_selected_even_when_another_school_tab_is_first(monkeypatch):
    monkeypatch.setattr(broker.STATE, "base_url", A)
    other, matching = Page(B + "/courses"), Page(A + "/courses")
    assert fetch([other, matching])["response"]["json"] == [{"id": 1}]
    assert not other.evaluations and not other.navigations
    assert len(matching.evaluations) == 1 and not matching.navigations
    assert matching.evaluations[0][1]["path"] == PATH


@pytest.mark.parametrize("configured,page_url", [
    (A, B + "/courses"),
    (A, "https://login.fixture.invalid/"),
    (A, "about:blank"),
    (A, "http://school-a.instructure.com/courses"),
    (A, "https://school-a.instructure.com:444/courses"),
])
def test_unmatched_provider_refuses_before_evaluation_or_navigation(monkeypatch, configured, page_url):
    monkeypatch.setattr(broker.STATE, "base_url", configured)
    page = Page(page_url)
    with pytest.raises((RuntimeError, ValueError), match="provider"):
        fetch([page])
    assert page.evaluations == [] and page.navigations == []


@pytest.mark.parametrize("url", [
    B + PATH,
    "//school-b.instructure.com" + PATH,
    "http://school-a.instructure.com" + PATH,
])
def test_other_provider_request_refuses_without_navigating_matching_page(monkeypatch, url):
    monkeypatch.setattr(broker.STATE, "base_url", A)
    page = Page(A + "/courses")
    with pytest.raises(RuntimeError, match="provider mismatch"):
        fetch([page], url)
    assert page.evaluations == [] and page.navigations == []


def test_same_provider_absolute_continuation_preserves_opaque_query(monkeypatch):
    monkeypatch.setattr(broker.STATE, "base_url", A)
    page = Page(A + "/courses")
    result = fetch([page], A + PATH)
    assert result["response"]["json"] == [{"id": 1}]
    assert page.evaluations[0][1]["path"] == PATH
    assert page.navigations == []


def test_equivalent_origin_spelling_and_custom_canvas_host_work(monkeypatch):
    monkeypatch.setattr(broker.STATE, "base_url", "https://CANVAS.school.invalid:443/")
    page = Page("https://canvas.school.invalid/courses")
    assert fetch([page])["response"]["json"] == [{"id": 1}]
    assert len(page.evaluations) == 1 and page.navigations == []


def test_page_provider_change_during_evaluation_refuses_returned_rows(monkeypatch):
    monkeypatch.setattr(broker.STATE, "base_url", A)
    page = Page(A + "/courses", after_fetch=B + "/courses")
    with pytest.raises(RuntimeError, match="provider mismatch.*changed"):
        fetch([page])
    assert len(page.evaluations) == 1 and page.navigations == []


def test_status_keeps_login_page_visible_without_fetch_or_navigation(monkeypatch):
    monkeypatch.setattr(broker.STATE, "base_url", A)
    page = Page("https://login.fixture.invalid/")
    result = broker._run_job(SimpleNamespace(pages=[page]), {"op": "status"})
    assert result["url"] == page.url and result["logged_in"] is False
    assert page.evaluations == [] and page.navigations == []
