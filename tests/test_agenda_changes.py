"""Saved-report semantics through the exact dependency-free consumer file."""

from __future__ import annotations

import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path

CORE_PATH = Path(__file__).resolve().parents[1] / "src/canvaspilot/agenda_changes.py"
SPEC = importlib.util.spec_from_file_location("agenda_changes_under_test", CORE_PATH)
assert SPEC is not None and SPEC.loader is not None
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)


def raw(value, **kwargs):
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, **kwargs) + "\n").encode()


def saved(events=(), assignments=()):
    """Explicit authored saved-report fixture, not a claimed producer run."""
    rows = []
    for kind, records in (("event", events), ("assignment", assignments)):
        for index, value in enumerate(records):
            record = deepcopy(value)
            record.setdefault("context_code", "course_23")
            course = record.get("effective_context_code", record["context_code"]).removeprefix("course_")
            rows.append({
                "kind": kind, "course_id": course, "source": {"collection": kind, "index": index},
                "record": record,
                "timing_issue": {"field": "all_day", "reason": "expected an explicit boolean"},
            })
    return {
        "schema": "canvaspilot.course-agenda.v1",
        "selection": {"course_ids": ["23", "61"], "context_codes": ["course_23", "course_61"],
                      "start_date": "2026-10-08", "end_date": "2026-10-11"},
        "collection_counts": {"event": len(events), "assignment": len(assignments)},
        "counts": {"total": len(rows), "timed": 0, "all_day": 0, "timing_unavailable": len(rows)},
        "timed": [], "all_day": [], "timing_unavailable": rows,
    }


