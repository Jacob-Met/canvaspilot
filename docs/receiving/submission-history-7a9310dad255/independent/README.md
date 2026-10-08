# Independent submission-history receiving

Reviewer: `7a9310dad255 / memory`. Implementation owner: `7a9310dad255 / root`.

This packet accepts the pinned native submission-history reader and its API, CLI and MCP behavior. It preserves the original failures, successful corrections and source identities separately. Publication or integration onto a later main branch requires its own source-composition check.

## Frozen independent contract

Before candidate implementation access, the reviewer read only the existing API/client/CLI/MCP entry points at public parent `55fe1e0a3c4ad85e1065f295e49d44722c3be32b` and the owner's declared interface. The independent contract, authored fixture and 557-line process receiver were frozen at 2026-10-08 12:51:55 UTC. The receiver has remained byte-identical:

- Receiver SHA256: `158aa881f34a479a0ebcca0bf679f6cdff28ef8a8588d5d2a6a585e1983e84c3`.
- Contract SHA256: `1ca24427f6dd1bcb9bcdd3e5b69614b3dd6cc1c69cb82d75c2aacd2def23b7fc`.
- Authored fixture SHA256: `4f5ca3be3b5676be3262fc9f503377231edbab562daac6e2c9f79ba5518d32aa`.

The cases use the actual native CanvasAPI and CanvasClient fixture interface, followed by real standalone CLI and MCP stdio processes against a loopback HTTP fixture. Every process receives an explicit synthetic token, loopback base URL and owned unused profile. No provider account, browser, session broker, content download or remote mutation is part of this receiving.

## Preserved results

| Source | Actual receiving | Disposition |
| --- | --- | --- |
| Public baseline `55fe1e0a` | API method absent; actual CLI exits 2 for unsupported command; real MCP catalog lacks the tool; zero HTTP calls | Establishes the missing capability |
| Native `d95a11f65314779a9a35993ae2072093fba18990` | 7 of 9 groups pass, 427 assertions; actual receiver exits 1 | Preserved negative result |
| Native `33e5d1257851ef97021c70b82cd523240a25e1b5` | Unchanged 9 of 9 groups pass, 465 assertions; actual receiver exits 0 | Complete independent behavior acceptance |
| Native `bc1baddd38b19fc454b2adb4a53acfd3cb6c254d` | Only the already-frozen G8/G9 MCP groups run: 2 of 2 pass, 82 assertions; actual receiver exits 0 | Final changed-MCP-boundary acceptance |

The first candidate's failures were genuine CLI output failures: inherited HTTPX request logs contaminated stderr. A successful CLI call emitted those lines, and an actual malformed-row refusal emitted them before its JSON error, preventing a JSON consumer from decoding stderr. G7 stopped at that first HTTP-shaped refusal in the negative run; its later 403 and malformed-JSON controls were not executed there. The successful corrected run executed all six refusal controls.

The CLI correction raises only the HTTPX logger threshold around the new command's call and restores its exact previous level in a finally block. The final MCP correction wraps anticipated ValueError messages as the SDK's ToolError. Actual final wire responses retain isError and expose the controlled positive-ID or malformed-comments explanation; a later valid call in the same native server process succeeds.

The final selector has SHA256 `704d0f247120eee445ec1d9fea5b8f5bd757b6d797b66e7852afd64c4d236a45`. It selects only receiver group dispatch; it changes neither the frozen case bodies nor product code. The seven skipped API/CLI groups are explicit in selection-proof.json. All 519 other entries in the final source manifest match the fully accepted 33e source manifest, and all 13 actual Python source modules were copied and byte-verified before the final MCP run.

## What the nine groups establish

The rich fixture preserves current submission data, four raw historical records including duplicates and an empty object, independent top-level comments, nested historical comments, submitted text/URLs/attachment metadata, original ordering and unknown fields. Mutating four returned nested branches leaves the native fixture dictionaries unchanged.

Nine missing/null/empty combinations preserve the history availability distinction. Assignment metadata always contains the six declared keys with null for missing values, while current and historical scalar absence remains absence. Zero, false and null are retained without synthetic attempts, a completeness claim, sorting, deduplication or grade/comment joining.

Both identifier positions undergo 56 pre-request refusal controls, including booleans, wrong types, Unicode digits, whitespace and path/query delimiters. Five admitted pairs cover padded IDs, a large integer, and 5,001-digit ASCII strings without integer coercion of the strings. Twenty-four malformed endpoint/row cases refuse the complete report while preserving their inputs.

Real CLI calls preserve the report across HTTP transport and reread changed backend data. Invalid IDs issue no HTTP requests. Malformed rows, HTTP403 and malformed JSON produce exit1 and a readable JSON error with empty success stdout. The real MCP catalog exposes the string/string caller; repeated calls see changed data, invalid calls remain errors, and failures do not poison the next valid call. Every successful report performs exactly the two declared GETs; only the inherited per_page=50 query addition is allowed.

## Independent source review

Candidate production code was inspected only after the unchanged complete receiving run. The reviewed delta contains five production modules: the new report/reader module and additive API, CLI, MCP and bundle wiring. Both identifiers are validated before requesting either endpoint. The reader uses only assignment and submissions/self GETs with the declared includes. It validates complete envelope/list/row shapes, keeps current/history/comments distinct, and deep-copies the complete projected result.

The subsequent final source review is limited to the ToolError import and the ValueError wrapper around only the new MCP tool. The prior CLI/API/report behavior and other tools remain unchanged.

The code and receiving are accepted for these exact native source pins. This does not claim a live Canvas account, institution-specific history completeness, browser behavior, downloaded content, submission or grade mutation, deployment, or automatic acceptance of a later main composition.

## Reproducibility and evidence

The archive retains the exact frozen receiver/contract/fixture, baseline and all three candidate process receipts, raw CLI stdout/stderr, MCP JSON-RPC transcripts, observed HTTP requests, source/dependency bindings, execution drivers, explicit final selector and separate production diffs. It also preserves the three small exact source closures, so the original negative candidate can be reconstructed after native paths disappear. Baseline code remains identified by the public parent commit.

The archive manifest lists every member's byte count and SHA256; all members were extracted in memory and checked. No executable, dependency cache, personal profile or provider credential is included.

Full-suite, lint and hosted-CI results authored by root are separate evidence and are not counted as this independent receiver's work.
