# Save submission-attempt history for offline review

Use the existing Canvas session or token to save one assignment's self-history report:

    canvaspilot export-submission-history 71 902 --out submission-history.html

Open the resulting HTML file directly in a browser. It needs no server, browser
session or network connection. Its contents remain fixed after later submissions
or grading changes. Use the browser's **Print** command for paper or PDF.

## Read the separate sections

The report shows the requested course and assignment selectors, then the
assignment metadata exactly as returned. The reported assignment ID, course ID
and Canvas link remain separate from those requested selectors; absent metadata
is not filled in. Creation time describes the local report file, not a
transactionally consistent observation at Canvas.

**Current submission** contains every field returned on the current record.
If grade_matches_current_submission is false, the report states that its
grade may describe an earlier attempt without choosing that attempt. A missing
or unfamiliar value does not become a confirmed match. The report never
calculates a grade or copies the current score into history.

**History in returned order** keeps each returned record once, in response
order. “Returned record 1” identifies its position in that list, not an attempt
number. Repeated, missing or unfamiliar attempt identifiers remain visible;
the exporter does not sort, deduplicate, append the current record or fill
gaps. A returned empty list differs from unavailable history. Neither establishes
that every submission attempt was returned.

**Top-level submission comments** remain separate. They are not assigned to
historical versions using dates, authors, positions or reported attempt values.
Comments nested inside a current or historical record stay inside that record.
A missing comment association and a returned empty comment list stay distinct.

Every field uses JSON notation to preserve the difference between an absent
field, explicit null, false, zero, empty text and an empty collection. Submitted
HTML and URLs appear as literal source text or metadata. Images, attachments,
media and other linked resources are not fetched or embedded. Additional fields
returned by the reader remain visible.

## Keep the complete reader result

**Download complete report JSON** saves the entire normalized result used to
render the document. Its original values and array order are retained, including
unknown fields, original numbers and source text. This is the existing
CanvasAPI.submission_history() result; it is not the raw HTTP response pages,
a download of attached files or a restorable Canvas backup.

The displayed checksum describes those JSON bytes. The HTML contains no scripts,
forms, external styles or remote resources. Text supplied by Canvas cannot create
active links or markup in the report. HTML-incompatible control/surrogate
characters are visibly escaped; their original values remain in the JSON.

## Reads, errors and output protection

The exporter calls the existing submission_history() reader exactly once.
That reader uses the assignment GET and the caller's submissions/self GET with
the existing history/comments associations. It does not request read_status,
mark comments read, submit work, post comments or change grades. The existing
client continues to determine authentication, access and the actual returned
data. The exporter does not add browser cookies, API tokens or session
configuration to the report.

A failed request, malformed report or unsupported non-JSON value refuses the
export. Unavailable history remains an explicit successful observation when
the existing reader supplies that state. It is never substituted for a request
failure. The normalized JSON is limited to 4 MiB and rendered HTML to 16 MiB;
larger reports are refused without truncation. The limits apply after the
existing client has decoded the responses.

The --out argument must name a new file in an existing writable directory. The
command protects an existing file, directory or symlink before source reads,
then uses the unchanged page-packet publisher's exclusive same-directory
hard-link publication. Unsupported filesystems refuse publication; there is no
overwrite fallback. A completed publication with a temporary-file cleanup
warning is reported as a success with cleanup_warning, following that
publisher's existing behavior.

Success writes a JSON summary to stdout, including requested selectors, report
creation time, returned-record counts, byte lengths and checksums. Expected
source, value or file errors produce JSON on stderr and exit status 1. Parser
usage errors retain argparse's usual status 2.

## Python use

    from pathlib import Path
    from canvaspilot.page_export import write_page_packet
    from canvaspilot.submission_history_export import build_submission_history_report

    # api is your existing configured CanvasAPI instance.
    content, summary = build_submission_history_report(api, 71, 902)
    cleanup_warning = write_page_packet(Path("submission-history.html"), content)

For an already retained normalized report, call
render_submission_history_report(report, course_id=71, assignment_id=902)
to render without a source request. Optional generated_at must be an aware
datetime and records only file creation context. The renderer preserves the
supplied report without modifying it.

The separate feedback/rubric, course-grade, page, calendar and module-progress
workflows retain their existing behavior. The original [history-reader
guide](submission-history.md) describes the underlying response projection.
