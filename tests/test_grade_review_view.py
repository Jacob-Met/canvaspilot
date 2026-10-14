"""Saved-grade view controls preserve the complete normalized report."""

from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import os
import unittest
from datetime import UTC, datetime
from html.parser import HTMLParser

if os.environ.get("CANVASPILOT_VIEW_TEST_SOURCE"):
    _spec = importlib.util.spec_from_file_location(
        "grade_view_subject", os.environ["CANVASPILOT_VIEW_TEST_SOURCE"]
    )
    _subject = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_subject)
    render_grade_review_report = _subject.render_grade_review_report
else:
    from canvaspilot.grade_review_export import render_grade_review_report


STAMP = datetime(2026, 10, 14, 0, 0, tzinfo=UTC)


def fixture():
    def assignment(identity, name, fields=None, visibility="reported_fields"):
        return {
            "fields": {"id": identity, "name": name, "points_possible": 20},
            "submission_state": "returned" if fields is not None else "not_returned",
            "submission": (
                {"grade_visibility": visibility, "fields": fields}
                if fields is not None
                else None
            ),
        }

    return {
        "course": {"id": 42, "name": "Fictional grade view"},
        "authenticated_user_id": 7,
        "totals_visibility": "reported_fields_only",
        "enrollments_state": "returned",
        "enrollments": [
            {"context": {"role": "StudentEnrollment"}, "reported_totals": {"computed_current_score": 0}}
        ],
        "grading_periods_state": "not_returned",
        "grading_periods": None,
        "assignment_groups": [
            {
                "id": 3, "name": "Labs Ω", "rules": {"drop_lowest": 1},
                "assignments_state": "returned",
                "assignments": [
                    assignment(9007199254740993, 'Lab <draft> "Ω"', {"score": 0, "missing": True, "late": False}),
                    assignment(102, 'Lab <draft> "Ω"', {"excused": True, "missing": None}, "not_posted"),
                    assignment(103, "", {"grade": "B", "grade_matches_current_submission": False, "late": True, "missing": False}),
                ],
            },
            {
                "id": 4, "name": "Labs Ω", "rules": None,
                "assignments_state": "returned",
                "assignments": [assignment(9007199254740994, "Future exam", None)],
            },
            {"id": 5, "name": "Unknown group", "assignments_state": "null", "assignments": None},
            {"id": 6, "name": "Empty group", "assignments_state": "returned", "assignments": []},
        ],
        "counts": {"groups_returned": 4, "assignments_returned": 4, "groups_without_assignment_list": 1},
        "collection_complete": None,
        "warnings": ["Fictional rows; whole-course completeness remains unknown."],
    }


