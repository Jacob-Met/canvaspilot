"""Diff-coverage gate for canvaspilot CI (T164).

Runs diff-cover on the coverage.xml produced by pytest --cov, comparing the
PR's diff against origin/main, and enforces the per-file baseline table
committed at the repo root (.diff-cover-baseline.json).

Semantics of the baseline table:
  - "default_fail_under": overall diff-coverage percent required for the PR.
  - "files": {path: percent_covered} — the per-file TOTAL coverage recorded
    when the baseline was generated from the baseline_commit. A touched file
    whose DIFF coverage falls below its baseline entry is flagged, so files
    cannot regress below their historical coverage level.
A baseline mismatch never rewrites the baseline; regeneration is a human
decision recorded in the commit that updates .diff-cover-baseline.json.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default=".diff-cover-baseline.json")
    ap.add_argument("--compare-branch", default="origin/main")
    args = ap.parse_args()

    with open(args.baseline) as fh:
        baseline = json.load(fh)
    default_fail_under = baseline.get("default_fail_under", 80)
    file_baselines: dict[str, float] = baseline.get("files", {})

    report_path = "diff-cover-report.json"
    dc = run([
        "diff-cover", "coverage.xml",
        f"--compare-branch={args.compare_branch}",
        f"--fail-under={default_fail_under}",
        f"--json-report={report_path}",
    ])
    print(dc.stdout)
    print(dc.stderr, file=sys.stderr)

    failures: list[str] = []
    if dc.returncode != 0:
        failures.append(
            f"overall diff coverage below {default_fail_under}% "
            f"(diff-cover exit {dc.returncode})"
        )

    # Per-file check against the committed baseline table. diff-cover's JSON
    # report shape (diff-cover >= 6): {"src_stats": {path: {"percent": n}}}.
    # Parse tolerantly — a missing per-file table never silently passes.
    per_file: dict[str, float] = {}
    try:
        with open(report_path) as fh:
            report = json.load(fh)
        stats = report.get("src_stats", {})
        for path, st in stats.items():
            if isinstance(st, dict) and "percent" in st:
                per_file[path] = float(st["percent"])
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"could not parse {report_path}: {exc}")

    if not file_baselines:
        failures.append("baseline table has no per-file entries")

    for path, pct in per_file.items():
        floor = file_baselines.get(path, default_fail_under)
        if pct < floor:
            failures.append(
                f"{path}: diff coverage {pct:.1f}% below baseline floor {floor:.1f}%"
            )

    if failures:
        print("DIFF-COVER GATE FAILED")
        for f in failures:
            print("  -", f)
        return 1
    print("DIFF-COVER GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
