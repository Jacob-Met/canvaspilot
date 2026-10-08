# Inbox review: source repair and native receiving

This packet supports [CanvasPilot issue 49](https://github.com/Jacob-Met/canvaspilot/issues/49). The CLI now lists an inbox and opens a conversation through the existing Python readers. Opening a conversation explicitly sends `auto_mark_as_read=false`, and malformed identifiers are rejected before transport. Existing unread, read and archived state is retained in the authored receiving fixtures.

## Why the change is needed

The [Canvas Conversations API](https://developerdocs.instructure.com/services/canvas/resources/conversations), checked on 2026-10-08, documents that reading a single conversation defaults to automatically marking it read. The original shared reader omitted the flag. Its inbox list also sent `scope=inbox`, although Canvas documents the non-archived inbox as the default obtained by omitting scope.

The repair adds `canvaspilot inbox [--scope inbox|unread|starred|archived|sent]` and `canvaspilot conversation ID`. Both return the original JSON. The existing Python readers and MCP tool names/signatures stay in place. Conversation IDs must be positive ASCII decimal integers or digit strings; booleans, floats, path/query/fragment strings, whitespace and zero are refused. Positive leading-zero strings remain admitted without a promise about how a particular Canvas server interprets that spelling. The MCP metadata describes these readers as read-only and idempotent.

An independent reviewer found a consequential first-candidate defect: a fragment-bearing string ID put the false flag inside the fragment on the session path. The actual session envelope therefore reached the synthetic provider without that query, and the unread state changed. The final shared-reader admission check closes this route before any request. The original counterexample, first-candidate source and failures remain in this packet.

## Exact source and scope

- Base: `ca2318fe7c56d2e4ec1b363ff8a945ab78bf4a0c`.
- First native candidate: `d1032f1eb44167282ef47803a42a86e25fb69001`.
- Reviewed native successor: `db32bde55db5080ed7ee856faab5cf1a2b5c949a`, tree `16e338cbcb783a57dad3357568a9539e1032c3f0`.
- Six owned paths: `src/canvaspilot/api.py`, `src/canvaspilot/cli.py`, `src/canvaspilot/mcp_server.py`, `tests/test_inbox_review.py`, `docs/inbox-review.md`, and the additive usage section in `README.md`.

`source-records.json` gives the Git blob and SHA-256 of all six paths. `source-changes.patch` is the complete base-to-successor patch; `candidate-v2.patch` preserves the corrective step. `native-history/` retains the exact commit objects. The peer package keeps frozen source copies for every observed stage. The published commit may have a different parent and identity when composed on current main; its actual tree and preservation check are a separate publication receipt.

Source review found no changes outside the two owned API readers, the additive CLI parser/dispatch statements, the two existing MCP tools' descriptions/annotations, and the new test and guide. Client, broker, bundle, dependencies, workflow and tool inventory are unchanged at the reviewed source. Shared files may receive other owners' additive work during publication; that composition must preserve it.

## Observed qualification

| Gate | Source and result |
| --- | --- |
| Original authored 19-case receiver | Base: 5 passed, 14 failed, no skips/errors. |
| First candidate with the same authored receiver | 13 passed, 6 failed. These six failures were receiver assumptions about inherited HTTPX INFO lines on stderr; actual outputs and exit behavior were retained. This run is not presented as a passing qualification. |
| Corrected authored receiver plus ID admission cases | Reviewed successor: 34 passed, no skips/errors. The receiver admits only the existing loopback HTTPX INFO line format before a final JSON error; other stderr still fails. |
| Inherited API, fixtures, broker encoding/links, token pagination and feedback tests | Reviewed successor: 96 passed, no skips/errors. |
| Independent normal journeys | The unchanged 10 groups fail on the base and pass on the first candidate. Each journey covers token and session modes. |
| Independent fragment counterexample | First candidate: token mode passed, session mode failed and changed the synthetic unread state. |
| Independent final receiving | Reviewed successor: 14 groups passed, no skips/errors. This includes the original 10 groups, the same two fragment witnesses, and two admission groups challenging 18 invalid values each through Python and registered MCP. |

These are distinct recorded selections, with overlapping behavior; the counts are not a claim of that many unique product scenarios. The author and inherited runs use native Python 3.14.4 and the already installed dependency environment without modifying it. Exact argv, source before/after hashes, actual process codes, JUnit and raw stdout/stderr are under `author/`. Independent process, state, MCP and source-preservation receipts are under `peer/`. `peer/REVIEW.md` explains its guarded replay procedure.

All final author/inherited source hashes remained identical before and after receiving. The independent reviewer separately verified the six-path fence and preserved unrelated API/CLI/MCP syntax and runtime bytes. Source Ruff and whitespace checks passed before freezing; hosted CI is a subsequent gate on the actual published head.

## Practical boundaries

Receiving uses authored loopback providers, disposable profiles and synthetic tokens. The token path uses actual HTTPX requests; the session path uses the actual broker envelope and a modeled provider response. Registered MCP stdio and real CLI subprocesses were exercised. No live school, browser, SSO/cookie flow, notification state, student outcome or attachment download is claimed. The tests never fetch the inert attachment URLs.

The result is a point-in-time read; another Canvas client can independently change conversation state. Inbox pagination keeps the client's existing 40-page safety limit and opaque continuation behavior. CLI stdout is JSON on success and empty on failure. Existing HTTPX INFO diagnostics can precede the final JSON error line on stderr. No request is added to reply, archive, star, mark read, or download attachments. The arbitrary REST escape hatch retains the server's normal defaults.

The source and receipts were produced in private native `/tmp` workspaces because the persistent ThinkPad volume had no free space. Git publication is the durable repository record; the volatile workspaces are not described as permanent storage. This work does not install a service, change the designated Windows hub, or perform firmware, live migration or cutover actions.

`file-inventory.json` hashes every packet payload except itself. Git binds the inventory's own final bytes, avoiding a circular checksum.
