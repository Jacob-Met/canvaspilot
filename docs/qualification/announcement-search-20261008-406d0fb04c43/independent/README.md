# Independent announcement-search receiving

Accepted for exact candidate `2239de20e604318feccd82b1eec3db4553e7c0e7` / tree `aa8c890ed82177024cf9bf35a13635974ed59c26`: **23 actual CLI cases and 220 assertions passed**. The source was the exact 20-module ZIP with SHA-256 `fb96edaf741668547fb62e7bdbc06695d3a7642d42e3a3ac9d6b4b083004ef37`. Four controls against baseline `1bafdaa31f7789d8e561680cb6001bbe38b2da64` also passed 35 assertions.

The independent oracle was authored from the declared contract and the baseline reader before candidate inspection. It starts real isolated Python CLI processes, loads the complete pinned source through standard ZIP imports from a sealed inherited memfd, and reaches the existing HTTPX client through a private numeric-loopback HTTP server. The API, client, normalizer, parser, HTTP transport and search helper are the actual project code. No API or transport replacement is used. Every ZIP member is checked against its byte count, SHA-256 and Git blob, and every loaded canvaspilot module must resolve inside that sealed ZIP.

| Cases | Independent consequence checked |
| --- | --- |
| 10 literal and Unicode queries | A match after character 400, duplicate and cross-course row order, title/message field order, full Straße casefold, final sigma, absence of Unicode normalization, literal dot/brackets, significant spaces, absence of query whitespace normalization, no cross-field joining, no nontext title coercion, and successful zero matches |
| 1 empty reader | Exact zero-returned/zero-matched JSON result |
| 8 invalid argument forms | Exit 2, empty stdout, no requests and zero client constructor/default-profile/default-base calls |
| 3 reader failures | Structured stderr and exit 1 for auth, second-page 503 and repeated pagination; no partial success output |
| 1 unchanged full reader | Exact inherited normalized rows remain unchanged after adding search |

The successful searches traverse both actual HTTP pages. The first query forwards the exact start-date value and preserves repeated course IDs in order. Expected full announcement rows preserve nulls, ID 0, timestamps, context, URL, duplicate entries and nontext title values. Matching fields are checked in title/message order. The error cases deliberately place matching rows before the later failure, so empty stdout establishes that an incomplete traversal is never presented as a successful partial search.

Each child starts with an HTTPX logger at INFO and an active stderr handler. The command must suppress request noise while it emits structured output and restore the caller's level afterward, including errors. Child audit guards reject filesystem writes, nested processes and connections or name lookups outside the one authored fixture endpoint. All accepted runs recorded zero forbidden operations and zero filesystem writes. The ordinary installed Python 3.12.14 / HTTPX 0.28.1 / MCP 2.3.0 / Pydantic 2.13.5 environment was read-only. No live Canvas account, provider, browser broker, credentials, installation or ambient proxy route was used.

## Preserved original failure and exact amendment

The original 13,550-byte oracle was frozen at 19:08:14 UTC with SHA-256 `57078cf95f740bbf40753f079ca75fd04b77881b309e796ad94b73a72c2a060e`. Its first baseline case correctly observed exit 2 and zero effects, then failed an overly strict assertion that the client module had not been imported. The published baseline package's `__init__.py` intentionally imports API/client and the MCP module at package import; this is independent of constructing a client or making a call.

The original oracle and exact failed receipt remain in this packet. Before candidate intake, the successor removed only the two import-absence clauses. It still requires zero client/default calls, zero writes and zero requests for refusal. Every query, expected result, error assertion and source guard remained unchanged. The accepted 13,444-byte successor SHA-256 is `10b7c66d3e742b2ba04c6307f3529c2e4736270d5eb8e8a9704703cc9598654f`; that same source ran the accepted baseline and candidate. The candidate manifest's `runtimeSourceManifest` array was passed under the harness's `source` input key without modifying any entry or assertion.

## Files and custody

[receiving.json](receiving.json) contains the compact result and exact pins. [source-manifests.json](source-manifests.json) retains both original source manifests and the input-key adaptation. The three files under `runs/` are the exact raw JSON stdout receipts from the original failed baseline, accepted baseline and accepted candidate, including every CLI stdout/stderr, request, loaded module and effect record. Both executable oracle versions are preserved. Source ZIPs are the immutable author objects already retained alongside this packet; their full Git/SHA/byte pins are repeated here.

The receiver wrote no local artifacts because shared scratch was full. The in-memory results were preserved and uploaded as ordinary immutable Git objects for root's single canonical tree composition. This packet does not mutate the PR branch.

This acceptance applies to the exact candidate ZIP. Later planner/grade CLI composition remains root's source-preservation and hosted-CI gate; this packet makes no claim to have executed a later snapshot or a live Canvas deployment.
