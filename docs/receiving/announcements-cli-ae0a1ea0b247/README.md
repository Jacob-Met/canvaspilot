# CanvasPilot announcement CLI author receiving packet

Source contribution: issue 58, baseline a5ce672e5b3580c1f52e13c49eefee830f11346c.
The four exact contribution blobs and every imported unchanged baseline file are bound in AUTHOR-RECEIPT.json and PACKET-MANIFEST.json. Removing the two new CLI spans and the README addition reconstructs the baseline bytes exactly.

## Actual outcomes

- Original maintained CLI has no announcements command: the stdlib entry and complete actual module both refuse with exit 2.
- Corrected authored receiver against that original source: 14 failures for the missing capability, 19 passing controls (including all 17 existing announcement API cases).
- First implemented command: 29 passing and four failing focused cases. Actual HTTPX informational logs mixed into structured error stderr. The exact rejected source and raw logs are preserved. The narrow command branch now restores the caller's HTTPX logger level in a finally clause and keeps JSON errors parseable.
- Frozen command: 33 focused cases pass; native Ruff check of src, tests and scripts passes.
- Complete unchanged existing suite plus new tests: 686 passed, 1 skipped, 6 subtests passed. The optional browser case was not run; no browser or live Canvas account qualification is claimed.

## Retained setup and harness distinctions

The earliest bounded dependency attempt installed nothing. One early module witness ran before the client file had been materialized; the complete source witness is separate.
The first authored fixture run inherited an optional SOCKS-proxy configuration. The corrected synthetic loopback harness clears only proxy variables. Before those assertions were reached, fixture expectations were aligned with existing HTML outer-whitespace cleanup and the existing whoami wrapper; invalid-detail admission was tightened so a generic unknown-command error could not count as success. Original source and logs remain.
The first candidate Ruff finding was the test subprocess call's missing explicit check=False and was corrected only there.

The first complete-suite run used the primary interpreter plus a borrowed PYTHONPATH. Inherited tests replace that path for their child processes, so 28 cases failed with dependency startup errors while 658 passed and one skipped. The retained successful rerun changes only the executable to the existing CanvasPilot environment's own bin/python. No dependency was installed, no original test was edited, and no API/client transport was replaced.

## Reproduction

Use a normal installed CanvasPilot development environment for hosted CI. This local run used the existing read-only environment:
`/workspace/scratch/ac386303dce2/runtime-execution/canvaspilot-env/bin/python`

Set PYTHONPATH to this packet's source/src, disable bytecode writes and clear HTTP_PROXY/HTTPS_PROXY/ALL_PROXY plus lowercase equivalents for the authored loopback fixtures. Then run:

```text
python -B -m pytest -q tests/test_announcements_cli.py tests/test_announcements_pagination.py
python -B -m ruff check src tests scripts
python -B -m pytest -q
```

This is author source qualification pending independent receiving and normal native integration. The packet contains no school data, credentials, browser profile, external provider response, owner lease or deployed-service claim.

## Immutable artifact

[author-packet.tar.gz](author-packet.tar.gz) is the exact 170,482-byte original author packet. SHA-256: `c0789b047cc5aa4a2245b6bce7e7055160ddfd213674946542a7dc69a7871ce2`; Git blob: `a26be29ead9d81b33d5659bf424ef6a89f65103e`. Its `canvas-announcements/evidence/PACKET-MANIFEST.json` binds all 131 entries. The source contribution overlays the complete actual parent; current CI and the independent disposition are bound in the PR conversation after this artifact is published.
