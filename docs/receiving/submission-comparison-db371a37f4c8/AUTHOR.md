# CanvasPilot submission comparison — author evidence

Contribution: estate-db371a37f4c8/product_execution, issue #67.

## Product outcome

`canvaspilot compare-submissions COURSE ASSIGNMENT --before history:1 --after current --out comparison.html` creates a new offline reading report from two explicitly selected returned records. History selectors are one-based returned-list positions. Duplicate attempt numbers, returned ordering, unknown metadata and missing/null/blank/empty distinctions remain intact.

The report shows readable text changes, exact URL spelling, returned attachment/media metadata and a local JSON download containing the exact selected records. Submitted markup remains inert. File bytes are not fetched, and equal file metadata does not establish equal or retained historical file content.

The existing API/history reader, client, authentication, MCP/bundle and workflows are unchanged. The only source contributions are the new comparison module, two additive CLI spans, two dedicated test files and their fixture, the guide and a README pointer.

## Source identity and composition

Initial discovery and original missing-command witness used main `0480cbce421bae532e3e909899fc8fb83789e878`, tree `f9ecaa4311d93cfe3a1fd1c9cc140834e2449341`. The thin native source contains all non-documentation repository files and the top-level documentation: 79 exact files, 582,304 bytes.

Before the comparison tests ran, main advanced to `6c4d5d2e7526cddc1aa6c90bfbef2d1188382ad3`, tree `50b0e4001ccad72078b073e2cc3606b619e064ff`. Its 81 admitted files include new quiz CLI commands and a course-file error fix. The history reader and API wrapper remain exact. The candidate has 86 files; all 79 inherited files outside README/CLI remain exact. Removing the two declared CLI spans reconstructs current canonical CLI byte for byte.

The native directories and private Git snapshot commits are isolated qualification records. Their thin commits are not canonical GitHub ancestry. Publication uses the complete canonical Git tree and its actual main parent.

Frozen source manifest: `composition-source-manifest-r1.json`, SHA-256 `c1f384b028c747f84f367f7ae0263db402589c15ea72067aa6f25ff6cedc4faa`.

## Qualified behavior

- The original actual CLI history read preserves the authored duplicate/out-of-order records, large integer and submitted content. The original comparison command exits 2 before any request or output.
- Native Ruff passes on the frozen composed source.
- All **58 dedicated tests pass**, including actual CLI processes with a strict CP1252 console, exact loopback GET/include behavior, Unicode output filenames, record and value-state fidelity, markup/control handling, declared text/source bounds, expected errors and protected/atomic output paths.
- The actual CLI-generated report opens in the existing Chrome for Testing 153.0.8010.12 headless shell. Four browser groups pass: exact offline/inert report; native pointer download; 390 px content/source wrapping; and print-media/PDF production. All 86 source files remain exact and the owned browser exits 0.
- The downloaded JSON is independently decoded with native Python, preserving integer `9007199254740993` and false-versus-zero values. This avoids JavaScript number coercion in the receiving proof.
- The author visually inspected all five screenshots: desktop context and text changes, phone text and attachments, and print-media layout. The actual browser also produced a PDF; its individual pages were not separately raster-inspected.

The exact four successful CLI reports are included under `reports/`, with origin receipts and byte hashes.

## Preserved failures and qualification boundary

The first source-packet write encountered transient native ENOSPC and left no target. A read-only probe found recovered capacity; one retry completed and all source Git blobs were verified.

The first original baseline receiver incorrectly expected the history include query without the client's inherited `per_page=50`. It stopped at that assertion after the original history command succeeded. The first driver/stdout/stderr remain unchanged. The corrected R2 receiver records the full actual query and completes the still-unexecuted missing-command control. This was a receiver correction, with no product source edit.

The first native lint attempt stopped before executing comparison tests: import ordering in the three new Python files and the exception class for a malformed assignment-summary type required adjustment. The original inputs, log and source hashes are preserved. No lint rule was disabled.

**The full native pytest attempt did not qualify the whole project.** It encountered ENOSPC inside pytest capture/temp-directory handling and reported:

`1 failed, 571 passed, 1 skipped, 545 errors, 34 subtests passed in 101.75s`

The first failure is an inherited discussion test's pytest capture/context-manager exit, with `OSError: [Errno 28] No space left on device`. Aggregate classification records 546 occurrences of that ENOSPC failure across the reported failed/error entries, plus temporary-directory creation failures. The 872,527-byte complete log is retained, SHA-256 `51e56a8a1af774e85890272cc3c0602e7cc8ad12cf9496d9081e241ae3775113`. All 86 source files remained unchanged. The native whole-project result is explicitly incomplete; it is not relabeled as a pass or silently rerun on unstable storage.

The normal hosted exact-source full suite is the remaining whole-project gate. Root independently froze its receiving contract before inspecting candidate code; that receiving is pending at the initial source/evidence publication and will have its own separate disposition and packet. No merge is authorized by this author packet alone.

## Reproduction

Use the repository's existing Python >=3.11 environment and dependencies. No dependency or workflow change is required:

```sh
python -m ruff check src tests scripts
python -m pytest -q tests/test_submission_comparison.py tests/test_submission_comparison_process.py
python -m pytest -q
```

The native author used the verified read-only Python 3.12.8 environment at `/Users/me/canvaspilot-announcements-3dcb83a1/.venv/bin/python`, with `PYTHONPATH` pointing to the private composed source and bytecode/user-site writes disabled. Fixtures use explicit synthetic tokens, unused private profile paths and loopback servers. No real Canvas account, school session, student data, provider mutation, installed CLI release or deployment is represented by this evidence.

This archive excludes disposable browser profiles, pytest temporary directories and Git internals. It contains their source/fixture definitions, exact source manifests, complete logs/receipts, the actual retained reports, and the browser outputs. Every archive member is hashed and verified again through decompression before publication.
