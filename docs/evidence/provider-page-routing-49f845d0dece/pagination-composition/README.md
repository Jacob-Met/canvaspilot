# Landed Link pagination and provider identity composition

## Verdict and source custody

ACCEPT the newly merged PR35 pagination path composed with the provider-origin correction and the scoped calendar CLI error handler. Production source is pinned at native `8f75e03121df061ff80f100ee276565d61fdb9c2`. The client is exactly the merged owner's `d3473b7805908c15b276689abff9dd0dbd8d428e8691d557a26a5b2285444797`; final broker SHA256 is `a692cd2812cbc09536f1b60c84892bc8e87d2ae984c5a5aa25a13f6537ba6da2`. The final CLI catches the precise landed CanvasPaginationError in the calendar command arm. All five hashes and canonical blobs are in source-custody.json.

The composed run recorded native head `b747b2ed00657587c3798936f8596209cdab7985`, a test-only follow-up whose five production files are byte-identical to 8f75e031. The legacy-compatibility run recorded 8f75e031 itself. These actual receipt heads are preserved. Every production hash was checked before and after each receiving run.

## Actual calendar/client/broker path

A new companion was frozen before execution at native `0590a79e437467cdac90b420828cb4bf036e6d58`, SHA256 `d2f0a8626f7bfcebd6f6cbf240b91d3dca228718024ebde5b3decda2dd10db7e`. Its diff from the prior receiver is retained. The original three provider cases and refusal checks remain; its authored terminal Page now returns the owner's Link metadata envelope and two distinct assignment pages. No prior receiver or receipt is changed.

The native run uses actual CLI, API, landed Link-pagination client, Handler, _call, queue, _canvas_page and _run_job. Only the terminal Page object is authored. Page one returns an absolute next Link with opaque query `cursor=next%2Bpage%2F2&per_page=1`; page two returns an explicit empty Link. The receiver observes both the absolute URL entering the production queue and the relative path/query passed to Page.evaluate, requiring the cursor query to survive without the initial filters being appended. It independently parses the emitted calendar using icalendar.

All **11 witness assertions passed**:

| Configured provider / selected page | Result |
| --- | --- |
| A / A | Exactly two API evaluations; two exported events with exact A identities, URLs and due dates |
| A / B | Structured CanvasAuthError, zero Page.evaluate calls, no calendar |
| B / B | Exactly two API evaluations; two exported events with exact B identities, URLs and due dates |

The fixed UID oracles are derived from the pinned calendar identity contract, the source origin, course `42`, and assignment IDs `1` and `2`. Assignment 1 is due at `2026-11-01T08:45:00Z`; assignment 2 at `2026-11-02T10:15:00Z`. Both original assignment-1 identities are unchanged. The four emitted UIDs are distinct, and the raw receipt records each exact UID, source URL, summary and due date. Exactly two pages per successful export proves that the empty terminal Link ends traversal.

The raw receipt and artifacts are in `../pagination-composed-run`; receiver exit was 0 under the existing project Python 3.13.7 environment. This run used no real browser, school account, credential or external school request.

## Legacy broker compatibility still holds

The unchanged mixed-version receiver `e48456f822ca8861374641f4fa698f62d15c099e955cef2de354c26f78c6b75f` also passed on the final five source pins. It used the exact old broker Handler health protocol. The final exporter reads health once and produces the explicit restart ValueError before any POST or queued job, with no artifact/profile. The new broker retains both boolean capabilities, `provider_origin_checks` and `link_pagination`; the completed two-page flow demonstrates that the actual new client accepts the composed health and response protocol.

This compatibility result is in `../pagination-legacy-compatibility`. The earlier baseline contrast and all earlier infrastructure failures remain preserved in their original packets.

## Independent browser receipt review

The final expression SHA256 is `10c759fc18d17167af671be400ee2aedc70357a04063a051420defa0e318f943`. It includes the landed owner's Link return property, so the older full-expression browser receipts are not relabeled as executions of these bytes. The author executed the unchanged origin receiver on the actual composed expression in Chrome 154.0.8037.98, with **5/5** cases passing.

Independent read-only review verified the current origin receiver hash, input hash, exact expression correspondence to the frozen broker, case counts, and decisive request observations. The input records native source 677130b0; its broker and expression bytes are identical to final 8f75e031. With a foreign document base, only configured-origin A receives the API request. The redirect case records API requests to A and then B, followed by refusal of the foreign returned data. It does not claim prevention of redirected network contact.

A separate actual Chrome/Playwright metadata receiver passes **4/4** assertions on the same exact expression: response status and JSON rows are preserved, only the Link header is returned, and the authored HttpOnly session cookie is sent in the local request without exposing cookie response headers in the broker envelope. Its driver, input and receipt hashes were independently checked. The owner's standalone dump-dom browser test timed out and remains a separate unqualified attempt; the Playwright result is not labeled as that test passing. Browser driver files and raw receipts are owned by the implementation author; exact native paths and hashes are in browser-review.json.

The native terminal-Page receiving and the browser expression receiving remain distinct boundaries. Neither is represented as a live-account end-to-end run. Root retains actual-main tree preservation, hosted gates and merge ownership.
