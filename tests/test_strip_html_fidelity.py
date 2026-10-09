"""Prompt fidelity through the shared text projection and assignment brief."""

from copy import deepcopy
from unittest import TestCase

from canvaspilot.api import CanvasAPI, strip_html


class TestHTMLTextFidelity(TestCase):
    def test_literal_comparisons(self):
        for source in (
            "If x < 5 and y > 2, explain.",
            "Keep x<5 and y>2.",
            "Use 0 <= x < 10; y >= 3.",
        ):
            with self.subTest(source=source):
                self.assertEqual(strip_html(f"<p>{source}</p>"), source)

    def test_quoted_attributes_are_not_text(self):
        for source in (
            '<p title="a > b">Need value</p>',
            "<p title='a > b'>Need value</p>",
            '<p title="a > <b>">Need value</p>',
            "<p title='say \"a > b\"' data-n=\"2\">Need value</p>",
        ):
            with self.subTest(source=source):
                self.assertEqual(strip_html(source), "Need value")

    def test_entities_decode_once_from_original_spelling(self):
        for source, expected in (
            ("&amp;lt;canvas&amp;gt;", "&lt;canvas&gt;"),
            ("&#38;lt;b&#38;gt;", "&lt;b&gt;"),
            ("&lt;!-- shown --&gt;", "<!-- shown -->"),
            ("A &madeup text", "A &madeup text"),
            ("A &madeup; text", "A &madeup; text"),
            ("A &notit text", "A ¬it text"),
        ):
            with self.subTest(source=source):
                self.assertEqual(strip_html(source), expected)

    def test_real_tags_separate_text(self):
        for source, expected in (
            ("<p>Do the <b>thing</b></p>", "Do the thing"),
            ("one<br/>two<img alt='never shown'>three", "one two three"),
            ("A<custom-element data-x='1'>B</custom-element>C", "A B C"),
        ):
            with self.subTest(source=source):
                self.assertEqual(strip_html(source), expected)

    def test_complete_comments_and_declarations(self):
        for source in (
            "Before<!-- threshold x > 5 -->After",
            "Before<!-- &lt;b&gt; -->After",
            "Before<!DOCTYPE html>After",
            "Before<?processing x='>'?>After",
        ):
            with self.subTest(source=source):
                self.assertEqual(strip_html(source), "Before After")

    def test_unfinished_suffixes_remain_text(self):
        for suffix in (
            "<",
            "<em",
            "<em title='unfinished",
            '<em title="unfinished>text',
            '<em title="unfinished <b>text',
            "<!-- unfinished > comment",
        ):
            with self.subTest(suffix=suffix):
                self.assertEqual(strip_html("Keep " + suffix), "Keep " + suffix)

    def test_script_and_style_are_not_visibility_filtered(self):
        for source, expected in (
            ("<script>a &amp; b</script>", "a & b"),
            ("<style>&amp;lt;tag&amp;gt;</style>", "&lt;tag&gt;"),
            ("<script>Keep this text", "Keep this text"),
            ("<style>Keep this text", "Keep this text"),
            ("<script>a <b>b</b></script>", "a b"),
        ):
            with self.subTest(source=source):
                self.assertEqual(strip_html(source), expected)

    def test_unsupported_prefix_remains_literal_before_a_real_tag(self):
        for source, expected in (
            ("A< broken <b>B</b>", "A< broken B"),
            ("A<unfinished <b>B</b>", "A<unfinished B"),
            ("A<5 <b>B</b>", "A<5 B"),
        ):
            with self.subTest(source=source):
                self.assertEqual(strip_html(source), expected)

    def test_empty_unicode_and_whitespace(self):
        for source, expected in (
            (None, ""),
            ("", ""),
            ("  <p>α\tβ</p>\r\n&lt;γ&gt; &nbsp; &#x1F600;", "α β <γ> 😀"),
        ):
            with self.subTest(source=source):
                self.assertEqual(strip_html(source), expected)

    def test_assignment_brief_retains_metadata_and_request(self):
        class ResponseTransport:
            def __init__(self, response):
                self.response = response
                self.calls = []

            def request(self, method, path, *, params):
                self.calls.append((method, path, params))
                return self.response

        for source, expected in (
            ("<p>If x < 5 and y > 2, explain.</p>", "If x < 5 and y > 2, explain."),
            ('<p title="a > b">Need value</p>', "Need value"),
            ("<p>Use &lt;img&gt; tags</p>", "Use <img> tags"),
        ):
            with self.subTest(source=source):
                response = {
                    "id": 9,
                    "name": "Exact title",
                    "description": source,
                    "due_at": None,
                    "points_possible": 0,
                    "submission_types": ["online_text_entry"],
                    "html_url": "https://example.test/assignments/9",
                    "rubric": [{"id": "r", "description": "Exact criterion", "points": 0}],
                    "rubric_settings": {"free_form_criterion_comments": False},
                    "use_rubric_for_grading": False,
                }
                before = deepcopy(response)
                transport = ResponseTransport(response)
                result = CanvasAPI(transport).assignment_brief(1, 9)
                self.assertEqual(result["prompt"], expected)
                self.assertEqual(result["title"], "Exact title")
                self.assertEqual(result["points_possible"], 0)
                self.assertIsNone(result["due_at"])
                self.assertEqual(result["submission_types"], ["online_text_entry"])
                self.assertEqual(result["html_url"], "https://example.test/assignments/9")
                self.assertEqual(result["course_id"], 1)
                self.assertEqual(result["assignment_id"], 9)
                self.assertEqual(result["rubric"], response["rubric"])
                self.assertEqual(result["rubric_settings"], response["rubric_settings"])
                self.assertIs(result["use_rubric_for_grading"], False)
                self.assertEqual(result["rubric_warnings"], [])
                self.assertEqual(
                    transport.calls,
                    [("GET", "/api/v1/courses/1/assignments/9", {"include[]": ["submission"]})],
                )
                result["rubric"][0]["description"] = "changed copy"
                result["rubric_settings"]["free_form_criterion_comments"] = True
                self.assertEqual(response, before)
