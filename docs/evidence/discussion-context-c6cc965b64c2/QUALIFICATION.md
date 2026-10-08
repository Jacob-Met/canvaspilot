# Discussion reader: accepted qualification and current composition

This index binds the additive discussion reader to the current inbox-aware source on `a5ce672e5b3580c1f52e13c49eefee830f11346c`. The earlier [author README](README.md), receipts and source snapshots remain immutable evidence of their named subjects. They do not become later-current test runs.

## Delivered workflow

`canvaspilot discussion COURSE TOPIC [--unread-only]`, `CanvasAPI.discussion_thread()`, and the read-only `canvas_discussion_thread` MCP tool open the existing cached topic/view response as a readable report. The report retains source fields and returned reply structure, typed identifiers, cleaned text, structural paths, unambiguous participant attribution and explicit read associations. Unread focus keeps selected entries together with their ancestors; missing or ambiguous unread metadata fails visibly instead of implying an empty discussion.

The existing raw `get_discussion`, listing/posting methods, client, session broker and transport behavior are retained. A local broker may use an outer HTTP POST to carry an inner Canvas GET; the qualification records these separately. The reader adds no Canvas write, automatic retry, new-entry merge or implicit mark-read operation.

The [user guide](../../DISCUSSIONS.md) describes the report and its boundary. The primary API contract is [Canvas discussion topics](https://developerdocs.instructure.com/services/canvas/resources/discussion_topics), especially the [cached full view](https://developerdocs.instructure.com/services/canvas/resources/discussion_topics#method.discussion_topics_api.view). Our association/ambiguity policy is documented separately from the server contract. Cached-view output is eventually consistent; these local synthetic controls do not establish live-school access, browser execution, or server freshness.

## Distinct qualification subjects

| Subject | Result | Meaning |
| --- | --- | --- |
| Unchanged original `79a2f2b2` baseline | 536 tests and 6 subtests passed; one optional Chromium skip | Raw topic/view reader works; the new terminal command, API method and MCP tool are absent. |
| Original author candidate on `79a2f2b2` | Ruff passed; 558 tests and 45 subtests passed; one optional Chromium skip | Full authored/inherited suite on the original source; all 53 executed inputs unchanged. |
| Submission/history composition on `39d835c8` | Ruff passed; 658 tests and 45 subtests passed; one optional Chromium skip | Full suite after the actual owner source changed; all 59 executed inputs unchanged. |
| Independent receiver on `39d835c8` | 14 distinct planned groups accepted across two recorded runs | Initial 12 pass plus two receiver-parent proxy setup failures before HTTP. The targeted replay passes only those two groups plus a source/transport check (3/3). |
| Lead source review on `39d835c8` | Accepted; zero runtime cases | Separate direct review of the pure module, guide, registration seams and official contract; nine source paths independently pinned. |
| Inbox composition on `a5ce672e` | Ruff passed; 60 tests and 39 subtests passed | Focused discussion, native consumers, current owner inbox and tool catalog checks. This is not a repeat of the 658-test suite. All 60 executed inputs unchanged. |
| Independent dispatch replay on `a5ce672e` | 4/4 groups passed | Current CLI focus, token MCP full/raw, broker MCP focus, and final source/transport pins. The accepted forest oracle is reused for this concrete dispatch composition risk. |

The Chromium skip is explicit and unchanged: `CANVASPILOT_CHROMIUM_BIN` is not supplied. No dependency installation, browser session, service deployment or live Canvas request was needed.

## Independent evidence

[The current39d receiver](independent-current39d/REVIEW.md) exercises a distinct heterogeneous forest, contradictory source parent IDs, numeric/string/duplicate identities, deleted context, forced/read disagreements and a separate new-entry stream. It preserves the raw JSON integer `9007199254741009` through the real consumers. It checks malformed/ambiguous response recovery and first-request HTTP refusals, then exercises the no-token session-broker path through a loopback-only synthetic broker.

The complete current39d packet has 43 exact files, 481,066 decoded bytes; outer uncompressed JSON SHA256 `9219971360d6747fca0b70bf028e05bb317e90d0c5ea5597a539ca7e27d6803f`. Its 14 CLI and two persistent MCP processes made 13 MCP calls. Across both recorded runs, 65 wire requests comprise 47 logical Canvas GETs and 18 broker health checks; 17 logical GETs traveled inside local broker POST envelopes. No original setup failure or raw case integer has been normalized away.

The separate [current-a5 dispatch packet](independent-currenta5/REVIEW.md) records three real consumer processes, ten wire requests and eight logical Canvas GETs. It verifies all 51 exported unowned current files and reverses only the new additions to recover all five modified owner files by their exact primary Git blobs. Both broker envelopes still carry inner Canvas GETs.

[The lead source review](independent/root-source-review-current39d.json) remains bound to `39d835c8` and contributes no extra runtime result.

## Source and tree preservation

The a5 canonical base tree is `0661a7005e577864cb87bc41e0e715409c92ee76`, reconstructed from all 948 leaves. The product-only overlay tree is `56c9809dcfd6833c9620aad52acbccd33a637842`. There are nine product/source/test/documentation paths: five additive edits to existing files and four new files. All 943 original leaves outside those five paths are retained exactly, including the merged inbox/history implementations, client/session/broker methods, dependency manifest, CI and inherited tests.

See [current source binding](composition/currenta5-source-binding.json), [owner composition](composition/currenta5-composition.json), [complete base leaves](composition/currenta5-base-leaves.json), and [current product patch](composition/currenta5-product.patch). Removing only the documented additions recovers all five edited owner files byte for byte. The new pure module and new API/MCP function bodies match the original functional freeze.

All 51 author evidence paths from the original 60-path publication packet are carried unchanged. Its nine then-current product files are recoverable from the current unchanged files and four exact [current39d beforeimages](history/current39d-source/). The original author packet is SHA256 `7fb908dd153f6aed4f37576cc2eb6b5105d5045ba6ac8cb3163f01f9f4f999e4`, 978,163 bytes. Its old prospective tree identifiers remain historical, not assertions about the later publication tree.

The final publication manifest lists the source/evidence payload hashes. GitHub readback, actual parent and CI are separate publication checks; local evidence does not claim those gates have already run.

## Preserved negative evidence

The initial unit receiver used an incorrect Python attribute name for MCP wire annotations; the wire product annotation was already correct. The first full candidate run reported 550 pass / 15 failures: eight new stderr assumptions conflicted with inherited HTTPX logging, and seven unchanged owner tests encountered shared-filesystem ENOSPC. The available tool-output excerpt is marked truncated rather than represented as a complete log.

A second launcher lost its pytest capture when it incorrectly assumed a transient `/dev` directory persisted between invocations. Its pytest outcome is not qualified. The final launcher creates and exports its own namespace within one process. Ruff corrections are retained separately, including the narrow existing ValueError-compatible annotations and test import sorting.

The independent current39d run retains two parent-proxy setup failures before HTTP and their narrowly scoped replay. Successful receipts do not overwrite those failed attempts. All fixture traffic is local and synthetic.
