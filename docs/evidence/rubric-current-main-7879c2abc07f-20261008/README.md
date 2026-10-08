# CanvasPilot rubric receiving on the integrated current source

The original owner integrated [PR41](https://github.com/Jacob-Met/canvaspilot/pull/41) at `5eb681b1714a64a273fc273ffe9985426474f52c`, tree `48fbcdc168ea0f25995f0bdcc1de47162abbf386`. Its parents are current calendar/feedback main `a03a8637efad8ff22103a0c5018c93f7ecbb7d8d` and original rubric owner head `5930d6fa58bf3262033dcdb00ff8580a87d61860`. The independent `7879c2abc07f` lane made no product merge or owner-branch change.

This packet preserves the [receiving claim](https://github.com/Jacob-Met/canvaspilot/pull/41#issuecomment-6059102469), its frozen source proposal, one unsuccessful local baseline attempt, and the current hosted/runtime source bridges that establish acceptance. It is archived on an isolated evidence branch; its helper scripts are historical receiving inputs.

## Actual receiving and integration evidence

[The complete source bridge](source-bridge.json) verifies that all 347 leaves and modes of the privately composed tree `718e9d88c9ed56ec257bc274774d0e8e4949eb6d` match the actual 353-leaf merge. The only six additional leaves are the original owner's later feedback-composition evidence. No tested production or maintained-test byte changed across that bridge.

The exact [PR job](https://github.com/Jacob-Met/canvaspilot/actions/runs/37771938513/job/113293389510) checks out `ef0ebc73614c9ae52d0aa1da4acd33121ae6a3de`, with current a03 and owner 5930 as parents and the same 48fbcdc tree. Its [complete decoded log](evidence/ci-pr-job-113293389510.log) reports Ruff success and **323 passed in 24.94 seconds**. The subsequent [main-push job](https://github.com/Jacob-Met/canvaspilot/actions/runs/37773429382/job/113298324457) checks out the actual 5eb681b merge and reports Ruff success and **323 passed in 32.48 seconds**; its [decoded log](evidence/ci-push-job-113298324457.log) is also retained.

[Independent public-entrypoint review](public-receiver-bridge.json) verifies the original owner's 20-method normal and optimized receivers, each with 111 public invocations. The test, fixture and public-output hashes match their original records. All preexisting Python modules other than CLI are exact between owner 5930 and the actual current composition. Removing only the calendar parser nodes and its isolated dispatch branch restores the entire owner CLI AST. Those valid 20/20 results carry forward on their recorded source; this lane did not execute another normal or optimized receiver.

## Preserved local failure

One local current-main baseline began at 11:55:13 UTC, just before the newer hosted qualification was discovered. It completed at 11:55:47 with **257 collected, 256 passed and one failure**. The [raw log](evidence/baseline-run.log), [receipt](evidence/baseline-run.json), [JUnit XML](evidence/baseline.xml), [private guard](guard/sitecustomize.py) and [runner](run_receiving.py) remain byte-exact.

The failed case supplied an empty host to the real broker's loopback-binding check. Our receiving-only DNS guard raised `PermissionError`; that changed the normal resolver failure class expected by the broker and its test. This is an instrumentation failure, not evidence of a rubric defect or a successful local baseline. The guard was not corrected or rerun after the independent current-source CI result was available.

All 72 frozen baseline/candidate source inputs matched before and after the attempt. Guard records contain 22 Python startups bound to our own baseline package, 143 synthetic loopback connections and one refused empty-host resolution. The candidate suite and additional local receiver stages were never started. Subsequent free space fell below the 16 MiB receiving floor, so local writes and runtime work stopped; the existing files were read directly into this Git packet without changing them.

## Product and primary-contract review

The new brief projects already supplied rubric criteria/ratings and retains source IDs, text, zero/fractional points, range/scoring flags and grading/display context. Unknown grading use remains distinct from explicit advisory false. Malformed optional fields produce local diagnostics while ordinary assignment fields remain available; settings are copied so caller edits do not alter the received object.

The parent checked these semantics against the [official Assignment API](https://developerdocs.instructure.com/services/canvas/resources/assignments) and [Instructure's assignment serializer](https://github.com/instructure/canvas-lms/blob/master/lib/api/v1/assignment.rb). Those sources identify rubric data and grading use as optional associated metadata, and the serializer includes the outcome and display fields retained by the projection. The existing assignment request supplies the data; this source change adds no account request.

The earlier source proposal and source-review records intentionally retain their original pending status. The later bridge and actual hosted logs establish the final disposition. Original `ultra-20b27c2e` owns the implemented contribution and integration. All runtime evidence uses the maintained offline fixtures or our synthetic local harness; no live Canvas account, student-data receiving or deployment is claimed.
