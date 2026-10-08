# Export assignment deadlines to a calendar file

`canvaspilot export-calendar` saves a local iCalendar snapshot for explicitly
selected Canvas courses:

```bash
canvaspilot export-calendar 42 77 --out deadlines-2026-10-08.ics
# Choose a different existing Canvas assignment selection:
canvaspilot export-calendar 42 --bucket all --out all-course-42-deadlines.ics
```

Use your existing session broker or the same token configuration as other
CanvasPilot commands. The command makes assignment **GET** requests through
the existing reader. It creates the file locally and prints a JSON receipt
with its path, SHA-256, selected courses, returned/exported counts and each
assignment omitted because its due date is absent.

Import the `.ics` file using your calendar application's file-import option.
Each entry is labeled with its course ID and assignment title and retains the
assignment link when Canvas supplies one. Entries mark the deadline instant:
they do not reserve study time or invent an assignment duration.

## Selection and dates

The default `--bucket upcoming` is the existing Canvas upcoming-assignment
selection. Supported values are `upcoming`, `past`, `overdue`, `undated`,
`ungraded`, `unsubmitted` and `all`; `all` omits the bucket filter.
Repeated equivalent course IDs are read once.

Exports cover the assignment rows returned by the existing client, including
its authentication and pagination behavior. They do not certify that all
school assignments or all pages were returned. Course calendars, personal
events, quizzes outside the assignment list, and unsupplied due-date overrides
are not inferred.

The source `due_at` timezone offset is converted to UTC; the importing
calendar displays that instant in its chosen timezone. A missing/null date
is listed in the receipt and omitted. A date without a timezone, a malformed
date, nonzero fractional seconds or a date outside the representable UTC range
refuses the export. No date is guessed or rounded. If no dated assignments
remain, the command returns an error and creates no empty calendar.

## Re-exporting and files

A deadline keeps the same UID when its name or due date changes, using the
Canvas source, course ID and assignment ID as identity. Different courses or
schools remain distinct. Session exports use the running broker's configured
Canvas provider, including when the CLI retains its default host; token and
fixture exports use their configured client base. The broker must identify a
valid provider and remain on that provider throughout the export. The writer
checks identity before reading and after each selected course, refusing a missing
or changed provider instead of publishing mixed-source identities. These checks
do not lock the broker or create a transactional server snapshot.

Session export requires a running broker with provider-origin checks. After
upgrading CanvasPilot, restart an older broker with the updated source; a missing
or false capability produces that instruction before assignment reads. The
updated broker chooses a page on the configured school's exact origin and
refuses mismatched page or request origins instead of switching schools. Finish
login to the configured school if its page is unavailable. The dispatched URL is
bound before fetch, so an HTML base element cannot change the destination.
Foreign response origins are refused before rows are returned; browser redirect
contact may already have occurred. This does not activate or restart a broker.

Import applications differ in how they handle an
already imported UID: this command does **not** guarantee that re-importing
will update or remove previous calendar entries. Check the import preview or
use a dedicated calendar for each snapshot as appropriate.

This is an explicit snapshot, not a subscription or automatic refresh.
Removed assignments are not emitted as cancellation notices. No invitation,
attendee, reminder alarm or calendar-account write is generated.

The output must be a new path. Existing files, directories and symlinks are
never replaced, including a path created while the export is running. All
selected course reads and formatting finish before a complete temporary file
is published. A failed course read or malformed dated assignment leaves no
partial snapshot. Local publication requires hard-link support; unsupported
filesystems fail safely. No directory-fsync/power-loss durability is claimed.
The file contains assignment titles and links supplied by Canvas; share it deliberately.

## Python interface

```python
from pathlib import Path
from canvaspilot.api import CanvasAPI
from canvaspilot.calendar_export import build_assignment_calendar, write_calendar

with CanvasAPI() as api:
    content, receipt = build_assignment_calendar(api, [42, 77])
write_calendar(Path("deadlines.ics"), content)
```

No new runtime dependency is required. The existing API, transport, broker,
MCP tools and their behavior are unchanged.

## Format and verification

The writer follows [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545)
sections 3.1, 3.3.5, 3.3.11, 3.6.1 and 3.8.4.7: CRLF lines, folding at
75 UTF-8 octets without splitting a character, escaped text, UTC timestamps,
persistent identities and point-in-time transparent events. Assignment
selection reuses the [Canvas assignment-list contract](https://developerdocs.instructure.com/services/canvas/resources/assignments).

`tests/test_calendar_export.py` exercises the native API and real CLI using
only authored fixtures and temporary loopback HTTP. The separate receiving
packet parses actual CLI output with an independent calendar parser. This
qualifies generated files and local requests; it is not a live-school or
particular calendar application's import certification.
