# Review your submission attempts

Use `canvaspilot submission-history COURSE ASSIGNMENT`, the `canvas_submission_history` MCP tool, or `CanvasAPI.submission_history(course_id, assignment_id)` to inspect the versions Canvas returns for your own assignment submission.

```sh
canvaspilot submission-history 71 902
```

The command uses the existing configured session broker or token. Course and assignment arguments must be positive numeric Canvas IDs. Leading zeroes are normalized; SIS aliases and other nondecimal identifiers are not supported by this command.

## What the report preserves

| Field | Meaning |
| --- | --- |
| `assignment` | Assignment ID, course ID, name, page URL, due date and available points. These six keys are always present; absent metadata is null. |
| `current_submission` | All fields returned on the current submission, excluding the two associations reported separately below. |
| `history.returned` | Whether Canvas supplied a history list. This is true for an empty list, and false when history was absent or null. |
| `history.records` | The exact returned record order and fields, or null when unavailable. |
| `submission_comments` | The top-level returned comments, with their own authorship and any attempt metadata, or null when unavailable. |

For example, a current record may report attempt 3 with `grade_matches_current_submission: false`, while history contains records for attempts 2 and 1. The current grade stays in `current_submission`; it is never copied into those earlier records. A historical zero score remains zero. Missing scalar fields remain absent, explicit null values remain null, and any comments nested in a historical record remain there.

History is a returned association, not a reconstructed attempt ledger. The reader does not fill gaps, deduplicate or sort records, append the current record, infer whether all attempts are present, or calculate a grade. Top-level comments are not assigned to historical attempts using order, timestamps or names. Submitted text, URLs, attachments, media and additional record fields remain as supplied; the command does not open or download their content.

## Reads and errors

The reader performs two GETs: the assignment and its `submissions/self` resource with `include[]=submission_history` and `include[]=submission_comments`. It does not request `read_status`, which the [Canvas Submissions API](https://developerdocs.instructure.com/services/canvas/resources/submissions) documents as marking submissions read. No submission, grading, comment or read-state write is performed.

A failed request or a malformed assignment/submission/history/comment structure refuses the report. The CLI writes a JSON error to stderr and exits with status 1; the MCP call returns an error. It never reports an error as an empty history. The existing client determines access and returned data; this command does not recover unavailable or withheld versions.

The [feedback command](../README.md#submission-feedback) remains the separate rubric/feedback view. Course-grade review and printable feedback exports remain their own workflows.
