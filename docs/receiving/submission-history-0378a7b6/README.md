# Offline submission-history receiving

Contributor: `chatgpt-0378a7b6b7c2/msi_product`. Claim: [CanvasPilot84](https://github.com/Jacob-Met/canvaspilot/issues/84).

The new `export-submission-history COURSE ASSIGNMENT --out NEW.html` command saves the complete normalized self-history reader result as a passive, readable HTML file. Current submission data, every returned historical record and top-level comments stay separate. It preserves returned order, duplicate/missing attempt numbers, zero/null/false/empty/unknown fields and exact local JSON. It adds no grade attribution, inferred chronology, missing attempt reconstruction or attachment fetch.

## Source and original witness

Original main: `f618c3ed13f191ea58642283c1f9cd45a0c1ca81`, tree `1bcfff90694cdb8358684ada58ff349562244de7` (1,333 tracked leaves).
Authored production commit: `7371f315869cbbea518c1ba2f1ff6e5639d384c0`.
Current-parent composition: `6fdb3dc955426da7667e1f4e3844c6741077369f`, tree `bec620b72b9ed59f4d99981e80728a90a880a955`, parent main `a5e7bec9f93132341e4031de184487310a51daae`.

Production changes are one dedicated formatter, additive CLI spans, one focused test module, guide and README pointer. Existing history reader, API/client, authentication, MCP/broker, pagination, shared publisher, dependencies and workflows are unchanged. The selected-record comparison owner remains distinct: this report reads the whole returned history without pair comparison.

The native original CLI succeeded through the existing history reader and refused the missing export command. Frozen fixtures contain authored fictional values, including current attempt4 with a mismatched grade, returned attempts[2,1,2,absent], zero/null/missing scores, nested versus top-level comments, literal markup and control characters. Only a disposable loopback endpoint and synthetic credential were used.

`preimplementation-freeze.json` pins the initial contract, drivers, fixtures and baseline receipts. Corrected receiving tools and failures are explained in `failure-notes.md`; initial results are retained without replacement.

## Observed qualification

- Actual MSI CLI receiving passes six groups: unchanged two self GETs, exact complete JSON, occupied output before reads, unavailable versus empty, malformed history, later-read failure, invalid selector and no partial report. The same authored input bytes remain unchanged. The composed current-parent CLI also passes these groups.
- Actual installed Chrome receiving passes nine groups: every visible field and returned order, current-grade context, separate comments, inert values, keyboard anchor/download, 390px layout, exact downloaded JSON, print generation, unavailable/empty messages, zero observed external requests and runtime errors.
- Desktop and phone screenshots were visually inspected. The native four-page PDF's extracted text retains all records and comments; PDF page-image inspection is not claimed.
- Independent root source and actual-artifact acceptance re-admits all 45 visible fields in original order, decodes the complete JSON and its digest, and checks record/comment attribution and absence of active resources. It imports no target implementation.
- Final formatter SHA-256: `b574c8e81f3f48753723416645c252a23a77368c1812fe7334c69d51cd86d17f`. Its three qualified artifacts remain byte-identical after narrow lint corrections.
- Full Windows gate limitations and exact clean-base replay are preserved. Linux Ruff passed against the exact composed tree. Its full pytest run reached 90% with four earlier failure markers, then exceeded the bounded 900-second limit; no complete Linux suite pass or attribution of those markers is claimed. A transient ENOSPC and high host load were also observed. Exact original logs, runtime, unchanged tree and limits are retained in `linux/`. Hosted CI/publication remain separate.

## Reproduction and scope

`receive_cli.py` accepts baseline/candidate mode, source root and proof root, with optional unique run name. It expects the two authored fixture JSON files beside it and the project's declared dependencies in the selected Python. The browser driver uses Playwright Core and an explicit existing Chrome path from this native receipt; adapt only those runtime paths on another host and retain its source hash difference.

The received native packet is under `D:\Hamon\worktrees\canvaspilot-history-0378a7b6-proof`. The Linux receiving clone/proof are `/home/jacob/canvaspilot-history-0378a7b6-linux` and its `-proof` sibling. Shared dependencies were reused read-only. All outputs and fixtures belong to this contribution; no installed service, live Canvas account or real learner record was used.

The manifest binds exact copied evidence bytes. The complete report download is normalized reader output, not raw HTTP pages, linked files or a restorable Canvas backup. Creation time is local file context. Returned history can be incomplete, and data may change after export. Ordinary repository publication and hosted gate receipts are separate integration facts.
