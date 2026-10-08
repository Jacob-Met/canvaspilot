# Submission-attempt history: pre-implementation contract

Contributor: chatgpt-0378a7b6b7c2/msi_product.
Original source: f618c3ed13f191ea58642283c1f9cd45a0c1ca81.
Native isolated source: D:\Hamon\worktrees\canvaspilot-history-0378a7b6.
Branch: work/0378a7b6-submission-history-report.

## Beneficiary and existing gap

A student can already request the current self submission and the history Canvas returns. The current CLI emits JSON. A saved, readable report should let that student review the returned versions later or print them, while retaining the existing distinctions between current submission, individual returned history records, and top-level comments.

## Product fence

Add export-submission-history COURSE ASSIGNMENT --out NEW.html through existing CLI authentication options. Add one dedicated formatter/builder and focused tests and documentation. Reuse the current page-packet exclusive byte publisher; do not modify it. Use CanvasAPI.submission_history exactly once. Its two GETs, self-user selection, original projection, returned ordering, and read-state behavior remain unchanged.

Do not edit feedback, grade review, original history reader, API, MCP, authentication, pagination, source submission, upload, attachments, discussion, groups, module progress or page/calendar export behavior. Neighboring grade-review export and groups scopes remain owned. Native coordination coverage is partial; GitHub ownership read and a normal project claim are queued until the observed primary API reset.

## Required report

- Standalone script-free HTML with inline styles and no automatic external resources. Native browser Print should produce a readable document.
- Requested course/assignment selectors and creation time are context; the full assignment metadata is shown as returned, including missing fields. Creation time is not a Canvas observation or submission time.
- The current submission is a separate complete record. If its grade_matches_current_submission is false, explicitly say that its grade may describe an earlier attempt; unknown never becomes a confirmed match.
- Every returned historical record appears once in original order, identified by its returned position. Duplicate/missing attempt identifiers and empty records remain; never sort, deduplicate, fill gaps, append the current record or infer complete coverage.
- Every field remains attached to its original record, including score zero, explicit null, false, absent fields, submitted body, attachments/media metadata and additional nested fields. No current grade, date, comment or identity is copied into a historical record.
- Top-level comments have their own section. They are not assigned to history records by attempt, position, author or time. Nested comments stay in their originating record.
- A missing/null history association is unavailable; a returned empty list is empty. The same distinction holds for top-level comments.
- Exact complete normalized report JSON can be downloaded locally. It is the unchanged reader output, not raw HTTP pages or a backup. Arbitrary provider text, URLs and markup remain inert.
- Report source JSON up to4MiB and final HTML up to16MiB; refuse rather than truncate. Preserve arbitrary finite JSON values and string-keyed containers, including absent/null/false/zero distinctions. Malformed containers or non-JSON values are errors.
- Existing target files, directories and symlinks remain protected before reads and at exclusive publication. Failed reads/rendering create no report. Existing writer publication/cleanup semantics are preserved.
- CLI success is structured JSON on stdout. Expected source/value/publication failures return structured stderr and exit1, never a fabricated empty report.

## Frozen receiving plan

Before product edits, author a native loopback provider fixture and a CLI receiver. Witness the original history JSON through the actual CLI and the absent export command on the original source. Keep those original requests, responses and output hashes.

The same receiver must drive the candidate command and verify two exact self GETs without read_status, successful file bytes/JSON roundtrip, source immutability, preserved current/history/comment separation, protected target, unavailable/empty distinctions and refused source failure. Use only authored fictional data and a synthetic credential local to the fixture.

A separately frozen browser receiver opens the generated real report from file: in a fresh owned Chrome profile, compares original displayed values by section and returned order, downloads the actual complete JSON, verifies keyboard navigation/390px layout, and records zero observed external requests/errors. It also generates a print PDF and retains screenshots; file generation alone does not certify their content.

Focused maintained tests protect the report semantics and CLI boundary. Run the existing repository lint/test gate once after the candidate. Independent review should challenge record attribution and unknown/empty behavior without duplicating the full suite.

## Ownership and publication

No AGENTS.md, CONTRIBUTING or SKILL.md exists in the original tracked tree. The normal CI runs ruff and pytest without path filters; focused added tests enter the existing gate automatically. No new workflow is needed.

Fresh native advisory scan at selection:211 readable /15 unreadable records. Relevant records are retained at /home/jacob/msi-discovery-0378a7b6/canvaspilot-coordination.json on ThinkPad. No history-report owner was found in readable coverage. This is an external source contribution, not a native goal lease. Parent and Mac received the proposed scope before edits. Publication remains held until the ordinary API reset and project issue read.
