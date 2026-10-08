# Read course announcements from the terminal

Use the same authenticated CanvasPilot configuration as the other read commands.
The course IDs below are fictional examples.

```bash
canvaspilot announcements 42 77
canvaspilot announcements 42 77 --detail full
canvaspilot announcements 42 --start-date 2026-10-01
canvaspilot announcements 42 77 --start-date 2026-10-01T00:00:00Z --detail full
```

Supply one or more positive numeric course IDs. The command calls the maintained
`CanvasAPI.list_announcements` reader once for that selection. It sends the
existing active-announcement request and follows the client's normal pagination.
A course's `context_code` stays beside every returned announcement, and rows keep
the order supplied by Canvas across pages.

## Message detail and supplied fields

The JSON array uses the existing API projection:

| Field | Meaning |
| --- | --- |
| `id`, `title` | Supplied announcement identity and title |
| `posted_at` | Supplied posting timestamp, including its original offset |
| `context_code` | Supplied course context |
| `message_text` | Message after the existing HTML/entity/whitespace cleanup |
| `html_url` | Supplied Canvas link |

Default `--detail compact` limits cleaned message text to 400 characters, followed
by an ellipsis when truncated. `--detail full` keeps the complete cleaned text.
It uses the same fields and date selection. Returned nulls, zero values and empty
strings retain the existing reader's meanings; no posting time or course is guessed.
The output is indented JSON with Unicode escapes, so decoded text also survives
a narrow terminal encoding. Links remain plain returned values.

## Date selection

The optional `--start-date` value passes to the existing reader. Use a date such
as `2026-10-01` or an ISO 8601 timestamp such as `2026-10-01T00:00:00Z`.
The command performs no local date conversion.

[Canvas's Announcements API](https://developerdocs.instructure.com/services/canvas/resources/announcements)
defines the inclusive start filter and its server defaults: an omitted start
defaults to 14 days ago, and the default end is 28 days after the start.
The returned date window remains controlled by that existing API contract.
The caller needs announcement-view permission for every selected course.

## Completion and errors

The command prints the JSON result after the reader finishes. An empty successful
collection prints `[]`. Authentication, HTTP and pagination failures produce a
nonzero exit, a JSON error on stderr, and no partial successful array on stdout.
The existing client limits and pagination checks still apply.

This read uses the selected client's current authentication and sends no
read-state update. Qualification uses synthetic loopback responses; the source
receipt does not claim a school account was accessed.

## Native qualification

```bash
python -m pytest -q tests/test_announcements_cli.py tests/test_announcements_pagination.py
```

The new test runs the real CLI in subprocesses against an authored loopback HTTP
server. It covers course selection, opaque continuation, compact/full text,
original null/zero/Unicode fields, an ASCII console, empty results, argument
refusal and first/later-page errors. Its existing API and identity-command
controls keep the prior behavior observable. No transport implementation is
replaced, and fixture requests use no real Canvas data or browser session.
