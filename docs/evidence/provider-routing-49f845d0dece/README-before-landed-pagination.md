# Provider routing correction and compatibility receiving

This packet supersedes the complete-provider acceptance claim for PR45's original
head1748e52. The original configured-provider correction and every historical
packet remain unchanged. The final implementation includes a real broker routing
repair and an explicit old-broker compatibility refusal.

Final native product freeze: 7452703ec4f55e7f63c11276a92dbfd647f6e718.
Actual main composed: 55fe1e0a3c4ad85e1065f295e49d44722c3be32b.
Only calendar_export.py and session_broker.py change in production. Current
main's CLI/API, rubric, announcements and module-progress changes remain exact.
No open PR35 client/parser source is imported; its owner retains integration.

## What the source now establishes

The calendar selects the configured session provider and requires exact boolean
provider_origin_checks=true from the running broker. A missing/false/ambiguous
capability returns an actionable updated-broker restart instruction before
assignment reads. Fixture/token exports retain their existing identity and do
not probe the broker.

The guarded broker prefers an existing page on the configured HTTP origin.
A fetch refuses a mismatched selected page or request URL instead of navigating
to another school. The browser expression resolves one target against the page
location, checks its origin and passes that same absolute target.href to fetch;
document.baseURI cannot redirect dispatch. Response/page origins are checked
before rows return. The former broker health and response structure is retained,
with only the new capability added.

This does not lock the browser, authenticate the local broker, certify school
content, or create a transactional Canvas snapshot. Redirected response data is
refused after the browser may already have contacted the redirect target.
No prevention of that redirected network contact is claimed. No runtime broker
was activated/restarted and no live account or school was used.

## Rejected and accepted source progression

| Native source | Actual receiving boundary | Result |
|---|---|---|
| Original configured-provider 3e251e5 | Actual CLI/Handler/queue/page selection/job + authored terminal Page | Independent A/B mismatch reproduced; PR45 held |
| First routing repair b6661032 | Same independent terminal contract | Matching A/A and B/B pass; A/B refuses before evaluation |
| First routing repair b6661032 | Actual Chrome production expression | 4/5; foreign HTML base still dispatches to B before response refusal |
| Absolute target successor 8e1a1b87 | Same actual Chrome receiver | 5/5; foreign base dispatches only to A |
| Absolute target successor 8e1a1b87 | Same adapted independent terminal receiver | Matching identities preserved; A/B refuses without artifact |
| Final capable/main composition 7452703 | Exact old broker Handler with new CLI + capable terminal replay | Old broker refused before POST/job; capable session controls pass |

Independent durable packets:

- [Original immutable wrong-page witness](https://github.com/Jacob-Met/canvaspilot/blob/b582b15754c675e2cf8c57ba6963fb27ba2a7541/docs/evidence/provider-page-routing-49f845d0dece/README.md).
- [Final absolute-target receiving](https://github.com/Jacob-Met/canvaspilot/blob/7bbfebcff5c6a4de8a6f0ac96e948a6c1aa692cf/docs/evidence/provider-page-routing-49f845d0dece/replay-absolute/RESULTS.md).
- [Final old-broker compatibility and composed-source receiving](https://github.com/Jacob-Met/canvaspilot/blob/35180358a209c9c9bc750b73af75bde040070b86/docs/evidence/provider-page-routing-49f845d0dece/compatibility/README.md).

Those packets are separate source-owned evidence commits, not hidden production
changes. Their original counterexample, two receiver generations, ENOSPC attempts
and exact source pins remain immutable. Final old-broker refusal receipt SHA256:
fbd6f18d5c67c3f5cf8010343bff02d3ac2a2549651200ad9bf98302ae7f6346.
Final capable composition receipt:
b245a0108a57b28de783ed335dd8de61311d8282df0864726d7eb954ae051fcf.

## Real browser evidence retained here

Chrome154.0.8037.98 executed the extracted production expression in a fresh
context with two authored loopback HTTP origins. Requests outside these fixture
origins were blocked. The five controls cover matching origin, mismatched page,
foreign HTML base, foreign requested URL and foreign redirected response.

The actual invoked-expression receiver SHA256 is
c400109a9fcf8a120b9f974d28d29150f2424b5652d7fb911c6474fbdd5234e9.
Those exact bytes produced baseline1/5, intermediate4/5 and successor5/5.
Expression/input hashes, document location/baseURI and actual HTTP requests are
in the receipts. The final production expression SHA256 remains
11190219dc24f939d0fcf31d65482e0a628c58b738809de2d8a0562bac7ce54e after capability
and current-main composition, so no duplicate browser replay was needed.

The first Node harness evaluated a function string without invoking it. Its
0/5 output contains zero requests and is not product evidence. The original
harness and receipt remain as receive_browser_origins.initial.cjs and
browser-initial/receipt.json. Only the invocation seam was corrected; the five
oracles stayed the same before the meaningful baseline/intermediate/final run.

This browser check executes actual production JavaScript, not Python broker
startup or a school login. Independent CLI receiving separately executes the
real Handler/_call/queue/_canvas_page/_run_job with only the terminal Page
authored. Neither boundary is mislabeled as a live-school check.

## Maintained native gates

Final current-main suite: 446 passed in45.71s. Configured Ruff and product-source
whitespace checks pass. Existing source/API/CLI owners' tests are preserved.
The contribution adds19 calendar-provider cases and13 broker-routing cases.

The first final-composition suite was interrupted by real disk exhaustion:
440 passed, one artifact-write failure and five temporary-directory errors.
Its original capable-tests.txt/JUnit remain. After confirming no cargo/rustc
processes, only this worker's reproducible Rust incremental cache was removed;
final binaries, their hashes, source and evidence remain. The same product/test
bytes then passed all446. No assertion or source edit was used to turn the
environment failure into a pass.

The full earlier284-pass gate, broker source patches, input/source pins,
main-composition record and final446-pass gate are preserved separately.
SHA256SUMS pins the packet files. Final hosted CI belongs to the published
successor head and is recorded in its PR conversation rather than retroactively
rewriting these native receipts.