class AgendaChangesTests(unittest.TestCase):
    def test_empty_and_decoded_equality_do_not_claim_raw_equality(self):
        value = saved()
        before, after = raw(value), raw(value, sort_keys=True, indent=2)
        result = core.compare_saved_agendas(before, after)
        self.assertTrue(result["document_equal"])
        self.assertNotEqual(result["inputs"]["before"]["sha256"], result["inputs"]["after"]["sha256"])
        self.assertEqual(result["groups"], [])
        self.assertTrue(all(n == 0 for n in result["counts"].values()))

    def test_strict_scalar_and_nested_equality(self):
        a = saved([{"id": 1, "n": 1, "b": False, "nested": {"a": 1, "b": [2, 3]}, "z": -0.0}])
        b = saved([{"id": 1, "n": 1.0, "b": 0, "nested": {"b": [2, 3], "a": 1}, "z": 0.0}])
        result = core.compare_saved_agendas(raw(a), raw(b))
        self.assertFalse(result["document_equal"])
        self.assertEqual(result["counts"]["changed"], 1)
        self.assertEqual([x["field"] for x in result["groups"][0]["field_changes"]], ["b", "n"])

    def test_missing_null_empty_and_array_order(self):
        a = saved([{"id": 1, "removed": None, "empty": "", "items": [1, 2]}])
        b = saved([{"id": 1, "added": None, "empty": [], "items": [2, 1]}])
        changes = core.compare_saved_agendas(raw(a), raw(b))["groups"][0]["field_changes"]
        self.assertEqual([x["field"] for x in changes], ["added", "empty", "items", "removed"])
        self.assertEqual(changes[0]["before"], {"state": "missing"})
        self.assertEqual(changes[0]["after"], {"state": "present", "value": None})
        self.assertEqual(changes[-1]["after"], {"state": "missing"})

    def test_duplicate_occurrences_are_never_paired(self):
        a = saved([{"id": "repeat", "title": "a"}, {"id": "repeat", "title": "b"}])
        b = saved([{"id": "repeat", "title": "a"}])
        group = core.compare_saved_agendas(raw(a), raw(b))["groups"][0]
        self.assertEqual(group["classification"], "ambiguous")
        self.assertEqual(len(group["before"]), 2)
        self.assertEqual(len(group["after"]), 1)
        self.assertEqual(group["field_changes"], [])
        same = core.compare_saved_agendas(raw(a), raw(a))
        self.assertTrue(same["document_equal"])
        self.assertEqual(same["counts"]["ambiguous"], 1)

    def test_typed_ids_course_and_kind_stay_separate(self):
        value = saved([{"id": 1}, {"id": "1"}, {"id": 1, "context_code": "course_61"}], [{"id": 1}])
        result = core.compare_saved_agendas(raw(value), raw(value))
        self.assertEqual(result["counts"]["unchanged"], 4)
        self.assertEqual(result["counts"]["ambiguous"], 0)
        self.assertEqual([g["identity"]["id_type"] for g in result["groups"]], ["integer", "string", "integer", "integer"])

    def test_source_position_reordering_does_not_change_unique_records(self):
        a = saved([{"id": 1, "title": "first"}, {"id": 2, "title": "second"}])
        b = saved([{"id": 2, "title": "second"}, {"id": 1, "title": "first"}])
        result = core.compare_saved_agendas(raw(a), raw(b))
        self.assertFalse(result["document_equal"])
        self.assertEqual(result["counts"]["unchanged"], 2)
        self.assertEqual([g["identity"]["id"] for g in result["groups"]], [1, 2])
        self.assertEqual(result["groups"][0]["after"][0]["entry"]["source"]["index"], 1)

    def test_presence_is_not_deletion_or_creation(self):
        result = core.compare_saved_agendas(raw(saved([{"id": 1}])), raw(saved([{"id": 2}])))
        self.assertEqual([g["classification"] for g in result["groups"]], ["before_only", "after_only"])
        self.assertTrue(any("deletion" in text for text in result["limitations"]))

    def test_exact_selection_and_date_admission(self):
        good = saved()
        variants = []
        for field, value in (("start_date", "2026-02-30"), ("end_date", "2026-10-07"),
                             ("start_date", "20261008"), ("course_ids", ["023", "61"]),
                             ("course_ids", ["23", "23"]), ("context_codes", ["course_61", "course_23"])):
            bad = deepcopy(good)
            bad["selection"][field] = value
            variants.append(bad)
        changed = deepcopy(good)
        changed["selection"]["end_date"] = "2026-10-12"
        variants.append(changed)
        for bad in variants:
            with self.subTest(selection=bad["selection"]), self.assertRaises(ValueError):
                core.compare_saved_agendas(raw(good), raw(bad))

    def test_shape_counts_indices_and_identity_admission(self):
        good = saved([{"id": 1}, {"id": 2}])
        variants = []
        def change(path, value):
            bad = deepcopy(good)
            target = bad
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            variants.append(bad)
        change(["schema"], "canvaspilot.course-agenda.v2")
        change(["counts", "total"], True)
        change(["counts", "timing_unavailable"], 1)
        change(["collection_counts", "event"], 3)
        change(["timing_unavailable", 1, "source", "index"], 0)
        change(["timing_unavailable", 1, "source", "index"], 2)
        change(["timing_unavailable", 1, "source", "index"], False)
        change(["timing_unavailable", 0, "record", "id"], True)
        change(["timing_unavailable", 0, "record", "id"], 1.0)
        change(["timing_unavailable", 0, "record", "id"], " ")
        change(["timing_unavailable", 0, "record", "context_code"], "course_999")
        change(["timing_unavailable", 0, "record", "assignment"], {"course_id": 61})
        change(["timing_unavailable", 0, "timing_issue", "reason"], None)
        for bad in variants:
            with self.subTest(report=bad), self.assertRaises(ValueError):
                core.compare_saved_agendas(raw(good), raw(bad))

    def test_strict_json_and_nonfinite_decoding(self):
        good = raw(saved())
        variants = [b"\xff", b"\xef\xbb\xbf" + good, b'{"a":1,"a":2}', b'{"a":NaN}',
                    b'{"a":Infinity}', good.replace(b'"total": 0', b'"total": 1e999')]
        for bad in variants:
            with self.subTest(raw=bad), self.assertRaises(ValueError):
                core.compare_saved_agendas(good, bad)
        with self.assertRaises(TypeError):
            core.compare_saved_agendas(good.decode(), good)

    def test_admitted_section_context_and_null_assignment_are_preserved(self):
        value = saved([{"id": 0, "context_code": "course_section_009",
                        "effective_context_code": "course_61", "assignment": None}])
        result = core.compare_saved_agendas(raw(value), raw(value))
        self.assertEqual(result["inputs"]["before"]["report"], value)
        self.assertEqual(result["counts"]["unchanged"], 1)

    def test_bounds_are_complete_refusals(self):
        self.assertEqual(core.MAX_INPUT_BYTES, 8 * 1024 * 1024)
        self.assertEqual(core.MAX_OUTPUT_BYTES, 32 * 1024 * 1024)
        self.assertEqual(core.MAX_RECORDS, 4096)
        self.assertEqual(core.MAX_DEPTH, 64)
        value = raw(saved([{"id": 1}, {"id": 2}]))
        for name, limit in (("MAX_INPUT_BYTES", 10), ("MAX_OUTPUT_BYTES", 10),
                            ("MAX_RECORDS", 1), ("MAX_DEPTH", 2)):
            original = getattr(core, name)
            try:
                setattr(core, name, limit)
                with self.subTest(limit=name), self.assertRaises(ValueError):
                    core.compare_saved_agendas(value, value)
            finally:
                setattr(core, name, original)

    def test_human_output_quotes_controls_and_retains_unicode_and_full_records(self):
        value = saved([{"id": "\x1b[2J", "title": "naïve\tline\nnext", "extra": [None, 0, False]}])
        before = raw(value)
        result = core.compare_saved_agendas(before, before)
        rendered = core.render_agenda_changes(result)
        self.assertNotIn(b"\x1b", rendered)
        self.assertNotIn(b"\t", rendered)
        self.assertIn(b"\\u001b", rendered)
        self.assertIn(b"\\u00ef", rendered)
        self.assertEqual(json.loads(core.render_agenda_changes(result, format="json")), result)
        self.assertEqual(before, raw(value))
        with self.assertRaises(ValueError):
            core.render_agenda_changes(result, format="html")


if __name__ == "__main__":
    unittest.main()
