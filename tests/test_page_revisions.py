"""Contract controls for read-only page history; all data is synthetic."""

import contextlib
import io
from copy import deepcopy
from unittest.mock import Mock, patch

import pytest

from canvaspilot.api import CanvasAPI
from canvaspilot.cli import main


class Reader:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return self.value

    def get_paginated(self, path):
        self.calls.append(("GET-pages", path, {}))
        return self.value


def test_history_preserves_complete_rows_order_identity_and_detachment():
    rows = [
        {"revision_id": "003", "latest": False, "updated_at": None,
         "edited_by": {"id": 4, "name": "Fictional editor"}, "unknown": [0, None, {"a": []}]},
        {"revision_id": 1, "latest": True, "body": "metadata kept even if unexpected"},
    ]
    reader = Reader(rows)
    api = CanvasAPI(reader)
    original = deepcopy(rows)
    result = api.list_page_revisions("00042", "page_id:7")
    assert result == original
    assert reader.calls == [("GET-pages", "/api/v1/courses/42/pages/page_id%3A7/revisions", {})]
    result[0]["unknown"][2]["a"].append(2)
    result[0]["edited_by"]["name"] = "local"
    assert rows == original
    assert api.list_page_revisions(42, "page_id:7") == original


def test_historic_body_and_unknown_projection_named_field_remain_exact():
    row = {"revision_id": "0007", "url": "former-locator", "title": "Earlier title",
           "body": "<h1>Earlier &amp; later</h1><p>研究</p>",
           "body_text": {"server": [False, None]}, "latest": False}
    reader = Reader(row)
    result = CanvasAPI(reader).get_page_revision("42", "today?100%#café", "007")
    assert result == {"revision": row, "body_text": "Earlier & later 研究"}
    assert reader.calls == [("GET",
        "/api/v1/courses/42/pages/today%3F100%25%23caf%C3%A9/revisions/7",
        {"params": {"summary": False}})]
    result["revision"]["body_text"]["server"].append("local")
    assert row["body_text"] == {"server": [False, None]}


@pytest.mark.parametrize("body,expected", [
    ({}, {}), ({"body": None}, {"body_text": None}), ({"body": ""}, {"body_text": ""}),
])
def test_missing_null_empty_body(body, expected):
    row = {"revision_id": 4, **body}
    reader = Reader(row)
    assert CanvasAPI(reader).get_page_revision(42, "p", "latest", summary=True) == {
        "revision": row, **expected,
    }
    assert reader.calls[0][2] == {"params": {"summary": True}}


@pytest.mark.parametrize("bad", [True, False, 0, -1, 1.2, None, "", "0", "00", " 1",
                                  "1 ", "+1", "１", "1/2", "1#x", "9" * 20,
                                  9223372036854775808, "9223372036854775808"])
def test_bad_ids_refuse_before_transport(bad):
    reader = Reader({"revision_id": 1})
    api = CanvasAPI(reader)
    with pytest.raises((TypeError, ValueError)):
        api.list_page_revisions(bad, "p")
    with pytest.raises((TypeError, ValueError)):
        api.get_page_revision(42, "p", bad)
    assert reader.calls == []


@pytest.mark.parametrize("bad", [None, 1, "", ".", "..", "x\x00y", "x\ny", "x\x7fy",
                                  "\ud800", "é" * 1025])
def test_bad_pages_refuse_before_transport(bad):
    reader = Reader([])
    with pytest.raises((TypeError, ValueError)):
        CanvasAPI(reader).list_page_revisions(42, bad)
    assert reader.calls == []


def test_literal_page_boundaries_and_numeric_max():
    reader = Reader([])
    api = CanvasAPI(reader)
    for value in ["é" * 1024, " leading ", "a/b", "a\\b", "%2F", "😀"]:
        assert api.list_page_revisions(9223372036854775807, value) == []
    assert "/pages/%252F/revisions" in reader.calls[-2][1]


@pytest.mark.parametrize("bad", [None, 0, 1, "false", [], {}])
def test_summary_is_not_coerced(bad):
    reader = Reader({"revision_id": 1})
    with pytest.raises(TypeError):
        CanvasAPI(reader).get_page_revision(42, "p", 1, summary=bad)
    assert reader.calls == []


@pytest.mark.parametrize("bad", [None, {}, [None], [{}], [{"revision_id": True}],
                                  [{"revision_id": 0}], [{"revision_id": "latest"}],
                                  [{"revision_id": 7}, {"revision_id": "007"}]])
def test_bad_history_refuses_whole_result(bad):
    reader = Reader(bad)
    before = deepcopy(bad)
    with pytest.raises((TypeError, ValueError)):
        CanvasAPI(reader).list_page_revisions(42, "p")
    assert reader.value == before


@pytest.mark.parametrize("bad", [None, [], {}, {"revision_id": 8},
                                  {"revision_id": 7, "body": []}])
def test_bad_selected_result_refuses(bad):
    reader = Reader(bad)
    with pytest.raises((TypeError, ValueError)):
        CanvasAPI(reader).get_page_revision(42, "p", 7)


def test_cli_bad_selectors_help_and_no_client():
    with patch("canvaspilot.client.CanvasClient") as constructor:
        for args in [
            ["page-revisions", "0", "p"], ["page-revisions", "42", ""],
            ["page-revision", "42", "p", "LATEST"],
            ["page-revision", "42", "p", "9223372036854775808"],
        ]:
            with contextlib.redirect_stdout(io.StringIO()) as out, \
                 contextlib.redirect_stderr(io.StringIO()), pytest.raises(SystemExit) as stop:
                main(args)
            assert stop.value.code == 2 and out.getvalue() == ""
        for cmd in ["page-revisions", "page-revision"]:
            with contextlib.redirect_stdout(io.StringIO()), pytest.raises(SystemExit) as stop:
                main([cmd, "--help"])
            assert stop.value.code == 0
        constructor.assert_not_called()


def test_cli_closes_client_and_restores_logging_after_result_or_failure():
    import logging
    logger = logging.getLogger("httpx")
    before = logger.level
    for value, code in [({"revision_id": 7, "body": "ok"}, None), ({"revision_id": 8}, 1)]:
        reader = Reader(value)
        reader.close = Mock()
        with patch("canvaspilot.client.CanvasClient", return_value=reader), \
             contextlib.redirect_stdout(io.StringIO()) as out, \
             contextlib.redirect_stderr(io.StringIO()) as err:
            if code:
                with pytest.raises(SystemExit) as stop:
                    main(["page-revision", "42", "p", "7"])
                assert stop.value.code == code and out.getvalue() == ""
                assert '"ok": false' in err.getvalue()
            else:
                main(["page-revision", "42", "p", "7"])
                assert '"body_text": "ok"' in out.getvalue()
        reader.close.assert_called_once()
        assert logger.level == before