class Page(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.script = []
        self.labels = {}
        self.current_label = None
        self.in_script = False
        self.feed(content.decode("utf-8"))

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "label":
            self.current_label = dict(attrs).get("for")
            self.labels[self.current_label] = ""
        if tag == "script":
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == "label":
            self.current_label = None
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        self.text.append(data)
        if self.current_label is not None:
            self.labels[self.current_label] += data
        if self.in_script:
            self.script.append(data)

    def by_id(self, identity):
        return next(attrs for _, attrs in self.tags if attrs.get("id") == identity)


class GradeViewTest(unittest.TestCase):
    def render(self, report=None):
        data = fixture() if report is None else report
        content, receipt = render_grade_review_report(data, generated_at=STAMP)
        return data, content, receipt, Page(content)

    def test_complete_json_and_report_values_are_unchanged(self):
        data = fixture()
        original = copy.deepcopy(data)
        _, content, receipt, page = self.render(data)
        payload = base64.b64decode(page.by_id("download-report")["href"].split(",", 1)[1], validate=True)
        self.assertEqual(payload, (json.dumps(original, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode("ascii"))
        self.assertEqual(data, original)
        self.assertEqual(receipt["json_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(receipt["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(receipt["assignments_returned"], 4)
        self.assertIn("whole-course completeness remains unknown", "".join(page.text))
        self.assertIn("Withheld by the reader", "".join(page.text))
        self.assertIn("does not match the current submission", "".join(page.text))

    def test_control_labels_remain_exact_without_select_option_text(self):
        _, _, _, page = self.render()
        self.assertEqual(page.labels, {
            "grade-search": "Find returned assignments",
            "grade-group": "Returned group",
            "grade-flag": "Canvas reported flag",
        })

    def test_controls_start_hidden_and_only_exact_trusted_script_is_allowed(self):
        _, _, _, page = self.render()
        self.assertIn("hidden", page.by_id("grade-view-controls"))
        self.assertEqual(page.by_id("grade-search")["type"], "search")
        self.assertEqual(page.by_id("grade-reset")["type"], "button")
        scripts = [(tag, attrs) for tag, attrs in page.tags if tag == "script"]
        self.assertEqual(len(scripts), 1)
        self.assertNotIn("src", scripts[0][1])
        script = "".join(page.script).encode("utf-8")
        digest = base64.b64encode(hashlib.sha256(script).digest()).decode("ascii")
        csp = next(attrs["content"] for tag, attrs in page.tags if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy")
        self.assertIn("script-src 'sha256-" + digest + "'", csp)
        self.assertNotIn("script-src 'unsafe-inline'", csp)
        self.assertIn("default-src 'none'", csp)
        self.assertFalse(any(key.startswith("on") for _, attrs in page.tags for key in attrs))

    def test_occurrences_keep_large_text_ids_literal_names_and_exact_true_flags(self):
        _, _, _, page = self.render()
        cards = [attrs for tag, attrs in page.tags if tag == "article" and attrs.get("class") == "assignment"]
        self.assertEqual([x["id"] for x in cards], ["assignment-0-0", "assignment-0-1", "assignment-0-2", "assignment-1-0"])
        self.assertEqual([x["data-review-id"] for x in cards], ["9007199254740993", "102", "103", "9007199254740994"])
        self.assertEqual([x["data-review-name"] for x in cards], ['Lab <draft> "Ω"', 'Lab <draft> "Ω"', "Assignment 103", "Future exam"])
        self.assertEqual([x["data-review-group"] for x in cards], ["0", "0", "0", "1"])
        self.assertEqual([x["data-review-missing"] for x in cards], ["true", "false", "false", "false"])
        self.assertEqual([x["data-review-late"] for x in cards], ["false", "false", "true", "false"])
        self.assertEqual([x["data-review-excused"] for x in cards], ["false", "true", "false", "false"])
        self.assertFalse(any("hidden" in x for x in cards))

    def test_duplicate_groups_unknown_lists_and_empty_lists_keep_context(self):
        _, _, _, page = self.render()
        options = [attrs["value"] for tag, attrs in page.tags if tag == "option" and attrs.get("data-grade-group") == "true"]
        self.assertEqual(options, ["0", "1", "2", "3"])
        text = "".join(page.text)
        self.assertIn("Canvas returned null", text)
        self.assertIn("empty assignment list", text)
        self.assertIn("drop_lowest", text)
        self.assertIn("Printing includes every returned assignment", text)
        self.assertEqual(page.by_id("grade-view-count")["role"], "status")
        self.assertIn("hidden", page.by_id("grade-no-match"))

    def test_markup_is_inert_and_print_retains_closed_detail_rule(self):
        data = fixture()
        data["assignment_groups"][0]["assignments"][0]["fields"]["name"] = '<img src="https://invalid.example/"> <script>not code</script>\u0080\ud800'
        _, content, _, page = self.render(data)
        self.assertFalse({"img", "iframe", "object", "form"} & {tag for tag, _ in page.tags})
        self.assertIn("\\u0080", "".join(page.text))
        self.assertIn("\\ud800", "".join(page.text))
        self.assertIn(b"details:not([open]) > *:not(summary)", content)
        self.assertIn(b".assignment[hidden] { display:block !important; }", content)

    def test_empty_report_still_has_complete_download_and_truthful_context(self):
        data = fixture()
        data["assignment_groups"] = []
        data["counts"].update(groups_returned=0, assignments_returned=0, groups_without_assignment_list=0)
        _, _, receipt, page = self.render(data)
        self.assertEqual(receipt["assignments_returned"], 0)
        self.assertIn("No assignment groups were returned", "".join(page.text))
        self.assertEqual(len([1 for tag, attrs in page.tags if tag == "article" and attrs.get("class") == "assignment"]), 0)
        self.assertEqual(json.loads(base64.b64decode(page.by_id("download-report")["href"].split(",", 1)[1])), data)


if __name__ == "__main__":
    unittest.main()
