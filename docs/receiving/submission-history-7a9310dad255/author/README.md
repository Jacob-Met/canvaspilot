# Self-submission history — author qualification

Accepted native product tree: bf2d1499fe0e3fdd620297fa01a1ab705b46637b. Public parent: 79a2f2b2cbb7e74128d731cf096c7e86f1942d4b. The nine scoped source, test and documentation paths preserve all 703 unrelated current-parent leaves. Publication must parent the actual public commit; native capture commits establish local byte identity only.

## Result

The current inherited and new suite passed **603 tests, with 1 skipped and 6 passing subtests**. Configured Ruff and the actual registered MCP catalog passed on the same unchanged source. The separately authored independent receiver passed **9 groups and 465 assertions**, covering API values, real CLI processes over synthetic loopback HTTP and actual MCP stdio.

The feature exposes CanvasAPI.submission_history, the submission-history CLI command and canvas_submission_history MCP tool. It performs two read-only GETs for assignment context and the caller's self submission, requesting returned history and comments without read_status. Current fields, raw historical records and top-level comments remain separate. Returned empty history is distinct from omitted or null history. It does not sort, deduplicate, infer attempts or join current grades/comments to old attempts. HTML, URLs and file metadata remain data. Positive ASCII decimal identifiers are normalized before any request, without an artificial magnitude limit.

## Failures and corrections

The original baseline runner supplied a global synthetic API token. Six inherited broker tests selected PAT behavior and stopped on TLS verification against their test host. No successful remote HTTP response occurred. Removing only the global token yielded the accepted 414-test baseline; the raw 408-pass, 6-failure run is preserved.

Initial source d95 failed actual CLI receiving because inherited HTTPX INFO logging contaminated the new command's machine-readable stderr. Only the new command now temporarily raises that logger's effective threshold and restores it on every path. Maintained process tests corrected their inspection of MCP wire annotation aliases. The independent receiver then passed all nine groups. The maintained suite still found that the MCP SDK hid an anticipated validation message. Only the new MCP tool now translates anticipated ValueError into the SDK's explicit ToolError, retaining error status. Final source bc1 passed all 481 tests on the original parent and the independent affected MCP replay.

The first current-parent suite passed 602 tests but rejected one inherited pagination continuation. The root runner forced a loopback Canvas origin while that fixture returns the standard Canvas origin. The guard correctly refused it. Explicitly unsetting only that override produced the accepted run. Global credentials remain empty; individual process fixtures own their synthetic token and loopback origin. No source, inherited assertion or expected value changed. Both runs are archived.

## Evidence

qualification.json binds source, result, scope and independent packet hashes. archive-manifest.json names every byte-verified author-evidence.tar.gz member. The archive retains complete raw results, original negative runs, drivers, contracts, capture/composition records, full leaf manifests and all nine owned files from each of four candidate revisions.

The sibling independent directory retains the original frozen receiver, fixture, contract, original failures, corrected complete receiving and anticipated-error MCP replay. The sibling independent-current-79a directory retains unchanged current-parent receiving and source-composition review.

Unchanged parent source is durable at public commits 55fe1e0a3c4ad85e1065f295e49d44722c3be32b and 79a2f2b2cbb7e74128d731cf096c7e86f1942d4b. Full archived manifests bind each leaf. The reproducible public GitHub archive is identified by immutable URL, SHA256 and full leaf verification rather than duplicated.

The final native run used Python 3.14.4, httpx 0.28.1, MCP 2.3.0, pytest 9.1.1 and Ruff 0.16.10. Hosted checks and actual public integration are separate gates. No school-account, browser-session, deployment or live Canvas behavior is claimed.
