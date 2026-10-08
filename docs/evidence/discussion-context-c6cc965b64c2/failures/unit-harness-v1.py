"""Authored reader tests use only synthetic Canvas discussion data."""
from __future__ import annotations
import asyncio
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.discussion_thread import build_discussion_thread


def fixture():
    topic = {"id": 7, "title": "Synthetic river planning", "message": "<p>Compare A &amp; B.</p>",
             "discussion_subentry_count": 99, "read_state": "unread", "user_can_see_posts": True,
             "attachments": [{"filename": "synthetic.txt", "url": "https://synthetic.example/file"}]}
    view = {"participants": [{"id": 9, "display_name": "Fixture reader α"},
                             {"id": 10, "display_name": "Fixture reader β"}],
            "unread_entries": [3, 5, 404], "forced_entries": [3],
            "entry_ratings": {"3": 1}, "server_extra": {"retained": True},
            "view": [
                {"id": 1, "user_id": 9, "parent_id": None, "message": "<p>Outer &lt;topic&gt;.</p>",
                 "replies": [
                     {"id": 2, "user_id": 10, "parent_id": 1, "message": "<p>Middle.</p>",
                      "replies": [{"id": 3, "user_id": 9, "parent_id": 2,
                                   "message": "<p>Unread answer.</p>", "opaque": {"x": 1}}]},
                     {"id": 4, "user_id": 10, "parent_id": 1, "message": "<p>Read sibling.</p>"}]},
                {"id": 5, "user_id": 10, "parent_id": None, "message": "<p>Unread root.</p>", "replies": []},
                {"id": 6, "user_id": 9, "parent_id": None, "message": "<p>Read root.</p>"}]}
    return topic, view


