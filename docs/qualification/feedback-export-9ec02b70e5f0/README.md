# Native feedback export qualification

This packet qualifies an explicit local HTML export in `Jacob-Met/canvaspilot`.
It was composed on main `55fe1e0a3c4ad85e1065f295e49d44722c3be32b`, tree
`7c1bd0a858a3fda82a4d5e69076801ae65a73ea1`. The complete primary tree has 435 blobs
and no `AGENTS.md`. The isolated receiving copy contains all 12 original product
modules and selected native context/tests, not all historical evidence directories.
Its 22 received files were verified against the current Git blob IDs before edits.

The source claim is [issue 34, comment 6059831651](https://github.com/Jacob-Met/canvaspilot/issues/34#issuecomment-6059831651).
GitHub publication and integration belong to the execution lead. This source work
does not claim a native resident-task lease, live school session or deployment.

## Result and boundary

`canvaspilot export-feedback COURSE ASSIGNMENT --out feedback.html` reads the
existing feedback API once and prepares one self-contained UTF-8 HTML sheet.
The user can retain, search or print the sheet without the app running. It renders
returned comments, rubric assessments and the submission's grading/attempt context.
Unknown, explicit empty and zero values remain distinct. The renderer does not
calculate a grade, infer a previous attempt number or repeat criterion joins.

The original API, feedback transformation, client, broker, MCP surface, bundle,
calendar exporter, dependencies and workflow remain exact parent bytes. Removing
the two additive `export-feedback` parser/dispatch blocks reproduces the entire
original CLI byte for byte. Removing the README's one added usage section
reproduces that complete parent file. `ownership-verification.json` records the
checks and the six changed paths. There is no read-status, submission, grading,
attachment fetch, authentication or pagination change.

The [usage guide](../../feedback-export.md) describes the exact sheet projection
and flags. In particular, `hide_points` removes rubric point fields;
`hide_score_total` removes the supplied rubric total without hiding criterion
points; `hide_outcome_results` concerns posting to the Learning Mastery Gradebook.
None reinterprets the separately reported submission grade. Native source and
current primary Canvas documentation establish this distinction.

## Native stages

| Stage | Result | Interpretation |
| --- | --- | --- |
| Exact original feedback reader | 25 passed | Existing fixture, real HTTP, CLI and MCP feedback behavior before this implementation. |
| Original CLI with the new consumer workflow | 1 failed | The real CLI rejects `export-feedback` with exit 2, before any GET or output file; the missing product flow is reproduced. |
| First authored export consumer | 11 passed, 9 failed | The nine failures are the receiver decoding the entire stderr stream as JSON, despite the existing HTTPX diagnostics preceding the final JSON refusal. Exact stdout/stderr and first-source evidence are retained. |
| Qualified source and receiver | 65 passed, zero skipped | 40 new export cases plus the unchanged 25 existing feedback cases. Source hashes were checked before and after this run. |
| Ruff 0.12.12 | Passed | Both changed production modules and both new maintained test files; no cache writes. |

The qualified CLI controls launch **20 real processes**. Seventeen execute the
unchanged native reader's **34 authored loopback GETs**; three refuse an existing
destination before any request. Eight commands produce new HTML sheets. The
ordinary-file refusal control preserves a separate earlier 23-byte file, which
must not be counted as a ninth successful export. The twelve nonzero results
are the intended read, identity, malformed-value and existing-path refusals.

The native consumer parses the actual produced HTML to check canonical fields,
source-provided authors and media-only comments, literal Unicode/markup, separate
display flags, exact zeros, unknown versus empty containers and old-grade context.
It forbids script/resource/form nodes. Separate native API/file tests challenge
duplicate/ambiguous criterion IDs, source immutability, subsecond UTC conversion,
unusable URL activation, missing identities, nested authorship, concurrent
destination creation, private file permissions and pre-publication filesystem
refusals. The whole existing repository test suite was not rerun.

The first formatter predates two deliberate view-completeness additions: it did
not distinguish an absent rubric-settings object from an empty one, and it did
not show a differing nested author name/ID. Its source is recovered exactly by
reversing those two recorded local patches. The first native driver and CLI were
copied unchanged into the archived first-source directory. That first run did not
capture start/end code hashes and is not represented as having done so. The final
65-case run includes both additions and did capture unchanged code hashes.

The receiver correction reads the final JSON error line while preserving all
transport stderr in its receipt. It does not suppress or reconfigure native
logging. The original failing receiver remains available as `.py.source`, which
also prevents pytest from accidentally collecting historical test code.

## Source and runtime

The frozen source map is `candidate-pins.json`. The final formatter's SHA-256 is
`3bc3f44f9d8f682fbf8442fed88e05d6148ecbf889e41c941ce65f067f59904b`;
the CLI is `a29e755832cec76a07178d1afffd245c07b665bc990e8bb99c84cbfdc737bf16`.
`qualified-native-run.json` binds the precise command and source hashes to the
65-case stdout/stderr. `native-source-pins.json` and `primary-source.json` retain
the received baseline and complete Git source catalogue.

No dependencies were installed. Qualification reused the already installed
native dependency directory read-only, with `PYTHONDONTWRITEBYTECODE=1`. The
documented production requirements and project configuration were not changed.
The supplemental runtime receipt records the actual interpreter and dependency
versions, plus the source roots needed to repeat the local command.

From an ordinary checkout with the project's existing development dependencies:

```sh
pytest -q tests/test_feedback_export.py tests/test_feedback_export_native.py \
  tests/test_submission_feedback.py tests/test_submission_feedback_native.py
ruff check src/canvaspilot/feedback_export.py src/canvaspilot/cli.py \
  tests/test_feedback_export.py tests/test_feedback_export_native.py
```

Set `CANVASPILOT_EXPORT_EVIDENCE` to an owned directory to retain each authored
CLI process and request receipt; this affects the test fixture only. The
maintained native driver accepts `CANVASPILOT_TEST_SOURCE` for the before-source
counterexample. The original numeric-NaN response is intentionally malformed
JSON accepted by the existing decoder and refused by the export; its complete
raw fixture receipt is preserved as `.json.source`, without rewriting NaN.

This receiving demonstrates native CLI, HTTP, file and semantic HTML behavior
on synthetic data. No school account, real learner data, browser profile, live
broker or model is used. Browser layout and actual printer output were not run:
the shared environment was within about 5 MiB of its 8 GiB memory ceiling.
Static styling and browser-readable HTML are implemented, but this packet makes
no visual-browser, print-device, live-Canvas or learning-outcome claim. Independent
receiving is a separate source-pinned packet owned by the runtime reviewer.
