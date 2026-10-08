# Save a module-progress report

```bash
canvaspilot export-module-progress 42 --out module-progress.html
canvaspilot export-module-progress 42 --module-id 7 --out module-7-progress.html
```

The command reads the same report as `canvaspilot module-progress` and saves
a new HTML file. Open it directly in a browser, follow the module links, and use
the browser's Print command to print or save a PDF. Reading the saved file needs
no server, browser storage, script, login or network connection.

## Reading the saved report

The overview identifies the course ID, optional selected module ID, transport
mode and report-creation time in UTC. The timestamp describes creation of the
local report; it is not an atomic observation time at Canvas. It does not identify
the learner or school by name, and the file does not refresh.

Every returned module and item stays in its original order. The visible report
preserves:

- The reader's module state and original reported value. Unsupported or missing
  states remain unknown. Completing every visible item does not let the exporter
  declare the module completed.
- All-versus-one requirement rules, the sequential-progress flag, prerequisite
  IDs, publication state, unlock time and completion time as supplied.
- Each item's complete reported requirement object, including minimum-score and
  minimum-percentage thresholds. Zero, false, null, empty text and empty arrays
  stay distinct. Missing requirements do not mean that an item is optional.
- Completed, incomplete, unknown and not-reported requirement counts and the
  reader's remaining-work context. Incomplete alternatives under a one-of rule
  are not a count of required tasks. A Canvas-completed module can retain an
  incomplete alternative while its reported remaining work is empty.
- Item coverage, diagnostics and the limits of the existing normalized reader.
  A returned-count match is not proof of whole-course completeness. A locked
  module does not establish the accessibility of each item; item access remains
  unassessed.

Names, URLs, unsupported values and requirement payloads are rendered as text.
Module navigation uses local anchors. Canvas item URLs are displayed as text,
so following the report's navigation does not mark an item read. Control
characters that HTML cannot represent reliably are displayed with escapes;
the complete JSON download preserves the original normalized values.

**Download complete report JSON** saves the exact normalized object used for
rendering. Its SHA-256 is shown beside the link and in the CLI receipt. This is
the result of `CanvasAPI.module_progress()`, not an archive of raw provider
response pages. The existing module reader may wrap a singleton response or
replace missing, short or unusable inline items with a secondary read.

## Selection and errors

Course and optional module IDs must be positive integers. A module selection
reports how many other returned modules were omitted. The existing progress
reader still validates all returned identities before selection; a foreign or
duplicate item cannot be hidden by selecting another module.

The command uses the existing token or session-broker authentication and GET
pagination. It makes one call to the progress API, which may perform multiple
GET requests. It does not mark items read, complete work, change grades or
submit anything. There is no new MCP command.

A failed or refused read returns a nonzero exit with JSON on stderr and does not
publish a partial report. An empty returned module list can be exported, with
its unknown-completeness boundary visible. It is not proof that the course is
empty.

The output parent directory must already exist. The selected output must be a
new path: regular files, directories, links and dangling links are protected.
A same-directory temporary file is fully written and synced, then the existing
calendar export publisher uses a hard link to publish without replacing an
entry. Filesystems that do not support that operation fail; there is no
overwrite fallback. A competing creator of the destination is also preserved.
Choose a different filename to save a later observation.

The exporter accepts at most 4 MiB of its serialized normalized JSON and 16 MiB
of rendered UTF-8 HTML. Oversized or non-JSON-finite values produce a reported
error before output publication. These are export limits; they do not change
the existing reader's request or pagination limits.

On success stdout contains JSON with the output path, selected IDs, returned
and included module counts, creation time, HTML byte count and SHA-256, and the
embedded JSON byte count and SHA-256. File paths and diagnostics remain
ASCII-escaped in this machine-readable CLI receipt.

## Python use

```python
from pathlib import Path

from canvaspilot.api import CanvasAPI
from canvaspilot.calendar_export import write_calendar
from canvaspilot.client import CanvasClient
from canvaspilot.module_progress_export import build_module_progress_report

with CanvasAPI(CanvasClient()) as api:
    content, receipt = build_module_progress_report(api, 42, module_id=7)
write_calendar(Path("module-7-progress.html"), content)
```

`write_calendar` is the existing new-file byte publisher, reused without a
change to its implementation. `render_module_progress_report(report)` can
render an already obtained normalized progress report without another read.

## Source contract and qualification

The report semantics come from the existing
[module-progress reader](module-progress.md) and Canvas's
[Modules API](https://developerdocs.instructure.com/services/canvas/resources/modules).
All development fixtures are synthetic. Renderer and actual-CLI checks live in
`tests/test_module_progress_export.py` and
`tests/test_module_progress_export_cli.py`; they use the unchanged reader and
disposable loopback responses, without a school account. Native browser
qualification is retained separately with its exact source and runtime pins.
