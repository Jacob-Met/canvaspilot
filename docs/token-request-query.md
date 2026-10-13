# Embedded queries in token-authenticated requests

Ordinary token-authenticated REST requests retain the query supplied in the path.
For example, both requested `include[]` values reach Canvas:

```python
from canvaspilot import CanvasAPI, CanvasClient

with CanvasClient() as client:  # uses your existing CANVAS_API_TOKEN setting
    result = CanvasAPI(client).api_request(
        "GET",
        "/api/v1/courses?include%5B%5D=term&include%5B%5D=teachers",
        params={"per_page": 7},
    )
```

The HTTP target ends with
`?include%5B%5D=term&include%5B%5D=teachers&per_page=7`.
The same behavior applies to `CanvasClient.request` and the existing
`canvas_api_request` MCP tool. The MCP tool accepts additional parameters as
`params_json`, for example `{"per_page":7}`.

## Query composition

The path's query stays first, with its original ordering, repeated keys, blank
values and encoded values. HTTPX still handles URL spelling, including encoding
literal Unicode. Additional `params` retain HTTPX's existing array, boolean,
null and scalar encoding and are appended once. Neither the supplied `params`
collection nor request body is modified.

When an accepted parameter collection encodes to no fields, an existing query
stays exact without an extra separator. With no query fields on either side,
the existing HTTPX empty-query marker is retained.

If both inputs name the same key, both occurrences remain: path
`?x=first` with `params={"x": "second", "per_page": 7}` sends
`?x=first&x=second&per_page=7`. This matches the existing broker and paginator
composition. The client does not decide how Canvas interprets duplicate names.
For a single-valued parameter, provide its chosen value in one input.

The existing implicit `per_page=50` still applies when `params` does not name
`per_page`. Consequently, a page size supplied only in the path is followed by
that default, just as it is in the existing broker and paginator. Supply
`params={"per_page": 7}` when choosing a page size explicitly.

## Source boundary and receiving

Only the ordinary token branch of `CanvasClient.request` changes. It composes
the complete HTTPX URL before dispatch instead of supplying `params=` alongside
an already queried URL. Method and body handling, authentication, response and
error classes, redirect behavior, lifecycle, fixture requests, broker requests,
pagination and generic API path admission retain their existing code.

The dedicated maintained tests use a real HTTPX client and disposable numeric
loopback HTTP server with fictional data and a synthetic token. They cover
embedded repeats/empty fields/opaque values, explicit parameter collisions and
encoding, no-query controls, JSON and form bodies, empty/text/JSON responses,
authorization and server errors, and the existing MCP tool. On the original
source the final course has 23 failures and five passing controls; the repaired
source passes all 28 as part of the 151-case affected course. Independent review
caught the empty-encoding separator case in the first patch. Its counterexample,
the intermediate empty-query-marker control and two earlier test-harness
invocation mistakes are retained separately from the final comparison.

No live Canvas response, school account, existing browser session or deployed
service was used. These tests establish the dispatched HTTP target and ordinary
local response behavior, not provider-specific duplicate-key interpretation.

References: [HTTPX request and URL interfaces](https://www.python-httpx.org/api/),
[the original broker encoding repair](https://github.com/Jacob-Met/canvaspilot/pull/29),
[the existing paginator](https://github.com/Jacob-Met/canvaspilot/pull/35), and
[this repair's source scope](https://github.com/Jacob-Met/canvaspilot/issues/136).
