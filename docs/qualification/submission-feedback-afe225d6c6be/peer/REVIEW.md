# Independent receiving: CanvasPilot submission feedback

Accept the reviewed feedback semantics on the immutable source based on
`5b1780ca4fcdce3d5f997cee401c86806ece822a`. Six independent native Python groups
passed. No production patch was needed. This receiver complements the parent's
separate actual API/CLI/MCP interface tests.

The contract and the exact executed program were frozen before the candidate
implementation was read. The reviewer copied seven files from the owner's
immutable snapshot, verified the five supplied production hashes, executed the
challenge once, then inspected the complete source delta. The client and
package initializer are unchanged from the base. Every copied file retained
its pre-execution hash.

## What the challenge established

- All six orders of a rubric containing duplicate IDs preserve the ambiguous
  assessment as unmatched; neither duplicate receives guessed feedback.
- One missing ID and six non-string IDs, including list and object values,
  consume none of eight tempting string-keyed assessments. Seven case,
  whitespace, numeric-string and Unicode variants match only exact strings.
- Seven mutations of returned nested criteria, matched and unmatched
  assessments, rubric settings, comment authors, attachments and media leave
  the original Canvas objects unchanged. Repeated transformation is stable;
  the API method also preserves its fake client's objects.
- Missing or null assessments remain unknown. An empty assessment object and
  an empty comment list remain explicitly empty. Zero scores, an empty grade,
  false current-grade status, negative grader ID and advisory rubric status
  keep their supplied values.
- Authentication, HTTP 503 and read-timeout failures propagate as the exact
  original exception objects at both read stages. An assignment failure makes
  one request; a submission failure makes two. None becomes a successful
  no-feedback result. These six injected failure paths are negative controls.

`semantic-review.json` contains every group and observation. The complete
candidate source manifest and `source-review.diff` bind the reviewed code.
The API method requests the assignment and then the self-submission with the
two requested associations; it does not catch and reinterpret request errors.
The transform counts valid string IDs before joining, keeps unused assessments,
and deep-copies the completed report. No existing client/auth/broker/sync method
was changed in the reviewed delta.

## Reproduction and bounds

Set `PYTHONDONTWRITEBYTECODE=1` and make the declared CanvasPilot dependencies
available on `PYTHONPATH`. Run `python review_feedback_semantics.py --source
<isolated-repository-root> --out <receipt.json>`. This run used Python 3.12.14
and the declared httpx 0.28.1 dependency. All Canvas reads used the deterministic
recording client in the driver; no network, school account or broker was used.

The malformed IDs are defensive test inputs, not claims about ordinary Canvas
responses. `PRIMARY_SOURCES.md` records the official API context. This receipt
does not establish live service access or end-to-end CLI/MCP behavior, and does
not itself qualify the owner's later composition onto main
`72357053a1629c349f700030013559fa6d8130f2`. The unchanged feedback module and
extracted API method can bind these semantic results to that composition;
the parent owns its exact-source interface qualification.
