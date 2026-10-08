# Submission history: independent receiving on current main

Accepted native source: `67a1963d8b34bff33ee504c8fd8a1fc4c4af9e86`, tree `bf2d1499fe0e3fdd620297fa01a1ab705b46637b`, composed on public CanvasPilot `79a2f2b2cbb7e74128d731cf096c7e86f1942d4b` / tree `0114a6230c473c1ee1d01b99c7121c754b781d54`.

The unchanged independent receiver passed **9 of 9 groups, 465 assertions**, through the actual CanvasAPI, CLI subprocesses over synthetic loopback HTTP, and real MCP stdio. Process 2848398 exited 0; the native wrapper measured 32.3096 seconds (RDC reported 32.51 seconds). All 13 imported source files matched the owner's manifest before and after execution, and all frozen receiver/contract/fixture hashes remained exact. No profile was created.

The raw receipt is SHA256 `8c64807921389fe427d05d898d445614b99c923a342856eee0d397adbfaa1d39`. Its source manifest is SHA256 `b81aed59a0751b602a425b745ad1aa8e73eb2f7c24a5a6c3609e3119ff8b779a`. The unchanged runner is SHA256 `158aa881f34a479a0ebcca0bf679f6cdff28ef8a8588d5d2a6a585e1983e84c3`.

## What this supplement adds

The original evidence packet retains baseline absence, d95's two concrete CLI logging failures, the corrected 33e 9/9 receiving, and the final bc1 2/2 MCP receiving. This supplement preserves a fresh run against the real current client, broker and calendar source received through PR35/PR45. It does not relabel the older results as current-source execution.

The same cases cover raw current/history/comment provenance and output isolation; missing/null/empty/zero distinctions; 56 identifier refusals before requests and very long valid IDs; malformed envelopes and late rows; actual CLI fresh data and refusal output; and actual MCP schema, repeated reads, typed/shape errors and recovery.

## Composition review

Seven of the nine feature files remain byte-identical to accepted bc1: the history module, API/bundle/MCP wiring, guide and both authored test files. Only CLI and README also contain incoming owner edits.

Mechanical review reverses exactly the two calendar-local `CanvasPaginationError` additions to restore the complete accepted bc1 CLI. Applying only the original history README changes onto the verified current 79a README reproduces the entire composed README. The history reader, error wrapper and frozen tests therefore retain their accepted semantics, and the new calendar handling is preserved. The source-review receipt records both comparisons.

## Evidence and limits

`evidence.tar.gz` contains the exact owner’s 712-file manifest, a manifest-verified read-only copy of the 13 source modules actually imported, unchanged receiving inputs, the native execution wrapper and RDC result, raw receipt and CLI/MCP/HTTP artifacts, and the composition review. `archive-manifest.json` pins every member; every member was reopened and verified after archive creation. No browser, dependency binary or profile is included.

To replay, unpack into an isolated directory with an installed compatible Python/HTTPX/MCP environment, then invoke the unchanged `receive_history.py --source SOURCE_ROOT --out NEW_OUTPUT_DIRECTORY` from that environment with bytecode writes disabled. Its contract and fixture must remain beside the runner. The receiver explicitly supplies synthetic credentials and fixture/profile settings; it makes no school-account or live broker calls. The recorded native wrapper retains the exact original command and source paths.

This is native source and synthetic caller qualification. It does not claim a live school response, installed broker activation, runtime deployment or learner outcome. The original eight-file packet remains immutable; publication and actual-head integration remain the lead's gates.
