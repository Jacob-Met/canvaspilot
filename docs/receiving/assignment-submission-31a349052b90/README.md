# Assignment submission visibility: source receiving

This directory preserves the native source and receiving evidence for the
assignment-row submission projection claimed in
[HAMON #140](https://github.com/Jacob-Met/hamon/issues/140#issuecomment-6059762346).
The [usage guide](../../assignment-submission.md) describes the product fields
and their limits.

The contribution retains eight reported current-user submission fields through
the existing assignment and sync API/CLI/MCP paths. Missing/null data remains
unknown. The existing aggregate `has_submitted_submissions` field and raw
self-submission reader keep their meanings; no request or policy calculation is
added.

## Frozen source and independent acceptance

Publication parent: `79a2f2b2cbb7e74128d731cf096c7e86f1942d4b`, tree
`0114a6230c473c1ee1d01b99c7121c754b781d54`. This parent includes the actual PR35
pagination and PR45 calendar/provider merges. All 49 native inputs were
materialized and hashed against that exact source. The six contribution blobs
and patch remain unchanged; the current client, broker, CLI and calendar helper
are preserved exactly.

The [manifest](manifest.json) pins the six product/test/guide files and both
archives. [Root's independent source review](root-source-review.md) accepts the
final helper and API hook without another source edit. The engine appendix
independently executes the session Handler and CLI on parent `ca2318fe` against
that final feature source. Its separate [current-parent binding](current-parent-binding.json) and
[static proof source](bind-current-parent.py) record which exercised source
spans remain unchanged on `79a2f2b2`.

| Evidence | Result and boundary |
| --- | --- |
| Original main `55fe1e0a` | 414 existing native tests passed. |
| Unchanged original API witness | Failed specifically because `submission` was omitted. |
| Unchanged original process receiver | Five feature failures and three preserved upstream-failure passes. |
| Feature on original base | All 447 tests passed, including 33 new cases. |
| Feature composed onto `ca2318fe` | Eight actual API/CLI/MCP PAT cases passed; 28 recorded GETs and no per-assignment submission reads. |
| Independent session receiving on `ca2318fe` | Four actual CLI processes across baseline and final candidate; corrected evaluation gives baseline one pass/one missing-field failure and final candidate two passes. |
| Publication composition on `79a2f2b2` | All six feature blobs and the exercised session path remain bound by source identity; no duplicate native invocation is counted. |

The 447-test result belongs to the original base. It is not described as a full
execution of later source. Before publication, one extra final LF was removed
from the helper, process test and guide; both Python ASTs and all other bytes
were proved identical. The final helper was then directly executed by the
independent session receiver. Hosted lint/full-suite results for the actual PR
head and final merge binding belong to the PR's receiving records.

The later broker adds a health capability field that the unchanged assignment
client does not consume. Its provider-routing changes are below the authored
browser-terminal seam, and the CLI change is confined to `export-calendar`.
Those new browser/provider behaviors retain PR45's own separate qualification;
the earlier four session processes are not relabeled as executions of them.

## Reproduction archives

- [Author native packet](author-native-receiving.tar.gz) contains all native source
  stages, tests, runners, original failures, raw CLI/MCP responses, decoded GET
  traces, runtime identity and exact source/EOF-composition proofs. All 312
  members were decoded and read back before publication.
- [Independent session appendix](independent-session-receiving.tar.gz) preserves
  the independent receiver, the four raw native process streams, original
  evaluator rejection, corrected offline evaluator and final source acceptance.

The session receiver uses the actual current broker Handler, HTTP transport,
pagination and CLI, with authored data only at the browser-terminal result seam.
It verifies opaque Link continuation and refuses missing later Link metadata
with empty stdout. The first evaluator incorrectly demanded empty stderr and
rejected normal HTTPX INFO lines before payload assertions. Its corrected
evaluation inspects the same retained streams; it runs no additional process.

All fixtures are synthetic. Existing Python dependencies were borrowed read-only;
no browser, live Canvas/student data, installed broker, account or deployment is
involved. The final published-head CI and normal current-parent merge checks
remain separate from these local/source receiving records.
