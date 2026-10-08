# Independent receiving on CanvasPilot 79a2f2b2

Two bounded native receiving methods pass in normal Python and with `-O`, with zero failures, errors, or skips. The tested parent is `79a2f2b2cbb7e74128d731cf096c7e86f1942d4b`, tree `0114a6230c473c1ee1d01b99c7121c754b781d54`. The received formatter is SHA-256 `a0db41dca9cce28c9fb7594c88ea6dc103b0f3104d5ba4d061bd93aaed92a714`; the composed CLI is `223654cbd53c539b327dfb7399ed01953381044f387c205bb1a7eb21f6c1808f`.

## Why this receiving step was necessary

One observed main-ref read at 13:22:46 UTC found five changes among the 26 edited-path and native-context checks: README, CLI, client, session broker, and calendar exporter. `comparison.json` retains every check and the compact upstream path differences; `current-blobs.json` retains the complete nontruncated 708-blob snapshot. All later blob reads used that immutable parent. This packet makes no claim about a later publication parent.

The incoming client changes concern complete collection traversal through Link metadata. The broker adds provider-origin checks and returns Link metadata, and the calendar exporter receives those requirements. The feedback API still makes two singular-resource reads. That distinction motivated the native receiving controls below. The five exact upstream source diffs are included; their implementation was not edited by this reviewer.

Independent source checks verify the author's 28-file current manifest before and after execution. All 22 unowned candidate files match the exact published parent. For the CLI, both original export-command insertions are byte-identical to the reviewed 55fe additions; removing them reconstructs the entire 79a2 CLI. The original README section is likewise one exact insertion. The current client, broker, and calendar modules remain byte-for-byte the incoming published modules. All 25 privately copied runtime files (12 parent, 13 candidate) remain exact through both modes.

## What the actual commands establish

The first method invokes the current parent's native `feedback` command and the composed CLI's same command against independently authored local Canvas responses. Their complete JSON outputs are equal. A fresh native `export-feedback` then writes an actual HTML file whose reported SHA-256 matches its bytes. The file preserves the supplied zero score, unknown missing status, attempt, prior-grade applicability, and returned comment metadata. Reusing that output path produces a structured refusal before any further request and preserves the existing bytes.

The second method sends the same real native CLI through an independently authored loopback server that implements the broker wire envelope. Its health response deliberately omits collection-pagination capability fields and its singular-resource envelopes omit response headers. The current parent and composed reader still return identical JSON, and the exporter creates the actual feedback sheet. Every broker request carries GET intent for exactly the selected assignment or self-submission; no collection traversal is invented. A subsequent authored provider refusal reaches the export command as the exact `CanvasAuthError` message, creates no file, and makes no second submission request.

This server is a test fixture. No actual session-broker process, browser, live account, login, or Canvas write is involved. The test does not execute or certify the broker's browser-origin enforcement; it qualifies the exporter/client receiving behavior for that server-side refusal and preserves the current owner modules unchanged.

| Observation | Normal | Optimized |
|---|---:|---:|
| Independent methods passed | 2 | 2 |
| Fresh native CLI processes | 8 | 8 |
| Direct authored Canvas GETs | 6 | 6 |
| Local broker health GETs | 7 | 7 |
| Local broker RPC POSTs, all with GET intent | 7 | 7 |
| Newly created HTML files | 2 | 2 |
| Expected refusals | 2 | 2 |
| Failures / errors / skips | 0 / 0 / 0 | 0 / 0 / 0 |

The original seven-method semantic review remains qualified at its original 55fe source. The one-byte CSS successor has its own separate actual-file/selector receipt. Those suites were not relabeled as current-parent tests or broadly repeated here.

## Evidence custody and reproduction

`receiving-summary.json` records the exact source, commands, results, and lossless archive hashes. `receiving-capsule.tar.gz.base64` contains 83 exact files totaling 623,672 uncompressed bytes: both tested runtime checkouts, the unchanged independent support, the runnable two-method probe, complete process and HTTP records, authored data, actual sheets, both logs, five source diffs, and source custody proofs. `receiving-capsule-index.json` identifies every member. Readable summaries, logs, current pins, and the preservation proof are also provided outside the capsule.

Shared storage was constrained. Before execution, 1,212,416 bytes were physically reserved in three owned shared files. The bounded source preparation, two sequential runs, archive creation, and persistence occurred within one ordinary owned `/dev` scope. No mount, device node, cgroup, or limit was changed. The archive was written into the reserved shared file with `r+b`, flushed and fsynced, then truncated to its actual size. Every member was verified before persistence and again from the persisted bytes before the ephemeral scope ended. `resource-receipt.json` retains the observed paths, mounts, capacity, and unchanged limit readings.

Verify without extracting:

```sh
python3 -B unpack_receiving.py
```

For an isolated replay, extract to a new directory, then invoke the archived probe with its `repo`, `before`, and `support` directories and a fresh output path:

```sh
python3 -B unpack_receiving.py --destination /path/to/new-replay
python3 -B /path/to/new-replay/verify_current_receiving.py \
  --source /path/to/new-replay/repo \
  --before-source /path/to/new-replay/before \
  --old-review /path/to/new-replay/support \
  --output /path/to/new-results
```

The archived support records the read-only installed HTTP dependency path used by these native CLI processes. Supply an equivalent installed CanvasPilot dependency environment if replaying elsewhere. The capsule is encoded as UTF-8 base64 text for ordinary Git blob publication; no separate binary upload is required.
