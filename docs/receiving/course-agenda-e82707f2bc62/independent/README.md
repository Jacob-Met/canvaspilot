# Independent selected-course agenda receiving

Receiver: `estate-e82707f2bc62/root`. Scope: [CanvasPilot issue 55](https://github.com/Jacob-Met/canvaspilot/issues/55).

## Independent controls

The protocol froze at 2026-10-08 14:45:54 UTC and the 12-case real-process receiver froze at 14:52:24 UTC, before the receiver opened candidate implementation or author tests. The receiver first read unchanged native CLI/MCP/client conventions and the official Canvas Calendar Events contract. All provider data is authored and served by an owned loopback HTTP server with a synthetic bearer.

Two actual pages of events and two of assignments cover 10 complete records across two selected courses: positive and negative fractional-hour offsets, sub-nanosecond ordering, an effective section context, all-day entries, unknown and malformed timing, distinct overrides sharing an assignment identity, nested due dates, literal HTML, nulls and numeric zero. Full returned records and their original types must survive. Continuation links contain only opaque percent-encoded cursors; original query filters may not be appended. Foreign/conflicting/non-object rows, late 403 responses and repeated links must refuse the whole agenda. Five invalid selection/date cases must make no request.

The registered MCP stdio session verifies native read-only annotations, reads a complete agenda, encounters a late provider denial, rejects a boolean course ID without HTTP, and succeeds again in the same session. Real installed HTTPX 0.28.1, MCP 2.3.0, Pydantic 2.13.5 and pytest 9.1.1 were used with Python 3.12.14. No browser or live Canvas account was used.

## Results and preserved failure

| Phase | Actual result |
| --- | --- |
| Original 39d835c8 baseline, frozen v1 receiver | 12 failed; the requested CLI route/MCP tool is absent |
| RFC-corrected candidate over original baseline, frozen v1 receiver | 11 passed; 1 receiver error after a real successful MCP call |
| Original baseline, affected MCP case with alias-access successor | 1 failed on the absent tool; 11 deselected |
| RFC-corrected candidate, affected MCP case with alias-access successor | 1 passed through success, refusal, invalid input and recovery; 11 deselected |

The receiver error was an SDK object-field spelling mistake: `result.isError` is not an object attribute in the installed MCP 2.3.0 model. Exactly four accesses were changed to `result.model_dump(by_alias=True)["isError"]`, matching the existing native process-test convention. Expectations, datasets, control flow and production source were unchanged. Reversing those four replacements reproduces the frozen original byte for byte. Original tests, failed output, JUnit, hashes and focused successor runs remain in the archive. The 11 unchanged passing CLI cases were not replayed locally; no earlier run is relabelled as 12 passing tests. The inherited native MCP runpy warning remains in preserved failed-run stderr.

The active peer test passed Ruff 0.16.10 with the project's default rules. Fixture teardown checks before/after package source hashes, no browser-profile creation and read-only requests. Candidate and focused-run outer receipts additionally record exact before/after source maps; the original baseline receipt does not contain a separate outer map.

## Source and integration boundary

Receiving binds original baseline `39d835c8becb04d81b65c90d1491d2d3a2727ffe` plus final RFC-corrected agenda source (blob `82ab4fa8f9b92b8d9e5d4c74962d138e1d882ebd`). The final publication composition over inbox parent `a5ce672e5b3580c1f52e13c49eefee830f11346c` preserves every existing API/CLI/MCP parent byte and adds exactly the same received blocks. Agenda core, bundle inventory and guide are byte-identical to the received final candidate. The complete README delta was read and accepted. `receiving.json` pins actual files, both source stages and all four runs.

This packet accepts the additive source for publication. Existing native CI must still lint the full tree and execute the entire test suite on the actual composed PR merge before integration. The tested synthetic merge and any eventual integration commit must be recorded separately. There is no live-learner, simultaneous-snapshot, recurrence-expansion, browser-broker or provider-write acceptance claim.

## Evidence

`protocol.json` is the frozen independent protocol. `peer-evidence.zip` contains original and active tests, raw run logs/JUnit/case responses, exact received source capsules, the narrow receiver correction, source-review proof, Ruff receipt and a per-member byte/SHA/Git-blob manifest. Every archive member was read back and compared after compression. The active portable receiver belongs at `tests/test_course_agenda_peer.py`.
