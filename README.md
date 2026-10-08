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
- **Submission history** — inspect returned attempts and submitted text/file metadata without assigning current grades or comments to earlier versions ([guide](docs/submission-history.md))
- **Submission comparison** — read two explicitly selected returned records side by side in a new offline HTML report, with exact source JSON ([guide](docs/submission-comparison.md))
- **Course grade review** — reported totals, assignment-group rules and each returned assignment's own grade/status, with hidden and unknown values kept explicit
- **Fixture mode** — offline dict backend for tests and CI; no Canvas required
- **40 MCP tools**, one stdio server, one env var for the host (`CANVAS_BASE_URL`) plus either a PAT or a running session broker
- **Course folder browsing** — select nested folders and inspect bounded file-metadata pages through CLI, MCP or Python
- **Module progress checklist** — review reported completion, remaining requirements and module locks through CLI, MCP or Python

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
canvaspilot submission-history <course_id> <assignment_id>
canvaspilot grade-review <course_id>
```

`canvaspilot sync` orders upcoming assignments by deadline across the selected
courses. It includes up to 10 courses and 5 assignments per course by default,
and reports omitted rows, unknown dates, and per-course read failures. Adjust
the overview with `--limit-courses` and `--limit-assignments-per-course`; see
[the sync guide](docs/SYNC.md) for CLI, Python, and MCP examples and count meanings.

Assignment lists and sync rows also include the current user's reported
submission state, attempt, and late/missing/excused flags when Canvas supplies
them. Missing data remains unknown; the existing `has_submitted_submissions`
flag describes submissions by any student. See the
[assignment submission guide](docs/assignment-submission.md) for field meanings,
selection examples and malformed-data warnings.

Read selected courses' calendar events and assignment deadlines together with
`canvaspilot agenda 42 77 --start 2026-10-08 --end 2026-10-15`. The
[course agenda guide](docs/course-agenda.md) explains timed, all-day and unavailable
timing, source identity and read limits. The same report is available through
`canvas_course_agenda` in MCP.

Read your own planner items with `canvaspilot planner --start-date 2026-10-08 --end-date 2026-10-15`.
The [planner CLI guide](docs/planner-cli.md) explains native date filters,
personal notes, supplied completion metadata and complete-list error behavior.
The command uses the existing planner API and does not change any planner state.

Save that same selection as an offline view with course/source-date/search controls
and a printable current view:
`canvaspilot export-agenda 42 77 --start 2026-10-08 --end 2026-10-15 --out agenda.html`.
The original native JSON remains available byte-identically.
[Review and print a saved agenda](docs/agenda-export.md).

Read your reported enrollment roles, states and grades with `canvaspilot enrollments`.
The [enrollments CLI guide](docs/enrollments-cli.md) explains the default active
filter, native state selection and the complete returned JSON collection.

To take selected course deadlines into a calendar application, save an explicit
local snapshot with `canvaspilot export-calendar 42 77 --out deadlines.ics`.
The [calendar export guide](docs/calendar-export.md) explains selection,
undated omissions, snapshot limits and safe re-import expectations.


To take explicitly selected course pages offline, use
`canvaspilot export-pages 42 course-introduction week-two-reading --out reading.html`.
The [page export guide](docs/page-export.md) explains numeric page IDs, the inert
original-source record, selection limits and protection of existing output.
With a PAT instead:

```bash
export CANVAS_API_TOKEN=...   # broker not needed
canvaspilot courses
```

To inspect Canvas-reported course totals and assignment grades together, run
`canvaspilot grade-review 42` or call the read-only MCP `canvas_grade_review` tool.
The [grade review guide](docs/grade-review.md) explains the original Canvas field
names, group/drop-rule context, visibility rules and returned-row limits. No
replacement course grade or missing-work status is inferred.

Save that same grade review for offline reading or printing with
`canvaspilot export-grade-review 42 --out course-grades.html`. The
[saved grade-review guide](docs/grade-review-export.md) explains reported totals,
assignment context, withheld/unknown values, the complete JSON download and
new-file protection.

## Save submission attempts for offline review

Save the existing self-history report as a readable standalone HTML file:

```bash
canvaspilot export-submission-history 71 902 --out submission-history.html
```

The report keeps the current submission, every returned historical record, and
top-level comments separate. Returned order and missing/empty distinctions stay
visible; current grades are never assigned to earlier attempts. It includes the
complete normalized JSON and works with the browser's Print command. Existing
files are protected. See [offline submission history](docs/submission-history-export.md)
for scope, provenance, limits and CLI/Python usage.

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

To read selected briefs alongside your own notes, use
`canvaspilot export-study 42 1001 1008 --out study.html`. The self-contained
workspace supports local review checks, downloaded working copies, and printing.
See the [assignment study workspace guide](docs/study-workspace.md) for the
selection, source, and note-saving boundaries.

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
| Courses | `list_courses`, `get_course`, `grade_review`, `list_modules`, `module_progress`, `list_pages`, `get_page`, `list_files`, `browse_files`, `list_announcements` |
| Assignments | `list_assignments`, `get_assignment`, `assignment_brief`, `submission_status`, `submission_feedback`, `submission_history`, `submit_assignment_text` |
| Discussions | `list_discussion_topics`, `get_discussion`, `discussion_thread`, `post_discussion_reply` |
| Quizzes | `list_quizzes`, `get_quiz`, `list_quiz_questions`, `list_quiz_submissions`, `start_quiz_submission`, `complete_quiz_submission` |
| Inbox / Calendar | `list_conversations`, `get_conversation`, `reply_conversation`, `list_calendar_events`, `course_agenda` |
| **Full REST** | `canvas_api_request`, `canvas_api_paginated` — any `/api/v1/...` path, including paginated reads through a current session broker (see Auth modes for collection requirements) |

Programmatic API bundle: `from canvaspilot.bundle import make_api, tool_inventory`.

### Read classic quizzes from the terminal

List a course’s classic quizzes, then inspect one returned quiz ID:

```bash
canvaspilot quizzes 42
canvaspilot quiz 42 9
```

Both commands accept the existing `--base-url`, `--profile` and `--token` options.
Course and quiz IDs must be positive numeric Canvas IDs. `quizzes` uses the existing
paginated reader and compact list fields; `quiz` returns the original detail JSON,
including any supplied timing, attempt-policy, lock and differentiated-date fields.
Null dates and false/zero values keep their original meaning. A failed read exits
nonzero with a JSON error on stderr and no partial success output.

These commands call only the existing [classic-quiz GET endpoints](https://developerdocs.instructure.com/services/canvas/resources/quizzes).
They do not start or complete an attempt, read questions, or change submissions.
New Quizzes and LTI assessments retain the existing separate support boundary.

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

### Read a discussion

After choosing a topic with `canvaspilot discussions <course_id>`, open it with
`canvaspilot discussion <course_id> <topic_id>`. Add `--unread-only` to keep known
unread replies together with their parent context. The same report is available
through `CanvasAPI.discussion_thread()` and `canvas_discussion_thread` in MCP.

The report keeps original entry fields and the returned reply structure, alongside
cleaned text, unambiguous author attribution and reported read markers. Missing
facts remain unknown; absent or ambiguous unread metadata does not become a
false empty result. Canvas's cached-view boundary and unmatched unread identifiers
remain visible. See [the discussion reader guide](docs/DISCUSSIONS.md) for fields,
selection rules and error behavior.

### Announcements

Read selected courses from the terminal with `canvaspilot announcements 42 77`.
Choose `--detail full` for complete cleaned message text and optionally supply
`--start-date 2026-10-01`. The command preserves the existing course context,
pagination and date-window rules; see [terminal announcement review](docs/announcements-cli.md)
for fields, defaults and error behavior.

`canvas_list_announcements` and `CanvasAPI.list_announcements()` use the existing
client paginator in both compact and full detail modes. Course and optional start-date
filters are retained, and results keep Canvas's page order and announcement metadata.
Compact message text remains limited to 400 characters plus an ellipsis; full detail
retains the complete stripped text. A failed page request raises an error instead of
returning the announcements collected before the failure. The selected client's
existing transport and pagination limits still apply.

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

## Review module progress

```bash
canvaspilot module-progress 42
canvaspilot module-progress 42 --module-id 7
```

Review Canvas-declared module states and completed, unfinished or unknown item
requirements. The checklist keeps all-versus-one requirements, prerequisites and
sequential-progress context. Missing student fields stay unknown; counts cover
returned rows. This read-only workflow never marks items read or complete. See
[the module-progress guide](docs/module-progress.md) for Python/MCP examples and
coverage meanings.

Save that same report for offline reading or printing:

```bash
canvaspilot export-module-progress 42 --out module-progress.html
canvaspilot export-module-progress 42 --module-id 7 --out module-7-progress.html
```

The self-contained HTML keeps the reader's states, all-versus-one rules,
thresholds, prerequisites, unknowns and coverage diagnostics visible. It includes
the complete normalized report as a JSON download and protects existing output
paths. See [offline module-progress reports](docs/module-progress-export.md).

## Course files

`canvaspilot files COURSE_ID`, `CanvasAPI.list_files(COURSE_ID)`, and
`canvas_list_files` read the existing paginated course file collection.
Authentication, request, and pagination errors propagate without a successful
partial result or an automatic change to a root-folder listing. This includes
errors on the first page. An empty successful collection remains an empty list;
the existing field projection and returned page order are unchanged.
Use the explicit folder browser below when you want a selected folder's direct
children instead of the course collection.

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

## Review your inbox

```bash
canvaspilot inbox --scope unread
canvaspilot conversation 901
```

List your conversations and select a returned ID to inspect its messages.
The CLI, Python API and existing MCP conversation reader explicitly preserve
unread state. Original message, participant and attachment metadata are returned;
linked content is not downloaded. See [inbox review](docs/inbox-review.md) for
scope choices, pagination and error behavior.

## Save course syllabi

Use `canvaspilot export-syllabus 42 57 --out syllabi.html` to keep explicitly selected syllabus bodies in one readable, printable offline HTML packet. Missing, unavailable and explicitly empty bodies stay distinct; linked files and media remain clearly marked external resources. The command protects existing output paths and refuses the whole file if a requested course cannot be read or validated. [Source, limits and usage](docs/syllabus-packet.md).

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

Token collection reads validate both the initial URL and each next URL against
the client's configured Canvas scheme, host and effective port before dispatch.
Initial absolute URLs retain their authored query and receive the initial
filters once. Session continuation stays on the broker's configured Canvas
origin and retains the exact absolute continuation URL.

Each applicable Link entry must carry a valid relation. Anchored links are
ignored as whole entries because they change the context; registered relation
names such as `next` are matched without regard to case. Quoted parameter values
and absolute URI extension relations remain supported. Invalid or ambiguous
metadata, repeated continuation URLs, a later-page error or non-list body, and
a known continuation beyond the 40-page limit raise an error. A terminal first
single-object response keeps its existing convention. `CanvasPaginationError`
is available from `canvaspilot.client`.

An older running broker without the capability flag produces an actionable
incomplete-collection error. Restart it with the current CanvasPilot version and
retry the read. Ordinary single requests remain compatible with older brokers.
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

Tests use offline fixtures and disposable loopback HTTP servers. Feedback tests
also exercise CLI subprocesses and the real MCP stdio interface; no Canvas account
or running browser is needed.

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


## Announcement text search

Find a literal phrase in the complete titles and cleaned messages for selected courses:

```bash
canvaspilot find-announcements 42 77 --text "room change" --start-date 2026-10-01
```

The result preserves ordered full announcement rows and identifies which fields matched.
See [announcement text search](docs/announcement-search.md) for matching, output, and complete-read behavior.

## Find text in course pages

Use `canvaspilot find-pages 42 --text "field journal"` to search returned page
titles and available body text. Unavailable bodies remain explicit; see
[page search and coverage](docs/page-search.md).
