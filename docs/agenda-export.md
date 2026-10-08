# Review a saved course agenda

Save the selected courses' event and assignment calendar records as one readable
HTML file. Open it offline, focus on a course or source date, inspect the original
source and print the current view.

```sh
canvaspilot export-agenda 42 77 --start 2026-10-08 --end 2026-10-15 --out agenda.html
```

The existing session broker or explicit `--base-url` / `--token` options work as
they do for `agenda`. The command makes one call to the existing course-agenda
reader. It does not create a browser session or request course names. The file
uses the selected course IDs as labels.

The destination must be new. A successful command prints a JSON receipt with
the output path, native counts, original-report SHA256 and HTML SHA256. A failed
read or export prints a structured error to stderr and exits 1; malformed command
syntax exits 2. Existing files, directories, hardlinks and even dangling symlinks
are preserved. A destination created during the read is also protected. Complete
bytes are prepared first and published with a same-directory create-only hardlink;
filesystems that cannot support that operation refuse without a replacement
fallback. No partial course selection is published as a successful report.

## Choose a useful view

The page has separate **Timed**, **All-day** and **Timing unavailable** sections.
The original order within each native group is retained. Timed entries display
the original timestamp, fractional precision and offset. All-day entries use the
explicit supplied date. Unavailable timing receives no invented date or midnight.

Use **Course**, **Source date** and **Search saved entries** together. Search is
case-insensitive and includes the saved entry text and its complete source. The
summary reports how many entries are visible out of the complete saved snapshot,
with counts for each timing section. **Reset view** restores every saved entry.

**Source date** is the literal date written in a timed entry's original timestamp,
or its declared all-day date. No conversion to your computer's time zone or UTC
takes place. Records whose timing is unavailable remain visible in every date
view after course and search filtering; the page states this rule beside the
control. Canvas selected the original requested range, so a local source-date
view is a view of the returned records, not a new provider query.

**Print this view** includes the current filter context, matching entries and their
complete saved source, with filter controls omitted. Long evidence wraps on paper.
The file also works without JavaScript: all entries and original JSON remain
available; interactive filters are hidden. There is no browser storage, saved
review status, personal note format or background network request.

## Retain the original evidence

Each entry shows its course, calendar kind, source ID with its original JSON type,
collection position and available timing, location and assignment details. A
supplied cancellation flag remains explicit. The readable description uses the
existing project's HTML-to-text helper; its original HTML and every nested field
remain in **Inspect complete saved source**.

**Download original agenda JSON** returns exactly the bytes the ordinary `agenda`
command would print for this report: Python's default `indent=2` JSON representation
plus its final newline. No fields are selected away, identifiers converted,
duplicates removed, unknown timing discarded or null/empty/zero values replaced.
The complete native report is also inspectable at the foot of the page. HTML-like
source text is displayed inertly; saved source URLs are text, not automatically
loaded resources.

This is a saved observation of two sequential calendar reads. Check Canvas for
changes. The view does not establish simultaneous provider state or infer
completion, grades, attendance or anyone's availability. Existing agenda, MCP,
iCalendar and other exports keep their separate contracts.

## Bounded complete export

The HTML consumer accepts at most **2000 native entries** and **4 MiB of original
native JSON**, inclusively. A larger report refuses the whole view and asks for a
smaller course/date selection. It never truncates the report to fit. The renderer
checks the native schema, course selection, complete counts/source positions,
timing grouping and stable order using the existing producer validators.

The Python API is `render_agenda_html(report) -> bytes`, followed by
`write_agenda_html(path, content) -> None`. Rendering has no provider or filesystem
write side effects and leaves the supplied native report unchanged. CSS and
controls are packaged with the module and embedded in the saved file.
