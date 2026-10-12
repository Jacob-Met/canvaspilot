# Paths for the generic Canvas API tools

The Python `CanvasAPI.api_request()` and `CanvasAPI.api_paginated()` methods,
and the MCP tools `canvas_api_request` and `canvas_api_paginated`, accept
relative Canvas REST targets rooted at the exact `/api/v1` path segment.

Valid examples include:

```text
/api/v1
/api/v1?per_page=10
/api/v1/courses
/api/v1/courses/7/pages/chapter%2Eone
```

A path such as `/api/v10/courses` or `/api/v1evil` is outside that root.
Absolute URLs, fragments, backslashes, embedded control characters and parent
traversal are refused with `ValueError` before the client request. The guard
also checks the once-percent-decoded resource path, so a browser-normalized
target such as `/api/v1/%2e%2e/%2e%2e/login` is refused before it can become
`/login`.

Valid paths retain their original spelling after the existing outer-whitespace
trim. The guard does not decode or rewrite the query, parameters, JSON body or
form body; the existing transport's parameter encoding still applies. An encoded
single dot in a page name remains valid. The prior refusal of literal `..`
and `://` in the supplied target remains in effect.

This is the generic API entry-point contract. The existing direct
`CanvasClient`, session-broker origin checks, redirect behavior, curated API
methods and pagination admission retain their own behavior. The guard does not
interpret a server's application-specific repeated decoding rules.

## Verification

```bash
python -m pytest -q tests/test_api_path_boundary.py tests/test_bundle_api.py tests/test_fixture.py
```

The regression course exercises both generic Python methods, both MCP functions
and the real token client with HTTPX's offline transport. Rejected targets
produce no client dispatch; positive controls preserve the requested target and
payload. It needs no Canvas account or running browser.
