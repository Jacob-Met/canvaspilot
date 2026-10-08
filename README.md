# CanvasPilot

Agentic Canvas LMS tools for LLMs — an **MCP server + CLI** that talks to Canvas's real REST API using the session your browser already has.

Most Canvas MCPs need a Personal Access Token. Many schools disable student PATs and hide Canvas behind SSO/MFA. CanvasPilot solves that with a **stay-open session broker**: you log in once in a real browser (Playwright, persistent profile), then every tool call rides that authenticated session — headless, for as long as the cookies live.

Same architecture as OpenCLI-style web agents (persistent browser session → site's real HTTP/JSON API), purpose-built for Canvas.

## Features

- **Auth designed for real schools** — session broker (SSO/MFA, no PAT needed) *or* classic `CANVAS_API_TOKEN`
- **Headless after one headed login** — `session start --headless` reuses the saved profile
- **Full REST surface** — courses, assignments, modules, pages, files, discussions, announcements, planner, inbox, calendar, activity stream, submissions, and **quizzes** (list/questions/submissions/start/complete)
- **Agent-shaped digests** — `assignment_brief` (cleaned prompt + rubric), `sync_summary` (courses + upcoming), `submission_status`
- **Fixture mode** — offline dict backend for tests and CI; no Canvas required
- **33 MCP tools**, one stdio server, one env var for the host (`CANVAS_BASE_URL`) plus either a PAT or a running session broker

## Install

Not published to PyPI yet — install from a checkout:

```bash
git clone https://github.com/Jacob-Met/canvaspilot.git
cd canvaspilot
pip install -e ".[browser]"
playwright install chromium
```

Requires Python 3.11+.

## Try it offline first

From an installed package or an editable source checkout:

```bash
python -m canvaspilot.offline_demo
# Optional: save to a NEW path (existing files are protected)
python -m canvaspilot.offline_demo --out synthetic-review.json
```

This exercises the high-level course and assignment-brief API on two explicitly
synthetic courses. It strips prompt markup, preserves a missing due date as
unknown, and returns readable JSON. No Canvas account, browser, token, session
broker, model call, submission, or runtime network connection is needed. The
example rejects writes and missing fixture routes instead of falling back to
live access. Installing package dependencies requires network access separately.

This is a small, inspectable behavior demonstration, not evidence of live
pagination, working school authentication, or student outcomes. The tests in
`tests/test_offline_demo.py` protect these boundaries.

## Quick start

```bash
export CANVAS_BASE_URL=https://<school>.instructure.com

# 1) Log in once (headed — finish SSO/MFA in the window), leave the broker running
canvaspilot session start

# 2) Later: restart headless on the same saved profile
canvaspilot session start --headless

# 3) Use it
canvaspilot whoami
canvaspilot courses
canvaspilot sync
canvaspilot brief <course_id> <assignment_id>
```

With a PAT instead:

```bash
export CANVAS_API_TOKEN=...   # broker not needed
canvaspilot courses
```

## MCP server

```bash
canvaspilot mcp          # stdio
```

Cursor / Claude Desktop / any MCP client:

```json
{
  "mcpServers": {
    "canvas": {
      "command": "canvaspilot",
      "args": ["mcp"],
      "env": { "CANVAS_BASE_URL": "https://<school>.instructure.com" }
    }
  }
}
```

Tools exposed (all prefixed `canvas_`):

| Area | Tools |
|------|-------|
| Identity | `whoami`, `sync_summary`, `planner_items`, `activity_stream`, `list_todo_items`, `list_enrollments` |
| Courses | `list_courses`, `get_course`, `list_modules`, `list_pages`, `get_page`, `list_files`, `list_announcements` |
| Assignments | `list_assignments`, `get_assignment`, `assignment_brief`, `submission_status`, `submit_assignment_text` |
| Discussions | `list_discussion_topics`, `get_discussion`, `post_discussion_reply` |
| Quizzes | `list_quizzes`, `get_quiz`, `list_quiz_questions`, `list_quiz_submissions`, `start_quiz_submission`, `complete_quiz_submission` |
| Inbox / Calendar | `list_conversations`, `get_conversation`, `reply_conversation`, `list_calendar_events` |
| **Full REST** | `canvas_api_request`, `canvas_api_paginated` — any `/api/v1/...` path, including paginated reads through the session broker (see Auth modes for older-broker compatibility) |

Programmatic API bundle: `from canvaspilot.bundle import make_api, tool_inventory`.

### Module contents

`canvas_list_modules` and `CanvasAPI.list_modules()` retrieve module items even
when Canvas omits the optional inline `items` array. Missing, null, malformed, or
shorter inline contents are fetched through the existing paginated module-items
route; valid complete inline arrays and modules reporting an integer zero need no extra
request. Compact output retains its existing item fields; `detail=full` preserves
Canvas's module metadata and the retrieved item payloads. A failed secondary
request or malformed item response is reported to the caller instead of being
presented as an empty module.

This follows the [Canvas Modules API](https://developerdocs.instructure.com/services/canvas/resources/modules)
contract. Requests use the selected client's existing fixture, token, or session
broker transport and pagination limits. Listing does not mark module items read
or complete.

## Auth modes

| Mode | How | When |
|------|-----|------|
| **session** (default) | Playwright persistent profile + local broker on `127.0.0.1:18765` | School disables student PATs / SSO+MFA |
| **token** | `CANVAS_API_TOKEN` → `Authorization: Bearer` | School allows PATs |
| **fixture** | `CanvasClient(fixture={...})` | Tests, offline demos |

Mode resolution is fixture > token > live broker > session, decided at runtime: `CANVAS_API_TOKEN` always wins and skips the broker; otherwise a live `GET 127.0.0.1:18765/health` probe decides whether the session broker is used. Bare "session" mode with no running broker raises on every request — "session (default)" means "broker if it's up", not "works with no setup".

Pagination follows Canvas's response `Link` headers in token mode and in current
session brokers. A session broker advertises `"link_pagination": true` in
`GET /health` and forwards only the `Link` response header alongside each fetch
result. The client follows an opaque `rel=next` URL even when a page is shorter
than the requested `per_page`; it stops when no next link remains, without
inventing a numeric page or requesting an extra empty page. Initial filters and
repeated `include[]` values apply only to the first request; subsequent URLs
retain the server's exact parameters. Ordinary single-request results keep their
existing decoded JSON/text shape.

Session continuation must stay on the broker's configured Canvas origin. Invalid
or ambiguous Link metadata, repeated continuation URLs, a later-page error, or a
known continuation beyond the 40-page limit raises an error instead of returning
the accumulated pages as a complete result. `CanvasPaginationError` is available
from `canvaspilot.client`. This does not change the existing token-mode page cap.
Each session Link entry must carry a valid relation. Link parameters that change
the context with `anchor` are unsupported and raise an error; registered relation
names such as `next` are matched without regard to case. Quoted parameter values
and absolute URI extension relations remain supported.

An older running broker without the capability flag keeps the previous numeric
`page=1..40` compatibility behavior, including its truncation warning. That
fallback still infers completion from page length and cannot handle opaque
server cursors reliably. Restart the broker with the current source to enable
Link following; no browser profile or Canvas login is replaced by this update.
The [Canvas pagination contract](https://developerdocs.instructure.com/services/canvas/basics/file.pagination)
explains why clients must check Link even when they request a page size.

The broker only listens on loopback — and `session_broker.main()` now refuses to start on any non-loopback bind address (fail-closed: a future host change cannot silently expose the unauthenticated `/fetch`/`/shutdown` endpoints to the network). Cookies never leave the Playwright profile directory; the MCP/CLI process never sees them — it asks the broker to make the request.

## Configuration

| Env | Default | Purpose |
|-----|---------|---------|
| `CANVAS_BASE_URL` | `https://canvas.instructure.com` | Your school's Canvas host |
| `CANVAS_API_TOKEN` | — | PAT (skips the broker) |
| `CANVAS_PROFILE` | `~/.canvaspilot/profile` | Playwright persistent profile dir |
| `CANVAS_SESSION_PORT` | `18765` | Broker port |
| `CANVASPILOT_REPORTS` | `~/.canvaspilot/reports` | Output dir for `scripts/` sweeps |

## Session broker commands

```bash
canvaspilot session start [--headless] [--base-url URL] [--profile DIR] [--port N] [--read-only]
canvaspilot session status
canvaspilot session stop
```

`--read-only` is for unattended agent use: the broker rejects non-GET/HEAD
`/fetch` ops with 403, so a runaway agent cannot mutate Canvas through the
session. `GET /health` advertises the mode (`"read_only": true|false`), so
clients can discover it. It is orthogonal to broker authentication (see issue
#5) — it limits *what* the broker can do, not *who* can call it.

## Scripts

- `scripts/readonly_sweep.py` — live read-only smoke across the whole tool surface (needs a running broker)
- `scripts/inventory_pass.py` — per-course inventory: tabs, LTI/external tools, modules, third-party mentions

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests use authored fixtures and loopback HTTP servers without Canvas access.

The optional native-browser check executes the production in-page fetch against
an authored loopback response in a fresh Chromium profile. It uses no school
session and verifies that the fixture cookie remains in the browser while only
Link metadata reaches the caller:

```bash
CANVASPILOT_CHROMIUM_BIN=/path/to/chromium python -m pytest -q tests/test_browser_link_metadata.py
```

`CANVASPILOT_CHROMIUM_PROFILE_ROOT` can select a writable parent for temporary
profiles (useful for a confined browser package). The browser test skips only
when `CANVASPILOT_CHROMIUM_BIN` is unset; an invalid configured executable fails.
All regular HTTP/client tests run offline without a browser binary.

## Responsible use

CanvasPilot gives an agent the same access you have — including submitting assignments and starting quiz attempts. Write tools are clearly named; wire approval gates in your agent if you don't want autonomous submits. Follow your institution's academic integrity policy.

Write caveats: the write path has no CSRF handling and has not been validated against live Canvas session authentication — submitting from session-broker mode may fail or behave unexpectedly. The author has not used the write tools against a live school; they exist as capability, not as a tested workflow.

## Origin

Extracted from the Suite monorepo (`packages/canvaspilot`), where it's synced via `git subtree`. (The monorepo is not publicly accessible; the link resolves for authorized collaborators.)

## License

MIT

## Maintainer

[Jacob Metoyer](https://jacobmetoyer.com/) — software and research tooling.
Upstream and collaborator credit are retained.

