# Prepare a local rubric self-check

Use the supplied rubric as a preparation checklist. For each criterion, choose
**Unreviewed**, **Needs work**, or **Checked locally**, and write your own evidence
or next step. Save a working HTML copy to continue later, or print it for review.

These statuses are your own notes. They are not selected rubric ratings, Canvas
completion, a submission, a grade, or evidence that an instructor agrees.

## Export the assignments you choose

Use the existing CanvasPilot authentication setup, then choose one course and
1–25 distinct assignments in the order you want to review:

```sh
canvaspilot export-selfcheck 42 1001 1008 --out selfcheck.html
```

Choose a new `.html` path in an existing directory. Existing files, directories
and symbolic links are protected; a file created after preflight also wins.
Output is prepared completely and published through the unchanged study
workspace writer. Its same-directory atomic publication requires hard-link
support; unsupported filesystems refuse instead of overwriting.

The command checks the whole selection and output path before making any read.
It then calls the unchanged `CanvasAPI.assignment_brief()` once per selected
assignment. A later failed read refuses the entire export; there is no partial
successful document. Normal authentication options remain available. This command
does not start a new login, invoke a model, or use a Canvas write endpoint.

The existing brief reader supplies cleaned prompt text, rubric criteria and
ratings, settings, warnings and selected metadata. It echoes the requested course
and assignment IDs: the exporter has not observed an independent raw response
identity check. Check Canvas for current content, attachments, media, access and
deadlines. The normalized source is preserved; the file is not a raw HTTP archive.

## Record your self-check

Open the exported HTML directly in a modern browser. Source checksum and local
state must validate before controls become available.

- Read the criterion and its longer description. **Supplied rubric details and
  ratings** shows the original rating order and available metadata.
- Choose your own status. A status never selects a supplied rating or adds points.
- Write an evidence note: a passage, example, uncertainty or next step.
- Use **Save working copy** and confirm the download completed before closing.
  Open that downloaded HTML to continue with the same source, choices and notes.
- **Print self-check** includes all selected assignments, criteria, rating text,
  local statuses and full notes. Use the browser's PDF destination if useful.

A repeated or missing criterion ID does not merge entries. Each self-check binds
to that criterion's original position within its selected assignment and to the
exact snapshot hash. Reordering or editing a different source does not migrate
the notes. A new export starts unreviewed.

There is no browser storage or autosave. Edits stay in the open tab; the original
file is not rewritten. Saving requests a separate `rubric-selfcheck-working.html`
download, and the browser may ask for its destination. If download preparation
fails, the current work remains in the tab. A saved working copy contains the
complete selected assignment snapshot and your notes together; share deliberately.

## Read the supplied rubric faithfully

The original assignment, criterion and rating order is retained. Missing rubric
data remains unavailable; an explicitly empty rubric is labeled empty. No criteria
are invented for either case. The brief reader's warnings stay available.

Assignment points, criterion labels, rating labels and the supplied rubric total
are separate source values. The page never sums them or computes a grade.
`hide_points` suppresses rubric criterion/rating/total labels;
`hide_score_total` suppresses the rubric total only. Missing flags retain the
ordinary visible behavior, while present unknown or malformed flags suppress
their corresponding labels conservatively. Source metadata remains embedded:
these settings are presentation controls, not redaction or authorization.

Numeric rubric labels are rendered by Python before browser JSON parsing, so
large integer IDs and point labels are not rounded for display. Their formatting
represents the normalized Python value, not the upstream raw number spelling.
Text is rendered literally, including angle brackets and template-like strings.

## Limits and refusal

The complete source is bounded to 4 MiB, 25 assignments, 500 criteria and 5,000
ratings. Exceeding a limit refuses the export; nothing is silently truncated.
Each local evidence note permits 5,000 UTF-16 code units (some emoji use two),
and encoded local state is bounded to 2 MiB. Unsupported lone Unicode surrogates
are refused. Shorten oversized notes before saving or printing.

A damaged source hash, unsupported schema, foreign or extra criterion key,
invalid status or invalid note refuses opening while leaving the file unchanged.
The checksum detects accidental corruption and source/state mismatch. It is not
a signature or proof of authorship; someone who rewrites the HTML can also
rewrite its code and hashes.

The page embeds its own script and styles with a hash-based content policy and
requests no external assets. Only explicit same-origin HTTP(S) assignment links
can leave the file. The ordinary study workspace and its notes/filter controls
remain separate and unchanged.

## Native verification

From a checkout with the existing development dependencies:

```sh
python -m pytest -q tests/test_rubric_selfcheck.py tests/test_rubric_selfcheck_cli.py
```

The browser receiver requires an existing Node 22 or later, Chromium, and
`pdftotext`. Give it a new output directory and the Python executable containing
the project's existing development dependencies:

```sh
node scripts/receive_rubric_selfcheck.mjs /absolute/new-receiving-directory /absolute/python /absolute/chromium
```

It uses a fresh browser profile, receives two actual working-copy downloads,
reopens both generations, checks the printed PDF, and retains its receipt and
screenshots. Its authored loopback fixture is stopped before offline page checks.

These use authored data and the existing loopback HTTP fixture, not a school,
session broker or real account. The separate browser receiving script opens
actual generated files and working-copy downloads with an existing Chromium.
Native software qualification does not establish live school authentication,
instructor acceptance, or student learning outcomes.
