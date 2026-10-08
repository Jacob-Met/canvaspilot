"""Independent conversation-export contract receivers; no live Canvas or network.

These tests exercise public rendering/building functions and the real CLI/client
against authored data. They do not claim real-school or browser receiving.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib
import json
import logging
import os
import socket
from datetime import UTC, datetime, timedelta, timezone
from html.parser import HTMLParser

import httpx
import pytest

TOKEN = "synthetic-conversation-export-not-a-credential"
BASE = "https://conversation-export-fixture.invalid"
STAMP = datetime(2026, 10, 8, 19, 30, tzinfo=UTC)
ABSENT = object()


class Element:
    def __init__(self, tag, attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def text(self):
        return "".join(child.text() if isinstance(child, Element) else child
                       for child in self.children)

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.walk()


class Document(HTMLParser):
    VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"})

    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(content.decode("utf-8"))
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Element(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def nodes(scope, *, cls=None, field=None, identity=None):
    return [
        node for node in scope.walk()
        if (cls is None or cls in node.attrs.get("class", "").split())
        and (field is None or node.attrs.get("data-field") == field)
        and (identity is None or node.attrs.get("id") == identity)
    ]


def only(items):
    assert len(items) == 1
    return items[0]


def packet_module():
    # Lazy import lets a missing baseline feature fail individual cases rather
    # than preventing collection of the independent CLI/destination receivers.
    return importlib.import_module("canvaspilot.conversation_export")


def download(document):
    link = only(nodes(document.root, identity="download-source"))
    assert link.tag == "a" and link.attrs.get("download")
    prefix = "data:application/json;base64,"
    assert link.attrs["href"].startswith(prefix)
    payload = base64.b64decode(link.attrs["href"][len(prefix):], validate=True)
    assert payload.isascii()
    return payload, json.loads(payload)


def render(source, **kwargs):
    return packet_module().render_conversation_packet(
        source, generated_at=kwargs.pop("generated_at", STAMP), **kwargs,
    )


def fixture_source():
    return {
        "id": 246,
        "subject": "Saved discussion — Zoë / 課題",
        "workflow_state": "unread",
        "starred": False,
        "message_count": 9,  # Returned rows are deliberately not claimed complete.
        "participants": [
            {"id": 7, "name": "Zoë 林", "avatar_url": "https://assets.invalid/avatar"},
            {"id": 42, "name": "أمل", "pronouns": None},
        ],
        "messages": [
            {
                "id": 902, "author_id": 7, "created_at": "2026-10-08T17:02:00Z",
                "body": "\n  Café\t& <em>literal supplied markup</em> \"quotes\" 👋\n\n",
                "attachments": [{"id": 31, "display_name": "résumé.pdf", "size": 0,
                                 "url": "https://assets.invalid/file?download=1"}],
                "forwarded_messages": [{"id": 800, "body": "quoted source", "unknown": []}],
                "media_comment": None, "generated": False,
            },
            {
                "id": 901, "author_id": 42, "created_at": "2026-10-07T09:00:00Z",
                "body": "Second returned row; older date.\n終わり ",
                "attachments": [], "forwarded_messages": [],
            },
        ],
        "unknown": {"large_integer": 9007199254740993, "zero": 0, "off": False,
                    "empty": "", "nil": None, "nested": [[], {}, "é"]},
    }


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch, tmp_path):
    """No inherited account routing, socket access or profile discovery."""
    for name in tuple(os.environ):
        if name.startswith("CANVAS_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("CANVAS_PROFILE", str(tmp_path / "unused-profile"))

    def denied(*args, **kwargs):
        raise AssertionError("A conversation-export receiver attempted network I/O")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


@pytest.fixture
def transport(monkeypatch):
    """Bind the real CanvasClient HTTPX path to one expected synthetic GET."""
    real_client = httpx.Client

    def install(payload, *, status=200, identifier="246"):
        requests = []

        def handler(request):
            requests.append({
                "method": request.method, "path": request.url.path,
                "query": list(request.url.params.multi_items()),
                "body": request.content,
            })
            assert request.url.host == "conversation-export-fixture.invalid"
            assert request.url.path == "/api/v1/conversations/" + identifier
            assert request.method == "GET"
            assert request.url.params.get_list("auto_mark_as_read") == ["false"]
            assert request.content == b""
            assert request.headers["Authorization"] == "Bearer " + TOKEN
            return httpx.Response(status, json=copy.deepcopy(payload))

        class FixtureClient(real_client):
            def __init__(self, *args, **kwargs):
                assert "transport" not in kwargs
                kwargs["transport"] = httpx.MockTransport(handler)
                kwargs["trust_env"] = False
                super().__init__(*args, **kwargs)

        monkeypatch.setattr(httpx, "Client", FixtureClient)
        return requests

    return install


def cli_arguments(output, *, identifier="246"):
    return [
        "export-conversation", identifier, "--out", str(output),
        "--base-url", BASE, "--token", TOKEN,
        "--profile", str(output.parent / "unused-profile"),
    ]


def test_readable_order_literal_bodies_and_lossless_download():
    source = fixture_source()
    before = copy.deepcopy(source)
    content, receipt = render(source)
    document = Document(content)
    articles = nodes(document.root, cls="message")
    assert len(articles) == 2
    for article, original, author in zip(articles, source["messages"], ("Zoë 林", "أمل"), strict=True):
        assert article.tag == "article"
        assert str(original["id"]) in article.text()
        assert str(original["author_id"]) in article.text()
        assert original["created_at"] in article.text()
        assert author in article.text()
        body = only(nodes(article, cls="message-body"))
        assert body.attrs["data-state"] == "value"
        assert body.text() == original["body"]
    assert "Saved discussion — Zoë / 課題" in document.root.text()
    assert "9" in document.root.text()
    payload, decoded = download(document)
    assert decoded == before
    assert source == before
    assert receipt["conversation_id"] == 246
    assert receipt["generated_at"] == "2026-10-08T19:30:00Z"
    assert receipt["html_bytes"] == len(content)
    assert receipt["sha256"] == hashlib.sha256(content).hexdigest()
    assert receipt["json_bytes"] == len(payload)
    assert receipt["json_sha256"] == hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize(("value", "state"), [
    (ABSENT, "missing"), (None, "null"), ("", "empty-string"),
    ([], "empty-list"), ({"unexpected": False}, "value"),
])
def test_field_states_distinguish_missing_null_empty_and_unsupported(value, state):
    source = {"id": 246, "messages": [{"id": 71}], "participants": []}
    if value is not ABSENT:
        source["subject"] = copy.deepcopy(value)
        source["messages"][0]["body"] = copy.deepcopy(value)
    content, _ = render(source)
    document = Document(content)
    assert only(nodes(document.root, field="subject")).attrs["data-state"] == state
    body = only(nodes(only(nodes(document.root, cls="message")), cls="message-body"))
    assert body.attrs["data-state"] == state
    if isinstance(value, dict):
        assert json.loads(body.text()) == value
    assert download(document)[1] == source


@pytest.mark.parametrize(("value", "state"), [
    (ABSENT, "missing"), (None, "null"), ([], "empty-list"),
    ("", "empty-string"), ({"unexpected": "shape"}, "value"),
])
def test_collection_states_and_non_object_rows_remain_visible(value, state):
    source = {"id": 246}
    if value is not ABSENT:
        source["messages"] = copy.deepcopy(value)
        source["participants"] = copy.deepcopy(value)
    content, _ = render(source)
    document = Document(content)
    for field in ("messages", "participants"):
        assert only(nodes(document.root, field=field)).attrs["data-state"] == state
    assert download(document)[1] == source

def test_non_object_collection_rows_are_not_dropped_or_reordered():
    rows = {"id": 246, "messages": ["first unusual row", None, 0, {"id": 75, "body": "last body"}],
            "participants": ["first unusual person", None, False, {"id": 9, "name": "Last person"}]}
    content, _ = render(rows)
    document = Document(content)
    articles = nodes(document.root, cls="message")
    assert len(articles) == 4
    assert "first unusual row" in articles[0].text()
    assert "null" in articles[1].text().lower()
    assert "0" in articles[2].text()
    assert only(nodes(articles[3], cls="message-body")).text() == "last body"
    people = only(nodes(document.root, field="participants")).text()
    positions = [people.lower().index(text.lower()) for text in
                 ("first unusual person", "null", "false", "Last person")]
    assert positions == sorted(positions)
    assert download(document)[1] == rows


def test_author_matching_preserves_json_type_and_reports_uncertainty():
    source = {
        "id": 246,
        "participants": [{"id": 1, "name": "Integer author"},
                         {"id": "1", "name": "String author"},
                         {"id": True, "name": "Boolean author"},
                         {"id": 2, "name": "First duplicate"},
                         {"id": 2, "name": "Second duplicate"}],
        "messages": [{"id": index + 80, "author_id": author, "body": "Body"}
                     for index, author in enumerate((1, "1", True, 2, 404))],
    }
    content, _ = render(source)
    articles = nodes(Document(content).root, cls="message")
    assert len(articles) == 5
    names = ("Integer author", "String author", "Boolean author")
    for index, name in enumerate(names):
        assert name in articles[index].text()
        assert all(other not in articles[index].text() for other in names if other != name)
    assert "ambiguous" in articles[3].text().lower()
    assert "unresolved" in articles[4].text().lower()
    assert "404" in articles[4].text()


def test_passive_html_and_control_display_preserve_original_json():
    source = fixture_source()
    body = "\n\tKeep LF and tab\rCR\x00NUL\x1fC0\x7fDEL\x85C1\ud800surrogate"
    source["messages"][0]["body"] = body
    source["subject"] = 'Literal <em title="quotation">heading</em> & text'
    source["participants"][0]["name"] = "<em>literal name</em>"
    content, _ = render(source)
    document = Document(content)
    forbidden = {"script", "iframe", "frame", "frameset", "object", "embed",
                 "img", "picture", "audio", "video", "source", "track",
                 "form", "input", "button", "select", "textarea", "base", "link"}
    for node in document.root.walk():
        assert node.tag not in forbidden
        assert not any(name.lower().startswith("on") for name in node.attrs)
        for attr in ("src", "srcset", "action", "formaction", "poster", "background"):
            assert attr not in node.attrs
        if "href" in node.attrs:
            assert node.attrs["href"].startswith(("#", "data:application/json;base64,"))
        if node.tag == "meta":
            assert node.attrs.get("http-equiv", "").lower() != "refresh"
    expected = "".join(
        "\\u" + format(ord(char), "04x")
        if (ord(char) < 32 and char not in "\n\t")
        or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF
        else char for char in body
    )
    article = nodes(document.root, cls="message")[0]
    body_node = only(nodes(article, cls="message-body"))
    assert body_node.text() == expected
    assert not any(node.tag == "em" for node in body_node.walk())
    assert download(document)[1] == source


def test_builder_reads_once_with_original_identifier_and_does_not_mutate_source():
    source = fixture_source()
    before = copy.deepcopy(source)
    calls = []

    class Reader:
        def get_conversation(self, identifier):
            calls.append(identifier)
            return source

        def __getattr__(self, name):
            raise AssertionError("Unexpected API/client access: " + name)

    content, receipt = packet_module().build_conversation_packet(
        Reader(), "000246", generated_at=STAMP,
    )
    assert calls == ["000246"]
    assert receipt["requested_conversation_id"] == "000246"
    assert receipt["conversation_id"] == 246
    assert source == before
    assert download(Document(content))[1] == before


@pytest.mark.parametrize("state", ["unread", "read", "archived"])
def test_real_reader_keeps_false_query_and_returned_state(transport, tmp_path, state):
    from canvaspilot.api import CanvasAPI
    from canvaspilot.client import CanvasClient

    source = fixture_source()
    source["workflow_state"] = state
    before = copy.deepcopy(source)
    requests = transport(source)
    with CanvasAPI(CanvasClient(base_url=BASE, token=TOKEN, profile=tmp_path / "unused-profile")) as api:
        content, _ = packet_module().build_conversation_packet(api, 246, generated_at=STAMP)
    assert len(requests) == 1
    assert requests[0]["method"] == "GET"
    assert ("auto_mark_as_read", "false") in requests[0]["query"]
    assert source == before
    assert download(Document(content))[1]["workflow_state"] == state
    assert not (tmp_path / "unused-profile").exists()


def test_actual_cli_new_file_receipt_original_id_and_logging_restoration(transport, tmp_path, capsys):
    from canvaspilot.cli import main

    source = fixture_source()
    requests = transport(source, identifier="000246")
    output = tmp_path / "saved conversation.html"
    logger = logging.getLogger("httpx")
    previous = logger.level
    logger.setLevel(logging.INFO)
    try:
        assert main(cli_arguments(output, identifier="000246")) is None
        assert logger.level == logging.INFO
    finally:
        logger.setLevel(previous)
    captured = capsys.readouterr()
    assert captured.err == ""
    receipt = json.loads(captured.out)
    assert receipt["ok"] is True
    assert receipt["requested_conversation_id"] == "000246"
    content = output.read_bytes()
    assert receipt["sha256"] == hashlib.sha256(content).hexdigest()
    assert receipt["html_bytes"] == len(content)
    assert download(Document(content))[1] == source
    assert len(requests) == 1
    assert sorted(path.name for path in tmp_path.iterdir()) == [output.name]


@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "dangling-symlink"])
def test_existing_destination_refuses_before_client_construction(kind, monkeypatch, tmp_path, capsys):
    from canvaspilot import client
    from canvaspilot.cli import main

    output = tmp_path / "existing.html"
    target = tmp_path / "owned-target.txt"
    if kind == "file":
        output.write_bytes(b"existing result stays exact")
    elif kind == "directory":
        output.mkdir()
        (output / "sentinel").write_bytes(b"keep")
    else:
        if kind == "symlink":
            target.write_bytes(b"target stays exact")
        try:
            output.symlink_to(target)
        except (NotImplementedError, OSError) as error:
            pytest.skip("Host does not permit disposable symlink creation: " + str(error))
    before = {path.name: (path.is_symlink(), path.read_bytes() if path.is_file() else None)
              for path in tmp_path.iterdir()}

    def unexpected_client(*args, **kwargs):
        raise AssertionError("Existing output must refuse before client construction")

    monkeypatch.setattr(client, "CanvasClient", unexpected_client)
    with pytest.raises(SystemExit) as caught:
        main(cli_arguments(output))
    assert caught.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    error = json.loads(captured.err)
    assert error["ok"] is False and error["error"] == "FileExistsError"
    after = {path.name: (path.is_symlink(), path.read_bytes() if path.is_file() else None)
             for path in tmp_path.iterdir()}
    assert after == before
    if kind == "directory":
        assert (output / "sentinel").read_bytes() == b"keep"


@pytest.mark.parametrize(("status", "payload"), [
    (401, {"error": "Synthetic denied read"}),
    (503, {"error": "Synthetic unavailable read"}),
    (200, ["unexpected root list"]),
])
def test_cli_reader_or_shape_error_leaves_no_file_and_restores_logging(status, payload, transport, tmp_path, capsys):
    from canvaspilot.cli import main

    requests = transport(payload, status=status)
    output = tmp_path / "never-created.html"
    logger = logging.getLogger("httpx")
    previous = logger.level
    logger.setLevel(logging.INFO)
    try:
        with pytest.raises(SystemExit) as caught:
            main(cli_arguments(output))
        assert caught.value.code == 1
        assert logger.level == logging.INFO
    finally:
        logger.setLevel(previous)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["ok"] is False
    assert len(requests) == 1
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("source", [None, [], "unexpected", {"id": 246, "unsupported": float("nan")}])
def test_root_and_nonfinite_json_admission(source):
    with pytest.raises((TypeError, ValueError)):
        render(source)


def test_byte_limits_and_aware_creation_time(monkeypatch):
    module = packet_module()
    assert module.MAX_SOURCE_BYTES == 4 * 1024 * 1024
    assert module.MAX_HTML_BYTES == 16 * 1024 * 1024
    source = {"id": 246, "messages": [{"id": 91, "body": "é & \t"}], "participants": []}
    content, receipt = render(source)
    payload, _ = download(Document(content))
    monkeypatch.setattr(module, "MAX_SOURCE_BYTES", len(payload))
    assert render(source)[0] == content
    monkeypatch.setattr(module, "MAX_SOURCE_BYTES", len(payload) - 1)
    with pytest.raises(ValueError):
        render(source)
    monkeypatch.setattr(module, "MAX_SOURCE_BYTES", 4 * 1024 * 1024)
    monkeypatch.setattr(module, "MAX_HTML_BYTES", len(content))
    assert render(source)[0] == content
    monkeypatch.setattr(module, "MAX_HTML_BYTES", len(content) - 1)
    with pytest.raises(ValueError):
        render(source)
    monkeypatch.setattr(module, "MAX_HTML_BYTES", 16 * 1024 * 1024)
    with pytest.raises((TypeError, ValueError)):
        render(source, generated_at=STAMP.replace(tzinfo=None))
    equivalent = STAMP.astimezone(timezone(timedelta(hours=5, minutes=30)))
    assert render(source, generated_at=equivalent)[1]["generated_at"] == receipt["generated_at"]
