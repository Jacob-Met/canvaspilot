# Token-only source exchange for the existing PR35 receiving route

Contributor: `estate-87eaaf0fdf63/estate_production`, 2026-10-08.

The complete held source is remotely available at
[7428deadc00a2372f258d48a0bd05e1c83a939ac](https://github.com/Jacob-Met/canvaspilot/commit/7428deadc00a2372f258d48a0bd05e1c83a939ac),
tree `f547d3e67e2d407ad804e3c799afd71b18988746`, on
`estate/87eaaf0fdf63-canvas-collection-transfer`. Its source matches the separately
qualified 169-test broker/PAT/parser composition. It predates the subsequent
module/sync composition and school-origin correction. There is no competing
main-targeting PR for this transfer.

## Exact bounded deliverable

`token-only.patch.gz.b64` losslessly encodes a gzip archive of the unmodified Git diff of the following two paths from
`640bca994bd98f2c4b1759e450ebeda0e0b92dab` to the qualified token increment
`e678faaa4809ac0eddfd17228c1e940d19865217`:

- `src/canvaspilot/client.py`: the token `get_paginated` traversal, its complete
  collection docstring, and removal of the unused legacy Link parser.
- `tests/test_token_pagination.py`: 26 synthetic-token HTTPX transport controls.

No broker traversal, broker response format, health capability, authentication
setup, module API, CLI, MCP, dependency or workflow change is in this patch.
`token_controls.py` preserves the exact test source separately for receiving.
`manifest.json` records source pins, all artifact hashes and the executed
`git apply --check` against the immutable original receiving checkout. That check
passed without modifying it. Gzip storage preserves the required space-only
context lines of the exact unified diff; decompression was checked byte-for-byte
and the decompressed patch passed admission again. The archive is stored as
base64 text for UTF-8 source transfer; decoding preserves the exact original
archive and patch hashes. Reconstruct it with:

```sh
base64 --decode token-only.patch.gz.b64 | gzip -dc > token-only.patch
```

The patch has not been
applied to an owner's branch.

Uncompressed patch SHA-256:
`e107c29a04f2e3d7dc966e4f2708df2456478b0a13e2fac81a78d9e5941d124e`.
Exact test-source SHA-256:
`34e6b063048e7231dc1162908a5b00340f1149c4c2824a267cf7b67a2d80c646`.

The original token qualification reproduced 17 failures with nine unchanged
controls; all 26 passed after the source correction. Its full source suite passed
129 tests. Exact original results remain in the held transfer's
[token qualification](https://github.com/Jacob-Met/canvaspilot/tree/7428deadc00a2372f258d48a0bd05e1c83a939ac/docs/qualification/token-pagination-20261008-87eaaf0fdf63).
No semantic tests were rerun for this export, and none of these results claims
qualification of PR35 or PR37.

## Receiving prerequisites at packet preparation

This is an exact source exchange, **not a patch directly applicable to PR35**.
The source increment expects the existing `CanvasPaginationError`, `broker_path`
and `next_link` interfaces from the shared pagination helper. That helper is in
the held transfer; PR35 instead defines its exception and session parser in
`client.py`. The receiving owner must adapt this small interface boundary on
an agreed source head and run the unchanged behavioral controls there.

At the packet's preparation read, PR35 had no owner acknowledgement selecting a final combined
receiving head. Donor `estate-86776bb3cdb8` has already provided its session-parser
correction as stacked [PR37](https://github.com/Jacob-Met/canvaspilot/pull/37),
head `dcf1bc02aa490c5e9ac79e3f486d9e2f2e34c2db`, targeting PR35's
`89fa86d20e4eff47ce42e18afd8cd8e75ab376c3`. PR37 remains open and unmerged.
This packet does not duplicate that donor's broker-parser work.

| Choice | Required receiving decision |
|---|---|
| Exact source head | Pin the PR35 owner's intended head after disposition of PR37 and current main. An open donor child is not owner acceptance. |
| Parser and exception interface | Share the accepted strict parser with token traversal, map the existing exception consistently, and retain token URL normalization without copying another broker parser. |
| Legacy broker completion | An ordinary successful list cannot disclose incomplete retrieval. Missing metadata must produce an explicit incomplete/restart error or a separately agreed result contract that identifies incompleteness. |
| URL admission | Preserve token initial/continuation scheme, host, effective port, userinfo and fragment checks; explicitly settle the difference between root-relative Link acceptance here and PR35's absolute-only continuation policy. |
| Documentation and existing source | The complete-collection docstring applies to the qualified combined contract. Keep broker compatibility claims accurate until legacy behavior is resolved; preserve the accepted module/sync, credential and broker protocol source. |

The tests preserve real HTTPX token/header setup while substituting only
MockTransport. They check foreign-target refusal before a request, opaque query
bytes, initial arrays/scalars and existing queries, cycles, exactly 40 terminal
pages versus an incomplete cap, malformed Link metadata, later HTTP errors,
and non-list pages with continuation. Only explicitly synthetic tokens are used.

## Thread delivery status

The normal GitHub connector rejected the attempt to post the concrete transfer
pin in PR35 with HTTP 403: a temporary secondary content-creation rate limit.
No comment was accepted, and there was no retry or alternate-route attempt.
`pending-pr35-comment.md` preserves the reviewable draft, and
`blocked-comment-receipt.json` records the rejection for later supported delivery.

Root owns source publication and final receiving coordination. The original
producer, PR35 and PR37 branches remain untouched by this packet.

## Subsequent receiving update

The PR35 owner later acknowledged the combined contract in
[comment 6058453998](https://github.com/Jacob-Met/canvaspilot/pull/35#issuecomment-6058453998),
including an actionable incomplete/restart error when metadata is absent.
The original table and rejected comment above remain historical evidence.
The [final composed-source qualification](../../qualification/collection-composition-20261008-87eaaf0fdf63/README.md)
records 278 passing tests and the later-page object correction required in
addition to this exact historical token patch. Final acceptance still requires
receiving the selected owner head under its declared broker/anchor policy.
