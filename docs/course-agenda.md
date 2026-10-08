# Read a selected-course agenda

Read the calendar events and assignment deadlines Canvas returns for up to ten
selected courses with one command:

```sh
canvaspilot agenda 42 77 --start 2026-10-08 --end 2026-10-15
```

The command prints one JSON report to standard output. It uses the same configured
Canvas host and PAT or existing session broker as the other readers. Dates are
required, inclusive `YYYY-MM-DD` bounds passed to Canvas. Course IDs must be
distinct positive decimal integers; leading zeroes are removed from the selection.
Select at most ten courses because Canvas ignores additional context codes. The
reader makes no assignment, calendar, submission or other learner-state writes.

## Read the report

`schema` is `canvaspilot.course-agenda.v1`. `selection` records the requested
course IDs, course context codes and date bounds. `collection_counts` records the
number of rows returned for each of the `event` and `assignment` calendar types;
`counts` reports their total and the number in each group below.

| Group | Meaning and ordering |
| --- | --- |
| `timed` | The record explicitly declares `all_day: false` and supplies a supported timestamp identifying a UTC instant. Event and assignment rows are combined in exact instant order. Equal instants keep returned order, with the event collection read first. |
| `all_day` | The record explicitly declares `all_day: true` and supplies a valid `all_day_date`. These rows are sorted by that date; no midnight instant or time zone is invented. |
| `timing_unavailable` | A required timing field is missing, null, invalid or ambiguous. The complete row remains visible, with a `timing_issue` identifying the field and reason. This group retains returned order. |

Each entry contains `kind` (`event` or `assignment`), resolved `course_id`, a
`source` containing the collection name and zero-based index in its concatenated
returned list, and the full original `record`. The index identifies a returned
position, not a page number or a permanent Canvas identity. IDs and timestamps
inside `record` keep their original types and text. The report also keeps title,
HTML description, location, URL, assignment overrides, nested assignment data,
hidden/locked flags and any additional supplied fields. It neither renders that
HTML nor expands recurrence rules or child events.

Numeric event IDs, string assignment IDs and repeated IDs in different courses
remain separate entries. No record is silently deduplicated. A course-section
record must carry a selected `effective_context_code`; conflicting course
contexts, explicit mismatched nested assignment course IDs, malformed identities
and non-object rows fail the read instead of being assigned to the wrong course.

An assignment calendar row can itself be declared all-day by Canvas. Its
`start_at`, nested `assignment.due_at` and override values are still preserved
inside `record`; the reader does not choose a different due date or replace an
override with the course-wide assignment date. A missing `all_day` flag cannot
establish whether a supplied timestamp should be presented as a timed event.

Timed sorting supports `YYYY-MM-DDTHH:MM:SS[.fraction]Z` and explicit `+HH:MM` or
`-HH:MM` offsets, including fractions more precise than microseconds. Under
[RFC 3339 section 4.3](https://www.rfc-editor.org/info/rfc3339/), `-00:00` still
identifies a UTC instant while leaving the local offset unknown. It therefore
participates in instant sorting, with its original marker preserved. Naive
timestamps, invalid calendar/clock values and unsupported leap-second notation
remain unavailable timing. Original values are always retained. Event end values
remain supplied observations; no duration is inferred.

## API and MCP

```python
from canvaspilot import CanvasAPI, CanvasClient

with CanvasClient() as client:
    report = CanvasAPI(client).course_agenda(
        [42, "77"], start_date="2026-10-08", end_date="2026-10-15",
    )
```

The read-only `canvas_course_agenda` MCP tool accepts:

```json
{
  "course_ids": [42, "77"],
  "start_date": "2026-10-08",
  "end_date": "2026-10-15"
}
```

Both surfaces return the same report. Booleans, fractional IDs, duplicate course
IDs, invalid dates and reversed bounds are rejected before a calendar request.
Missing CLI arguments produce the normal argparse exit 2. Invalid values or a
read failure produce exit 1, no report on stdout, and one JSON error on stderr.
The MCP equivalent is an error result; a failed read does not poison the next
read in the same session. Valid empty results and unavailable timing remain
successful observations, not errors or proof that work is complete.

## Selection and evidence limits

The reader uses Canvas's documented
[Calendar Events API](https://developerdocs.instructure.com/services/canvas/resources/calendar_events),
with separate `type=event` and `type=assignment` requests. It supplies the selected
course contexts and explicit dates to both, following the existing paginator's
opaque continuation links. It does not request `all_events`, `undated` or
`sub_assignment`, and does not reinterpret or locally filter Canvas's date-range
selection. A returned overlapping or otherwise out-of-range-looking row remains
visible for inspection. Separate date-sorted and instant-sorted groups do not
assert an ordering between an all-day date and an offset timestamp.

The two paginated collections are sequential observations through the current
caller's access. They are not an atomic or simultaneous snapshot and cannot
establish that the caller sees every course obligation. The unchanged paginator
can accept a terminal JSON object as a singleton list; the agenda validates the
client-returned list and every record, but cannot prove the original wire
response was an array. Malformed continuing pages, invalid continuations,
permission errors and other read failures propagate; no successful partial
agenda is emitted. Returned collection counts describe received rows only.

Calendar `hidden`, `locked` and workflow flags do not establish whether a student
can attend, submit or has completed anything. The report preserves supplied facts
without deriving attendance, availability, submission state, grades or reminders.
It does not export a file; the separate
[assignment calendar export](calendar-export.md) remains available for that task.

Qualification uses synthetic records through native API/CLI/MCP and unchanged
transport, plus the existing repository CI. It does not claim a live school
account, browser session or measured learner outcome.
