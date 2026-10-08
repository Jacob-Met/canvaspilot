# Current-user submission facts in assignment lists

Assignment lists now retain a compact `submission` object from Canvas's
already-requested `include[]=submission` response. This lets a student or an
assistant read the student's reported submission state beside each assignment
without fetching each submission separately.

The same data reaches the existing Python `CanvasAPI.list_assignments()` and
`sync_summary()` methods, CLI `assignments` and `sync` commands, and MCP
`canvas_list_assignments` and `canvas_sync_summary` tools.

## Read a course or the existing upcoming overview

```bash
# Existing default: Canvas's upcoming assignment selection
canvaspilot assignments 41
canvaspilot sync

# Omit the Canvas bucket filter when reviewing the course's returned assignments
canvaspilot assignments 41 --bucket ""
```

For MCP, call `canvas_list_assignments` with
`{"course_id": "41", "bucket": ""}` to omit the bucket filter.
The default remains `"upcoming"`. Sync keeps its existing upcoming filter,
course and assignment limits, deadline ordering, omission counts and per-course
errors. It is an overview of that selection; it does not claim to enumerate
every missing assignment. Client authentication, pagination and page limits
continue to apply.

## Read the two distinct signals

Canvas defines the outer `has_submitted_submissions` field as whether at least
one student has submitted to the assignment. It does not establish whether the
requesting student has submitted.

The included `submission` describes the requesting user when Canvas supplies it.
For example, this synthetic excerpt is consistent: another student can have
submitted while the current student's work is reported missing.

```json
{
  "id": 901,
  "has_submitted_submissions": true,
  "submission": {
    "workflow_state": "unsubmitted",
    "attempt": 0,
    "submitted_at": null,
    "late": false,
    "missing": true,
    "excused": false
  },
  "submission_warnings": []
}
```

The compact projection retains only these supplied fields:

| Field | Accepted reported value | Meaning in this output |
| --- | --- | --- |
| `workflow_state` | String or null | Canvas's submission state label, preserved verbatim. |
| `submission_type` | String or null | The reported submission type. |
| `submitted_at` | String or null | The reported timestamp, without date conversion. |
| `late_policy_status` | String or null | Canvas's late-policy status label, preserved verbatim. |
| `attempt` | Nonnegative integer or null | The reported attempt, including zero. |
| `late` | Boolean or null | Canvas's reported late flag. |
| `missing` | Boolean or null | Canvas's reported missing flag. |
| `excused` | Boolean or null | Canvas's reported excused flag. |

Flags remain independent reported facts. CanvasPilot does not reconcile
combinations, derive them from the workflow label, compare the due date with the
local clock, or infer a grade or required action. New string state labels are
preserved. The original assignment fields, including `due_at`,
`submission_types`, and `has_submitted_submissions`, keep their existing meanings.

## Unknown and malformed optional data

An absent or null submission produces `"submission": null` and an empty
`submission_warnings` list. This means no submission object was supplied; it
does not mean missing, late, excused, submitted or unsubmitted. An explicitly
supplied empty object remains `{}`.

Inside a supplied object, omitted fields stay omitted and explicit nulls stay
null. A malformed optional container produces null plus a warning. A known
field with an invalid type is omitted with a warning naming its location;
usable neighboring fields remain. For example, `"missing": "false"` is not
converted to a boolean, and `"attempt": true` is not converted to one.
Warnings do not include the malformed value.

This projection excludes answer bodies, attachments, comments, scores, grades,
and other fields. Use the existing raw `submission_status` operation or
submission feedback report for their existing detailed responses. Their
contracts are unchanged. Both compact and full assignment-list modes contain
the same submission projection; full mode continues to add the cleaned prompt.

An upstream request failure still fails the assignment list. A later-page
failure does not return a successful partial list. Sync retains its existing
per-course error row while continuing with other courses; a failed read is
never represented as a successful `submission: null` row.

## Source and executable checks

The field meanings follow Instructure's
[Assignments API](https://developerdocs.instructure.com/services/canvas/resources/assignments)
and [Submissions API](https://developerdocs.instructure.com/services/canvas/resources/submissions).
The projection uses the response already requested by CanvasPilot; it adds no
endpoint or request.

`tests/test_assignment_submission.py` exercises the public assignment and sync
APIs with synthetic, transport-blocked responses. It covers unknown versus
reported state, malformed optional values, explicit false/null/zero, future
labels, unchanged original fields, and unchanged raw submission behavior.
`tests/test_assignment_submission_process.py` exercises actual HTTP, CLI child
processes and MCP stdio against a disposable loopback server with external
connections blocked. It checks page traversal, changed current-user state,
unchanged aggregate state, sync propagation and later-page failures.
