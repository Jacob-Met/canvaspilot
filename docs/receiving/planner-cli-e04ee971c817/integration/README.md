# Current planner CLI integration

This is the current receiving index for the planner CLI contribution. The parent [README](../README.md), original candidate pins and original publication manifest describe the immutable author freeze at `75e5d51f661a9165e1a494b47ef2433001d877ea`. Their dated pending gates and historical source pins are preserved rather than rewritten.

## Current source

The integration base is native `543a81ef22cdb6996a83233e86c7fd887e0f977b`, tree `1efaf4d3fe14cb24cfe9f41d0fc7ff8ba1b4a821`. It includes the accepted grade-review, module-progress-export, page-export and grade-review-export contributions. The complete native tree has 1,382 leaves and no AGENTS.md.

| Contribution | Git blob |
| --- | --- |
| `src/canvaspilot/cli.py` | `14d7edde66a0c1979bf79d9544d075b65c98d1f4` |
| `README.md` | `21b50a527973946bd77e3e883b4366798a922309` |
| `tests/test_planner_cli.py` | `e41b4bcfec8103e333a3292776087e8ed84f8848` |
| `docs/planner-cli.md` | `7d1d54d03face5afd51fc4be015ba10a927ad9ef` |

The parser and dispatch blocks are byte-identical to the independently received original planner additions. Removing them recovers the entire native CLI `1206ba8d` exactly. Removing the one README paragraph recovers native `07d4e993`. The API `3ec81dee`, client, all helpers and bootstrap, native grade-review, progress-export, page-export and grade-review-export implementation, dependencies and workflow remain from current main.

## Executed phases

Each row is a distinct retained execution. They are not combined into a fabricated full-suite rerun.

| Phase | Actual execution | Result |
| --- | --- | --- |
| Original missing-command baseline | Three actual Python children: help, parser refusal, existing native planner API/client fixture | 11 conditions pass |
| Initial author CLI receiving | Nine actual exact-source children | 58 conditions pass; one `whoami` expectation is wrong |
| Corrected control | One actual child; same product source, corrected native `whoami` wrapper expectation | 10 conditions pass |
| Quiz/file-listing composition | One actual child on compiled current CLI/API | 10 conditions pass |
| Grade-review composition | One actual child on the next compiled native CLI/API | 10 conditions pass |
| Module-progress-export composition | One actual child on that compiled native CLI/API | 10 conditions pass |
| Independent source receiving | Nine actual Python children, including one native parser-refusal baseline | 123 evaluated conditions pass |
| First hosted gate | Declared dependencies install, then new-test Ruff refusal | Test suite skipped |
| Second hosted gate | Declared package/dev dependencies, Ruff, complete pytest | 792 passed, 1 skipped, 57 subtests passed |
| Third hosted gate on native module-export composition | Declared package/dev dependencies, Ruff, complete pytest | 871 passed, 1 skipped, 57 subtests passed |
| Page-export composition | Author exact-byte comparison and independent parent exact-byte review | All native and prior planner bytes preserved; no new local child run |
| Grade-review-export composition | Exact native additions and original planner removal | Complete current native bytes preserved; no new local child run |
| Final current-tree hosted gate | Required on the final publication head | Pending at this evidence commit; see PR #72's final run and merge receipt |

The initial author failure was an incorrect expectation that `whoami` returned a bare profile, rather than the existing `{mode, base_url, profile}` wrapper. The original receiver and failure remain under `../author/`. The first hosted gate only required import ordering and explicit `check=False` in the new test; [ci-1.json](ci-1.json) and its exact decoded log excerpt remain unchanged. No product behavior changed in either correction.

[ci-2.json](ci-2.json) records run 37809390738 and actual checkout `b9b74faff5c9b7db1a946a2bab64d8843c2c9298`. Its tree is exactly `bd6dc1c88a884748cec6a2e0992dfcac364b1895`, the tree of head `1425925f`. This is evidence for that head, before the later native compositions. [ci-3.json](ci-3.json) separately records run 37816905848, **871 passed, 1 skipped, 57 subtests passed**, and actual checkout `5381afe3fc83581923b2e9350bbd6741a3a88de9`, whose tree exactly equals head `16ddd61e`. Main then accepted page export and grade-review export, so the final commit's own check is observed before merge and reported in PR #72; this avoids another evidence-only commit restarting the same gate.

## Independent review and current composition

[Independent receiving README](../independent/README.md), [exact raw results](../independent/results.json), [portable driver](../independent/receive_cli.py), [complete replay input](../independent/input.json) and [packet manifest](../independent/manifest.json) preserve the nine-child, 123-condition PASS on original CLI `df01e112` and API `cd17584b`. The independent [grade-review proof](../independent/composition-grade-review.json) and [module-export proof](../independent/composition-module-export.json) separately verify the later native additions and then-current `99247f6d` source; they do not relabel the original executed run.

[Grade-review preservation](grade-review-composition.json) and [raw result](grade-review-composition-results.json) retain the first late native composition. [Module-progress-export preservation](module-progress-composition.json) and [raw result](module-progress-composition-results.json) record that native source. [Page-export composition](page-export-composition.json) records the last additive native change and the separate parent byte-only review at 2026-10-08T17:51:19Z. Removing only the new page-export spans from composed `24ef2d4a` recovers previously received `99247f6d`; removing our planner spans recovers complete current native `0e1a04c3`. API `3ec81dee` is unchanged. The original reverse-check extractor omitted a leading blank line; its four false byte comparisons are retained in this proof, followed by the corrected exact-span result on unchanged candidate source. [Grade-review-export composition](grade-export-composition.json) records the subsequently accepted PR #79. Removing the same original planner spans from final `14d7edde` recovers current native `1206ba8d`; removing PR #79's additions recovers page-composed `24ef2d4a`. All other current native files and modes are preserved in the complete tree. The reusable exact-source receiver is [receive_planner_composition.py](../author/receive_planner_composition.py). It accepts `--native-source`, a CLI file or literal full source, an optional API file or literal full source, the retained fixture, and `--only-case dated`.

The namespace/import-only HTTPX receiver executes full native CLI/API/client/helper source with explicit transport and effect refusal. It does not execute the package bootstrap or installed command. Its `native_support` field records retained on-disk files; `compiled_api_source` identifies the current full API actually compiled into the child. These are intentionally separate. The hosted test module exercises real package imports, HTTPX and native Link pagination against disposable loopback HTTP fixtures.

## Custody and limits

The [current publication manifest](publication-grade-export-manifest.json) lists every other intended contribution and receiving file, with Git blob, SHA-256, length and mode. Its own Git blob is included in the final branch/merge readback. The previous [48-path manifest](publication-final-manifest.json) remains exact historical evidence for head `16ddd61e`. [Text-byte verification](text-pin-verification.json) records the operational raw pin check when the local hash subprocess could not be created; this is separate from the already completed product tests. Publication starts from the complete current native tree and preserves every unrelated leaf and mode. The expected-head merge is read back against its actual first parent, rather than an assumed earlier base.

[Local materialization observation](local-materialization-observation.json) records a later tool call that could not find a previously created `/dev` directory. No complete local Git capsule was created by that attempt, and no cause is asserted. The source and historical evidence were already durable in the original Git commits. This is separate from the earlier capacity refusals recorded before creating any candidate directory.

All planner fixtures, HTTP tokens and returned rows are synthetic. No live Canvas account, school API, course, student record, browser session, provider, installed release or production state was used or changed.
