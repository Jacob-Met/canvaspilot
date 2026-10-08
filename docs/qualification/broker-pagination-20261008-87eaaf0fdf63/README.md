# CanvasPilot complete broker collection reads

Contribution: `estate-87eaaf0fdf63/estate_production`, 2026-10-08. Receiving
baseline: `b0655cfc6f298c956fcdd27fbba32e3c5609516f` on `main`.

## Receiving failure and change

The real public `CanvasAPI.list_assignments(7)` path returned only 10 of 25
fictional assignments when a server capped the first response to ten rows while
returning an opaque `next` URL. The broker dropped the Link header, and the client
treated fewer than its requested fifty rows as the end. This was reproduced in
Python and then through the exact original broker JavaScript in Chromium.

[Canvas's primary pagination contract](https://developerdocs.instructure.com/services/canvas/basics/file.pagination)
requires following the supplied continuation URL; server page-size limits are
unspecified. The candidate exposes only `response.link`, preserves initial filters,
follows the opaque URL on the configured origin, and refuses an unverifiable or
truncated collection. A running older broker needs a restart with the updated
package; there is no numeric fallback. Ordinary `broker_fetch` calls retain their
decoded-body result. The token and fixture branches remain unchanged.

Continuation URLs become root-relative before being passed to the broker so they
cannot trigger its absolute-URL navigation behavior. Changed scheme/host/port,
userinfo, fragments, backslashes and protocol-relative paths are refused. Repeated
pages, multiple next relations, malformed headers, non-JSON responses and a next
link remaining after forty requests raise `CanvasPaginationError`. A terminal
single JSON object retains the existing append-and-stop convention.

## Executed qualification

Environment: Python 3.12.14, httpx 0.28.1, pytest 8.4.2, ruff 0.13.3, mcp 2.3.0,
Playwright 1.63.0 and Chromium 153.0.8010.0. `requirements-test.txt` preserves the
installed dependency versions used by the local checks.

| Boundary | Baseline | Candidate |
|---|---|---|
| Native repository test suite | 59 passed | 103 passed after independent receiving tests were integrated |
| Public assignment API with broker response decoding | 10/25 rows, one request | 25/25 rows, three requests |
| Actual broker JavaScript in fresh Chromium | 10/25 rows, Link dropped | 25/25 rows, Link retained |
| Initial repeated filters and opaque continuation | Numeric page added | Filters once, continuation query retained |
| Full lint gate | Two existing E402 late imports in the live-sweep script | Passed after the import-only prerequisite |
| Independent actual HTTP receiving | 11 failures / one unchanged-body control passed | 12 passed |

The updated repository tests exercise short and empty intermediate pages, opaque
cursor escaping and commas, repeated query parameters, non-list terminal behavior,
later HTTP errors, cycles, forty-page success versus truncation, old broker metadata,
malformed/ambiguous relations and rejected continuation origins. They invoke the
real public client and decode real httpx response objects; the browser receiver
executes the existing `_run_job` in-page fetch.

The coordinating root independently authored `tests/test_broker_http_receiving.py`
before inspecting these tests. It runs the actual HTTP `Handler`, `_call` queue,
`broker_fetch` and public CanvasAPI on a private loopback port, replacing only the
browser worker's replies with fictional response envelopes. Its SHA-256 is
`876b391cb8db6101ed5dc13d09624271f7961100f06467d3ca06d356c1c0cd61`.
The unchanged file passed twelve candidate controls and failed eleven baseline
controls, with the existing decoded-body contract passing on both. The two logs
are retained as `independent-*-http.txt`.

One later qualification rerun encountered `OSError: [Errno 28] No space left on
device` on the shared filesystem; its incomplete stdout and error excerpt are
preserved as `tests-enospc-*`. It is not a passing run. After capacity became
available, the integrated suite completed: **103 passed in 8.02 seconds**, with
empty stderr. `tests-candidate.txt` and `lint-candidate.txt` retain the final gate
outputs. The live sweep was never invoked.

`browser-baseline.json` and `browser-candidate.json` preserve actual request paths,
counts, browser version and exact source-file SHA-256 values. The browser receiver
uses a new ephemeral context and intercepts every request. No account, token,
existing browser profile, provider request, submission, write endpoint or real
student information was used.

To reproduce with the desired source selected on `PYTHONPATH`:

```sh
PYTHONPATH=/absolute/source/src python \
  docs/qualification/broker-pagination-20261008-87eaaf0fdf63/browser_receiving.py \
  --chromium /absolute/path/to/chromium --expect candidate
python -m pytest -q
ruff check src tests scripts
git diff --check
```

For the immutable baseline use `--expect baseline` and its source directory. The
receiver asserts the preserved failure, rather than reporting it as a passing
complete collection.

## Integration boundary and ownership

The complete source tree has no AGENTS.md. Current repository issues, open PRs and
pagination-specific ownership were inspected before edits. Authentication proposals
#7/#8/#9, proxy-environment receiving for #26, and explicitly non-merge CI demos
#27/#28 retain their scopes. This contribution makes no authentication, CLI,
workflow, live broker or account changes. A small prerequisite import relocation
in `scripts/readonly_sweep.py` is isolated in a subsequent commit: its two existing
late imports fail the repository's full lint command on the exact baseline. The
live sweep is not executed during qualification.

The native hamon-ie connector was unavailable to the coordinating root due to an
authentication error, so this record does not assert a native goal lease. Current
GitHub secondary write-rate limiting also holds external publication pending
normal recovery; no alternate publication route is used to bypass it. This
receipt establishes implemented and locally verified source, not merged source,
an installed broker, live school completeness or measured student outcomes.
