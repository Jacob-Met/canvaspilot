# HTML parser compatibility correction

This test-only follow-up preserves the syllabus packet's production bytes from PR #80 head `60986834820abbe6b5a51b4d2cc6b6b80559409a`.

The original hosted job [113457378013](https://github.com/Jacob-Met/canvaspilot/actions/runs/37819733999/job/113457378013) checked out synthetic merge `dd93da752adce9a77619c1f8cd2179fb360f887b`. On Python 3.12.15, Ruff passed and pytest reported **1 failed, 1,026 passed, 1 skipped, 54 subtests passed**. The sole failure was an assumption that every supported HTMLParser rejects `<![unrecognized]>`. The [original log](original-hosted-job.log) is retained unchanged.

Official CPython 3.12.8 dispatches this declaration to its marked-section parser and raises AssertionError for the unknown status. CPython 3.12.15 instead tolerates and ignores the declaration. The product already handles parser AssertionError as a whole-packet ValueError; its guide permits malformed HTML to project differently. No product refusal was added to force an older parser behavior.

The [test-only diff](test-only.diff) replaces the runtime assumption with two strict regressions:

1. An injected parser AssertionError on the second course must become the exact Course 43 ValueError, preserve its cause and retain ordered course reads.
2. The original malformed source is calibrated against the actual standard parser. A rejecting parser must produce the handled refusal. A tolerant parser must produce the exact visible reading, no live declaration or active elements, supplied status and an exact UTF-8 source download.

The [compatibility receipt](receipt.json) records six passing maintained assertion-body executions: both regressions under ambient Python 3.12.14, and the same interpreter with the version-pinned 3.12.8 and 3.12.15 parser modules. Seven deliberately introduced defects were detected, covering removed exception handling, changed reading projection and changed source download. The old test passes under the old parser and fails under both tolerant profiles, reproducing the relevant hosted discrepancy.

These checks used an explicitly bounded standard-library adapter for the selected test bodies' raises and monkeypatch semantics. They are **not a pytest run** and **not executions of two additional Python interpreters**. Only the pinned html.parser and _markupbase sources were substituted; other standard-library code remained local. No package or browser was installed. Exact hosted CI for the corrected PR is the next integration gate.

The [complete compatibility archive](compatibility-evidence.tar.gz) contains the baseline and corrected test files, unchanged product module, actual assertion-body runner, all raw profile outputs, original failed CI log, precise diff, source pins and official parser inputs with their licenses. The [archive manifest](manifest.json) records every member. The original native Mac receiving and the earlier author/independent archives remain unchanged and keep their original attribution.

Primary source inputs:

- [CPython v3.12.8 html.parser](https://github.com/python/cpython/blob/v3.12.8/Lib/html/parser.py)
- [CPython v3.12.15 html.parser](https://github.com/python/cpython/blob/v3.12.15/Lib/html/parser.py)
- [CPython v3.12.8 _markupbase](https://github.com/python/cpython/blob/v3.12.8/Lib/_markupbase.py)
- [CPython v3.12.15 _markupbase](https://github.com/python/cpython/blob/v3.12.15/Lib/_markupbase.py)

The two _markupbase bodies were read independently and match exactly. The archive preserves the original execution runner, whose recorded parser directory points to the root review's read-only inputs; the same exact input bodies are included under `inputs/`. Archive paths and receipts describe the actual execution and do not claim an automatic replay on another host.
