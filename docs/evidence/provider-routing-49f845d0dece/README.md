# Calendar provider identity and guarded broker routing

The final source refuses a calendar whose selected browser page or fetch origin
does not agree with the configured Canvas provider. Session export also requires
an explicitly capable broker; an older running broker receives an actionable
restart instruction before assignment requests. Calendar source/UID identity,
actual page selection, absolute fetch dispatch and returned response origin now
share the same provider boundary.

Product freeze: `8f75e03121df061ff80f100ee276565d61fdb9c2`.
Final maintained-test freeze: `b747b2ed00657587c3798936f8596209cdab7985`.
Actual main composed: `ca2318fe7c56d2e4ec1b363ff8a945ab78bf4a0c`, which merged PR35.
The five production SHA-256 pins are in
`landed-pagination/final-source-pins.json`.

## Scope and current-main preservation

Only three existing production files change: calendar_export.py,
session_broker.py, and the export-calendar arm of cli.py. The last change adds
only CanvasPaginationError to that arm's import and exception tuple, so an
incomplete later page produces the existing structured CLI diagnostic without
a partial calendar or traceback.

The landed PR35 client is byte-exact, as are all owner API behavior, unrelated
CLI arms and tests. Both health flags, link_pagination and provider_origin_checks,
remain present; headers.link remains in the browser response. The sole merge
conflict was the adjacent health flag slot. The exact source diff and all
576 preserved existing main leaves are recorded in
`landed-pagination/{source-diff.patch,main-preservation.json}`.

There was no long-lived broker activation or restart. All receiving used
synthetic data and disposable loopback services; no live school, login or
calendar account was contacted.

## Meaningful before/after receiving

The original configured-provider-only head1748e52 was rejected: an actual
production Handler/queue/_canvas_page/_run_job with an authored terminal Page
could return schoolB rows while health/report/UID named schoolA. The first
routing correction b666 refused that mismatch, but actual Chrome still followed
a foreign HTML base during relative fetch dispatch. The absolute-target8e1
successor resolved the URL once and passed that exact target.href to fetch.

Every previous witness and accepted intermediate remains unchanged. See
[the earlier source/evidence account](README-before-landed-pagination.md),
[original independent mismatch packet](https://github.com/Jacob-Met/canvaspilot/blob/b582b15754c675e2cf8c57ba6963fb27ba2a7541/docs/evidence/provider-page-routing-49f845d0dece/README.md),
[absolute-target receiving](https://github.com/Jacob-Met/canvaspilot/blob/7bbfebcff5c6a4de8a6f0ac96e948a6c1aa692cf/docs/evidence/provider-page-routing-49f845d0dece/replay-absolute/RESULTS.md),
and [old-broker capability receiving](https://github.com/Jacob-Met/canvaspilot/blob/35180358a209c9c9bc750b73af75bde040070b86/docs/evidence/provider-page-routing-49f845d0dece/compatibility/README.md).

The same retained calendar consumer receiver ran against the actual landed
composition677130 and final product8f75: **26/27 before, 27/27 after**. Its only
before failure was the missing structured error for malformed later-page Link
metadata. Both runs refused the incomplete artifact. The successful controls
parse changed second-page deadlines and Unicode, preserve UIDs, retain opaque
continuations, account honestly for missing due dates, preserve prior exports,
and keep provider identities distinct. Raw CLI stdout/stderr, calendars and
receipts are under `landed-pagination/cli-before` and `cli-after`; the receiver
is `landed-pagination/receive_calendar_pages.py`.

Independent final receiving executes production CLI/client/Handler/queue/page
selection/job with only the terminal Page authored. All11 assertions pass:
both providers export two distinct assignments with exact identities, URLs and
due instants; the opaque cursor and query survive; terminal empty Link stops
at two pages; mismatched page is refused before evaluation. The unchanged
legacy-broker receiver confirms one health read, zero POST/jobs, restart
ValueError and no artifact/profile. Its immutable packet is linked in PR45.

## Actual Chrome and Link metadata

The unchanged invoked-expression receiver c400109a executed the final combined
expression in Chrome154.0.8037.98 against two loopback origins: **5/5 pass**.
Matching provider and foreign HTML base dispatch only to the configured origin;
mismatched page and foreign requested URL refuse before fetch; foreign redirected
response data is refused. The final expression SHA-256 is
`10c759fc18d17167af671be400ee2aedc70357a04063a051420defa0e318f943`.
It differs from accepted11190219 only by the landed owner's headers.link return;
the guard and absolute dispatch segment is exact. This is recorded in the
preservation record, extracted input and `landed-pagination/browser/receipt.json`.

The owner's optional native --dump-dom test timed out on this MacChrome after
30seconds. Its unchanged test and raw failure are preserved. A separate actual
Chrome Playwright control executes the exact same production expression and
retains the owner's substantive assertions: actual JSON/status, only Link
metadata returned, and fixture cookie kept in browser. **4/4 pass**, with
requests/result/source and receiver hashes in `metadata-playwright.json`.

The historical Node zero-request failure is retained and clearly identified as
a function-invocation harness error. It is not a product baseline.

## Final native gates and limitations

**536 tests passed, six subtests passed, one optional browser skip, in60.45s**.
Configured Ruff and product whitespace checks pass. The normal suite's optional
browser skip is complemented by the explicit actual-Chrome controls above.

The first full run with the two new CLI regression cases passed534 and failed
those2 because their parser tried to decode pre-existing HTTPX log lines as
JSON. Original test bytes and output remain. Only that test's stderr parser
changed to read the final JSON line, matching existing CLI tests and the
unchanged consumer. All five production hashes stayed fixed. Final outputs
are `verified-{pytest,ruff,whitespace}.txt` and `verified-gates.json`.

Earlier disk-exhaustion and intermediate446/284 receipts remain unchanged.
SHA256SUMS covers this packet. Hosted CI belongs to the eventual published
successor and is recorded in the PR conversation.

This does not lock the browser or provide a transactional Canvas snapshot.
The response-origin guard rejects foreign redirected data after the browser
may already have contacted that redirect target; it does not prevent that
network contact. Actual Chrome receiving covers the production JS expression,
while independent CLI receiving covers broker routing with an authored Page.
Neither is represented as live-account broker startup.
