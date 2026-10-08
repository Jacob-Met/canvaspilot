# Review a course's reported grades

Run `canvaspilot grade-review 42`, call `CanvasAPI.grade_review(42)`, or use the
read-only MCP tool `canvas_grade_review` with `{"course_id": "42"}`. The three
entry points return the same JSON review for the authenticated caller.

The review puts course totals, assignment-group rules and each returned
assignment's own submission status together. It helps answer “what grade has
Canvas reported?”, “is this score from before my resubmission?” and “which
assignments does Canvas explicitly mark missing or excused?” It does not
calculate a different grade or decide which assignment a drop rule removes.

## What is read

The consumer makes only these Canvas GET requests through the existing client:

1. `/api/v1/users/self/profile`, to bind supplied user IDs to the caller.
2. `/api/v1/courses/42`, requesting `total_scores`,
   `current_grading_period_scores` and `grading_periods`.
3. `/api/v1/courses/42/assignment_groups`, using the existing paginator with
   `include[]=assignments`, `include[]=submission` and
   `override_assignment_dates=true`.

It does not request observed users, an enrollment roster, unpublished grades,
submission bodies, feedback comments or read-status changes. The existing
`feedback` command remains the entry point for one assignment's comments and
rubric assessment.

These read shapes and field meanings follow the official
[Courses](https://developerdocs.instructure.com/services/canvas/resources/courses),
[Assignment Groups](https://developerdocs.instructure.com/services/canvas/resources/assignment_groups)
and [Submissions](https://developerdocs.instructure.com/services/canvas/resources/submissions)
contracts. The course's enrollment rows describe the current caller. Included
assignment submissions are that caller's current submission. A supplied
conflicting course, group, assignment or user ID refuses the whole review.

## Read the result

| Result | Meaning |
| --- | --- |
| `course` | Supplied course identity and grading settings, including whether group weights apply and whether Canvas hides final grades. |
| `authenticated_user_id` | ID returned by the self-profile request, without profile name or contact details. |
| `enrollments` | Each returned enrollment's role/state and its separate `reported_totals`. Multiple enrollment rows are retained separately. |
| `reported_totals` | Only supplied canonical computed current/final fields and current-period computed fields. Original Canvas field names are retained. |
| `grading_periods` | Supplied period identity, title and dates, separate from all returned assignment groups. |
| `assignment_groups` | Returned groups in reader order, their supplied weights/drop rules, and each returned assignment's fields and own submission. |
| `submission.fields` | Supplied score/grade, attempt, posting and grading timestamps, and reported missing/late/excused/current-attempt flags, subject to the visibility rules below. |
| `counts` | Counts over the rows actually returned. Boolean counts require an explicit `true` or `false`; the categories may overlap. |
| `warnings` | Paths of malformed optional values omitted from the projection. They remain unknown. |

For example, a reported score of `0` remains zero and a reported grade of
`"0"` remains a string. `computed_current_score` and
`computed_final_score` are separate Canvas totals. Current-period totals
retain their `current_period_...` names and the supplied period context.
Assignment groups are requested without a period filter; the review never
claims that their displayed rows reproduce a particular total.

The `drop_lowest`, `drop_highest` and `never_drop` rules are shown as
reported. No assignment is labeled “dropped” from those rules. Group weights
are retained even when they are zero or do not sum to 100; the course's
`apply_assignment_group_weights` flag supplies their context. An excused
submission remains explicitly excused. Its flag is not changed by a score,
date, workflow state or assignment's possible points.

A false `grade_matches_current_submission` remains false alongside the
reported score and attempt. Canvas uses that flag when a student resubmitted
after the work was graded. The consumer neither calls the older score the
latest attempt's grade nor discards it.

## Visibility and unknown values

Only a fixed projection of supplied fields is returned; the tool never fills
a withheld total from assignments. It excludes all unposted and override total
fields. When `course.hide_final_grades` is true, `totals_visibility` becomes
`hidden_by_course` and every `reported_totals` object is empty. Otherwise
`reported_fields_only` means only that the displayed fields were supplied;
it does not promise a complete or currently visible gradebook.

Each returned submission has `grade_visibility`:

- `assignment_not_visible` when Canvas explicitly reports
  `assignment_visible=false`.
- `not_posted` when Canvas explicitly supplies `posted_at=null`.
- `reported_fields` otherwise. Missing posting metadata does not prove
  posting, grading or withholding; any retained values are simply those
  supplied by the caller's response.

For the first two states the consumer omits `grade`, `score`,
`entered_grade`, `entered_score` and `points_deducted`, even if
inconsistent neighboring values were supplied. Posting/visibility flags and
the other available context remain, so a withheld grade cannot look like
zero. Malformed explicit visibility controls refuse the review.

Within a `fields`, `context` or `reported_totals` object, an omitted key
means it was not supplied or was omitted with a warning; an explicit JSON
`null` remains null unless a visibility rule removes the grade field.
Absent, null and empty enrollment/period/assignment-list containers have
separate `..._state` values. A missing submission is
`submission_state=not_returned`; an explicit null submission is
`submission_state=null`. Neither means “missing work.” Only Canvas's
explicit `missing=true` contributes to `counts.missing_true`.

## Reader and error boundary

`collection_complete` is always `null`. The inherited
`CanvasClient.get_paginated` returns normalized rows, without a completeness
receipt or original response shape. This consumer therefore reports
`upstream_response_shape=not_observed` and does not call a returned empty
list a complete gradebook. The existing reader's session/PAT limits still
apply. Missing assignment lists remain unknown, with
`counts.groups_without_assignment_list` showing how many groups lack one.

The requests are separate reads, not an atomic server snapshot. The review
does not establish a new provider-identity or authentication guarantee; it
uses the same connection and reader as the rest of CanvasPilot. Existing
broker/provider and pagination contributions retain those source boundaries.

Authentication, HTTP and pagination exceptions propagate through the API and
become MCP tool errors. The CLI exits 1, emits no successful review on stdout,
and writes an error JSON object to stderr. Existing client logging may precede
that object on stderr; successful output remains JSON on stdout. Malformed
required containers, explicit visibility metadata, conflicting source IDs or
duplicate group/assignment IDs refuse the whole review. A date-restricted
course is refused before assignment groups are requested.

## Local qualification

```bash
pytest -q tests/test_grade_review.py tests/test_grade_review_process.py
```

The source cases cover changed grades/weights, zero/null/missing fields, hidden
and unposted grades, resubmission flags, source identity, duplicate records,
malformed structures and optional-value warnings. The process tests start a
bounded loopback HTTP fixture and run the actual HTTPX client, CLI subprocesses
and registered MCP stdio tool. They follow a real response Link to a changed
second-page score and refuse a later-page HTTP denial without returning a
partial successful report. The fixture's learner, course and assignments are
synthetic. No school account, browser login, submission, real grade or student
outcome is exercised.

