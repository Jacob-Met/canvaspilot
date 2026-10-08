# Planner CLI: source, receiving and integration

This packet supports [CanvasPilot issue68](https://github.com/Jacob-Met/canvaspilot/issues/68): expose the existing current-user planner API through `canvaspilot planner`, with optional `--start-date` and `--end-date`. The beneficiary can inspect course work and personal planner notes in the terminal without changing completion, dismissal or any Canvas state.

## Source scope

The four contribution paths are `src/canvaspilot/cli.py`, `tests/test_planner_cli.py`, `docs/planner-cli.md` and one README paragraph. The API, client, auth/session broker, MCP, package bootstrap, dependencies and workflow are unchanged. Current main `6c4d5d2e7526cddc1aa6c90bfbef2d1188382ad3` supplied the before-images. Removing only the two enumerated planner parser/dispatch additions recovers its complete CLI byte-for-byte; removing the README paragraph recovers its complete README. The new native quiz command remains intact. The native API's recently accepted course-file change is preserved exactly.

Final CLI blob is `df01e112b3c7f525e99b3179176d57497391f16b`; native API support is `cd17584bed618fb4a42d7128d204b2683b889600`. All consequential pins and source preservation are recorded separately. The original baseline is upstream `17d63dc43fde30efd8d3454ef09b1d1a8c5bcd0d`, captured in clean local commit `69d95c7e7ce6e242e6d147c37976c3dd1887443f`. A local capture is not asserted as upstream ancestry.

## What actually ran locally

The original baseline has11 passing conditions across three actual Python children: the original CLI help, actual parser refusal of the absent command, and a positive call through the full native API/client fixture implementation. The synthetic planner data and raw streams are retained under `baseline/evidence/baseline/`.

The first author receiver executed the exact candidate CLI source in nine actual `-I -B -S` children. The eight planner/default/object/error/parser cases passed. The sole failed condition was the receiver's expectation for the unchanged `whoami` control: it expected a bare profile, while the native method returns `{mode, base_url, profile}`. The initial58-pass/1-fail receipt and exact initial receiver remain unchanged. Only this expected fixture was corrected; a single rerun of that control passed10 conditions. Production code did not change for this correction.

Current main then gained the quiz CLI and a native `list_files` correction. The planner additions were applied byte-exact over that current CLI and the README paragraph over current documentation. The native API differs from the earlier API only inside `list_files`; all surrounding bytes, including planner, identity and construction/cleanup behavior, match. One bounded current-composition child compiled the complete current API and composed CLI source, used the real unchanged native fixture client/helpers, and passed10 conditions. These are11 local author CLI children in total, not a claim that the entire first nine-case receiver was rerun on current main.

Every product child preserves raw date arguments, complete returned values and ordinary client inputs. The planner error cases verify no partial successful stdout; the native client is closed once and the caller's HTTPX logger level is restored. Audit tripwires reject file mutation, networking, subprocesses and optional graphical/browser/MCP imports. The metadata pipe is a receiver observation channel, not a product output or file write.

## Execution limits and pending native gate

Local Python3.12.14 lacks HTTPX, MCP and pytest. The receiver deliberately creates a namespace package, skipping `__init__`/bundle/MCP bootstrap, and supplies an import/exception-only HTTPX adapter whose other attributes fail. It executes complete original source, not a rewritten planner implementation. The original fixture run imports API/client/helpers from exact recorded source files. The current-composition run explicitly compiles the exact current API source as well as the CLI. This is not installed-entrypoint, real HTTPX, live token/session, Link-pagination or school-authentication evidence.

The new six-method test module instead launches the actual package CLI against a disposable loopback HTTP server, with an explicit synthetic token and clean configuration. It covers eight child calls: real Link pagination and raw date query values, lossless course/personal rows, default empty output, the native terminal-object convention, initial and later errors, parser refusal and the unchanged identity route. Its source parses; **those package/HTTP tests have not yet executed at this author freeze**. The existing hosted CI must run with the declared dependencies before integration. Independent receiving remains a separate gate. Later check receipts may be added without rewriting these dated observations.

Two local source-capture attempts refused before creating a directory when shared capacity was below their explicit margin. Source, full receipts and publication payload were retained in memory instead, then frozen through the complete GitHub tree. The original baseline and all prior source/review freezes remain intact. `environment-observations.json` records these boundaries; it does not turn an unexecuted filesystem witness into a passing test.

## Portable replay

Use installed project dependencies for the actual package/HTTP tests:

```bash
python -m pytest -q tests/test_planner_cli.py
```

For the separate dependency-limited fixture receiver, choose a checkout/source capsule containing the pinned native files and the candidate CLI, and use the retained synthetic fixture. Keep this evidence unchanged and redirect into a new file:

```bash
python3 -B -S author/receive_planner_composition.py \\
  --native-source CHECKOUT --cli CHECKOUT/src/canvaspilot/cli.py \\
  --api CHECKOUT/src/canvaspilot/api.py \\
  --fixture baseline/evidence/baseline/synthetic-planner.json > NEW_RESULTS.json
```

The receiver supports `--only-case dated` for the bounded composition control, and `--only-case unchanged-whoami` for the corrected continuity control. Without it, all nine families run. It creates no fixture or result file itself; shell redirection follows normal shell overwrite rules. The recorded inline-source execution and a file-based replay compile the same exact bytes, with source labels reflecting their actual inputs. Historical CLI `author/historical-cli-0480.py` and the initial receiver support the retained first-run counterexample. Use original API/client source from the pinned original main to reproduce that older composition.

The product guide links the official [Canvas Planner API](https://developerdocs.instructure.com/services/canvas/resources/planner). No provider call, browser session, installed release, live Canvas write, new dependency or workflow change is part of this contribution.
