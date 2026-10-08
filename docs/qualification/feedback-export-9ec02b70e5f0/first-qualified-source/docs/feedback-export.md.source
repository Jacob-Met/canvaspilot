# Keep a readable copy of returned feedback

Use CanvasPilot's existing authentication and select one course and assignment:

```sh
canvaspilot export-feedback 41 902 --out feedback.html
```

Open `feedback.html` in a browser to read the sheet or use the browser's Print
command. It is one local file with its own styles. Its text can be selected and
searched, and the layout adapts to a narrow window. The file has no scripts,
embedded media, external fonts or automatic network resources. Following its
returned assignment link is an explicit visit to Canvas and may require login.

The command accepts the same `--base-url`, `--profile` and `--token` arguments as
the existing `feedback` command. It reads through the unchanged
`CanvasAPI.submission_feedback` method: one assignment GET and one self-submission
GET requesting `submission_comments` and `rubric_assessment`. It does not request
`read_status`, mark feedback read, submit work, change grades or fetch attachment
bodies. The existing transport's authentication and errors still apply.

## What the sheet contains

The header identifies the requested course and assignment separately from the
returned IDs, gives the assignment's returned title, due date and link, and records
when the copy was prepared in UTC. Source timestamps keep their original timezone
notation. A present returned course/assignment ID that contradicts the request
refuses the export; an absent returned ID remains explicitly unknown.

**Submission and grading** keeps the current attempt, submission state and type,
reported score and grade, assignment possible points, submission/grading/posting
times, submitting user and grader IDs, and reported late, missing, excused and
revision-request flags. A negative grader ID stays negative. The sheet does not
infer a person's role or calculate a grade.

The grade-applicability notice follows the exact returned flag:

| Returned value | Meaning shown |
| --- | --- |
| `false` | Grading preceded the latest resubmission; the displayed grade must not be treated as assessing the current attempt. |
| `true` | Canvas reports that the grade matches the current submission. |
| Missing, `null`, or another value | Whether the grade matches the current submission was not established. |

The flag does not supply the number of the graded attempt. The export never
subtracts one from the current attempt or labels an inferred earlier attempt.

**Rubric feedback** preserves the native reader's criterion order, exact-ID joins,
unmatched assessments, criterion descriptions and details, available rating
descriptions, range/scoring flags, reported assessment points, rating IDs and
comments. It labels the rubric's reported grading/advisory status. Missing
criteria, an empty criterion list, an absent assessment and an empty assessment
remain distinct. No assessment is joined again by label or array position.

These supplied rubric settings remain distinct:

| Setting | Export behavior when `true` |
| --- | --- |
| `hide_points` | Omit numeric rubric possible points, criterion points, rating points and assessment points, including unmatched assessments. Retain the supplied text. |
| `hide_score_total` | Omit the supplied rubric possible-points total. Criterion and assessment points remain visible unless `hide_points` also applies. No earned total is calculated in either case. |
| `hide_outcome_results` | Show the returned setting about withholding outcomes from the Learning Mastery Gradebook. It does not hide the already-returned criterion feedback. |

These settings govern the rubric presentation; they do not hide or reinterpret
the separately returned submission score, grade or assignment possible points.
An unusable non-boolean visibility setting refuses the sheet rather than guessing
its meaning. Missing/null settings and an explicitly empty settings object are
identified separately.

**Submission comments** retain response order and the supplied author name/ID,
creation and edit timestamps, and literal comment text. A supplied nested author
display name or ID is also shown when it differs from the top-level field,
including when that top-level value is missing. Authors are never all relabeled
as instructors. Media-only comments remain visible with their returned type and
ID. Attachment identifiers, names and supplied content types are listed, without
downloading their contents or embedding their URLs.

The sheet renders those fields, rather than every possible future Canvas metadata
field. The existing `canvaspilot feedback 41 902` JSON command remains available
for the complete native-reader result. Markup in names, criterion text and comments
is displayed literally; it cannot create HTML elements in the sheet.

## Files and errors

The destination must be new. Existing files, directories and symlinks are refused
before the two reads begin. After the document is complete, publication uses a
same-directory temporary file and a non-overwriting hard link, matching the native
calendar writer's existing pattern. A destination created during the reads or
preparation also wins: the export does not replace it. Filesystems that do not
support this operation return an error without an overwrite fallback. New files
use the temporary file's private permissions (`0600` on POSIX).

The command prints a success JSON object containing the output path, requested
IDs, capture time and SHA-256 only after publication. A read, validation or
publication error exits nonzero and prints a final JSON diagnostic to stderr;
the existing transport may emit its own diagnostic lines before that object.
Read or validation failures do not create a feedback file. A failed acknowledgement
after a filesystem operation can leave a complete file, so inspect an existing
destination before choosing a new name for a retry.

The copy contains the returned user's feedback, comments and identifiers. It stays
where you save it; choose deliberately whether to share it. It is a snapshot of the
existing reader's two responses, not an atomic server snapshot, a complete attempt
history or a file that updates when Canvas changes.

## Python

```python
from pathlib import Path

from canvaspilot.api import CanvasAPI
from canvaspilot.feedback_export import build_feedback_document, write_feedback_document

with CanvasAPI() as api:
    content, receipt = build_feedback_document(api, 41, 902)

write_feedback_document(Path("feedback.html"), content)
```

`build_feedback_document` returns complete UTF-8 bytes and the receipt without
writing a file. A supplied `captured_at` must be a timezone-aware `datetime`;
subsecond precision is retained. `render_feedback_document` can render an existing
native feedback result when passed the explicit requested IDs and capture time.
The renderer does not mutate that result or re-run its joins. Non-finite numbers,
unrenderable container shapes and conflicting present identities are refused.

## Source contract and receiving

Canvas's primary [Submissions documentation](https://developerdocs.instructure.com/services/canvas/resources/submissions)
defines the grade-applicability, attempt, author and media fields. The
[Rubrics documentation](https://developerdocs.instructure.com/services/canvas/resources/rubrics)
describes rubric criteria, ratings and associations. The
[Canvas Data Access Platform dataset reference](https://developerdocs.instructure.com/services/dap/dataset/dataset-namespaces/dataset-canvas)
distinguishes the three `rubric_associations` visibility/posting flags. The native
feedback API is the receiving boundary; this feature changes its presentation
and explicit local export only.

Focused tests use the actual native API and CLI against authored loopback HTTP
responses, then parse the resulting HTML. They cover canonical joins, source
immutability, zero/unknown/empty values, grading applicability, all separate
visibility flags, returned authorship, literal Unicode and markup, failed reads,
identity refusals, existing destinations, a concurrent destination creation and
filesystem refusal cleanup. No school account or learner data is used in this
qualification.

```sh
pytest -q tests/test_feedback_export.py tests/test_feedback_export_native.py \
  tests/test_submission_feedback.py tests/test_submission_feedback_native.py
```
