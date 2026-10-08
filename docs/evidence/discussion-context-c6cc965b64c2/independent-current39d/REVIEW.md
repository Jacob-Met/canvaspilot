# Independent receiving: cached discussion reader

## Decision and exact subject

Accepted for source review on the frozen current39d composition. No product defect or source change is requested.

The receiving subject is the source export at /dev/shm/c6cc965b64c2-canvas-discussion/candidate-current39d, based on CanvasPilot main 39d835c8becb04d81b65c90d1491d2d3a2727ffe (tree 53b67d3f06b4c780e508325ec42b2b435ec57e97). This directory is a source export, not a Git checkout. All 59 exported source, configuration, test and documentation files matched their frozen SHA256, Git-blob and byte-count pins before and after each receiving run.

The reader module SHA256 is 11f955f827c29421143782518a1aaf1894d0892739c3b56c4d5e413da74555ff. The current API, CLI and MCP SHA256 values are respectively 1760e4ef1060dbf932e1d55d427e8ce57446e24cbebba0760df3fc4b4bf5b055, 1787673902c05df2dc826fe937efb956df9342d982f6f54bfaaa0f3144b5625f and 69437b00220b81e0d933b5bd01e16800c0ad880799dff8104d407031d94b33d1. The complete source manifest is included.

## Independent scope and execution

The reviewer wrote a separate receiver and fixture. Author tests were read to avoid merely repeating their cases; the full pytest suite was not rerun. Execution used the installed native Python 3.12.14 interpreter, HTTPX 0.28.1, MCP 2.3.0 and Pydantic 2.13.5. No dependency was installed.

Fourteen distinct receiving groups are accepted across two preserved runs:

- Initial run: 12 groups passed; two direct Python API groups stopped before HTTP because the receiver parent inherited a SOCKS proxy and its optional socksio dependency was absent. All actual child process environments were already isolated. These are receiver setup failures, preserved in the original receipt and tracebacks.
- Targeted replay: only those two API groups and the final source/transport check ran again. All three passed after clearing the receiver parent's proxy environment locally. Product source, assertions, fixtures and dependencies were unchanged.

The initial receipt is intentionally not rewritten to claim 14/14. The targeted driver and its small environment/selection delta are retained separately.

The runs together executed 14 real CLI processes and two persistent MCP stdio processes. Thirteen MCP tool calls and 65 loopback HTTP requests were recorded. Of those, 47 were logical Canvas GET requests; the remainder were broker health checks. Seventeen logical GETs traveled through a local broker POST envelope. Every broker envelope had method GET, no request body, and the expected Canvas path. There was no Canvas write, direct fallback from broker mode, profile creation or browser startup.

## Consumer findings

A distinct ten-entry heterogeneous forest exercised nested and deleted context, contradictory source parent IDs, explicit empty versus absent replies, numeric/string identity collisions, duplicate entry and participant identities, missing/boolean identities, opaque source fields and a separate new-entry stream.

An independent consumer rebuilt the exact original forest from returned path, parent_path, replies_supplied and entry fields. The source parent_id conflict remained inspectable and did not reparent a reply. The integer 9007199254741009 remained an exact Python integer and exact decimal JSON token through the real API, CLI and MCP responses; numeric 100 and string "100" remained distinct. Raw JSON report artifacts are stored as text to preserve those numeric tokens across packaging.

Unread focus retained exactly paths [0], [0,0], [0,0,0] and [1], with context flags true, true, false and false. A deleted ancestor retained its raw fields while derived text and author remained unavailable. An entry with source read_state "unread" but absent from the actual unread marker list was reported read; forced-state membership remained a separate supplied fact. Duplicate entry identities stayed unknown, and duplicate participants were not used for attribution.

Missing/null unread lists refused focused selection; explicit empty lists produced a known empty selection. Unmatched-only markers yielded no located rows while retaining duplicate unmatched identifiers and warnings. A marker matching duplicate IDs refused ambiguous focus. Persistent Python and MCP consumers recovered on the next explicit valid request and used the new marker set without stale selection or implicit retry.

