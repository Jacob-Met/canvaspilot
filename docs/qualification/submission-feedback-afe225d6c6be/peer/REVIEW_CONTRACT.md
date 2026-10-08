# Independent CanvasPilot submission-feedback semantic review

Base: Jacob-Met/canvaspilot at 5b1780ca4fcdce3d5f997cee401c86806ece822a.
Scope: issue #34 feedback read flow, complementary to the parent's actual API/CLI/MCP interface receiver.

This contract is recorded before the product implementation freeze is inspected.

1. Rubric association is permitted only for a unique exact string criterion ID.
   Duplicate, absent and non-string IDs cannot guess, stringify, or consume a
   submission assessment. Unmatched assessment entries must remain recoverable.
2. Transformation must not mutate the Canvas assignment or self-submission
   objects supplied by the client, including nested criteria, metadata, comment
   attachments/media, and assessment records.
3. If reading either assignment or self-submission fails, the original failure
   must propagate. A transport/access/API failure must not become empty or
   missing feedback. An assignment failure must not trigger a submission read.
4. Missing assessment, an empty assessment mapping, zero scores, empty comments,
   and explicit non-current grade markers retain their distinct meanings.

Use isolated frozen source, project-native Python and deterministic fake client
responses/errors. No live school, account, profile, broker or authentication
operations. The implementation owner retains source ownership; root controls
publication. Parent already covers the four principal API/CLI/MCP cases, so
this review will not repeat them without a concrete remaining risk.
