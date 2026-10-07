"""T164 demo part 2: tests for bundle_coverage_demo (gate should now PASS)."""

from canvaspilot.bundle import bundle_coverage_demo


def test_bundle_coverage_demo_counts():
    result = bundle_coverage_demo(["a", "b", "a"])
    assert result["total"] == 3
    assert result["unique"] == 2
    assert result["counts"] == {"a": 2, "b": 1}


def test_bundle_coverage_demo_empty():
    result = bundle_coverage_demo([])
    assert result == {"total": 0, "unique": 0, "counts": {}}
