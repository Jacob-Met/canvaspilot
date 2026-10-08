# CanvasPilot current39 independent export receiving

## Qualified result

Both normal Python and optimized Python passed on the frozen composition based on published parent `39d835c8becb04d81b65c90d1491d2d3a2727ffe` (tree `53b67d3f06b4c780e508325ec42b2b435ec57e97`). Each mode ran the actual native `canvaspilot.cli feedback 77 314` and `canvaspilot.cli export-feedback 77 314 --out ...` subprocesses against the existing synthetic loopback Canvas fixture: two processes, four GET requests, and one actual HTML file per mode. The normal run took 2.12 seconds; optimized took 4.56 seconds. All 30 pinned inputs remained byte-identical before and after each run.

Existing feedback JSON stdout remained byte-identical to the previously qualified native receipt. The complete HTML bytes matched the retained current0d HTML except for one uniquely located capture timestamp. The independent HTML consumer also checked semantic fields and ordered rubric/comment tables, numeric zero versus absent values, prior-attempt feedback, the actual export receipt hash, and literal script-like comment text remaining ordinary text.

Source preservation was independently derived from complete current39 native before-images. Removing exactly two CLI insertions and one README insertion recovered every original byte. The inserted blocks were byte-identical to the earlier qualified export contribution. The incoming API, bundle, MCP server, and submission-history files remained complete and exact. All 40 previous CanvasAPI method bodies remained exact; the only added API method was the native lazily imported submission_history method. The export formatter was unchanged. The new submission-history behavior itself was outside this bounded receiving check.

## Source and receiver identity

- Current source manifest: SHA-256 `560196c2439531be7d988b10b7a9f5a41a2e3d207b3336649410f810c50d659b`; all 30 file byte counts, SHA-256 values, and Git blob IDs are retained as `candidate-pins.json` inside both capsules.
- Current CLI: SHA-256 `53ab0e1587154b86e3a186765506b42673dc085e24e19b54de0aaf42b9f80b91`, Git blob `f915d544fb8b31a6eb1dcf573bf36ee510aedcf9`.
- Unchanged formatter: SHA-256 `a0db41dca9cce28c9fb7594c88ea6dc103b0f3104d5ba4d061bd93aaed92a714`.
- Qualified independent receiver: verify_canvas39_composition_fixed.py, SHA-256 `20227d258e5d0d2bdbdf6d98c253ef2619b0e7ce206500467f5dd50f9b451819`.
- Reused transport and independent HTML parser: receiving_support.py, SHA-256 `27b2851617939bdce42549cb5a0de2e663f66b7ceea6ee53e6ff24b88ec6089b`; the exact source is archived as support.py.source.

## Read or reproduce the retained evidence

native-results.json is the readable receiving summary. native-evidence-index.json lists all 31 actual evidence members (266,648 uncompressed bytes). native-evidence.tar.gz.base64 is a deterministic, lossless gzip/tar capsule: 72,085 encoded bytes, SHA-256 `b8e26364b129d029c393fddec8a231b3ce8dc26c9d10632b8424c5ea497b5a61`. It preserves both actual output files, all CLI commands/stdout/stderr and loopback receipts, exact source preservation proofs, source pins, prior comparison outputs, and receiver/support source. Member names and hashes were verified against the original private files before those files were removed, then verified again from retained bytes.

The included unchanged unpacker verifies encoded bytes, compressed bytes, all ordinary member names, exact member allowlist, byte counts and hashes before display or extraction:

~~~sh
python3 -B unpack_receiving.py native-evidence-index.json
python3 -B unpack_receiving.py native-evidence-index.json --cat normal/result.json
python3 -B unpack_receiving.py native-evidence-index.json --output /new/empty/path
~~~

The receiver is directly runnable with its eight explicit source, pin, before-image, existing fixture, prior-receipt, and output paths. Exact normal and optimized invocations and environment are in normal.execution.json and optimized.execution.json inside the capsule. Preserve the specified source and oracle hashes when supplying equivalent checkouts or extracted prior packets. The receiver uses explicit checks that remain active under -O; it does not import the formatter as its output oracle.

## Earlier failures retained separately

The original receiver verify_canvas39_composition.py (SHA-256 `69c7da24a695e9815683b8ae4a46924e0754ae6c7c8f6808b3b50b9895b5ab53`) stopped in both modes on a list-to-bytes join mistake before any CLI process. receiver-error-results.json and its separate 11-member capsule preserve both actual failures and the original source. The successor changed only that receiver join expression. A separate wrapper metadata typo occurred after the complete first capsule had already been written and verified; its index was recovered from those exact retained bytes. It is recorded explicitly in the error index and summary.

The first successful native rerun then reached its explicit custody bound: 72,057 encoded bytes exceeded the preallocated 65,536-byte extent. Its exact stdout and resulting missing private outputs are retained in custody-bound-failure.json; it is not used as the qualified receipt. The final unchanged receiver ran once more after physically allocating a 98,304-byte evidence extent, wrote the complete capsule without relinquishing that allocation first, and verified readback. The initial shared-storage ENOSPC before any CLI process, plus the exact-hash transfer of our already Git-verified published Recall duplicates, are retained in published-recall-reclaim.json. ScopeSignal files and peer files were untouched.

This qualification used a synthetic local token, two existing read routes and ordinary temporary files. It made no live-account requests or GitHub writes, allocated no browser, and made no product implementation changes. It was the requested narrow receiving check; it did not repeat the full native suite. Parent coordinates publication of the unchanged current39 composition and this independent packet.
