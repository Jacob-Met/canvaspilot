# Upcoming deadline overview

The sync overview reads active courses and their upcoming assignments, then
orders the selected assignments by deadline across courses. Use it to see which
of those deadlines comes next and whether the overview omitted any returned
courses or assignments.

## CLI

With your existing CanvasPilot connection configured:

```bash
canvaspilot sync
canvaspilot sync --limit-courses 20 --limit-assignments-per-course 12
```

The defaults are 10 courses and 5 assignments per course. Both limits must be
positive integers. The CLI rejects invalid limits before creating a client.

Courses retain the order returned by the course API. Only the selected courses
have their assignments fetched. Within each selected course, assignments with
recognized timezone-aware due dates are ordered first, and the per-course limit
is applied to that order. The resulting assignments are then ordered together
across courses.

The operation uses the existing course and assignment GET requests with the
`upcoming` assignment bucket. Canvas determines which assignments belong to that
bucket; the overview does not independently filter against the local clock.

## Dates and ties

Deadline order compares timezone-aware timestamps by their instant. For example,
`2026-10-10T00:30:00+02:00` comes before `2026-10-09T23:00:00Z`.
Assignments with the same instant retain their original order: selected course
order first, then assignment order within that course.

Every `due_at` value is returned unchanged. Missing dates, date-only strings,
timestamps without a timezone, and unrecognized values are treated as unknown
and placed after the recognized deadlines. Unknown dates retain their source
order and count toward the per-course assignment limit. The overview does not
infer a timezone or supply a date for them.

## Reading the counts

The original `mode`, `course_count`, `courses`, and `upcoming_assignments` fields
remain. Assignment rows still include their course name. The overview also
returns these selection details:

| Field | Meaning |
| --- | --- |
| `course_count` | Number of courses selected for assignment reads, including courses whose assignment read failed. |
| `courses_returned` | Number of courses returned by the existing course API before the overview's limit. |
| `courses_omitted` | Returned courses excluded by `limit_courses`. |
| `limits.courses` | Effective course limit. |
| `limits.assignments_per_course` | Effective assignment limit for each selected course. |
| `course_summaries` | One summary for each selected course, in selected course order. |

Each item in `course_summaries` has the following fields:

| Field | Successful assignment read | Failed assignment read |
| --- | --- | --- |
| `course_id` | Course identifier | Course identifier |
| `status` | `"ok"` | `"error"` |
| `assignments_returned` | Assignment rows returned before selection | `null` |
| `assignments_included` | Rows included in the overview | `null` |
| `assignments_omitted` | Returned rows excluded by the assignment limit | `null` |
| `unknown_due_dates` | Unknown dates among **all returned rows**, including omitted rows | `null` |

An empty successful course has zero for all four counts. A failed course keeps
unknown counts as `null` and retains its `{"course_id": ..., "error": ...}` row
in `upcoming_assignments`, after dated assignments. Other courses still appear.
If the initial course-list request fails, the operation raises that error.

For example, a successful course could report:

```json
{
  "course_id": 101,
  "status": "ok",
  "assignments_returned": 8,
  "assignments_included": 5,
  "assignments_omitted": 3,
  "unknown_due_dates": 2
}
```

This means three returned assignments were left out of the overview and two of
the eight returned assignments had unknown due dates. It does not imply that
both unknown dates are present in the five included rows. Increase the assignment
limit to include more of the returned rows.

All counts describe rows returned by CanvasPilot's existing API methods. Those
methods have their own pagination limits and receive only the data visible to
the current account. Increasing the overview limits does not prove that every
course or assignment in Canvas has been retrieved.

## Python

```python
from canvaspilot.api import CanvasAPI

with CanvasAPI() as api:
    overview = api.sync_summary(
        limit_courses=20,
        limit_assignments_per_course=12,
    )
```

Both arguments must be positive Python integers. Booleans, floating-point
numbers, strings, and `None` raise `ValueError` before any sync reads. Calling
`CanvasAPI()` itself still follows the existing client setup; callers can also
pass an already configured `CanvasClient`.

## MCP

Call the existing `canvas_sync_summary` tool:

```json
{
  "limit_courses": 20,
  "limit_assignments_per_course": 12
}
```

The result is the same JSON overview. Either argument can be omitted to use its
default. The tool schema requires positive integer JSON values: `true`, `1.5`,
`"2"`, and `null` are invalid. Validation occurs before the tool resolves its
Canvas API instance.

## Offline verification

From an installed source checkout, run:

```bash
pytest -q tests/test_sync_summary.py
```

The tests use authored synthetic routes through the native fixture client and
exercise the API, CLI, and registered MCP tool. They cover chronological
selection, offsets and ties, unknown dates, selection counts, partial read
failures, and validation before lookup. Network, broker, and default-profile
lookup seams are blocked in these tests.
