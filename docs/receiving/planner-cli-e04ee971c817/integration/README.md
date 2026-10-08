# Current planner CLI integration

This is the current receiving index for the planner CLI contribution. The parent [README](../README.md), original candidate pins and original publication manifest describe the immutable author freeze at `75e5d51f661a9165e1a494b47ef2433001d877ea`. Their dated pending gates and historical source pins are preserved rather than rewritten.

## Current source

The integration base is native `1bafdaa31f7789d8e561680cb6001bbe38b2da64`, tree `fc4c5cee949a3a15caf32111af9144cb7eb95b6d`. It includes the accepted grade-review and module-progress-export contributions. The complete native tree has 1,205 leaves and no AGENTS.md.

| Contribution | Git blob |
| --- | --- |
| `src/canvaspilot/cli.py` | `99247f6d57c4eda52a99e32683ed8d33c56b8d9b` |
| `README.md` | `88f76d780b3437807c570d696c5335cb5cac259f` |
| `tests/test_planner_cli.py` | `e41b4bcfec8103e333a3292776087e8ed84f8848` |
| `docs/planner-cli.md` | `7d1d54d03face5afd51fc4be015ba10a927ad9ef` |

The parser and dispatch blocks are byte-identical to the independently received original planner additions. Removing them recovers the entire native CLI `8d6644d0` exactly. Removing the one README paragraph recovers native `bd0d1624`. The API `3ec81dee`, client, all helpers and bootstrap, native grade-review and progress-export implementation, dependencies and workflow remain from current main.

## Executed phases

Each row is a distinct retained execution. They are not combined into a fabricated full-suite rerun.

| Phase | Actual execution | Result |
| --- | --- | --- |
| Original missing-command baseline | Three actual Python children: help, parser refusal, existing native planner API/client fixture | 11 conditions pass |
| Initial author CLI receiving | Nine actual exact-source children | 58 conditions pass; one `whoami` expectation is wrong |
| Corrected control | One actual child; same product source, corrected native `whoami` wrapper expectation | 10 conditions pass |
| Quiz/file-listing composition | One actual child on compiled current CLI/API | 10 conditions pass |
| Grade-review composition | One actual child on the next compiled native CLI/API | 10 conditions pass |
| Module-progress-export composition | One actual child on final compiled native CLI/API | 10 conditions pass |
| Independent source receiving | Nine actual Python children, including one native parser-refusal baseline | 123 evaluated conditions pass |
| First hosted gate | Declared dependencies install, then new-test Ruff refusal | Test suite skipped |
| Second hosted gate | Declared package/dev dependencies, Ruff, complete pytest | 792 passed, 1 skipped, 57 subtests passed |
| Final current-tree hosted gate | Required on the final publication head | Pending at this evidence commit; see PR #72's final run and merge receipt |

The initial author failure was an incorrect expectation that `whoami` returned a bare profile, rather than the existing `{mode, base_url, profile}` wrapper. The original receiver and failure remain under `../author/`. The first hosted gate only required import ordering and explicit `check=False` in the new test; [ci-1.json](ci-1.json) and its exact decoded log excerpt remain unchanged. No product behavior changed in either correction.

[ci-2.json](ci-2.json) records run 37809390738 and actual checkout `b9b74faff5c9b7db1a946a2bab64d8843c2c9298`. Its tree is exactly `bd6dc1c88a884748cec6a2e0992dfcac364b1895`, the tree of head `1425925f`. This is evidence for that head, before the later native compositions. The final commit's own check is observed before merge and reported in PR #72; this avoids another evidence-only commit restarting the same gate.

## Independent review and current composition

[Independent receiving README](../independent/README.md), [exact raw results](../independent/results.json), [portable driver](../independent/receive_cli.py), [complete replay input](../independent/input.json) and [packet manifest](../independent/manifest.json) preserve the nine-child, 123-condition PASS on original CLI `df01e112` and API `cd17584b`. The independent [grade-review proof](../independent/composition-grade-review.json) and [final module-export proof](../independent/composition-module-export.json) separately verify the later native additions and final `99247f6d` source; they do not relabel the original executed run.

[Grade-review preservation](grade-review-composition.json) and [raw result](grade-review-composition-results.json) retain the first late native composition. [Module-progress-export preservation](module-progress-composition.json) and [raw result](module-progress-composition-results.json) record the final native source. The reusable exact-source receiver is [receive_planner_composition.py](../author/receive_planner_composition.py). It accepts `--native-source`, a CLI file or literal full source, an optional API file or literal full source, the retained fixture, and `--only-case dated`.

The namespace/import-only HTTPX receiver executes full native CLI/API/client/helper source with explicit transport and effect refusal. It does not execute the package bootstrap or installed command. Its `native_support` field records retained on-disk files; `compiled_api_source` identifies the current full API actually compiled into the child. These are intentionally separate. The hosted test module exercises real package imports, HTTPX and native Link pagination against disposable loopback HTTP fixtures.

## Custody and limits

The [final publication manifest](publication-final-manifest.json) lists every other intended contribution and receiving file, with Git blob, SHA-256, length and mode. Its own Git blob is included in the final branch/merge readback. [Text-byte verification](text-pin-verification.json) records the operational raw pin check when the local hash subprocess could not be created; this is separate from the already completed product tests. Publication starts from the complete current native tree and preserves every unrelated leaf and mode. The expected-head merge is read back against its actual first parent, rather than an assumed earlier base.

[Local materialization observation](local-materialization-observation.json) records a later tool call that could not find a previously created `/dev` directory. No complete local Git capsule was created by that attempt, and no cause is asserted. The source and historical evidence were already durable in the original Git commits. This is separate from the earlier capacity refusals recorded before creating any candidate directory.

All planner fixtures, HTTP tokens and returned rows are synthetic. No live Canvas account, school API, course, student record, browser session, provider, installed release or production state was used or changed.
