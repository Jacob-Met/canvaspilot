# Canvas discussion reading qualification

This contribution adds a terminal and curated MCP reader for one discussion, with an optional unread selection that retains its ancestor context. It is coordinated in [issue 52](https://github.com/Jacob-Met/canvaspilot/issues/52). The original raw discussion API already works; the baseline witness records that positive control and the absence of the new terminal command. No raw-reader failure is invented.

## Frozen source and current composition

The first qualified parent was `79a2f2b2cbb7e74128d731cf096c7e86f1942d4b`. The final author composition uses current parent `39d835c8becb04d81b65c90d1491d2d3a2727ffe`, whose canonical tree is `53b67d3f06b4c780e508325ec42b2b435ec57e97`. The prospective product-only tree is `5be45a6d8625f3d6331ed0f3d4222467eaf8af7b`. These are source and tree pins; this author snapshot does not claim that a branch has already been published.

There are nine product/test/documentation paths: the new pure reader module, one API method, one CLI command, one MCP wrapper, one catalog entry, two test modules, README guidance and the discussion guide. The existing package manifest and CI workflow are unchanged.

Main advanced while the author checks ran. The current composition retains the owner's assignment-submission metadata and submission-history additions. The reader module, its two new API/MCP function bodies, its tests and its guide are unchanged from the first qualified source. The README tool count increases from the current owner's 37 to 38. The existing 46 API functions and 40 MCP functions are preserved; all 55 current base source/test/configuration inputs are bound in `source-binding.json`. All 59 executed candidate files stayed identical before and after qualification.

The full current nine-path diff is `composition/current39d-product.patch`; the shorter runtime diff is `composition/current39d-runtime.patch`. `composition/current39d-source.json` records each allowed insertion/import change and the original-function comparison. `composition/current-main-leaves.json` and `composition/current39d-overlay.json` bind the complete current tree, including all 734 unowned original leaves.

## Reader contract

The entry points are:

```bash
canvaspilot discussion COURSE_ID TOPIC_ID
canvaspilot discussion COURSE_ID TOPIC_ID --unread-only
```

The corresponding API is `CanvasAPI.discussion_thread(course_id, topic_id, unread_only=False)`; the MCP tool is `canvas_discussion_thread` with a strict JSON boolean flag. Route IDs are validated before dispatch. The API calls the unchanged raw `get_discussion()` operation and derives the report locally.

The report keeps original topic fields and original entry fields beside cleaned text and derived associations. Structural position paths, parent paths, direct reply counts and the distinction between missing and explicitly empty replies retain the returned tree structure. Original `parent_id` values are not used to move entries between branches.

Unread focus selects uniquely identified unread entries and every ancestor needed to understand them. Other read branches are omitted; source order is retained. Missing read markers remain unknown. An explicitly empty unread list is a valid empty selection; absent or null unread markers refuse unread focus. Repeated matching IDs refuse an ambiguous unread selection, while the full reader retains every occurrence. Numeric and string identities are distinct. Duplicate participant IDs do not establish authorship. Deleted entries remain as context without invented text or attribution.

Unlocated unread IDs, original view metadata, and any separately supplied new-entry data remain inspectable. No separate new-entry stream is requested or merged. Source topic counts are not forced to agree with observed tree counts. See the [discussion guide](../../DISCUSSIONS.md) and the official [cached-view contract](https://developerdocs.instructure.com/services/canvas/resources/discussion_topics#method.discussion_topics_api.view); `primary-contract.json` distinguishes the documented server fields from this reader's ambiguity policy.

Errors do not become empty successful reports. CLI failures have a nonzero exit, no success stdout and a semantic JSON error on stderr. Existing HTTPX request logging may precede that diagnostic and is retained. MCP failures are tool errors. The new reader adds no Canvas write operation or automatic replay. A configured session broker may carry the existing Canvas GETs in its own outer transport envelope; it is not a Canvas discussion mutation.

## Author qualification

| Source/run | Observed result | Meaning |
| --- | --- | --- |
| Original raw API/CLI witness | Raw topic and three-entry tree returned through the existing two operations; new command exits 2 | An additive workflow gap, with a working raw API positive control |
| Unchanged original full suite | 536 passed, 1 skipped, 6 subtests passed | Existing baseline before the contribution |
| First pure authored run | 14 passed, one test-harness error | The installed MCP Python model uses snake-case attributes; wire aliases were already correct |
| Corrected pure authored run | 15 groups passed | Test inspected the actual wire aliases; product annotation was unchanged |
| First full candidate attempt | 550 passed, 15 failures, 1 skipped, 38 subtests passed | Eight authored stderr assumptions and seven owner temporary-file ENOSPC failures; available truncated tool output retained |
| Second full capture attempt | Unqualified | The launcher lost its result when its assumed /dev evidence directory did not persist between exec invocations |
| Final first-parent gate | 558 passed, 1 skipped, 45 subtests passed; Ruff passed | Complete immutable receipt `author/native-gate-v3.json` |
| Current39d gate | 658 passed, 1 skipped, 45 subtests passed; Ruff passed | Complete immutable receipt `composition/native-current39d-v1.json` |

The one final skip is explicit: the existing browser test requires `CANVASPILOT_CHROMIUM_BIN`. No browser result is inferred from that skip.

The new suite has 15 pure/API/wrapper groups and seven actual process groups. The current native records contain 15 CLI invocations and 5 MCP tool calls. Their local HTTP fixtures exercise all-entry and unread views, changed read markers, invalid route/flag admission, malformed responses, and 403/404/503 refusals. The MCP checks use the actual stdio protocol and SDK, including the boolean schema and read-only/destructive wire annotations. CLI stdout/stderr and MCP response objects are retained. The fixture request lists are reset between some subcases; each subcase asserts its own exact request pair before reset. They are not presented as a packet capture of an external service.

The pure tests cover reply reconstruction, source order, ancestors, forced/read facts, missing and empty markers, typed and duplicate IDs, deleted/media-only entries, conflicting parent IDs, copy independence, a separate new-entry stream, malformed containers and iterative deep traversal. Existing reader, transport and session-broker tests are unmodified.

Runtime: Python 3.12.14; pytest 9.1.1; Ruff 0.16.10; httpx 0.28.1; MCP 2.3.0; pydantic 2.13.5. No dependency was installed or changed for this work. The existing virtual environment was used read-only with bytecode writing disabled.

## Failure custody and reproduction

The `failures/` directory retains the original annotation-attribute test, original stderr-assumption tests, initial lint output, the available first full-run tool excerpt, storage failures and the exact second launcher. The first full output was truncated by its tool output limit; it is explicitly labeled as the available excerpt, not a recovered complete log. The second run's pytest outcome is unavailable and is not counted as a pass.

Four narrow lint annotations preserve the new reader's ValueError contract for malformed remote values, following the existing feedback reader. The tested module before those comments is retained, and its AST matches the final module. The only other lint edits order imports in the two new test files. No transport logs or owner exception handling were changed to make tests pass.

For normal reproduction, use the existing project commands:

```bash
ruff check src tests scripts
pytest -q
```

The two authored modules can be run alone with:

```bash
pytest -q tests/test_discussion_thread.py tests/test_discussion_thread_native.py
```

The recorded gate drivers bind the exact isolated roots and use a regular-file temporary namespace inside their single exec invocation. They capture complete results before that private /dev mount ends. Source manifests and both successful gate receipts are also retained outside that transient namespace. The drivers describe an author environment, not a requirement that end users have those absolute paths.

This qualification uses synthetic data, local HTTP and real local CLI/MCP processes. It does not establish live-school access, a signed-in browser result, Windows behavior, or the recency of a server's cached data. Independent receiving is a separate record added after this author freeze.
