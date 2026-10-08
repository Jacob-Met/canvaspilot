# Complete Canvas coursework pagination

## Result and source

The corrected source at `bb284ae3ddbf2e6918f009bf4f96552d9820b62e`
passes **146 tests with two mode-only skips**, including a fresh Chromium
request path through the real broker queue and HTTP handler, client decoder,
and high-level assignment API. The authored three-page response returns
assignment IDs `[1, 2, 3]`, including the assignment after an empty
intermediate page. The same browser control on current main returns only
`[1, 2]`.

Repository: [Jacob-Met/canvaspilot](https://github.com/Jacob-Met/canvaspilot).
The contribution composes on main
`874ad9c073fc5bab625e583849dbbe4eaf7fc6af`, which includes PR #26's broker
proxy-environment isolation. The first candidate frozen for independent
review was `fd3996aada3f34b7093fa361eb7e423c4c587d90`; the corrected source
adds the independently received relation/context supplement. This evidence
directory is committed separately after qualification, so its source commit
identifies the tested code without a self-referential evidence hash.

`source-receipt.json` records all eight changed source, test, and API/document
files with Git blob IDs and SHA-256 hashes, the exact base and source commits,
and runtime versions. Final runtime: Python 3.12.14, Chromium 153.0.8010.0,
Playwright 1.63.0, and Node 24.19.0.

## User need and behavior

The original session broker discarded Canvas's `Link` response metadata.
Its client guessed numbered pages and stopped when a page contained fewer
rows than requested. Canvas permits a server-specific maximum page size and
requires clients to follow its opaque next URLs. A short page therefore can
hide later coursework from assignment lists and course digests.

The client now uses response links in both token and broker modes. Only the
first request receives the caller's filters. Each subsequent URL retains its
opaque query, including repeated parameters and punctuation. A short or empty
page continues when it has a next link; a full final page needs no speculative
extra read. The broker exposes only two additive response fields, `link` and
`url`; public `broker_fetch()` still returns the decoded body.

The original 40-page bound remains. A continuing link after page 40, malformed
or ambiguous relation metadata, unsupported anchored link contexts, changed
origins, repeated pages, or invalid response URLs raise an explicit
`CanvasPaginationError` without returning the accumulated list as complete.
An older running broker must be restarted after updating: missing pagination
metadata produces an actionable restart error. Original non-list body
behavior, authentication controls, proxy isolation, and CLI source remain
intact.

Primary contracts:

- [Canvas pagination](https://developerdocs.instructure.com/services/canvas/basics/file.pagination): page size has an unspecified server maximum; next URLs are opaque and include their complete query parameters.
- [RFC 8288 section 3](https://www.rfc-editor.org/rfc/rfc8288.html#section-3): serialized parameter values.
- [RFC 8288 section 3.2](https://www.rfc-editor.org/rfc/rfc8288.html#section-3.2): an anchor changes the resource context and cannot simply be ignored while following the link.
- [RFC 8288 section 3.3](https://www.rfc-editor.org/rfc/rfc8288.html#section-3.3): relation presence and registered/extension relation syntax.

This parser implements a bounded Canvas pagination policy. It does not claim
general RFC conformance: unsupported anchored contexts and repeated `rel`
parameters are conservatively refused.

## Before/after evidence

| Source and control | Result | Evidence |
| --- | --- | --- |
| Original discovery source `b0655cfc6f298c956fcdd27fbba32e3c5609516f`, actual client and assignment API over authored broker envelopes | Expected `[1, 2, 3]`; returned `[1, 2]` in one request despite an opaque next link | `baseline-missing-coursework.json` |
| Current base `874ad9c073fc5bab625e583849dbbe4eaf7fc6af`, exact final author pagination tests and real browser control | 40 failed, 9 passed, 2 mode-only skips; browser returns `[1, 2]` | `baseline-tests.log` |
| First frozen candidate `fd3996aada3f34b7093fa361eb7e423c4c587d90`, complete native suite with real browser | 108 passed, 2 mode-only skips | `candidate-tests.log` |
| Same frozen candidate, 38 independent receiving controls | 18 failed, 20 passed | `receiving/final-before.txt` |
| Frozen candidate plus independently checked parser supplement, same 38 receiving controls | 38 passed | `receiving/final-after.txt` |
| Corrected source `bb284ae3ddbf2e6918f009bf4f96552d9820b62e`, complete suite including incorporated receiving controls and real browser | 146 passed, 2 mode-only skips in 9.08 seconds | `final-tests.log` |
| Corrected source, Ruff across source, tests, and scripts | All checks passed | `lint.log` |

Independent review found that missing `rel`, malformed bare or quoted
relations, and unsupported `anchor` contexts could let the first candidate
assert completion or follow a link in a different context. The checked
supplement is retained with its original failing and passing controls.
`receiving/REVIEW.md` describes those authored counterexamples and the
separate receiving method; `receiving/review-source-receipt.json` preserves
exact source, patch, test, and log hashes. The original independent test is
retained there. Its incorporated copy in `tests/` differs only in import
ordering required by this repository's Ruff configuration.
Raw failure output and the received patch retain their original whitespace
so that their recorded hashes remain reproducible; source changes pass
`git diff --check` separately from those evidence bytes.

The receiving tests make actual HTTP requests to a disposable local broker
fixture, plus native httpx token requests. Their controls include malformed
proxy environment values, false/zero/empty/JSON-null legacy bodies,
case/default-port equivalent cycles, quoted valid parameters and URI
extension relations, and malformed response URLs.
`receiving/pr26-preservation.json` records unchanged existing proxy/auth
helpers and the complete CLI file against current main.

The browser control uses fresh Chromium with all requests intercepted and
service workers blocked. It executes the actual in-page fetch function,
broker handler/queue, client, and `CanvasAPI.list_assignments`. The final log
retains the three exact request URLs and an empty unhandled-request list.
The native suite's `listening` line comes from an existing patched startup
test; it does not indicate that a production broker was started.

## Reproduce

Install the repository's native development dependencies in an isolated
environment, then run from this checkout:

```sh
python -m pip install -e '.[dev]'
CANVASPILOT_TEST_CHROME=/absolute/path/to/chromium python -B -m pytest -q -s
ruff check src tests scripts
git diff --check
```

Without `CANVASPILOT_TEST_CHROME`, the optional browser control skips
explicitly. The recorded final run set it to a dedicated copied Chromium
runtime. The two recorded skips are token-mode instances of broker-only
compatibility tests; the browser control executed and passed.

For the baseline comparison, create a separate checkout at
`874ad9c073fc5bab625e583849dbbe4eaf7fc6af`, copy only
`tests/test_link_pagination.py` and `tests/test_link_pagination_browser.py`
from the qualified source into that checkout, and run those two files with
`PYTHONPATH` set to that checkout's absolute `src` directory. The same
Chromium executable must be supplied. The 40 failures above are the expected
negative result, not a passing baseline qualification.

For independent correction reproduction, create a separate checkout at
`fd3996aada3f34b7093fa361eb7e423c4c587d90` and execute the retained original
`receiving/test_independent_link_receiving.py` with that checkout's `src` on
`PYTHONPATH`. Apply `receiving/link-metadata-review.patch` and repeat the same
test file to reproduce the 18-failure-to-38-pass result.

## Qualification boundary

All Canvas rows, headers, identities, and URLs in these controls are authored
fixtures. These results establish the changed retrieval behavior and its
composition with the actual browser/broker/client path. They do not establish
live school authentication, a particular school's response behavior, or
student outcomes. No existing browser profile, school session, production
service, provider operation, submission, or message was used.
