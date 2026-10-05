# Session Broker HTTP API

The session broker (`canvaspilot session start`) keeps one Playwright persistent
context open and exposes an in-page Canvas fetch over localhost HTTP so CLI/MCP
calls do not re-run SSO every time.

Base URL: `http://127.0.0.1:<port>` — port is `18765` by default, overridden with
the `CANVAS_SESSION_PORT` env var. Binds **localhost only** (`127.0.0.1`).

> **Security notice (2026-10-05):** at current tip this API has no token
> authentication — anything that can reach localhost can drive your logged-in
> Canvas session. Two mitigations have landed since the original notice: the
> broker **refuses to start** on any non-loopback bind (fail-closed at
> startup), and `--read-only` rejects all non-`GET`/`HEAD` operations. Do not
> proxy it or expose it beyond `127.0.0.1`. Shared-secret auth remains
> proposed in canvaspilot issue #5 (PRs #7/#8/#9, still open).

All responses are JSON. `GET` paths match by prefix (`/health...`).

## Startup flags

`canvaspilot session start` accepts:

| Flag | Default | Effect |
|------|---------|--------|
| `--port` | `18765` (`CANVAS_SESSION_PORT`) | Listen port (localhost only — enforced, see notice) |
| `--base-url` | — | Canvas base URL (also sets `CANVAS_BASE_URL`) |
| `--profile` | — | Playwright persistent-profile directory |
| `--headless` | off | Run browser headless (use after a headed login into the same profile) |
| `--read-only` | off | Reject non-`GET`/`HEAD` `/fetch` ops with 403; for unattended agent use |

## Endpoints

### `GET /health` — broker liveness (no browser round-trip)

```json
{
  "ok": true,
  "ready": true,
  "url": "https://canvas.instructure.com/...",
  "title": "Dashboard",
  "headless": false,
  "error": null,
  "base_url": "https://canvas.instructure.com"
}
```

- `ready` — Playwright context is up and a Canvas page is open.
- `error` — set at startup only (e.g. `"playwright missing: ..."`); null when fine.

The CLI's `broker_health()` probes this with a 2s timeout and treats any
non-200 as "no broker".

### `GET /status` — browser job (needs the page)

```json
{ "ok": true, "url": "...", "title": "Dashboard", "headless": false, "logged_in": true }
```

- `logged_in` — current page is on an `instructure.com` URL and not at a
  `login.microsoft` SSO screen.

### `POST /fetch` — perform one Canvas request inside the logged-in page

Request body (JSON; `{"op": "fetch", ...}` also accepted — the `op` field is
ignored for routing):

```json
{
  "method": "GET",
  "path": "/api/v1/courses?per_page=50",
  "headers": { "Accept": "application/json" },
  "body": null
}
```

- `method` — default `"GET"`; uppercase applied server-side.
- `path` — relative path runs on the Canvas host (same-origin). An absolute URL
  is allowed: the broker navigates the page to that host first, then requests the
  relative path — so cross-site fetches are intentional page navigations, not
  silent third-party requests.
- `body` — string or JSON object; sent only for non-`GET`/`HEAD` methods
  (objects get `Content-Type: application/json`).

Response:

```json
{
  "ok": true,
  "response": {
    "status": 200,
    "json": { "..." : "parsed body" },
    "text": null
  }
}
```

- `response.text` is populated (max 4000 chars) only when the body is **not**
  valid JSON; otherwise it is `null`.
- The fetch runs with `credentials: 'include'`, so Canvas session cookies ride
  along — no token needed.

Errors (HTTP 200 wrapper with `"ok": false`, or client-side exceptions):

| Condition | Envelope |
|---|---|
| Request body is not JSON | HTTP 400 `{"ok": false, "error": "bad json"}` |
| Browser loop not ready (60s) | `{"ok": false, "error": "browser not ready"}` |
| Job takes > 120s | `{"ok": false, "error": "job timeout"}` |
| Canvas answered 401/403 | wrapped as `CanvasAuthError` by `client.py` ("log in in the broker window") |
| Canvas answered other 4xx/5xx | wrapped as `httpx.HTTPStatusError` by `client.py` |

### `POST /shutdown` — stop the broker

```json
{ "ok": true, "shutdown": true }
```

The broker process exits ~0.3s after responding. Unknown paths return
`{"ok": false, "error": "not found"}` (404).

## Operational notes

- Startup emits two JSON lines on stdout: `{"status": "session_ready", ...}`
  (browser + profile + port) and `{"status": "listening", "url": ...}`.
- Job queue is a single in-page worker; concurrent `/fetch` calls serialize.
- In-page fetch drops response headers, so Canvas `Link: rel=next` pagination is
  invisible here. `CanvasClient.get_paginated()` compensates with explicit
  `?page=N&per_page=M` requests (max 100 per page, 40-page cap, warns on
  truncation). The token auth path follows `Link` headers normally.
- `POST` requests honor the `Content-Length` header (`{}` when absent); a
  missing body is treated as an empty object.
- Logging is silenced (`log_message` no-op) — there is no access log on this
  listener, another reason to keep it localhost-only.

Source of truth: `src/canvaspilot/session_broker.py` and
`src/canvaspilot/client.py` (client envelope semantics).
