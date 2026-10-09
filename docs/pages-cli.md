# Discover and read course pages

List the page locators exposed to your selected Canvas account, read a returned
locator, then optionally use the existing offline exporter:

```bash
canvaspilot pages 42
canvaspilot page 42 course-introduction
canvaspilot export-pages 42 course-introduction --out reading.html
```

Both reader commands accept the existing `--base-url`, `--profile` and `--token`
options. Course IDs must be positive numeric IDs. No browser is launched by these
commands; they use the selected client's existing token or session broker route.

`pages` uses `CanvasAPI.list_pages()` and its existing paginator. JSON rows retain
the existing `url`, `title`, `published`, `updated_at` and `front_page`
projection in returned order. Use the `url` field as a page locator. False stays
false, absent projected fields stay null, and an empty successful collection is
`[]`. Unknown metadata is not included by that existing projection, and its
existing non-object row filtering is unchanged.

`page` uses `CanvasAPI.get_page()`. Its existing JSON projection contains
`url`, `title`, `body_html`, `body_text` and `published`. The original HTML
is a JSON string; the command does not execute or render it. Cleaned text uses the
API's existing cleaner and is not a faithful reproduction of layout or media.
Missing HTML remains null; an explicitly empty body stays an empty string. The
cleaned text for either follows the current API's empty-string convention.

Pass a returned locator literally, quoting it for your shell when necessary:

```bash
canvaspilot page 42 'week-two-reading'
canvaspilot page 42 page_id:170
```

The optional `page_id:ID` form explicitly chooses a numeric page ID. Bare numeric
text retains its normal page-locator meaning. Locators follow the same admission
rules as `export-pages`: at most 512 UTF-8 bytes, no surrounding whitespace,
path separators, dot/parent components or control characters. The complete
locator is percent-encoded once as one path segment, so literal percent, query
and fragment characters remain part of the chosen locator. Admission completes
before creating a client or accessing Canvas.

These commands perform only the existing GET reads. They do not search page
bodies, follow links, download embedded media, mark module work complete, edit
pages, submit work or export a file. Page search and `export-pages` are separate
consumers of the same course content.

Successful reads print JSON to stdout. A request, authentication, pagination or
decoding failure exits nonzero with a JSON error on stderr. A failed later list
page produces no partial successful collection. A malformed single-page response
is an error rather than an empty page. An output write or flush failure also exits
nonzero; a downstream pipe may already have received some bytes. HTTPX logging is
restored after each command and the client is closed on success or failure.

The response is a current API read, not an atomic course snapshot. Existing
pagination limits and API projections still apply. Qualification uses synthetic
offline HTTP fixtures, not a live school account.
