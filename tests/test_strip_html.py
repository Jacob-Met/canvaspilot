"""Regression tests: strip_html must not eat escaped-tag text.

Canvas assignment bodies often contain escaped HTML (e.g. a web-dev prompt
telling students to "Use <img> tags", stored as "&lt;img&gt;"). The old
implementation unescaped entities BEFORE removing tags, so that literal text
was mistaken for markup and silently deleted from assignment briefs.
"""

from canvaspilot.api import CanvasAPI, strip_html
from canvaspilot.client import CanvasClient


def test_escaped_tags_survive_as_text():
    assert strip_html("Use &lt;canvas&gt; tags in your HTML") == "Use <canvas> tags in your HTML"


def test_real_tags_are_still_removed():
    assert strip_html("<p>Do the <b>thing</b></p>") == "Do the thing"


def test_entities_are_unescaped():
    assert strip_html("Tom &amp; Jerry") == "Tom & Jerry"


def test_empty_inputs():
    assert strip_html(None) == ""
    assert strip_html("") == ""


def test_assignment_brief_keeps_escaped_tag_text():
    fixture = {
        "profile": {"id": 1, "name": "Fixture"},
        "routes": {
            "GET /api/v1/courses/1/assignments/9": {
                "id": 9,
                "name": "HW1",
                "description": "<p>Use &lt;img&gt; tags with alt text</p>",
            },
        },
    }
    api = CanvasAPI(CanvasClient(fixture=fixture, base_url="https://example.test"))
    brief = api.assignment_brief(1, 9)
    assert brief["prompt"] == "Use <img> tags with alt text"
    assert "<p>" not in brief["prompt"]
    api.close()
