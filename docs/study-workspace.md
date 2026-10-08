# Assignment study workspace

Export the assignments you choose into one HTML file, read their prompts and
rubrics, and keep your own study notes beside them. A local review checkbox
helps you track what you have read. **Save working copy** downloads a new file
with those notes and checkboxes; reopen that file to continue later. **Print**
includes the selected briefs, rubric descriptions, your notes, and local review
markers.

## Export your selection

Use the existing [CanvasPilot authentication setup](../README.md#quick-start),
then supply one course and the assignment IDs you want, in the order you want
to read them:

```bash
canvaspilot export-study 42 1001 1008 1012 --out study-week-4.html
```

The parent directory must already exist. Choose a new filename: an existing
file, directory, or symbolic link is never replaced. The command reports the
selected IDs and snapshot SHA-256 as JSON when it succeeds. A failed read or
invalid selection produces an error and no newly published workspace.

Open the HTML file in a modern browser. Once the export has completed, the
workspace operates from that file without a server or network connection.
The **Open the assignment in Canvas** links are an explicit way to leave the
snapshot and check the current assignment.

The export accepts 1–25 distinct assignment IDs from one course. IDs are positive
ASCII decimal strings, at most 19 digits, with a maximum value of
9223372036854775807. Leading zeros are canonicalized, so selecting both 81 and
081 is refused as a duplicate. The complete selection and output path are
checked before the first API read. The snapshot is limited to 4 MiB of UTF-8
source JSON.

## Continue your notes later

1. Enter your own questions, plans, and reminders under **My study notes**.
2. Check **I have reviewed this assignment locally** when useful to you.
3. Select **Save working copy**, then keep the downloaded HTML file.
4. Open that downloaded file to continue; later saves create another working
   copy of the same assignment snapshot.

Notes and review checks initially stay in the open tab. There is no browser
storage or autosave, and the original file is not edited. The download status
reports that a download was requested; the browser or operating system may
still ask where to save it. Confirm that you have the downloaded file before
closing the tab. A download preparation failure leaves the notes in the tab.

Each assignment permits up to 50,000 UTF-16 code units of notes, matching the
browser text field's length limit. Characters outside the basic multilingual
plane, such as many emoji, use two code units.

The working file contains its selected brief snapshot and your notes together.
Treat it as your own local document when copying or sharing it. Opening a newer
Canvas export does not automatically move notes to it: notes are bound to their
exact original snapshot, course, and assignment IDs.

## Read the supplied brief faithfully

The workspace calls the unchanged `CanvasAPI.assignment_brief()` once for each
selected assignment. It retains that method's normalized brief projection:

- Title, reported due-date text, assignment points, submission types, Canvas
  link, and cleaned prompt text.
- Supplied rubric criteria and rating order, descriptions, long descriptions,
  zero or fractional point labels, range/scoring flags, and optional metadata.
- Rubric settings, whether Canvas reports the rubric as grading or advisory,
  and the reader's warnings about omitted malformed optional fields.

The due-date text is shown as reported, including its offset; it is not silently
converted into a different time zone. Missing values stay unavailable, and an
empty supplied rubric remains distinct from a missing rubric. Assignment points
and rubric point totals remain separate supplied values. The workspace does
not add rating points, choose a learner's rating, or calculate a grade.

Rubric `hide_points` suppresses rubric criterion, rating, and total point labels;
`hide_score_total` suppresses the rubric total without suppressing the individual
rating labels. An unusable hide flag conservatively omits the corresponding
point labels. These are presentation settings: the unchanged normalized
settings and rubric metadata remain in the file's snapshot. They are not a
redaction or authorization boundary. The field meanings follow Canvas's
[Rubrics API](https://developerdocs.instructure.com/services/canvas/resources/rubrics).

Prompts use the existing reader's cleaned text. Original formatting, embedded
media, attachments, and any access-sensitive content outside that projection
are not fetched or reconstructed. Check Canvas for those details and for later
updates.

The existing brief method echoes the **requested** course and assignment IDs.
It does not expose the raw assignment response's identity to this exporter.
The workspace checks its normalized selection and states that raw response
identity was not observed; it does not claim an independent upstream identity
check. The underlying assignment GET retains its existing
`include[]=submission` and client pagination parameter, but submission bodies,
grades, feedback, and history are outside the exported brief projection.

The local checkbox is your own study marker. It does not report or change Canvas
completion, submission, grading, enrollment, locks, or access. No Canvas write
endpoint is used by this command or the exported page.

## Print a working brief

Use **Print** after entering notes, or after reopening a saved working copy.
The print layout includes every selected assignment, prompt, supplied rubric,
literal note text, and the local review state. It hides navigation and editable
controls so long notes print as ordinary text rather than a scrollable field.
Choose the browser's PDF destination if you want a PDF.

## Try the installed package without a Canvas account

This example reuses CanvasPilot's existing explicitly synthetic, read-only
fixture client. It cannot fall back to a live school or session:

```python
from pathlib import Path
from canvaspilot.api import CanvasAPI
from canvaspilot.offline_demo import OfflineOnlyClient
from canvaspilot.study_workspace import build_study_workspace, write_study_workspace

with CanvasAPI(OfflineOnlyClient()) as api:
    content, report = build_study_workspace(
        api, "101", ["1001"], source_base_url="https://example.test"
    )
write_study_workspace(Path("synthetic-study.html"), content)
print(report)
```

The output must use a new path, just like the CLI. The HTML, CSS, and JavaScript
resources are included in the package wheel.

## Snapshot and file behavior

The canonical source JSON is stored as a string with its SHA-256. The browser
verifies those exact UTF-8 bytes, then validates that every saved note belongs
to the same hash and selected assignment keys. New exports and downloaded
working copies both start closed until those checks finish. A damaged snapshot,
foreign note map, invalid review value, or oversized note refuses to open while
leaving the file unchanged.

This hash detects corruption and accidental source/state mismatches. It is not
a signature or proof of who authored a file; someone who can rewrite the HTML
can also rewrite its code and hashes.

Assignment and note text is rendered with text nodes. The page contains its own
script and style with hash-based Content Security Policy, requests no external
assets, and uses no browser storage. Source links are shown only for HTTP(S)
URLs on the configured Canvas origin without embedded credentials.

The CLI prepares the complete output in a temporary file in the destination
directory, flushes it, and publishes it using a new hard link. A file created by
another process after preflight wins; the export refuses to replace it. This
requires a filesystem that supports same-directory hard links. Unsupported
filesystems and I/O failures are reported without falling back to an overwrite.

## Reproduce the checks

The focused Python cases use dictionary fixtures and disposable loopback HTTP:

```bash
python -m pytest -q tests/test_study_workspace.py tests/test_study_workspace_cli.py
```

The optional native-browser receiver uses the development environment and a
locally installed Chrome/Chromium executable. Give it a new evidence directory:

```bash
python scripts/verify_study_workspace_browser.py \
  --chrome /path/to/chrome \
  --output /new/study-workspace-evidence
```

It exercises an actual CLI export, real downloads and fresh offline reopens,
the pending-verification boundary, print output, keyboard and 320-pixel touch
layout, damaged or mismatched state, literal markup, and controlled download
failures. Its receipt records the exact source inventory, page HTTP requests
and errors, and output hashes. This is synthetic software qualification;
school authentication, student outcomes, and institution-specific behavior
are not claimed.
