# Collection page-shape receiving

This correction receives the terminal later-page object finding reported in
[PR35 review 5454974316](https://github.com/Jacob-Met/canvaspilot/pull/35#pullrequestreview-5454974316).
The root worker supplied that cross-source finding for independent reproduction
on immutable composition `9ee9a1687b5962a861e59ad6beb4c92fdcc5c179`.

## Reproduction and correction

Both production pagination loops accepted a terminal JSON object after a list
and returned it as an additional collection item. An empty first list also
triggered the defect. Checking whether the accumulated output is nonempty would
therefore fail to reject the empty-first-page case.

The correction tracks the loop's page index and raises `CanvasPaginationError`
for any later non-list page. The existing first-response singleton convention
is retained, including an empty object. An empty list can still continue to a
later list. The broker envelope, metadata parser, origin policy, authentication,
and continuation URLs are untouched.

The new test file was authored before the source edit. Its broker cases use the
production `Handler`, queue dispatch, `broker_fetch`, and actual loopback HTTP,
reusing the independently authored broker receiving fixture. Token cases retain
production client construction and Authorization setup while substituting only
HTTPX's transport with a synthetic token. All response data is fictional.

| Receipt | Result | Scope |
| --- | --- | --- |
| `baseline.json` | 4 failed, 6 passed in 1.18 s | Later object after populated and empty first lists fails in both modes; compatibility controls pass. |
| `candidate-focused.json` | 48 passed in 2.10 s | New 10 page-shape controls, existing 12 actual HTTP broker controls, and existing 26 token controls. |
| `lint-configured.json` | Passed | CI's `ruff check src tests scripts` scope, with caching disabled. |
| `lint-all-files-negative.json` | Four existing errors | An overbroad scan included archived evidence scripts outside the configured scope. Their bytes match the immutable baseline, as recorded in the configured-scope receipt. |

Raw pytest stdout and stderr, commands, source hashes and the unchanged test
hash are retained in the JSON receipts. The candidate command used `PYTHONPATH`
pointing to this isolated worktree, disabled bytecode and pytest caches, and used
an owned temporary directory. No entire-suite run, browser download, remote
Canvas call, GitHub write, source publication or owner-branch change is claimed
for this correction. Root integration owns the final composition gate.

## PAT exchange follow-on

The token exchange frozen at `c75ce7c22f0f82bc809a66c00152b9aa69f7fcf2`
preserves the original `e678faaa4809ac0eddfd17228c1e940d19865217` delta exactly.
That historical patch and its receipts are unchanged. A receiver adapting that
token loop to an agreed PR35 head must also receive this page-position guard
and the token cases in `tests/test_collection_page_shape.py`. The old export
alone does not reject a terminal object after a list.

This follow-on requires no new broker protocol or duplicate session Link parser.
It does not resolve the separately documented PR35 metadata/capability handshake,
legacy incomplete-result contract, exception location, or URL admission choices.
Those choices still require the source owner's agreed receiving head.