The report preserved the separate new_entries stream without merging it into the cached forest. Topic-declared counts remained independent from the ten observed rows and four focused rows. Mutating report fields did not alter either input, and later input mutations did not rewrite previously returned fields.

## Actual interface and failure boundaries

The Python API rejected seven invalid selections before any HTTP request. Positive decimal IDs with leading zeroes were preserved in both actual request paths. The original get_discussion method and canvas_get_discussion MCP tool returned their original raw topic/view pair exactly.

Real CLI token reads and broker reads produced the same full/focused contract. A first topic request returning 401 or 403 stopped after one GET; no view read, initial post, retry or partial success report followed. Empty 204 topic data, HTML view data and truncated JSON produced nonzero CLI errors with empty stdout. Because the inherited raw reader obtains both resources before shape validation, the 204 topic control still made the normal view GET; this is observed behavior, not an inferred short circuit.

A broker authentication refusal and a broker-reported native 503 remained visible. When broker health itself was unavailable, one health request was made and no Canvas request or browser/profile action followed. Later explicit valid requests recovered. The fixture distinguishes the broker's outer POST /fetch from its inner Canvas GET, so the receipt does not incorrectly classify transport POSTs as Canvas mutations.

The MCP schema exposed string course/topic IDs and a boolean unread_only field, plus readOnlyHint true and destructiveHint false. Actual stdio calls rejected numeric IDs, a string or null unread flag, and a path-bearing ID before HTTP. A single persistent token MCP process recovered after unread ambiguity; a single broker MCP process recovered after native 503 and missing unread metadata. The existing raw and posting tools remained in the inventory; no posting tool was invoked.

CLI stderr can include inherited HTTPX logging. Assertions inspect the final semantic error JSON and retain the complete stderr transcript. MCP errors are recorded as actual protocol isError responses; generic tool error text is not expanded into an invented structured server error.

## Independent current-owner preservation

The reviewer fetched the named current GitHub tree and five modified base-file contents independently. All 50 exported paths outside the nine-path reader contribution match current main by Git blob. Reversing exactly the declared reader insertions/replacements recovers the API, CLI, MCP, curated bundle and README base bytes exactly. Existing API and MCP function ASTs also match; the independent ast.walk count includes 48 API named definitions and 40 MCP definitions. This verifies owner preservation without relying solely on the author's declaration.

This source comparison includes the current assignment/submission-history owner additions. It does not relabel the historical 79a author run as current. The author's current39d full gate and root's separate source review are outside this independent run count.

## Primary contract and limits

The official full-topic API documents a cached threaded view, supplied unread/forced markers, possible access/cache errors, and a separate optional new-entry stream:
https://developerdocs.instructure.com/services/canvas/resources/discussion_topics#method.discussion_topics_api.view

Current source:
https://github.com/Jacob-Met/CanvasPilot/tree/39d835c8becb04d81b65c90d1491d2d3a2727ffe

These controls establish behavior against explicit synthetic API responses through real native consumer processes. They do not establish access to any school, a live Canvas discussion or browser session, the freshness/completeness of Canvas's cache, or a deployment. Read-only refers to the product's outgoing Canvas operations; the receiver's local fixture broker uses POST as its transport envelope.

No author source, author tests, installed environment, shared profile, browser state or GitHub object was modified by this receiver. Its only runtime files were logs in a private transient /dev directory. Every artifact was exported in the same process before that transient directory disappeared.

## Preserved preparation evidence

A preliminary read guessed a nonexistent config.py path and failed before any runtime test; that read failure is kept separately. The initial parent-proxy failures are in the original run, not hidden as successful tests. The replay applies only process-local environment isolation and targeted group selection. Raw response artifacts, complete stderr, source pins, request logs and exact drivers are retained for review and reproduction.

