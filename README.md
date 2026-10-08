# CanvasPilot

Agentic Canvas LMS tools for LLMs — an **MCP server + CLI** that talks to Canvas's real REST API using the session your browser already has.

Most Canvas MCPs need a Personal Access Token. Many schools disable student PATs and hide Canvas behind SSO/MFA. CanvasPilot solves that with a **stay-open session broker**: you log in once in a real browser (Playwright, persistent profile), then every tool call rides that authenticated session — headless, for as long as the cookies live.

Same architecture as OpenCLI-style web agents (persistent browser session → site's real HTTP/JSON API), purpose-built for Canvas.

## Features

- **Auth designed for real schools** — session broker (SSO/MFA, no PAT needed) *or* classic `CANVAS_API_TOKEN`
- **Headless after one headed login** — `session start --headless` reuses the saved profile
- **Full REST surface** — courses, assignments, modules, pages, files, discussions, announcements, planner, inbox, calendar, activity stream, submissions, and **quizzes** (list/questions/submissions/start/complete)
- **Agent-shaped digests** — `assignment_brief` (cleaned prompt + rubric), `sync_summary` (courses + upcoming), `submission_status`
- **Submission feedback** — self submission comments and rubric assessments alongside current-attempt and grading metadata
- **Fixture mode** — offline dict backend for tests and CI; no Canvas required
- **35 MCP tools**, one stdio server, one env var for the host (`CANVAS_BASE_URL`) plus either a PAT or a running session broker
- **Course folder browsing** — select nested folders and inspect bounded file-metadata pages through CLI, MCP or Python

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
canvaspilot feedback <course_id> <assignment_id>
```

`canvaspilot sync` orders upcoming assignments by deadline across the selected
courses. It includes up to 10 courses and 5 assignments per course by default,
and reports omitted rows, unknown dates, and per-course read failures. Adjust
the overview with `--limit-courses` and `--limit-assignments-per-course`; see
[the sync guide](docs/SYNC.md) for CLI, Python, and MCP examples and count meanings.

To take selected course deadlines into a calendar application, save an explicit
local snapshot with `canvaspilot export-calendar 42 77 --out deadlines.ics`.
The [calendar export guide](docs/calendar-export.md) explains selection,
undated omissions, snapshot limits and safe re-import expectations.

With a PAT instead:

```bash
export CANVAS_API_TOKEN=...   # broker not needed
canvaspilot courses
```

## Assignment briefs

`canvaspilot brief <course_id> <assignment_id>`, the Python
`CanvasAPI.assignment_brief()` method, and the MCP `canvas_assignment_brief` tool
return the same JSON brief: the cleaned prompt, due date, assignment points,
submission types, Canvas link, and the rubric supplied with the assignment.

- `rubric` preserves the supplied criterion and rating order, IDs, descriptions,
  long descriptions, points (including zero), range/scoring flags, and outcome
  identifiers. Rubric text is not rewritten. Only these canonical rubric fields
  are projected; `get_assignment()` retains the complete original rubric payload.
- `rubric_settings` preserves the supplied settings object, including any display
  flags such as `hide_points`, `hide_score_total`, and free-form criterion comments.
  The CLI and MCP return data, without rendering a Canvas rubric UI. Consumers
  should honor the distinct display flags when rendering it.
- `use_rubric_for_grading` preserves Canvas's boolean: `false` means the rubric is
  advisory; `null` means the assignment response did not supply a usable value.
- `rubric_warnings` is normally empty. Malformed optional containers, entries, or
  canonical field values are omitted locally with a warning that names their
  location, while the ordinary brief and usable neighboring entries remain.

A missing or `null` rubric remains `null`; a supplied empty list remains `[]`.
Missing criterion fields are not filled in, and missing ratings remain unknown.
No criteria, score totals, or grading requirements are inferred. Assignment
`points_possible` and rubric settings' `points_possible` remain separate supplied
values. This uses the existing assignment GET request, without another rubric
request or a change to authentication.

The field meanings follow Canvas's [Assignments API](https://developerdocs.instructure.com/services/canvas/resources/assignments)
and [Rubrics API](https://developerdocs.instructure.com/services/canvas/resources/rubrics).
The public-path tests in `tests/test_assignment_brief_rubric.py` use a clearly
synthetic assignment and forbid HTTP and broker access.

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
| Courses | `list_courses`, `get_course`, `list_modules`, `list_pages`, `get_page`, `list_files`, `browse_files`, `list_announcements` |
| Assignments | `list_assignments`, `get_assignment`, `assignment_brief`, `submission_status`, `submission_feedback`, `submit_assignment_text` |
| Discussions | `list_discussion_topics`, `get_discussion`, `post_discussion_reply` |
| Quizzes | `list_quizzes`, `get_quiz`, `list_quiz_questions`, `list_quiz_submissions`, `start_quiz_submission`, `complete_quiz_submission` |
| Inbox / Calendar | `list_conversations`, `get_conversation`, `reply_conversation`, `list_calendar_events` |
| **Full REST** | `canvas_api_request`, `canvas_api_paginated` — any `/api/v1/...` path (escape hatch for everything else; in session-broker mode `api_paginated` returns a single page only — see Auth modes) |

Programmatic API bundle: `from canvaspilot.bundle import make_api, tool_inventory`.

### Submission feedback

Use `canvaspilot feedback <course_id> <assignment_id>`, the MCP tool
`canvas_submission_feedback`, or `CanvasAPI.submission_feedback(course_id, assignment_id)`
to review your submission comments and rubric evidence together. The report uses
the [assignment](https://developerdocs.instructure.com/services/canvas/resources/assignments)
and [self submission](https://developerdocs.instructure.com/services/canvas/resources/submissions)
GET endpoints, requesting `submission_comments` and `rubric_assessment`. It uses
the selected client's existing authentication and returns only what Canvas exposes
to that user.

The JSON report contains:

- `assignment`: the assignment's identity, title, URL, due date, and possible points.
- `submission`: Canvas's score, grade, attempt, workflow state, grader ID, and
  submission/grading timestamps. A false `grade_matches_current_submission` means
  the student resubmitted since grading; the displayed grade may describe an
  earlier attempt. A missing flag remains `null`. Negative grader IDs are retained
  because Canvas can identify an autograder that way.
- `rubric.criteria`: each original `criterion` beside its `assessment`, joined
  only by a unique exact string criterion ID. Criterion descriptions, ratings,
  `ignore_for_scoring`, and `criterion_use_range` remain available. Missing or
  ambiguous IDs leave the assessment in `rubric.unmatched_assessments`, keyed by
  its original ID. Assessment points and comments are preserved as returned.
- `rubric.use_rubric_for_grading` and `rubric.settings`: Canvas's grading/advisory
  distinction and rubric settings. The report does not sum rubric points or infer
  a grade. `assessment_returned` says whether Canvas returned an assessment object,
  including an empty object; it does not mean the submission has been graded.
- `submission_comments`: original comment objects, including authors, timestamps,
  media comments, and attachments when supplied. Students and peers can also
  author these comments. Media-only comments remain present.

Zero marks remain zero. Missing/null comments or rubric data remain `null`, while
explicitly returned empty arrays/maps remain empty. A criterion with no matching
assessment has `assessment: null`; omitted assessment points or comments remain
omitted. An inaccessible submission or malformed response is reported as an error,
so it cannot be mistaken for a submission with no feedback. This operation performs
two GETs and does not mark comments read, submit work, or change a grade.

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

## Browse course folders

```bash
canvaspilot browse-files 42
canvaspilot browse-files 42 --folder-id 110 --files-page 2 --per-page 20
```

Start at the course root, then choose a returned child folder ID. Each result
contains the selected folder and one requested page each of direct child folders
and files. Only metadata is returned; file bodies and download/preview URLs are
excluded. A foreign folder or permission failure returns an error, not an empty
listing. `has_more` is unknown because the existing request interface omits
pagination headers; `next_page_to_try` is an optional probe, not a completeness
claim. See [folder-browser usage and contract](docs/folder-browser.md) for the
MCP/Python interfaces, page limits and examples.

## Auth modes

| Mode | How | When |
|------|-----|------|
| **session** (default) | Playwright persistent profile + local broker on `127.0.0.1:18765` | School disables student PATs / SSO+MFA |
| **token** | `CANVAS_API_TOKEN` → `Authorization: Bearer` | School allows PATs |
| **fixture** | `CanvasClient(fixture={...})` | Tests, offline demos |

Mode resolution is fixture > token > live broker > session, decided at runtime: `CANVAS_API_TOKEN` always wins and skips the broker; otherwise a live `GET 127.0.0.1:18765/health` probe decides whether the session broker is used. Bare "session" mode with no running broker raises on every request — "session (default)" means "broker if it's up", not "works with no setup".

Pagination follows response `Link` headers only in token mode (up to 40 pages). In session-broker mode the broker returns a single page (`per_page` ≤ 100); paginate by repeated calls.

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

Tests use offline fixtures and disposable loopback HTTP servers. Feedback tests
also exercise CLI subprocesses and the real MCP stdio interface; no Canvas account
or running browser is needed.

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

