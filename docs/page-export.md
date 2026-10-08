# Take selected course pages offline

`export-pages` saves the pages you name into one local HTML reading packet. Open
the file in a browser to read it, jump between the selected pages, inspect their
supplied identity and metadata, or print the reading text. The file works without
a running CanvasPilot process or a network connection.

Use the same Canvas host and authentication you use for other CanvasPilot reads:

```bash
canvaspilot export-pages 42 course-introduction week-two-reading --out reading.html
```

The course ID is a positive numeric Canvas ID. Each page argument is its URL
locator, such as `course-introduction` from
`/courses/42/pages/course-introduction`; pass the locator, not the full URL.
Quote locators containing shell punctuation. The selection order becomes the
packet's reading order. There is no implicit course-wide search or export.

## Select a numeric page ID deliberately

Canvas's [Pages API](https://developerdocs.instructure.com/services/canvas/resources/pages)
accepts a URL locator or page ID in the single-page route and gives a matching
URL priority. Use Canvas's explicit `page_id:` form when you intend an ID:

```bash
# The page whose URL locator is literally "7".
canvaspilot export-pages 42 7 --out numeric-url.html

# The page whose supplied numeric page_id is 7.
canvaspilot export-pages 42 page_id:7 --out numeric-id.html
```

The exporter checks the returned course ID and every selected page identity.
A bare numeric locator must match the returned URL; it never silently accepts a
numeric-ID fallback. `page_id:7` must match the returned page ID. Duplicate
arguments and two different locators resolving to the same page are refused.
The packet also retains the provider's original ID values, including numeric
strings and integers larger than JavaScript's exact integer range.

## What the packet contains

Each page has a reading-text projection, a deliberate link back to that Canvas
page, and two expandable records:

- **Supplied page identity and metadata:** `page_id`, `url`, `title`, and any
  supplied `created_at`, `updated_at`, `published`, `front_page`,
  `locked_for_user` and `editor` fields. Values are retained without interpreting
  timestamps or inferring publication or progress. Missing fields remain absent
  in this record; missing/null publication and update values are labelled
  “Not supplied” in the reading view.
- **Original Canvas HTML:** the exact decoded `body` string, displayed as inert
  text, with its UTF-8 byte count and SHA-256. Unicode, original entities and
  CR/LF line endings remain in this retained source. This is the supplied body
  string, not the original HTTP response bytes.

The packet also shows the supplied course `id`, `name` and `course_code` when
present, the configured Canvas source and the export time in UTC. Other course
and page response fields are outside this export's projection. The original
HTTP response envelopes are not archived.

The reading projection is intentionally simpler than Canvas's rich page. It
keeps text, paragraph breaks, code indentation, image alt text and inert link
destinations. It labels omitted embedded media, removes script/style/template
content from the reading view, and does not reproduce rich layout, list
numbering, table styling or interactive content. Inspect the retained original
HTML whenever the text projection is insufficient.

Provider HTML is never inserted as executable markup. The packet has no
JavaScript, external font, image, stylesheet or embedded frame. Links within
the supplied body are text references. Opening the file or expanding its
records makes no automatic network requests; following an explicit “Open this
page in Canvas” link uses your browser and may require your normal login.
Closed source records are omitted from printing; open a record first if you
also want to print that retained source.

## Complete selection and output behavior

Choose **1–20** pages. Each supplied body may contain at most **512 KiB** of
UTF-8 text, with **2 MiB** of original bodies across the whole selection and a
**16 MiB** final HTML limit. Oversized or malformed content, a locked page, a
missing/null body, an identity mismatch or any failed read refuses the whole
selection. An explicitly supplied empty body is valid and labelled as empty.
An earlier successful page is never published as a partial packet when a later
read fails.

The destination must be a **new path in an existing directory**. Existing
files, directories, symbolic links (including dangling links) and hard links
are protected. The CLI refuses an already present destination before reading
Canvas. It also refuses a destination that appears during the reads.

Only after all reads and rendering succeed does the exporter write a private
temporary file in the destination directory, flush and sync it, close it, and
publish the complete bytes through an exclusive hard link. It never truncates
or replaces an existing destination. A failed write, sync, close or publication
leaves the original inputs and existing output intact. Temporary-file cleanup
is best effort. If publication succeeds but removing the temporary link fails,
the CLI reports success with a `cleanup_warning` naming that leftover link;
the complete packet already exists. Filesystems without hard-link support
refuse the operation rather than using a replacement fallback. The exporter
does not claim a multi-file transaction or power-loss durability for the
directory entry.

A successful command exits `0` and prints a JSON receipt to stdout: output path,
configured source, selected IDs/locators/titles in order, original-body byte
counts and hashes, export time, and final HTML byte count and SHA-256. A refused
operation exits `1` and writes a final JSON error record to stderr. The existing
transport may print HTTP diagnostics before that error record. Argument-parser
errors exit `2`. No success receipt is printed for a failed creation.

## Snapshot and authentication limits

The command issues one course GET and one single-page GET per requested page
through the existing `CanvasClient`. It neither changes authentication nor
starts a browser session. Session-broker mode uses the existing provider-origin
health guard and refuses a broker without the current origin-check capability.
Configured source identity is checked around each read; an observed change
refuses the packet. The transport's existing redirect behavior remains in
place. These checks are not an atomic provider/read transaction or a new
guarantee about redirects.

The pages are read sequentially. Their source may change between requests or
after export, and the generated timestamp is not a Canvas update timestamp.
This file is a selected reading copy, not a complete course backup, submission
receipt, grade record or evidence that you completed a requirement. No Canvas
page, completion state, submission or grade is written.

The content limits above are checked after the existing client decodes each
JSON response; they are not HTTP streaming or response-download limits. Images,
attachments and other resources are never fetched by this feature. Treat the
local packet as course content and follow the course's rules when sharing it.

## Reproduce the authored controls

```bash
python -m pytest -q tests/test_page_export.py tests/test_page_export_process.py
```

The fixture in `tests/fixtures/page_packet.json` is entirely authored. Unit
controls reject live HTTP and broker access; process controls use only a private
loopback HTTP server with an authored token. They cover selected identity,
retained source, inert markup, strict content limits, later-read failures,
exclusive file publication and preservation of existing inputs and outputs.
They do not establish that a school account is authenticated or that a specific
school's pages are available. Source-pinned native and browser qualification
receipts are retained in [the receiving evidence](evidence/page-packet-5f566b5ec8ef/).
