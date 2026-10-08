# Independent CanvasPilot rubric brief review

**Accepted for source integration at the exact candidate below. No blocking
finding was reproduced.** This review was executed independently from the
author's tests through the native API, CLI and registered MCP tool dispatcher.
Production source was read-only throughout.

## Source and custody

The current baseline is CanvasPilot commit
`5b1780ca4fcdce3d5f997cee401c86806ece822a`, complete Git tree
`5d3b9b7b8f3cca5f3940f31e020ad4310078dd70`. The reviewer independently
fetched that primary tree and verified all **42 baseline blobs** before
execution. All six candidate file pins were then verified; all **38 unowned
baseline blobs** retain their exact bytes. The complete tree has no AGENTS.md.

| Executed source | SHA-256 |
|---|---|
| Candidate API | `e35290d0899a88cd5fe03178218b2d7e9f8318cb800a09c18180efef33a1150c` |
| Candidate CLI | `3b15ed6c1ec973ed046163837a65bcdad9f60288bb3ea821fe792a11b4bcfec9` |
| Candidate MCP server | `0850fd3d4c06cf7d539dd5a606aed1a8b4e168c6ed2e70c8e617885b4b5810a9` |
| Independent unchanged harness | `0d4f352f81c0c2a39415df9effdf4ffc0318e7f6dd21a6876e459233f28d8a0b` |
| Independent synthetic fixture | `b0185efda8933d88cd209d7162e39bcc5f825421d25f0c790126dac37c11ab08` |

The baseline API Git blob is `5807bd4c7bbe23aaacedfa7281fed3ce94256432`;
candidate API blob is `bcc564bd293966deff85a10164e4daca4daeb935`.
Independent AST comparison confirms that only `CanvasAPI.get_assignment` and
`CanvasAPI.assignment_brief` changed and `_brief_rubric` was added. Every other
API member, including the concurrent module-list implementation, is identical.
The source-verification JSON retains the full mapping. Each individual run
also records all native source hashes before and after; all were unchanged.

## Results

Executed 2026-10-08 10:12:35–10:12:40 UTC, Python 3.12.14, httpx 0.28.1,
mcp 2.3.0 and pydantic 2.13.5. Identical test and fixture bytes ran on both
sources and in both Python modes.

| Source | Normal Python | Optimized Python |
|---|---|---|
| Current unchanged baseline | 3 methods pass; 17 methods fail | 3 methods pass; 17 methods fail |
| Exact candidate | **20 methods pass** | **20 methods pass** |

Every run has zero errors and zero skips. Each baseline run has **111 failure
entries**: 108 surface subtest failures and three direct method failures,
belonging to the 17 failing methods; these are not 111 distinct methods. Both candidate runs have zero failure entries. The baseline
failures retain the missing rubric contract and missing help metadata, while
the three positive controls verify the original brief fields, full assignment
fields and integer requested-ID behavior.

Each run captures **111 public invocations, 37 per API/CLI/registered-MCP
surface**, with the input digest, exact GET request and complete public output.
Additional direct aliasing and repeated-MCP assertions are outside that capture
count. Complete unabridged failure logs and all public outputs are retained.

## Receiving cases

- Original title, due time, assignment points, submission types, identifiers,
  URL query/fragment, and independently expected cleaned body remain exact.
  Escaped `<lab>` text survives body cleanup; rubric HTML/entities remain literal.
- Criteria and unsorted rating levels preserve order, zero/fractional points,
  IDs, nullable descriptions and missing fields. No IDs, scores or requirements
  are inferred. Outcome IDs, vendor GUID, ranges and non-scoring flags survive.
- Advisory and grading rubrics remain distinct. `hide_score_total` and
  `hide_points` remain independent; raw point data and supplied metadata are
  preserved. The rubric total does not replace the assignment's point total.
- Missing/null rubric data remains unavailable; an empty rubric remains an
  available empty list. Nullable ratings and sparse records remain sparse.
- Malformed optional containers, criterion/rating rows and typed canonical
  fields retain the ordinary brief and healthy neighbors. Diagnostics identify
  the original paths; all unusable criteria yield an explicitly diagnosed empty
  result. Boolean/string/nonfinite point values do not leak into public points.
- Grading flags reject truthiness coercion. The complete supplied settings
  object, including nested unknown metadata, survives without reinterpretation.
  Mutating a returned brief does not mutate that supplied object or ratings.
- The real CLI emits the same JSON contract. The registered MCP dispatcher
  returns its real text envelope, rereads changed fixture data on later calls,
  and exposes rubric information in its registered description. CLI help also
  advertises the supplied rubric.

## Primary contract

The review used the official [Assignments API documentation](https://developerdocs.instructure.com/services/canvas/resources/assignments)
and [Rubrics API documentation](https://developerdocs.instructure.com/services/canvas/resources/rubrics),
plus Canvas's [assignment serializer pinned at `1c9f0bb8`](https://github.com/instructure/canvas-lms/blob/1c9f0bb8013ed69c4f2efe11fd483025469b7e6c/lib/api/v1/assignment.rb),
Git blob `ba97b808ca7215d5f2714459ddf5e3477e75e31b`. These sources establish
that a rubric can be advisory, ratings/descriptions can be nullable, and grading
use, point visibility, scoring flags and outcome metadata are separate values.
This review therefore checks supplied JSON custody and diagnostics; it does
not infer a grade or require a separate visual rubric renderer.

## Replay and limits

Install the repository's declared dependencies in a suitable environment, then
run the unchanged portable harness with its adjacent fixture:

```sh
python -B test_independent_rubric_brief.py --source /absolute/qualified/checkout --output /absolute/new/result
python -B -O test_independent_rubric_brief.py --source /absolute/qualified/checkout --output /absolute/new/optimized-result
```

The output directory must be new. `review-runs.json` preserves the exact original
commands and return codes; `run_review.py` preserves this session's source checks
and orchestration with its original local paths. `primary-tree.json` and
`independent-source-verification.json` bind the original receiving source.

The native `CanvasClient` fixture transport is the only injected backend. API
projection, CLI dispatch/rendering and registered MCP dispatch are real. The
captured public calls also forbid HTTP-client and broker construction, so this
is an offline source-integration review. It does not demonstrate a live Canvas
session, SSO, server-side visibility enforcement or an end-user task outcome.
The author's separately retained full-suite results and earlier disk-full
attempts remain separate observations; this review does not relabel them.
