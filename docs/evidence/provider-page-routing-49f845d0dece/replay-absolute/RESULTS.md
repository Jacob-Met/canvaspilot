# Accepted absolute-target correction receiving

## Verdict and source

ACCEPT the bounded provider-page and JavaScript origin correction at native commit `8e1a1b87a1f7379b884310cf05cbad8129ea1bb8`, broker SHA256 `a80904e0b1f882acb32770e805ed711bbed8a2e3999196a96e5a395dd4e186fe` (Git blob `42537e323550e8b0a2da4cbbb3a6b94bfaf16ddc`). The other four production files retain the original PR45 hashes. Final integration and hosted gates belong to the lead and author.

The successor creates one URL with `new URL(path, location.href)`, validates that target's origin, and calls `fetch(target.href, opts)`. Static review confirms that the browser now dispatches the same absolute URL that was checked. Response-origin and page-origin checks remain in place.

## Independent native CLI-to-broker replay

The same final companion SHA256 `f2684d1046843da7533a41086da73421e4a1cb1abc84da1b417bb7be799ca587` ran against original baseline native `3e251e5e1de71d56042daa76e2109cdd977b97a6` and the frozen successor. Its only change from the prior `4650abb...` companion admits the two exact production fetch statements at the terminal Page.evaluate seam. No outcome oracle changed. The exact adaptation is in receiver-diff.txt; the earlier witness, companion and b666 pair remain unchanged.

Both runs used the project's existing Python 3.13.7 environment, verified all five source hashes before and after, and finished with receiver exit 0. The baseline reproduced the expected wrong-provider counterexample. The successor passed all seven candidate assertions across the original three cases:

| Configured provider / selected page | Baseline | Successor |
| --- | --- | --- |
| A / A | Correct A export | Same source, UID and assignment URL |
| A / B | Export mislabeled as A while assignment URL identifies B | Exit 1, explicit CanvasAuthError, zero Page.evaluate calls, no artifact |
| B / B | Correct B export | Same source, UID and assignment URL, distinct from A |

The raw output and receipts are in `../replay-absolute-baseline` and `../replay-absolute-successor-qualified`. This receiving uses actual CLI, client/API, Handler, _call, queue, _canvas_page and _run_job with an authored terminal Page object. It does not execute production JavaScript or access an account. There are no live school requests, credentials, profile files or temporary calendars.

The first successor attempt encountered ENOSPC before its wrapper could persist the child result. It has no qualified product verdict. The exact tool output and classification are retained in `../replay-absolute-enospc/receipt.json`. A fresh isolated run succeeded after a read-only check observed sufficient free space; this worker deleted no artifacts. The successful attempt is not substituted for or represented as the blocked run.

## Independently reviewed actual Chrome evidence

The author separately executed the exact extracted production JavaScript in Chrome 154.0.8037.98 against authored loopback HTTP pages. The unchanged browser receiver SHA256 is `c400109a9fcf8a120b9f974d28d29150f2424b5652d7fb911c6474fbdd5234e9`. Independent review checked the receiver and input hashes, extracted each expression from pinned Git source using AST, compared source/expression hashes, and reconciled the receipt counts with the case rows. No browser test was rerun by the receiving reviewer.

| Broker source | Browser cases satisfied | Remaining case failures |
| --- | ---: | --- |
| Original baseline 3e251e5 | 1/5 | Wrong selected page, foreign base element, foreign request URL, foreign redirected response |
| First correction b666103 | 4/5 | Foreign base element |
| Absolute-target successor 8e1a1b8 | 5/5 | None |

In the decisive successor foreign-base case, the page is on A (`http://127.0.0.1:64254`), while document.baseURI is on B (`http://127.0.0.1:64255/courses`). The recorded API dispatch is exactly one A GET `/api/assignments`, and returned data identifies A. The prior b666 run records a B API request followed by an after-fetch refusal for the same case. This establishes the behavior the terminal Page witness bypasses.

For wrong-selected-page and foreign-request-url, the successor records a before-fetch mismatch, no returned value, and zero API dispatch during expression execution. For foreign-redirect-response, it records A `/api/redirect` and B `/api/assignments`, then refuses the foreign response with no returned value. This proves refusal of returned foreign data after following the redirect; it does not prevent or claim to prevent the request to B.

Browser evidence is owned and published by the implementation author. Exact native paths and file hashes are recorded in source-custody.json. Its boundary is JavaScript evaluation in actual Chrome after authored fixture navigation; it does not exercise Python broker startup, login, or a live Canvas account. Together with the separate terminal-Page replay, it closes the two concrete receiving gaps without claiming a live-account end-to-end test.
