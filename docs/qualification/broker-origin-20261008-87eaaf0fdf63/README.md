# Receiving the running broker's configured Canvas origin

Contributor: `estate-87eaaf0fdf63/estate_production`, 2026-10-08. Exact receiving
baseline: `d4895a33a5d28e9e81d09deffe744a48462b6930`, root's current composition
after merging main `1393f40047297147029d8571bfd824f74e58e1dc`.

The origin insight is contributed by `estate-ac386303dce2` in
[PR35](https://github.com/Jacob-Met/canvaspilot/pull/35), read at exact head
`89fa86d20e4eff47ce42e18afd8cd8e75ab376c3`. This contribution independently
receives that behavior and applies only its configured-origin correction to
the existing composed implementation.

## Reproduced gap and minimal correction

A default `CanvasClient` uses `https://canvas.instructure.com`, while the running
broker can be configured for a different school host. The baseline discarded
the broker's existing health response and validated a returned school-host next
link against the client default. The public assignment call therefore raised
after the first page even though the broker advertised the correct configured
school origin and the continuation was valid.

The correction retains the existing health response, validates its advertised
`base_url` before any fetch, and uses that origin for both the initial collection
URL and all next links. If the origin field is absent, explicit client
configuration remains the fallback. A present empty, malformed or wrongly typed
origin is refused; it is not replaced silently with the default. Errors do not
echo metadata secrets or fragments.

The existing URL validator, Link metadata format, explicit incomplete/restart
errors, page cap, broker dispatch, ordinary request result and token branch are
preserved. No capability handshake, alternate response headers or numeric
fallback is introduced. PR35's branch and receiving ownership are unchanged.

## Executed receiving

`tests/test_broker_origin_receiving.py` reuses the root-authored production
Handler/queue fixture from `test_broker_http_receiving.py`. It invokes actual
loopback HTTP health and fetch requests, production broker decoding and public
`CanvasAPI.list_assignments()`. Only the browser worker's responses are fictional.
No browser, real account, token, existing profile or provider request is used.

The 15 new tests were authored before the source edit. On the pinned baseline,
**13 failed and two existing-contract controls passed**: the school-origin case
failed after its first page, and twelve invalid advertised origins were ignored
instead of refusing before a fetch. The passing controls cover matching explicit
client configuration and an omitted health-origin field.

After the correction, the 15 new tests, root's 12 existing HTTP receiving tests
and all 26 token pagination controls pass together: **53 passed in 2.50 seconds**.
`baseline.json` and `candidate.json` preserve exact output and exit codes.
`verification.json` records tested source identities. The complete lint and staged
whitespace gates are also recorded. The coordinating root owns the final combined
full-suite and installed-package gate; this receipt does not relabel a focused
receiving run as a full-suite run.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q \
  -p no:cacheprovider tests/test_broker_origin_receiving.py \
  tests/test_broker_http_receiving.py tests/test_token_pagination.py
ruff check src tests scripts
git diff --cached --check
```

This is qualified source for the held combined transfer. It does not assert
acceptance by the PR35 owner, a live broker restart or deployed school results.
