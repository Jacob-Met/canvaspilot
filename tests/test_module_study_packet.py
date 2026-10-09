"""Module selection, source fidelity and passive-document behavior."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from datetime import UTC, datetime
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest

from canvaspilot.module_study_packet import (
    MAX_BODY_BYTES,
    MAX_ITEMS,
    MAX_RESOURCES,
    build_module_study_packet,
)

STAMP = datetime(2026, 10, 8, 22, 0, tzinfo=UTC)


def page_item(identity=2, locator="reading", **extra):
    return {"id": identity, "module_id": 7, "position": 2, "type": "Page",
            "title": "Read this", "page_url": locator, **extra}


def assignment_item(identity=3, content_id=1001, **extra):
    return {"id": identity, "module_id": 7, "position": 3, "type": "Assignment",
            "title": "Writing", "content_id": content_id, **extra}


def module(items=None, **extra):
    if items is None:
        items = [page_item(), assignment_item(), page_item(4)]
    return {"id": 7, "course_id": 42, "name": "Field methods", "state": "started",
            "items_count": len(items), "items": items, "requirement_type": "one",
            "require_sequential_progress": False, "prerequisite_module_ids": [],
            "unknown_module_field": {"zero": 0, "empty": [], "false": False},
            **extra}


def page(locator="reading", **extra):
    return {"page_id": 101, "url": locator, "title": "A reading",
            "body": "<h2>Read A &amp; B</h2><p>Take your own notes.</p>",
            "locked_for_user": False, "editor": "rce", **extra}


def brief(assignment="1001", **extra):
    return {"course_id": "42", "assignment_id": assignment, "title": "Explain",
            "due_at": None, "points_possible": 0, "submission_types": [],
            "prompt": "Explain the reading.", "html_url": None, "rubric": [],
            "rubric_settings": None, "use_rubric_for_grading": False,
            "rubric_warnings": [], **extra}


class API:
    def __init__(self, rows=None, pages=None, briefs=None):
        self.rows = [module()] if rows is None else rows
        self.pages = {"reading": page()} if pages is None else pages
        self.briefs = {"1001": brief()} if briefs is None else briefs
        self.calls = []
        self.client = SimpleNamespace(
            base_url="https://canvas.example.test", fixture={}, token=None, mode="fixture",
        )

    def list_modules(self, course, *, detail):
        self.calls.append(("modules", course, detail))
        return self.rows

    def api_request(self, method, path):
        self.calls.append(("page", method, path))
        from urllib.parse import unquote
        value = self.pages[unquote(path.rsplit("/", 1)[1])]
        if isinstance(value, Exception):
            raise value
        return value

    def assignment_brief(self, course, assignment):
        self.calls.append(("brief", course, assignment))
        value = self.briefs[assignment]
        if isinstance(value, Exception):
            raise value
        return value


class Document(HTMLParser):
    def __init__(self, data):
        super().__init__()
        self.tags = []
        self.attrs = []
        self.source = None
        self.feed(data.decode())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        self.attrs.append((tag, attrs))
        if tag == "a" and attrs.get("download") == "module-study-source.json":
            prefix, encoded = attrs["href"].split(",", 1)
            assert prefix == "data:application/json;base64"
            self.source = base64.b64decode(encoded, validate=True)


def build(api=None, **kwargs):
    return build_module_study_packet(api or API(), 42, 7, generated_at=STAMP, **kwargs)


def test_keeps_original_order_repeated_positions_and_one_read_per_content():
    api = API()
    original = copy.deepcopy((api.rows, api.pages, api.briefs))
    data, receipt = build(api)
    doc = Document(data)
    retained = json.loads(doc.source)
    assert retained["module"] == api.rows[0]
    assert retained["item_resources"] == [0, 1, 0]
    assert retained["resources"] == [
        {"kind": "Page", "requested_locator": "reading", "page": api.pages["reading"]},
        {"kind": "Assignment", "requested_id": "1001", "brief": api.briefs["1001"]},
    ]
    assert api.calls == [
        ("modules", "42", "full"),
        ("page", "GET", "/api/v1/courses/42/pages/reading"),
        ("brief", "42", "1001"),
    ]
    assert original == (api.rows, api.pages, api.briefs)
    assert receipt["items"] == 3 and receipt["unique_resources"] == 2
    assert receipt["source_json_sha256"] == hashlib.sha256(doc.source).hexdigest()
    assert receipt["sha256"] == hashlib.sha256(data).hexdigest()
    assert receipt["bytes"] == len(data)
    assert [a["id"] for tag, a in doc.attrs if tag == "article"] == ["item-1", "item-2", "item-3"]


def test_selected_module_only_and_unknown_values_retain_complete_source():
    selected = module([], state=None, name="", items_count=0)
    api = API([module([], id=8), selected])
    data, receipt = build(api)
    raw = json.loads(Document(data).source)
    assert raw["module"] == selected and raw["modules_returned"] == 2
    assert raw["collection_complete"] is None and raw["upstream_module_shape"] == "not_observed"
    assert receipt["unique_resources"] == 0 and len(api.calls) == 1
    assert b"zero items" in data and b"Unavailable (null)" in data and b"Empty text" in data


@pytest.mark.parametrize("kind", ["SubHeader", "File", "Quiz", "Discussion", "ExternalUrl", "ExternalTool", "FutureType", None])
def test_nonreading_items_are_explicit_references_without_any_body_read(kind):
    item = {"id": 5, "type": kind, "title": "Source reference", "content_id": 44,
            "external_url": "https://example.invalid/not-fetched", "position": 0}
    api = API([module([item])])
    data, receipt = build(api)
    assert len(api.calls) == 1 and receipt["reference_only_items"] == 1
    assert b"Reference only." in data
    assert json.loads(Document(data).source)["module"]["items"] == [item]


@pytest.mark.parametrize("bad", [None, True, 0, -1, "", " 7", "../7", "ä¸ƒ", "7/8", "9" * 65])
def test_invalid_selection_refuses_before_module_read(bad):
    api = API()
    with pytest.raises((TypeError, ValueError)):
        build_module_study_packet(api, 42, bad, generated_at=STAMP)
    assert api.calls == []


@pytest.mark.parametrize("change", [
    lambda m: m.update(items_count=None),
    lambda m: m.pop("items_count"),
    lambda m: m.update(items_count=True),
    lambda m: m.update(items_count=2),
    lambda m: m.update(items_count=4),
    lambda m: m.update(course_id=43),
    lambda m: m["items"][0].update(module_id=8),
    lambda m: m["items"][0].update(page_url=None),
    lambda m: m["items"][1].update(content_id=False),
    lambda m: m["items"][1].update(id=2),
])
def test_unusable_module_identity_counts_and_targets_refuse_before_content(change):
    selected = module()
    change(selected)
    api = API([selected])
    with pytest.raises((TypeError, ValueError)):
        build(api)
    assert api.calls == [("modules", "42", "full")]


@pytest.mark.parametrize("rows", [None, {}, [None], [], [module(id=8)], [module(), module()]])
def test_bad_or_ambiguous_module_collection_refuses(rows):
    api = API()
    api.rows = rows
    with pytest.raises((TypeError, ValueError)):
        build(api)
    assert len(api.calls) == 1


def test_100_items_are_retained_and_101_refuses_before_content():
    items = [{"id": i + 1, "type": "File", "title": f"Reference {i}"} for i in range(MAX_ITEMS)]
    data, receipt = build(API([module(items)]))
    assert receipt["items"] == 100
    assert len(json.loads(Document(data).source)["module"]["items"]) == 100
    api = API([module(items + [page_item(101)])])
    with pytest.raises(ValueError, match="100-item"):
        build(api)
    assert len(api.calls) == 1


def test_20_unique_resources_pass_and_21_refuses_before_any_content():
    items = [page_item(i + 1, f"page-{i}") for i in range(MAX_RESOURCES)]
    pages = {f"page-{i}": page(f"page-{i}", page_id=i + 100) for i in range(MAX_RESOURCES)}
    api = API([module(items)], pages=pages)
    _, receipt = build(api)
    assert receipt["unique_resources"] == 20 and len(api.calls) == 21
    api = API([module(items + [assignment_item(30)])], pages=pages)
    with pytest.raises(ValueError, match="20-unique-content"):
        build(api)
    assert len(api.calls) == 1


def test_repeat_references_do_not_consume_unique_resource_limit_or_deduplicate_items():
    items = [page_item(i + 1) for i in range(100)]
    api = API([module(items)])
    data, receipt = build(api)
    assert len(api.calls) == 2 and receipt["items"] == 100 and receipt["unique_resources"] == 1
    assert json.loads(Document(data).source)["item_resources"] == [0] * 100


@pytest.mark.parametrize("body, label", [
    (None, b"body is unavailable (null)"),
    ("", b"supplied page body is empty"),
    ("<p>Visible source</p>", b"Visible source"),
])
def test_page_body_observations_and_lock_metadata_stay_distinct(body, label):
    returned = page(body=body, locked_for_user=True, lock_explanation="Not open yet")
    api = API([module([page_item()])], pages={"reading": returned})
    data, _ = build(api)
    assert label in data and b"Not open yet" in data
    assert json.loads(Document(data).source)["resources"][0]["page"] == returned


def test_absent_body_and_block_editor_metadata_are_retained_without_inventing_html():
    returned = page(editor="block", block_editor_attributes={"title": "Original block"})
    del returned["body"]
    data, _ = build(API([module([page_item()])], pages={"reading": returned}))
    assert b"Page body was not returned" in data
    assert json.loads(Document(data).source)["resources"][0]["page"] == returned


@pytest.mark.parametrize("returned", [
    None, [], page(url="wrong"), page(page_id=None), page(course_id=99),
    page(body=False), page(body="x" * (MAX_BODY_BYTES + 1)),
])
def test_unusable_page_response_refuses_whole_packet(returned):
    api = API([module([page_item()])], pages={"reading": returned})
    with pytest.raises((TypeError, ValueError)):
        build(api)
    assert len(api.calls) == 2


def test_no_content_is_obtained_through_supplied_external_or_api_urls():
    item = page_item(locator="reading?x=1#part", url="https://example.invalid/api", html_url="javascript:bad")
    api = API([module([item])], pages={"reading?x=1#part": page("reading?x=1#part")})
    build(api)
    assert api.calls[1] == ("page", "GET", "/api/v1/courses/42/pages/reading%3Fx%3D1%23part")


def test_passive_html_escapes_source_and_download_preserves_large_ids_and_controls():
    source = '<script>not executable</script><img src="https://example.invalid/x"><p>Text &amp; cafÃ©</p>'
    item = page_item(title='<script>title</script>', original_id=9223372036854775807,
                     extra={"control": "\x01", "unicode": "æ—¥æœ¬", "empty": [], "false": False})
    api = API([module([item])], pages={"reading": page(body=source)})
    data, _ = build(api)
    doc = Document(data)
    assert not {"script", "img", "iframe", "object", "form", "link"} & set(doc.tags)
    assert all(a["href"].startswith(("#", "data:")) for tag, a in doc.attrs if tag == "a")
    raw = json.loads(doc.source)
    assert raw["module"]["items"][0] == item
    assert raw["resources"][0]["page"]["body"] == source
    assert b"&lt;script&gt;title&lt;/script&gt;" in data


@pytest.mark.parametrize("stamp", [STAMP.replace(tzinfo=None), "2026-10-08", False])
def test_invalid_capture_time_refuses_before_http(stamp):
    api = API()
    with pytest.raises(ValueError):
        build_module_study_packet(api, 42, 7, generated_at=stamp)
    assert api.calls == []


def test_provider_change_after_module_read_refuses_before_content():
    api = API()
    original = api.list_modules

    def moved(*args, **kwargs):
        rows = original(*args, **kwargs)
        api.client.base_url = "https://other.example.test"
        return rows

    api.list_modules = moved
    with pytest.raises(ValueError, match="provider changed"):
        build(api)
    assert len(api.calls) == 1


def test_later_native_error_propagates_without_a_partial_packet():
    api = API(briefs={"1001": ValueError("reader refused")})
    with pytest.raises(ValueError, match="reader refused"):
        build(api)
    assert [c[0] for c in api.calls] == ["modules", "page", "brief"]


def test_normalized_brief_retains_zero_advisory_warnings_and_unknown_prompt_boundary():
    returned = brief(prompt="", rubric=[{"id": "criterion-0", "points": 0}],
                     rubric_warnings=["Source omitted malformed neighboring criterion."])
    data, _ = build(API([module([assignment_item()])], briefs={"1001": returned}))
    assert b"normalized brief contains no prompt text" in data
    assert b"no grade or rubric total is calculated" in data
    assert json.loads(Document(data).source)["resources"][0]["brief"] == returned