class DiscussionThreadTests(unittest.TestCase):
    def test_all_entries_keep_original_fields_order_and_exact_tree_reconstruction(self):
        topic, view = fixture()
        result = build_discussion_thread(topic, view)
        self.assertEqual([r["entry"]["id"] for r in result["entries"]], [1, 2, 3, 4, 5, 6])
        self.assertEqual(result["topic"], topic)
        self.assertEqual(result["topic_message_text"], "Compare A & B.")
        self.assertEqual(result["view_metadata"], {k: v for k, v in view.items() if k != "view"})
        reconstructed = []
        by_path = {}
        for row in result["entries"]:
            path = tuple(row["path"])
            entry = deepcopy(row["entry"])
            if row["replies_supplied"]:
                entry["replies"] = []
            by_path[path] = entry
            if row["parent_path"] is None:
                reconstructed.append(entry)
            else:
                by_path[tuple(row["parent_path"])]["replies"].append(entry)
        self.assertEqual(reconstructed, view["view"])
        self.assertEqual(result["counts"]["observed_entries"], 6)
        self.assertEqual(result["topic"]["discussion_subentry_count"], 99)
        self.assertEqual(result["source"], {"kind": "canvas_cached_discussion_view",
                                           "eventually_consistent": True,
                                           "new_entries_requested": False})

    def test_unread_focus_keeps_each_ancestor_once_in_source_order(self):
        result = build_discussion_thread(*fixture(), unread_only=True)
        self.assertEqual([r["entry"]["id"] for r in result["entries"]], [1, 2, 3, 5])
        self.assertEqual([r["context_only"] for r in result["entries"]], [True, True, False, False])
        self.assertEqual([r["path"] for r in result["entries"]], [[0], [0, 0], [0, 0, 0], [1]])
        self.assertEqual(result["counts"], {"observed_entries": 6, "returned_entries": 4,
                                          "known_unread_entries": 2, "unknown_read_state_entries": 0})
        self.assertEqual(result["unmatched_unread_entries"], [404])

    def test_read_and_forced_markers_use_separate_supplied_facts(self):
        result = build_discussion_thread(*fixture())
        rows = {r["entry"]["id"]: r for r in result["entries"]}
        self.assertEqual(rows[3]["read_state"], "unread")
        self.assertIs(rows[3]["forced_read_state"], True)
        self.assertEqual(rows[5]["read_state"], "unread")
        self.assertIs(rows[5]["forced_read_state"], False)
        self.assertEqual(rows[1]["message_text"], "Outer <topic>.")
        self.assertEqual(rows[3]["author"]["display_name"], "Fixture reader α")

    def test_empty_read_marker_list_is_distinct_from_missing_or_null(self):
        for empty_tree in (False, True):
            for value in ("missing", None, []):
                with self.subTest(empty_tree=empty_tree, value=value):
                    topic, view = fixture()
                    if empty_tree:
                        view["view"] = []
                    if value == "missing":
                        del view["unread_entries"]
                    else:
                        view["unread_entries"] = value
                    result = build_discussion_thread(topic, view)
                    if value == []:
                        self.assertEqual(result["counts"]["known_unread_entries"], 0)
                        self.assertEqual(build_discussion_thread(topic, view, unread_only=True)["entries"], [])
                    else:
                        self.assertIsNone(result["counts"]["known_unread_entries"])
                        self.assertTrue(all(r["read_state"] == "unknown" for r in result["entries"]))
                        with self.assertRaisesRegex(ValueError, "did not supply unread_entries"):
                            build_discussion_thread(topic, view, unread_only=True)

    def test_missing_and_ambiguous_authors_are_not_invented(self):
        topic, view = fixture()
        view["participants"].append({"id": 9, "display_name": "Different fixture author"})
        view["view"][0]["replies"][0]["user_id"] = 12345
        result = build_discussion_thread(topic, view)
        rows = {r["entry"]["id"]: r for r in result["entries"]}
        self.assertIsNone(rows[1]["author"])
        self.assertIsNone(rows[2]["author"])
        self.assertEqual(rows[5]["author"], view["participants"][1])
        self.assertEqual(result["view_metadata"]["participants"], view["participants"])

    def test_deleted_and_media_only_entries_remain_present_without_invented_body(self):
        topic, view = fixture()
        view["view"][0]["replies"][0] = {"id": 2, "deleted": True, "replies": [
            {"id": 3, "user_id": 10, "parent_id": 2, "attachment": {"filename": "synthetic.wav"}}]}
        result = build_discussion_thread(topic, view, unread_only=True)
        rows = {r["entry"]["id"]: r for r in result["entries"]}
        self.assertIsNone(rows[2]["message_text"])
        self.assertTrue(rows[2]["context_only"])
        self.assertIsNone(rows[3]["message_text"])
        self.assertEqual(rows[3]["entry"]["attachment"], {"filename": "synthetic.wav"})

    def test_identifier_types_remain_distinct_and_boolean_ids_are_unknown(self):
        topic = {"id": 7}
        view = {"participants": [{"id": 1, "display_name": "Integer"}, {"id": "1", "display_name": "String"}],
                "unread_entries": ["1"], "view": [{"id": 1, "user_id": 1},
                                                    {"id": "1", "user_id": "1"}, {"id": True}]}
        result = build_discussion_thread(topic, view)
        self.assertEqual([r["read_state"] for r in result["entries"]], ["read", "unread", "unknown"])
        self.assertEqual([r["author"]["display_name"] for r in result["entries"][:2]], ["Integer", "String"])
        focused = build_discussion_thread(topic, view, unread_only=True)
        self.assertEqual([r["entry"]["id"] for r in focused["entries"]], ["1"])

    def test_duplicate_entry_ids_keep_occurrences_but_refuse_ambiguous_unread_focus(self):
        topic, view = fixture()
        view["view"][2]["id"] = 3
        result = build_discussion_thread(topic, view)
        self.assertEqual(len(result["entries"]), 6)
        self.assertEqual([r["read_state"] for r in result["entries"] if r["entry"]["id"] == 3],
                         ["unknown", "unknown"])
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            build_discussion_thread(topic, view, unread_only=True)

    def test_original_parent_ids_do_not_reparent_the_returned_tree(self):
        topic, view = fixture()
        view["view"][0]["replies"][0]["parent_id"] = 999
        result = build_discussion_thread(topic, view, unread_only=True)
        row = result["entries"][1]
        self.assertEqual(row["entry"]["parent_id"], 999)
        self.assertEqual(row["parent_path"], [0])
        self.assertEqual(row["path"], [0, 0])

    def test_original_and_returned_data_are_independently_mutable(self):
        topic, view = fixture()
        before = deepcopy((topic, view))
        result = build_discussion_thread(topic, view)
        self.assertEqual((topic, view), before)
        result["topic"]["attachments"][0]["filename"] = "edited"
        result["entries"][2]["entry"]["opaque"]["x"] = 12
        result["entries"][2]["author"]["display_name"] = "edited"
        result["view_metadata"]["server_extra"]["retained"] = False
        self.assertEqual((topic, view), before)

    def test_new_entry_stream_and_unknown_metadata_are_retained_without_merging(self):
        topic, view = fixture()
        view["new_entries"] = [{"id": 3, "message": "Newer, separate version"}]
        result = build_discussion_thread(topic, view)
        self.assertEqual(result["view_metadata"]["new_entries"], view["new_entries"])
        self.assertEqual(result["entries"][2]["entry"]["message"], "<p>Unread answer.</p>")
        self.assertEqual(result["counts"]["observed_entries"], 6)

    def test_malformed_containers_refuse_instead_of_becoming_empty(self):
        cases = [
            (None, {}), ({}, []), ({}, {}), ({}, {"view": None}),
            ({}, {"view": [None]}), ({}, {"view": [{"id": 1, "replies": None}]}),
            ({}, {"view": [], "participants": {}}),
            ({}, {"view": [], "participants": [None]}),
            ({}, {"view": [], "unread_entries": {}}),
            ({}, {"view": [], "unread_entries": [True]}),
            ({}, {"view": [], "forced_entries": [None]}),
        ]
        for topic, view in cases:
            with self.subTest(topic=topic, view=view), self.assertRaises(ValueError):
                build_discussion_thread(topic, view)

    def test_cyclic_tree_refuses_and_deep_flat_output_keeps_paths(self):
        root = {"id": 0, "replies": []}
        root["replies"].append(root)
        with self.assertRaisesRegex(ValueError, "cyclic"):
            build_discussion_thread({}, {"view": [root]})
        root = {"id": 0}
        cursor = root
        for ident in range(1, 130):
            child = {"id": ident}
            cursor["replies"] = [child]
            cursor = child
        result = build_discussion_thread({}, {"view": [root], "unread_entries": [129]}, unread_only=True)
        self.assertEqual(len(result["entries"]), 130)
        self.assertEqual(result["entries"][-1]["path"], [0] * 130)
        self.assertFalse(result["entries"][-1]["context_only"])
        json.dumps(result)

    def test_api_validates_before_requests_and_preserves_original_raw_reader(self):
        topic, view = fixture()
        routes = {"GET /api/v1/courses/42/discussion_topics/7": topic,
                  "GET /api/v1/courses/42/discussion_topics/7/view": view}
        client = CanvasClient(fixture={"routes": routes}, token="", base_url="https://synthetic.example")
        api = CanvasAPI(client)
        with patch.object(client, "request", wraps=client.request) as calls:
            expected = build_discussion_thread(topic, view, unread_only=True)
            self.assertEqual(api.discussion_thread("42", "7", unread_only=True), expected)
            self.assertEqual(calls.call_args_list[0].args, ("GET", "/api/v1/courses/42/discussion_topics/7"))
            self.assertEqual(calls.call_args_list[1].args, ("GET", "/api/v1/courses/42/discussion_topics/7/view"))
            self.assertEqual(calls.call_count, 2)
            for bad in ("../7", "7?read=true", " 7", "", "0", 0, -1, True, 1.5, None, "١"):
                with self.subTest(bad=bad):
                    calls.reset_mock()
                    with self.assertRaises(ValueError):
                        api.discussion_thread(bad, 7)
                    calls.assert_not_called()
            for bad in (0, 1, "false", None):
                calls.reset_mock()
                with self.assertRaises(ValueError):
                    api.discussion_thread(42, 7, unread_only=bad)
                calls.assert_not_called()
            self.assertEqual(api.get_discussion(42, 7), {"topic": topic, "view": view})
        api.close()

    def test_registered_mcp_wrapper_calls_the_same_method_and_is_read_only(self):
        from canvaspilot import mcp_server
        from canvaspilot.bundle import tool_inventory
        topic, view = fixture()
        api = CanvasAPI(CanvasClient(fixture={"routes": {
            "GET /api/v1/courses/42/discussion_topics/7": topic,
            "GET /api/v1/courses/42/discussion_topics/7/view": view}}, token=""))
        with patch.object(mcp_server, "_api", api):
            returned = asyncio.run(mcp_server.canvas_discussion_thread("42", "7", unread_only=True))
        self.assertEqual(json.loads(returned), build_discussion_thread(topic, view, unread_only=True))
        self.assertIn("canvas_discussion_thread", tool_inventory()["curated"])
        tool = mcp_server.mcp._tool_manager.get_tool("canvas_discussion_thread")
        self.assertTrue(tool.annotations.readOnlyHint)
        self.assertFalse(tool.annotations.destructiveHint)
        api.close()


if __name__ == "__main__":
    unittest.main()
