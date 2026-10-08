# Announcement pagination: source and independent receiving

The announcement API now calls the existing `CanvasClient.get_paginated()` instead
of making one request. The course/start-date parameters, output fields, order,
HTML stripping and compact/full text behavior are unchanged. A later-page failure
reaches the caller instead of leaving it with a successful first-page result.

## Exact source boundaries

- Native baseline parent: `72357053a1629c349f700030013559fa6d8130f2`, tree
  `919634af69c067e04f391fca84b3071ab8da9159`.
- Baseline API blob: `336955bd9a305f8c71e2a9c49d4ca5731afa6193`.
- Natively qualified API blob: `3b9b16b211393f4da4be5a7fde2b49ae81ccf263`.
- Current publication parent: `e8cd1aecf8e5ca9ede0313b2576ddd71303b82ad`, tree
  `5479f4a3b56660671973259596b0b07568f367e6`.
- Current parent API blob: `f66a0916554361c075f82bf0bcf3b8e49aa272d8`.
- Composed publication API blob: `81b0f44edb7d5ff80770745050c8f3a296203e75`.
- Dedicated test: `tests/test_announcements_pagination.py`, blob
  `a2c03bfa853867a6a491b7b5b08b67cbc92037be`; its qualified bytes are unchanged.

Current main includes feedback PR #40. The complete `list_announcements` method
still matches the native baseline, and the composed method matches the native
candidate exactly. All API bytes outside the one call and all README bytes outside
the announcement paragraph are preserved. Current `client.py`,
`session_broker.py`, package initializer and all inherited test files used by the
earlier run retain their exact blobs. The newer feedback module and bundle, CLI
and MCP changes remain in the current tree. This composition was checked as
source; the whole newer tree has not been rerun locally.

## Recorded results

| Boundary | Result | Exact record |
| --- | --- | --- |
| Original token HTTP baseline | Three failed contracts and three positive controls: both detail modes return 50 of 61 rows, and the API never reaches the later authentication error; the existing paginator succeeds or raises on the same fixtures. | `baseline-receiving.json` |
| Author token/MCP candidate | 17 focused tests pass; 209 total tests pass, including 192 inherited cases. | `native-qualification.json`, `focused.log`, `full.log` |
| Independent broker baseline | Five failed cases and two positive controls. | `announcements-broker-base.json` |
| Independent broker candidate | All seven cases pass with unchanged source, records and filters. | `announcements-broker-candidate.json` |
| Current-main composition | Exact method/dependency and tree-preservation review; no additional runtime execution. | `qualification.json` |
| Local lint | Ruff could not start because its executable was unavailable; no source analysis result exists. | `ruff.log` |

The independent root receiver exercises the actual API, existing broker paginator,
health/fetch helpers and query encoding. Only `_broker_request`, the terminal
HTTP boundary, is replaced. The caller supplies tuple parameters with two
`context_codes[]` values, `active_only`, `per_page` and a start date. Compact and
full 61-record cases reach page two, the 100-record case reaches the terminal
empty third page, and later 403/500 responses refuse the whole operation. Empty
and single-page controls retain their behavior. This is an independent test
implementation and an exercised branch beyond the author's token/MCP fixtures.

Root reviewed the source and focused tests and accepted the exercised contract.
The original token baseline was not rerun after authoring. The independent broker
baseline is a separate receiver. Packet assembly only verifies/copies recorded
bytes; it performs no additional tests or lint retries.

## Receivers and replay

`receive_announcements_broker.py` is the exact independent root receiver. With a
normal CanvasPilot test environment containing `httpx`, it accepts an explicit
source checkout and writes a receipt:

```sh
PYTHONDONTWRITEBYTECODE=1 python receive_announcements_broker.py --source /path/to/pinned-canvaspilot --output /path/to/broker-receipt.json
```

Run the dedicated source test through the repository's ordinary pytest command.
The authored qualification driver `qualify.py` is retained unchanged as a
historical command record, including its original source/runtime paths.
`baseline-receiver.py` and `current-primary.json` likewise retain the original
token receiver and its embedded primary-source packet. That historical script's
package-initializer path is recorded literally; it is not presented as a portable
launcher. The initializer's exact blob is recorded in both raw receipts and
`qualification.json` and remains unchanged in the publication parent.

`manifest.json` pins every other evidence file. `qualification.json` pins the
source delta, both receiving boundaries and current tree comparison. Raw results,
including the baseline failures and unavailable-linter traceback, are retained.

## Remaining limits

The existing client/broker response-shape rules and 40-page guard remain in force.
The separately owned broker Link-continuation proposals #35/#37 are not included
or represented as adopted. This change adds no new pagination engine or unlimited
completeness guarantee.

All inputs are synthetic. There was no live Canvas account, browser, broker
session, network request, student record or installed-service operation. Exact-head
hosted CI remains the gate for the newer published composition and lint; this
packet contains no hosted-CI success claim.

Endpoint contract: https://canvas.instructure.com/doc/api/announcements.html
