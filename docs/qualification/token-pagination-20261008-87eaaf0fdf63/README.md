# CanvasPilot complete token collection reads

Contribution: `estate-87eaaf0fdf63/estate_production`, 2026-10-08. Receiving
baseline: `640bca994bd98f2c4b1759e450ebeda0e0b92dab`, the frozen and independently
qualified broker pagination increment. This follow-on changes only the token
collection path and removes its unused legacy Link parser.

## Observed defects and resulting behavior

The baseline `CanvasClient.get_paginated()` returned a successful partial list
when its fortieth response still advertised a next page. It also passed an
absolute foreign `rel=next` target directly to its HTTPX client, whose configured
Authorization header was present on the resulting foreign request. These were
reproduced using a synthetic token and `httpx.MockTransport`; no network or
account was contacted and no user credential was obtained.

The token path now uses the continuation parser and configured-origin validator
already reviewed for the broker increment. Initial and continuation URLs must
match the configured scheme, hostname and effective port. Userinfo, fragments,
backslashes and ambiguous protocol-relative paths are refused. The client makes
no request to an invalid target. Errors do not include opaque cursors or token
values. Credentials, mode selection, browser policy, single-request methods and
HTTPX's existing redirect behavior are unchanged; the URL restriction described
here applies to authored collection and Link continuation targets.

A short or empty intermediate page still follows its supplied next URL. Exact
cursor encoding and repeated query values survive. Initial parameters keep
HTTPX's native list, boolean and null encoding, preserve an existing initial
query, and apply once even when the initial URL is absolute. A terminal fortieth
page succeeds; a remaining next link raises `CanvasPaginationError` rather than
returning a partial list. Cycles, malformed or ambiguous Link metadata and
non-list pages with a next link also raise. Existing terminal single-object and
later HTTP error behavior remain covered.

[Canvas's primary pagination contract](https://developerdocs.instructure.com/services/canvas/basics/file.pagination)
requires following opaque Link URLs and leaves maximum page sizes unspecified.
This contribution does not assume numeric cursors or treat row count as a
completion signal.

## Executed qualification

The 26 controls in `tests/test_token_pagination.py` were authored before the token
source edit. They exercise production client initialization, token/header setup,
URL building, response processing and `get_paginated()` results while replacing
only the HTTP transport. Every token is an explicitly synthetic fixture value.
A guard fails the tests if token mode probes the session broker.

| Control set | Frozen baseline | Candidate |
|---|---|---|
| Focused token continuation suite | 17 failed, 9 existing-contract controls passed | 26 passed |
| Foreign continuation target | Second request includes configured synthetic Authorization | Error after first request; target is never requested |
| Forty pages with a remaining next link | Returns 40 rows as a successful list | Raises incomplete-collection error after 40 requests |
| Exactly forty terminal pages | Complete collection returned | Complete collection returned |
| Later 401/403/429/500 | Error propagated | Error propagated without partial output |
| Full integrated repository suite | Broker increment: 103 passed | 129 passed in 8.13 seconds |
| Full lint and whitespace gates | Broker prerequisite already qualified | Passed |

`baseline-tests.txt` preserves the actual failed controls against the immutable
source, and `candidate-tests.txt` preserves the corresponding targeted pass.
Only trailing whitespace from pytest's error padding is trimmed in the readable
baseline text; `baseline-output.json` preserves the exact original stdout string.
`full-tests.txt`, `lint.txt` and `diff-check.txt` record the completed full gates;
all three have exit code zero and empty stderr. `verification.json` records source
and test SHA-256 values. The existing
broker qualification directory remains a historical receipt of its exact frozen
source; its statement that the token path was unchanged applies to that earlier
increment.

An initial full-gate orchestration hit shared-filesystem ENOSPC while attempting
to preserve the first test log and established no successful full-suite result.
`enospc-incomplete.txt` records that event. Removing only reproducible Python
bytecode caches in this contribution's own virtual environment freed 25.3 MB.
The recorded passing full run then used `PYTHONDONTWRITEBYTECODE=1`; no other
worker's path was modified.

Reproduce the baseline and candidate controls with the intended source first on
`PYTHONPATH`, using the dependency versions in the broker qualification's
`requirements-test.txt`:

```sh
PYTHONPATH=/absolute/frozen-broker-source/src python -m pytest -q \
  tests/test_token_pagination.py --tb=short
PYTHONPATH=src python -m pytest -q tests/test_token_pagination.py --tb=short
PYTHONPATH=src python -m pytest -q
ruff check src tests scripts
git diff --check
```

## Ownership and integration

The coordinating root requested this continuation after the broker contribution
was frozen. Current open authentication proposals #7/#8/#9 concern the localhost
broker authentication decision and retain their merge holds. This token-only
collection change does not modify those choices or branches. The repository
contains no AGENTS.md. The coordinating root retains current-main composition,
independent receiving, publication and distribution ownership.

These receipts establish locally implemented and verified source. They do not
claim an installed release, a running school session, live provider completeness,
or a measured student outcome.
