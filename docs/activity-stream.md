# Read your Canvas activity stream

Run `canvaspilot activity` to read the available current-user global activity
stream as one JSON collection. It uses your existing CanvasPilot base URL and
authentication configuration.

```bash
canvaspilot activity
canvaspilot activity --base-url https://example.instructure.com
```

The command also accepts the existing `--profile PATH` and `--token TOKEN`
options. It adds no course, date, read-state or active-course filter, and accepts
no positional arguments. Unknown options fail during argument parsing.

## What the JSON means

The response retains each decoded record as supplied by Canvas, including
unknown fields, nested values, duplicate rows, HTML-containing strings, Unicode,
zero, false and null. It keeps page order and row order. It does not shorten
messages, strip markup, sort events, merge duplicates or fetch linked content.

A record's supplied `read_state`, type, course/group context, title and timestamps
remain source observations. Missing fields stay missing. The command does not
mark an event read, hide it or delete it.

The [Canvas Users API](https://developerdocs.instructure.com/services/canvas/resources/users#method.users.activity_stream)
describes this endpoint as a paginated global activity stream. It is an available
feed, not a complete historical archive, complete assignment inventory or
complete list of unread work. Canvas documents a 4 KB message limit for
DiscussionTopic and Announcement activity records. Reading every available page
cannot recover content the endpoint did not return.

## Pages and complete-result behavior

`CanvasAPI.activity_stream()` uses the existing
`CanvasClient.get_paginated("/api/v1/users/self/activity_stream")` reader.

- The first request uses the client's current `per_page=50` setting.
- The reader follows Canvas's opaque `rel="next"` links, including after a short
  or empty continuing page. It does not invent page numbers or reapply first-page
  parameters to the next URL.
- A terminal page ends traversal without an extra empty-page probe.
- The existing same-origin, repeated-link and malformed-link checks apply.
- Forty pages is the current client limit. A terminal fortieth page succeeds;
  a remaining next link at that boundary raises a pagination error.

These are the existing client rules, not a new paginator. Canvas's
[pagination documentation](https://developerdocs.instructure.com/services/canvas/basics/file.pagination)
explains why callers must follow returned links rather than infer completion from
the number of returned items.

The command collects the complete accepted result before printing success JSON.
Authentication, HTTP, JSON-decoding or pagination failure returns exit status 1,
leaves success stdout empty, and prints one JSON error object to stderr:

```json
{"ok": false, "error": "CanvasPaginationError", "message": "…"}
```

The `error` and `message` values describe the actual failure; they are not fixed
to the example above. An incomplete traversal is not reported as a successful
partial feed. Ordinary HTTPX request logging is suppressed during the read, and
the caller's previous logger level is restored. The existing client close path
runs on success and failure.

| Result | Exit status | Output |
| --- | --- | --- |
| Successful read | 0 | One indented JSON array and a final newline on stdout |
| Successful empty feed | 0 | `[]` and a final newline on stdout |
| Read or pagination failure | 1 | One JSON error on stderr; empty stdout |
| Unknown or invalid command arguments | 2 | Argument-parser error before client construction |
| `--help` | 0 | Command help without a Canvas request |

The endpoint normally returns an array. The original client's compatibility
behavior is retained: a first terminal non-list JSON value is wrapped in a
one-element list. A non-list continuing page or later non-list page is rejected.
There is no new record schema validation or normalization.

Session authentication uses the existing broker route. Complete collection reads
require the current broker's Link-response metadata; an older broker without
that metadata produces the existing explicit incomplete-collection error.
Authentication and broker implementation are unchanged.

## Python and MCP

The Python method keeps its no-argument interface:

```python
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient

with CanvasAPI(CanvasClient()) as api:
    activity = api.activity_stream()
    for record in activity:
        print(record)
```

Configure the normal token or running CanvasPilot session broker before a live
read. The existing MCP tool `canvas_activity_stream` delegates to the same method
without new arguments, so it also receives the paginated collection.

## Local qualification

`tests/test_activity_stream.py` exercises the actual API and CLI against synthetic
loopback HTTP responses, plus the existing fixture route and a disposable
synthetic broker. It checks literal records, opaque links, short and empty
continuation pages, terminal compatibility, first and later failures, the
forty-page boundary, argument refusal, logger restoration and client closing.
The tests use no live Canvas account or user browser session.

```bash
python -m pytest tests/test_activity_stream.py
```
