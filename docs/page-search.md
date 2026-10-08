# Find text in course pages

Use `canvaspilot find-pages 42 --text "field journal"` to locate a phrase in the
returned pages for one course. Results are JSON, with the original page identity,
title, body and other returned fields preserved. Open a returned page in Canvas or
pass its locator to the existing `export-pages` command for a reading copy.

Search compares a literal Unicode-casefold substring separately against each
supplied title and the existing page reader's cleaned `body_text`. The exact query
is retained, including whitespace. There is no regular expression, ranking,
accent folding, cross-field matching or inferred word boundary. The existing
HTML cleaning removes tags, decodes entities and collapses whitespace; it is not
a browser rendering or a search of images, attachment bytes or linked resources.

Each result identifies the one-based returned position and matching fields.
Returned order and duplicate page identities remain intact. `pages_returned`,
`titles_searched` and `bodies_searched` describe the actual collection. A supplied
empty body is searched and can have no match; absent, null and locked bodies are
listed explicitly in `unavailable_bodies`, with their original page object.
Titles can still match when a body is unavailable. Block-editor attributes are
retained as returned data but are not searched as HTML. An empty `matches` list
does not establish that unavailable content lacks the phrase.

The command uses the existing paginated Pages GET with `include[]=body`.
It does not use Canvas's `search_term`, which searches partial titles only.
Authentication and pagination behavior remain those of the existing client.
A later-page failure refuses the result rather than printing earlier matches.
The read is not an atomic course snapshot and does not prove access to every
course resource. No page read/completion state, course, submission or account is
changed; no per-page body fallback or embedded-content request occurs.

Arguments must be one positive decimal course ID and a non-whitespace UTF-8 query
of at most 512 bytes. The decoded collection is limited to 1,000 rows and 8 MiB;
these checks run after the existing transport has decoded its response. Malformed
rows, non-text supplied title/body values, invalid lock flags and non-finite JSON
refuse the complete result. Failure is nonzero structured JSON on stderr with
no partial successful stdout. No output file or profile is created by this command.

The normal `--base-url`, `--profile` and `--token` options remain available.
The Python interface is `canvaspilot.page_search.find_pages(api, course_id, query)`.
Existing page listing, page retrieval, export and every other command are unchanged.

Primary contract: [Canvas Pages API](https://developerdocs.instructure.com/services/canvas/resources/pages),
read 2026-10-08. It documents paginated page collections, the optional body include,
title-only server search, and block-editor attributes.
