"""Semantic controls for literal announcement search."""
from __future__ import annotations

import unittest
from copy import deepcopy

from canvaspilot.announcement_search import search_announcements, validate_query


class AnnouncementSearchTests(unittest.TestCase):
    def test_ordered_duplicate_rows_and_field_attribution(self):
        rows = [
            {"id": 7, "title": "Straße notice", "message_text": "Unrelated", "posted_at": None},
            {"id": 7, "title": "STRASSE", "message_text": "Meet on Straße", "context_code": "course_77"},
            {"id": 0, "title": None, "message_text": ""},
        ]
        report = search_announcements(rows, "strasse")
        self.assertEqual(report["query"], "strasse")
        self.assertEqual(report["match_mode"], "literal_casefold")
        self.assertEqual(report["announcements_returned"], 3)
        self.assertEqual(report["announcements_matched"], 2)
        self.assertEqual(report["matches"], [
            {"matched_fields": ["title"], "announcement": rows[0]},
            {"matched_fields": ["title", "message_text"], "announcement": rows[1]},
        ])

    def test_metacharacters_are_literal(self):
        rows = [
            {"title": "xxxx", "message_text": "something else"},
            {"title": None, "message_text": "The exact token is [x]+.* here."},
        ]
        report = search_announcements(rows, "[x]+.*")
        self.assertEqual(report["matches"], [
            {"matched_fields": ["message_text"], "announcement": rows[1]},
        ])

    def test_significant_query_whitespace_is_retained(self):
        rows = [
            {"title": "room", "message_text": "classroom"},
            {"title": "Choose room two", "message_text": ""},
        ]
        report = search_announcements(rows, " room ")
        self.assertEqual(report["query"], " room ")
        self.assertEqual([m["announcement"] for m in report["matches"]], [rows[1]])

    def test_no_cross_field_join_or_additional_unicode_normalization(self):
        rows = [{"title": "Room", "message_text": "change"}]
        self.assertEqual(search_announcements(rows, "room change")["matches"], [])
        self.assertEqual(
            search_announcements([{"title": "Cafe\u0301", "message_text": ""}], "café")["matches"],
            [],
        )
        report = search_announcements([{"title": "ΟΣ", "message_text": ""}], "ος")
        self.assertEqual(report["announcements_matched"], 1)

    def test_optional_nontext_values_are_not_invented_search_text(self):
        rows = [{"id": i, "title": title, "message_text": ""}
                for i, title in enumerate([None, 0, False, ["0"], {"text": "0"}])]
        self.assertEqual(search_announcements(rows, "0")["matches"], [])
        self.assertEqual(search_announcements(rows, "0")["announcements_returned"], 5)
        rows[1]["message_text"] = "body"
        self.assertEqual(
            search_announcements(rows, "body")["matches"][0]["announcement"]["title"], 0,
        )

    def test_invalid_query_precedes_source_admission(self):
        for query in ["", " \t\n", "\u2003", None, False, 0, ["query"]]:
            with self.subTest(query=query), self.assertRaisesRegex(ValueError, "non-whitespace"):
                search_announcements(object(), query)
        self.assertEqual(validate_query(" query "), " query ")

    def test_invalid_normalized_container_does_not_return_partial_matches(self):
        for rows in [None, (), {}, [{"title": "query"}, "malformed"]]:
            with self.subTest(rows=rows), self.assertRaises(TypeError):
                search_announcements(rows, "query")

    def test_report_does_not_mutate_or_alias_source_metadata(self):
        rows = [{"id": 0, "title": ["original"], "message_text": "query", "posted_at": None}]
        before = deepcopy(rows)
        report = search_announcements(rows, "query")
        self.assertEqual(rows, before)
        report["matches"][0]["announcement"]["title"].append("edited report")
        self.assertEqual(rows, before)


if __name__ == "__main__":
    unittest.main()
