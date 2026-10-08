# Submission feedback: author qualification

Claim: [CanvasPilot #34](https://github.com/Jacob-Met/canvaspilot/issues/34).
Production commit `a98da7dce9f4839a20a21a6973d7cc7e6fa635a2` has tree
`8abeb42ccb66263841ade748cc33103b4fe4c4fe` and direct parent
`72357053a1629c349f700030013559fa6d8130f2`. The parent contains the received
deadline-summary and course-folder capabilities. All 118 untouched parent files
and all 38 existing `CanvasAPI` methods are preserved. The nine contribution
paths, original blobs, and final hashes are in `source-freeze.json`.

## Product behavior

Students can request the same feedback report through
`CanvasAPI.submission_feedback(course_id, assignment_id)`,
`canvaspilot feedback COURSE ASSIGNMENT`, or the MCP tool
`canvas_submission_feedback`. The existing client makes two Canvas reads:

1. `GET /api/v1/courses/{course_id}/assignments/{assignment_id}`.
2. `GET /api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/self`
   with `include[]=submission_comments&include[]=rubric_assessment`.

The existing client supplies `per_page=50` on both requests. The report joins
rubric assessments only to unique exact string criterion IDs. It preserves
unmatched assessments, zero marks, missing values, advisory/non-scoring rubric
metadata, attempt and grading timestamps, negative grader IDs, and the explicit
`grade_matches_current_submission` flag. Submission comments retain their own
authors, timestamps, media, and attachments. No grade is calculated and no
student/instructor role is inferred from a comment's presence.

Contract sources are the official
[Assignments API](https://developerdocs.instructure.com/services/canvas/resources/assignments)
and [Submissions API](https://developerdocs.instructure.com/services/canvas/resources/submissions).
The report uses the existing request transport and exception behavior.

## Receiving results

The frozen final source passes **217 tests**, including **25 new feedback cases**
(16 semantic fixture cases and 9 actual HTTP/CLI/MCP cases). The inherited folder,
deadline, module, broker, and bundle tests also pass. The complete repository lint
command `ruff check src tests scripts` and `git diff --check` pass.

The new native tests use a disposable `127.0.0.1` HTTP server, a synthetic token,
real `CanvasClient` requests, CLI child processes, and an initialized MCP stdio
session. They check the exact two-GET request shape, changed marks and attempts,
404/403/500 failures, CLI failure output, and MCP tool-error semantics. The
semantic tests cover reordered/duplicate/missing/non-string criterion IDs,
comments without marks, absent versus empty feedback, media-only comments,
advisory rubrics, source-object independence, and malformed collections.

`final-native.xml` retains individual results and `final-native.log` records
`217 passed in 27.57s`. `final-lint.log` records the full lint gate. Root and peer
independent receiving packets are kept separately from this author packet.

## Reproduce

From a checkout containing the contribution, use a Python environment with the
project's declared runtime requirements and its declared `pytest`/`ruff` dev
tools. For example:

```bash
python3 -m venv .venv-feedback
.venv-feedback/bin/python -m pip install -e . 'pytest>=8.0' 'ruff>=0.4'
PYTHONPATH=src .venv-feedback/bin/python -m pytest -q -p no:cacheprovider
.venv-feedback/bin/ruff check src tests scripts
git diff --check
```

The focused receiving command is:

```bash
PYTHONPATH=src .venv-feedback/bin/python -m pytest -q \
  tests/test_submission_feedback.py tests/test_submission_feedback_native.py
```

This run used Python 3.12.14, httpx 0.28.1, MCP 2.3.0, pydantic 2.13.5,
pytest 9.1.1, and Ruff 0.11.4. `runtime.json` records the resolved runtime
closure. No dependency manifest was changed. The local venv references the
existing isolated dependency target through a plain `.pth` file, which lets
inherited child-process tests retain their dependencies when they replace
`PYTHONPATH`. A normal installed venv provides the same import behavior.

## Retained negative evidence and limits

The initial base `5b1780ca4fcdce3d5f997cee401c86806ece822a` failed all three
new-operation entry-point witnesses: missing API method, rejected CLI command,
and missing MCP tool. These original failures are in `baseline-native.log.json` and
`baseline-native.xml.json`.

Two early native harness runs are retained: the first found an inherited SOCKS
proxy dependency in the test environment and MCP SDK Python attribute naming;
the next over-specified the text of an MCP error. The final tests isolate only
their disposable loopback environment and inspect stable MCP wire aliases.
They require the framework's error flag without requiring exception details
that MCP intentionally hides. No production workaround was introduced.

The first full suite run reported 213 passed and 4 inherited folder subprocess
failures because those children replaced `PYTHONPATH` and lost the target-only
dependencies. `inherited-subprocess-setup.log.json` preserves the failures. Running
the unchanged source/tests through the small installed-environment venv
resolved them; the final 217-test result is recorded separately.

Receiving used synthetic data only. No live Canvas account, browser profile,
school permissions, SSO flow, or runtime deployment was exercised. Actual
feedback visibility remains whatever the authenticated Canvas API returns.

Four negative reports use lossless UTF-8 JSON envelopes (`*.log.json` and
`*.xml.json`) because pytest emits trailing spaces in tracebacks. Each envelope
records the original filename, byte count, SHA-256, and complete `text` string;
no original output bytes were normalized. For example, from this directory:

```bash
python -c 'import json; print(json.load(open("baseline-native.log.json"))["text"], end="")'
```
