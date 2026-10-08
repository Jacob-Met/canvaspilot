"""Qualify only the newly explicit normalized-reader markers and projection preservation."""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
import sys
import unittest
import test_independent_receiving_v2 as prior

prior.PACKAGE = prior.ROOT / "candidate-v2"
CORRECTION = "96e4f3d37b4e2e222e30ff34a0bab96bed95b8cd"

class BoundaryMarkerControls(prior.IndependentReceiving):
    def assert_markers_and_unchanged_projection(self, report, before):
        self.assertEqual(report["reader_source"], "CanvasAPI.list_modules(detail=full)")
        self.assertEqual(report["upstream_response_shape"], "not_observed")
        self.assertIsNone(report["collection_complete"])
        reduced = dict(report)
        del reduced["reader_source"]
        del reduced["upstream_response_shape"]
        self.assertEqual(reduced, before)

    def test_cli_module_singleton_has_explicit_boundary_and_same_projection(self):
        original = json.loads((prior.ROOT / "initial-wire-observations.json").read_text())
        observed = next(e for e in original["evidence"] if e.get("surface") == "cli"
                        and e["arguments"] == ["201"])
        before = json.loads(observed["stdout"])
        result = self.cli("201")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_markers_and_unchanged_projection(json.loads(result.stdout), before)

    def test_mcp_item_singleton_has_explicit_boundary_and_same_projection(self):
        original = json.loads((prior.ROOT / "mcp-wire-observations.json").read_text())
        observed = next(e for e in original["evidence"] if e.get("surface") == "mcp"
                        and e["arguments"] == {"course_id": "202"})
        before = json.loads(observed["content"])
        result = asyncio.run(self.mcp_calls([{"course_id": "202"}]))[0]
        self.assertFalse(result["isError"])
        self.assert_markers_and_unchanged_projection(json.loads(result["content"]), before)

if __name__ == "__main__":
    names = [
        "test_cli_module_singleton_has_explicit_boundary_and_same_projection",
        "test_mcp_item_singleton_has_explicit_boundary_and_same_projection",
    ]
    suite = unittest.TestSuite(BoundaryMarkerControls(name) for name in names)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    packet = {"schema": "canvaspilot.independent_boundary_receiving.v1",
              "source_commit": CORRECTION, "tests": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "evidence": prior.EVIDENCE}
    print("CANVAS_REVIEW_JSON=" + json.dumps(packet, ensure_ascii=False))
    sys.exit(not result.wasSuccessful())
