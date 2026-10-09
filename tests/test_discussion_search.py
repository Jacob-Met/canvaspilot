"""Focused contract tests for the read-only discussion-topic search."""

import copy
import io
import json
import logging
import sys
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from canvaspilot import cli
from canvaspilot.discussion_search import (
    MAX_INPUT_BYTES,
    MAX_OUTPUT_BYTES,
    collect_discussions,
    search_discussions,
    serialize_discussion_search,
    validate_selection,
)


def topic(title="Reef", message="a complete opening", **metadata):
    return {
        "id": 7, "title": title, "posted_at": None, "published": False,
        "message_text": message, "html_url": "", **metadata,
    }


def selection(rows, course="12"):
    return {"course_id": course, "topics": rows}


class SearchTests(unittest.TestCase):
    def test_full_opening_and_field_order_without_cross_field_join(self):
        rows = [topic("reef", "x" * 1400 + "reef"), topic("red", "blue")]
        result = search_discussions([selection(rows)], "REEF")
        self.assertEqual(result["matches"][0]["matched_fields"], ["title", "message_text"])
        self.assertEqual(result["matches"][0]["topic"]["message_text"], rows[0]["message_text"])
        self.assertEqual(search_discussions([selection(rows)], "red blue")["matches"], [])

    def test_unicode_casefold_literal_punctuation_and_no_normalization(self):
        rows = [topic("Straße", "café a.*b"), topic("STRASSE", "cafe\u0301")]
        self.assertEqual(search_discussions([selection(rows)], "strasse")["matched_count"], 2)
        self.assertEqual(search_discussions([selection(rows)], "CAFÉ")["matched_count"], 1)
        self.assertEqual(search_discussions([selection(rows)], "a.*b")["matched_count"], 1)
        self.assertEqual(search_discussions([selection(rows)], "a.+b")["matched_count"], 0)

    def test_significant_query_whitespace_is_retained(self):
        rows = [topic("reef", "x reef y"), topic("reef", "x reefy")]
        result = search_discussions([selection(rows)], " reef ")
        self.assertEqual(result["query"], " reef ")
        self.assertEqual([m["topic_position"] for m in result["matches"]], [1])
        for bad in ("", " \t\n", "\u00a0"):
            with self.assertRaises(ValueError):
                search_discussions([selection(rows)], bad)

    def test_duplicate_course_and_topic_occurrences_keep_original_order(self):
        row = topic()
        source = [selection([row, row], "0012"), selection([row], 9), selection([row], "12")]
        result = search_discussions(source, "reef")
        self.assertEqual(
            [(m["selection_number"], m["course_id"], m["topic_position"]) for m in result["matches"]],
            [(1, "12", 1), (1, "12", 2), (2, "9", 1), (3, "12", 1)],
        )
        self.assertEqual(result["topic_count"], 4)

    def test_no_match_empty_title_and_empty_prompt_counts(self):
        result = search_discussions([selection([topic(None, ""), topic("", "")]), selection([], "9")], "x")
        self.assertEqual(result["matched_count"], 0)
        self.assertEqual(result["topic_count"], 2)
        self.assertEqual(result["empty_message_text_count"], 2)
        self.assertEqual(result["selections"][1]["topics_returned"], 0)
        self.assertIn("not replies", result["boundary"])

    def test_unknown_values_are_preserved_detached_and_inputs_unchanged(self):
        row = topic(extra={"none": None, "false": False, "zero": 0, "empty": "", "list": [1, {"x": "雪"}]})
        source = [selection([row])]
        before = copy.deepcopy(source)
        result = search_discussions(source, "reef")
        self.assertEqual(result["matches"][0]["topic"], row)
        text = serialize_discussion_search(result)
        self.assertEqual(json.loads(text), result)
        self.assertTrue(text.endswith("\n"))
        result["matches"][0]["topic"]["extra"]["list"][1]["x"] = "changed"
        self.assertEqual(source, before)

    def test_malformed_nonmatching_later_row_refuses_whole_result(self):
        for bad in (topic("no", 4), topic(2, ""), {"id": 8}, None, [], topic(extra={1: "x"})):
            source = [selection([topic()]), selection([bad], "9")]
            before = copy.deepcopy(source)
            with self.assertRaises(ValueError):
                search_discussions(source, "reef")
            self.assertEqual(source, before)

    def test_nonjson_values_cycles_nonfinite_and_unicode_refuse(self):
        for bad in (float("nan"), float("inf"), (1, 2), set(), object(), "\ud800"):
            with self.assertRaises(ValueError):
                search_discussions([selection([topic(extra=bad)])], "reef")
        cyclic = []
        cyclic.append(cyclic)
        with self.assertRaises(ValueError):
            search_discussions([selection([topic(extra=cyclic)])], "reef")

    def test_container_depth_boundary(self):
        value = 0
        for _ in range(28):
            value = [value]
        search_discussions([selection([topic(extra=value)])], "reef")
        with self.assertRaises(ValueError):
            search_discussions([selection([topic(extra=[value])])], "reef")

    def test_selection_admission_and_query_utf8_boundary(self):
        self.assertEqual(validate_selection(["0001", 2, "0001"], " x "), (["1", "2", "1"], " x "))
        for courses in ([], ["1"] * 11, "1", [True], [0], [-1], ["0"], ["+1"], [" 1"], ["١"], ["1" * 21], [10**20]):
            with self.assertRaises(ValueError):
                validate_selection(courses, "x")
        self.assertEqual(validate_selection(["1"], "é" * 256)[1], "é" * 256)
        for query in ("é" * 257, "\ud800", None, 1):
            with self.assertRaises(ValueError):
                validate_selection(["1"], query)

    def test_topic_and_normalized_byte_boundaries(self):
        search_discussions([selection([topic()] * 1000)], "reef")
        with self.assertRaises(ValueError):
            search_discussions([selection([topic()] * 1001)], "reef")
        source = [selection([topic(message="")])]
        overhead = len(json.dumps(source, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode())
        source[0]["topics"][0]["message_text"] = "x" * (MAX_INPUT_BYTES - overhead)
        search_discussions(source, "no-match")
        source[0]["topics"][0]["message_text"] += "x"
        with self.assertRaises(ValueError):
            search_discussions(source, "no-match")

    def test_output_limit_refuses_instead_of_truncating(self):
        with self.assertRaises(ValueError):
            serialize_discussion_search({"long": "x" * MAX_OUTPUT_BYTES})

    def test_collect_calls_only_selected_occurrences_and_retains_failure(self):
        class API:
            def __init__(self):
                self.calls = []
            def list_discussion_topics(self, course):
                self.calls.append(course)
                if course == "9":
                    raise RuntimeError("later read failed")
                return [topic()]
        api = API()
        result = collect_discussions(api, ["0012", "12"], "reef")
        self.assertEqual(api.calls, ["12", "12"])
        self.assertEqual(result["matched_count"], 2)
        with self.assertRaisesRegex(RuntimeError, "later read"):
            collect_discussions(api, ["12", "9"], "reef")
        before = list(api.calls)
        with self.assertRaises(ValueError):
            collect_discussions(api, ["12"], " ")
        self.assertEqual(api.calls, before)


    def test_boundary_is_the_exact_frozen_contract_literal(self):
        expected = (
            "Searches only returned titles and complete normalized opening prompts from "
            "the existing topic-list reader; not replies, attachments, hidden/unavailable "
            "raw content or a freshness/completeness guarantee. The existing paginator is "
            "reused unchanged; pagination failure refuses the result, and its provider "
            "conventions/limits remain."
        )
        result = search_discussions([selection([topic(None, "")])], "absent")
        self.assertEqual(result["boundary"], expected)
        self.assertEqual(json.loads(serialize_discussion_search(result))["boundary"], expected)
        self.assertEqual(result["empty_message_text_count"], 1)



class CLITests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.closed = []
        self.constructions = []
        self.default_reads = []
        self.fail_course = None
        self.close_error = False
        self.raw = {
            "12": [{"id": 7, "title": "same", "message": "<p>x &lt;Reef&gt;  late</p>", "published": False}],
            "9": [{"id": 7, "title": "reef", "message": None, "published": 0}],
        }
        outer = self

        class AuthError(RuntimeError):
            pass

        class PaginationError(RuntimeError):
            pass

        class HTTPError(Exception):
            pass

        class Client:
            def __init__(self, **kwargs):
                outer.constructions.append(kwargs)
            def get_paginated(self, path, params):
                outer.calls.append((path, params))
                course = path.split("/")[4]
                if outer.fail_course == course:
                    raise PaginationError("later page refused")
                return copy.deepcopy(outer.raw[course])
            def request(self, *args, **kwargs):
                raise AssertionError("detail/provider operation forbidden")
            def close(self):
                outer.closed.append(True)
                if outer.close_error:
                    raise OSError("close refused")
        client_module = types.ModuleType("canvaspilot.client")
        client_module.CanvasClient = Client
        client_module.CanvasAuthError = AuthError
        client_module.CanvasPaginationError = PaginationError
        def default_base():
            outer.default_reads.append("base")
            return "https://fixture.invalid"
        def default_profile():
            outer.default_reads.append("profile")
            return None
        client_module.default_base_url = default_base
        client_module.default_profile = default_profile
        http = types.ModuleType("httpx")
        http.HTTPError = HTTPError
        self.modules = patch.dict(sys.modules, {"canvaspilot.client": client_module, "httpx": http})
        self.modules.start()
        self.level = logging.getLogger("httpx").level
        logging.getLogger("httpx").setLevel(logging.DEBUG)

    def tearDown(self):
        self.modules.stop()
        logging.getLogger("httpx").setLevel(self.level)

    def run_cli(self, args, output=None):
        output = output if output is not None else io.StringIO()
        errors = io.StringIO()
        code = 0
        with redirect_stdout(output), redirect_stderr(errors):
            try:
                cli.main(args)
            except SystemExit as exc:
                code = exc.code
        return code, output.getvalue(), errors.getvalue()

    def test_real_parser_dispatch_and_exact_unchanged_api_normalization(self):
        code, output, errors = self.run_cli(["find-discussions", "0012", "9", "12", "--text", "REEF"])
        self.assertEqual((code, errors), (0, ""))
        result = json.loads(output)
        self.assertEqual([m["course_id"] for m in result["matches"]], ["12", "9", "12"])
        self.assertEqual(result["matches"][0]["topic"]["message_text"], "x <Reef> late")
        self.assertEqual(result["matches"][1]["topic"]["published"], 0)
        self.assertEqual(result["empty_message_text_count"], 1)
        self.assertEqual([p for p, _ in self.calls], ["/api/v1/courses/12/discussion_topics", "/api/v1/courses/9/discussion_topics", "/api/v1/courses/12/discussion_topics"])
        self.assertTrue(all(params == {"order_by": "recent_activity", "only_announcements": False} for _, params in self.calls))
        self.assertEqual(len(self.closed), 1)
        self.assertEqual(logging.getLogger("httpx").level, logging.DEBUG)

    def test_invalid_query_and_course_before_client_profile_setup(self):
        for args in (["find-discussions", "12", "--text", " "], ["find-discussions", "../x", "--text", "x"], ["find-discussions", "12"]):
            code, output, _ = self.run_cli(args)
            self.assertEqual((code, output), (2, ""))
        self.assertEqual((self.constructions, self.default_reads, self.calls), ([], [], []))

    def test_later_pagination_failure_has_no_partial_stdout(self):
        self.fail_course = "9"
        code, output, errors = self.run_cli(["find-discussions", "12", "9", "--text", "reef"])
        self.assertEqual((code, output), (1, ""))
        self.assertFalse(json.loads(errors)["ok"])
        self.assertEqual(len(self.closed), 1)
        self.assertEqual(logging.getLogger("httpx").level, logging.DEBUG)

    def test_malformed_later_source_and_close_failure_refuse(self):
        self.raw["9"][0]["title"] = 4
        code, output, _ = self.run_cli(["find-discussions", "12", "9", "--text", "reef"])
        self.assertEqual((code, output), (1, ""))
        self.close_error = True
        code, output, _ = self.run_cli(["find-discussions", "12", "--text", "reef"])
        self.assertEqual((code, output), (1, ""))
        self.assertEqual(len(self.closed), 2)
        self.assertEqual(logging.getLogger("httpx").level, logging.DEBUG)

    def test_short_write_and_failed_flush_are_not_success(self):
        class Short(io.StringIO):
            def write(self, value):
                super().write(value[:3])
                return 3
        class FlushFailure(io.StringIO):
            def flush(self):
                raise OSError("flush failed")
        for output in (Short(), FlushFailure()):
            code, _, errors = self.run_cli(["find-discussions", "12", "--text", "reef"], output)
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(errors)["ok"])

    def test_help_and_existing_discussions_parser_remain_available(self):
        code, output, errors = self.run_cli(["find-discussions", "--help"])
        self.assertEqual((code, errors), (0, ""))
        self.assertIn("--text", output)
        code, output, errors = self.run_cli(["discussions", "--help"])
        self.assertEqual((code, errors), (0, ""))
        self.assertIn("course_id", output)
        self.assertEqual(self.constructions, [])


if __name__ == "__main__":
    unittest.main()
