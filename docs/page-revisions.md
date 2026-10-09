# Read a course page's recorded history

An authorized page editor can list Canvas's recorded revisions and read a chosen
historical version without changing the current page:

```sh
canvaspilot page-revisions 42 "week-one"
canvaspilot page-revision 42 "week-one" 7
canvaspilot page-revision 42 "page_id:170" latest --summary
```

Use the existing CanvasPilot connection options or configured token/session.
Canvas requires page **edit/update rights** for revision history. Ordinary page
view permission does not establish that access. A permission denial remains an
error; these commands do not request additional privileges or revert a page.
The historical title and URL can differ from today's locator.

Python uses `CanvasAPI.list_page_revisions(course_id, page_url)` and
`CanvasAPI.get_page_revision(course_id, page_url, revision_id, summary=False)`.
The registered read-only MCP tools are `canvas_list_page_revisions` and
`canvas_get_page_revision`, with the same named arguments. Choose an explicit
positive revision ID or the literal `latest`. The optional summary flag must be
a boolean; it asks Canvas to omit content.

The list retains complete returned revision objects in reader order. Show returns an envelope with the complete server object under `revision`
and adds the existing cleaned-text projection as the outer `body_text` when a
body field is present. The supplied revision metadata, historical `body`, title
and URL stay exact, including any server key also named `body_text`.
Absent content stays absent; explicit null remains null and an empty body stays
empty. The original HTML is data in JSON, not an executed page. Unknown metadata
and original ID representations are retained. A selected numeric ID must match
the returned revision; a renamed historic URL need not match the current locator.

Course and numeric revision IDs accept positive ASCII decimal values through
9223372036854775807, with at most 19 input digits. Leading zeros are canonicalized.
A locator is literal Unicode text, at most 2048 UTF-8 bytes, with no ASCII control
characters or lone surrogate values. Empty, "." and ".." locators are refused.
Locators are encoded exactly once as a URL path segment; no trimming or case
conversion is performed. Canvas's numeric-locator precedence remains: use
`page_id:170` when explicitly selecting a numeric page ID.

Malformed revision rows, duplicate revision IDs and a mismatched selected ID
refuse the whole result. The CLI reports JSON on stdout only after the entire
operation succeeds; read failures exit 1 with error JSON on stderr. Invalid
arguments exit 2 before constructing a client. MCP failures are tool errors.
The client closes on success or read failure.

These commands reuse the existing GET client and paginator unchanged. The result
describes returned rows, not a certified complete or atomic history. Existing
pagination caps, normalized-response behavior, broker boundaries and school
permissions still apply. No POST, PUT, deletion, revert or marking operation is
introduced. No local fixture establishes access to a real course.

The endpoint and permission contract is the official
[Canvas Pages API](https://developerdocs.instructure.com/services/canvas/resources/pages).
It distinguishes List revisions, Show revision and the separate modifying Revert
operation.

Native qualification uses fictional loopback responses, actual CLI subprocesses,
and registered MCP calls:

```sh
python -m pytest -q tests/test_page_revisions.py tests/test_page_revisions_process.py
```
