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

```bash
pip install "canvaspilot[browser]"      # or: pip install -e ".[browser]" from a checkout
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
| **Full REST** | `canvas_api_request`, `canvas_api_paginated` — any `/api/v1/...` path (escape hatch for everything else; in session-broker mode `api_paginated` returns a single page only — see Auth modes) |

Programmatic API bundle: `from canvaspilot.bundle import make_api, tool_inventory`.

## Auth modes

| Mode | How | When |
|------|-----|------|
| **session** (default) | Playwright persistent profile + local broker on `127.0.0.1:18765` | School disables student PATs / SSO+MFA |
| **token** | `CANVAS_API_TOKEN` → `Authorization: Bearer` | School allows PATs |
| **fixture** | `CanvasClient(fixture={...})` | Tests, offline demos |

Mode resolution is fixture > token > live broker > session, decided at runtime: `CANVAS_API_TOKEN` always wins and skips the broker; otherwise a live `GET 127.0.0.1:18765/health` probe decides whether the session broker is used. Bare "session" mode with no running broker raises on every request — "session (default)" means "broker if it's up", not "works with no setup".

Pagination follows response `Link` headers only in token mode (up to 40 pages). In session-broker mode the broker returns a single page (`per_page` ≤ 100); paginate by repeated calls.

The broker only listens on loopback. Cookies never leave the Playwright profile directory; the MCP/CLI process never sees them — it asks the broker to make the request.

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

Tests run entirely in fixture mode.

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
