import copy
import math
import unittest
from unittest.mock import patch

from canvaspilot.file_search import search_course_files, validate_selection


class Reader:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def list_files(self, course):
        self.calls.append(course)
        value = self.rows[course]
        if isinstance(value, Exception):
            raise value
        return value


class FileSearchTests(unittest.TestCase):
    def test_literal_unicode_and_separate_fields(self):
        rows = [
            {"id": 8, "display_name": "Straße NOTES.pdf", "filename": "notes.pdf"},
            {"id": 8, "display_name": "stras", "filename": "se"},
            {"id": None, "display_name": "[a.*]", "filename": "Résumé"},
        ]
        api = Reader({"42": rows})
        result = search_course_files(api, ["0042"], "STRASSE")
        self.assertEqual(result["course_ids"], ["42"])
        self.assertEqual([x["match"] for x in result["courses"][0]["observations"]], [True, False, False])
        self.assertEqual(result["courses"][0]["observations"][0]["matched_fields"], ["display_name"])
        self.assertEqual(api.calls, ["42"])
        self.assertEqual(search_course_files(api, [42], "[a.*]")["counts"]["matched"], 1)
        self.assertEqual(search_course_files(api, [42], "resume")["counts"]["matched"], 0)

    def test_unknown_is_not_a_known_nonmatch(self):
        rows = [
            {}, {"display_name": None, "filename": "other"},
            {"display_name": "", "filename": ""},
            {"display_name": None, "filename": "notes"},
            {"display_name": "notes", "filename": "notes"},
        ]
        report = search_course_files(Reader({"1": rows}), ["1"], "notes")
        self.assertEqual(report["counts"], {"returned": 5, "matched": 2, "unknown": 2, "nonmatching": 1})
        obs = report["courses"][0]["observations"]
        self.assertEqual([x["match"] for x in obs], [None, None, False, True, True])
        self.assertEqual(obs[4]["matched_fields"], ["display_name", "filename"])
        self.assertEqual(obs[0]["unavailable_fields"], ["display_name", "filename"])

    def test_duplicate_ids_order_exact_metadata_and_detached_result(self):
        rows = [{"id": 2**60, "display_name": "a", "filename": "", "unknown":
                 {"false": False, "zero": 0, "minus": -0.0, "nested": ["📚", None]}}] * 2
        before = copy.deepcopy(rows)
        api = Reader({"77": [], "42": rows})
        report = search_course_files(api, ["77", "42"], "a")
        self.assertEqual(api.calls, ["77", "42"])
        obs = report["courses"][1]["observations"]
        self.assertEqual([x["source_index"] for x in obs], [0, 1])
        self.assertEqual([x["source"] for x in obs], before)
        self.assertEqual(math.copysign(1, obs[0]["source"]["unknown"]["minus"]), -1)
        obs[0]["source"]["unknown"]["nested"].append("changed")
        self.assertEqual(rows, before)
        self.assertEqual(obs[1]["source"], before[1])

    def test_whitespace_and_compatibility_are_literal(self):
        api = Reader({"1": [{"display_name": "a b", "filename": "ＡＢ"}]})
        self.assertEqual(search_course_files(api, ["1"], " b")["counts"]["matched"], 1)
        self.assertEqual(search_course_files(api, ["1"], "b ")["counts"]["matched"], 0)
        self.assertEqual(search_course_files(api, ["1"], "ab")["counts"]["matched"], 0)

    def test_invalid_selection_never_reads(self):
        for ids in ([], ["1"] * 2, ["01", 1], [True], ["0"], ["-1"], [" 1"],
                    ["１"], ["1" * 21], list(range(1, 12)), ("1",), [1.0]):
            with self.subTest(ids=ids):
                api = Reader({})
                with self.assertRaises(ValueError):
                    search_course_files(api, ids, "a")
                self.assertEqual(api.calls, [])

    def test_query_admission_and_utf8_boundary(self):
        for query in ("", " \t\n", None, 1, "\ud800", "é" * 257):
            with self.subTest(query=repr(query)), self.assertRaises(ValueError):
                validate_selection(["1"], query)
        self.assertEqual(validate_selection(["1"], "é" * 256)[1], "é" * 256)

    def test_malformed_reader_and_name_refuse_complete_report(self):
        for rows in ({}, [None], [{"display_name": []}], [{"filename": False}],
                     [{"id": float("nan")}], [{"id": {1: "a"}}],
                     [{"id": "\ud800"}], [{"id": (1, 2)}]):
            with self.subTest(rows=repr(rows)), self.assertRaises((ValueError, UnicodeError)):
                search_course_files(Reader({"1": [], "2": rows}), ["1", "2"], "x")

    def test_late_course_failure_propagates(self):
        api = Reader({"1": [{"display_name": "a", "filename": "a"}], "2": RuntimeError("late")})
        with self.assertRaisesRegex(RuntimeError, "late"):
            search_course_files(api, ["1", "2"], "a")
        self.assertEqual(api.calls, ["1", "2"])

    def test_row_limit_is_combined_and_inclusive(self):
        row = {"display_name": "a", "filename": ""}
        self.assertEqual(search_course_files(Reader({"1": [row] * 5000}), ["1"], "a")["counts"]["returned"], 5000)
        with self.assertRaisesRegex(ValueError, "5,000"):
            search_course_files(Reader({"1": [row] * 3000, "2": [row] * 2001}), ["1", "2"], "a")

    def test_source_and_output_budget_refuse_without_truncation(self):
        row = {"display_name": "a", "filename": "", "extra": "x" * (4 * 1024 * 1024)}
        with self.assertRaisesRegex(ValueError, "4 MiB"):
            search_course_files(Reader({"1": [row]}), ["1"], "a")
        with patch("canvaspilot.file_search.MAX_OUTPUT_BYTES", 1), self.assertRaisesRegex(ValueError, "16 MiB"):
            search_course_files(Reader({"1": []}), ["1"], "a")

    def test_nested_container_boundary(self):
        x = "a"
        for _ in range(16):
            x = [x]
        self.assertEqual(search_course_files(Reader({"1": [{"extra": x}]}), ["1"], "a")["counts"]["unknown"], 1)
        with self.assertRaisesRegex(ValueError, "nested"):
            search_course_files(Reader({"1": [{"extra": [x]}]}), ["1"], "a")
