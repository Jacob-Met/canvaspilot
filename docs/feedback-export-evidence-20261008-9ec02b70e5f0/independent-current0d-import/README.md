# Independent current0d API import receiving

Both assigned native export invocations pass: one in normal Python and one with `-O`. Each fresh CLI process imports the actual current API module and its new `assignment_submission` dependency, performs exactly the two authored loopback GETs, and creates one actual 12,466-byte feedback HTML file. The command's digest receipt matches the actual bytes. Every visible feedback string and every semantic field equals the previously qualified a0db export after replacing only the fresh capture timestamp.

## Exact receiving context

- Parent: `0d1898544a90079e2dcc7ceb3fa4bc6bca88a2bc`.
- Tree: `de9fca025ebe325807bd53cd9b7f3b6be50c6d19`.
- Current API Git blob: `8de750525055991ca470fb4881d0368a07631818`.
- New imported module Git blob: `95b1f19927e4eecf99fc852325737c3cfe86cd0d`.
- Formatter SHA-256: `a0db41dca9cce28c9fb7594c88ea6dc103b0f3104d5ba4d061bd93aaed92a714`.
- CLI SHA-256: `223654cbd53c539b327dfb7399ed01953381044f387c205bb1a7eb21f6c1808f`.
- Author's 29-file manifest SHA-256: `7ff1ec504102adf538801b2cb6a17b451cad7b0699d4e08ff858aa121cbfb4a3`.

Relative to the frozen current79 candidate, only README, API, and the new assignment-submission module differ. The other 26 candidate files remain exact. All 29 author files and all 14 private runtime modules are verified before and after this receiving step. The new assignment-list helper's own behavior is outside this test: this checks that its import does not break the unchanged feedback path. The earlier seven-method, current79 two-method, and author 97-case suites were not replayed or relabeled.

Normal execution returned zero in 1.40 seconds including its wrapper; optimized execution returned zero in 2.50 seconds. There were two fresh CLI processes, four Canvas GETs, and two newly created files across both modes. There were no browser allocations, live accounts, actual broker processes, GitHub writes, or new moving-main reads.

## Evidence and reproduction

`receiving-summary.json` contains both exact invocations and result records. Full stdout/stderr, request receipts, authored data, actual files, all 14 runtime modules, unchanged independent support, and source maps are retained in the 44-file lossless capsule. Its 282,805 raw bytes are encoded as 78,585 bytes of UTF-8 base64 text. Every archive member was checked before persistence, from the persisted shared bytes before the temporary execution scope ended, and again in a later execution. Preparation, both invocations, archive creation, and persistence occurred within one ordinary owned `/dev` scope; 475,136 shared bytes were physically reserved beforehand. No mount, device, limit, or cgroup was changed.

Run `python3 -B unpack_receiving.py` to verify all members without extracting. Use `--destination /path/to/new-replay` for an isolated replay, then invoke the archived `verify_import_context.py` with `--source /path/to/new-replay/repo`, `--support /path/to/new-replay/support`, `--prior-html /path/to/new-replay/prior-actual-export.html`, and a fresh `--output` directory. The unchanged support records the installed read-only dependency path used by the real CLI. Readable normal/optimized logs, result summaries, current pins, and resource observations are provided outside the capsule.
