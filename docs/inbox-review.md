# Review your Canvas inbox

List your conversations, then choose an ID returned by that list:

```bash
canvaspilot inbox
canvaspilot inbox --scope unread
canvaspilot conversation 901
```

The commands use your selected Canvas client and current-user permissions, just
like the existing course readers. Common `--base-url`, `--profile`, and `--token`
options retain their existing meanings.

## Choose a list

| Scope | Canvas selection |
| --- | --- |
| `inbox` (default) | Read and unread conversations that are not archived |
| `unread` | Unread conversations |
| `starred` | Starred conversations |
| `archived` | Archived conversations |
| `sent` | Sent conversations |

The friendly `inbox` value omits the API scope parameter, using Canvas's documented
default. Other values are passed to Canvas as filters. The existing client follows
Canvas's validated Link continuations, preserving returned order. A continuation
failure is reported as an error instead of printing a partial list as success.
The client's existing 40-page limit and session-broker capability requirements
still apply.

The JSON list contains the original returned rows. Listing does not load every
conversation's message bodies. Select one returned conversation ID to read its
message payload.

## Preserve unread state while reviewing

`conversation` returns the original supplied conversation object, including
messages, participants, forwarded messages and attachment/media metadata.
Text, order, zero values, empty values, unknown fields and missing fields retain
their supplied meanings. Linked content is not fetched or rendered.

The reader explicitly sends `auto_mark_as_read=false`. An unread conversation
therefore stays unread under Canvas's documented contract, so reviewing it does
not clear that reminder to follow up. Existing read or archived state is also
preserved by this request. The response is a point-in-time server result; another
client or participant can change the conversation separately.

Python and MCP use the same readers:

```python
api.list_conversations(scope="unread")
api.get_conversation(901)
```

The existing `canvas_list_conversations` and `canvas_get_conversation` MCP tools
advertise read-only behavior. Their names, arguments and returned JSON structures
are unchanged. This preservation applies to these curated readers; an arbitrary
REST request through an escape-hatch tool retains Canvas's own endpoint defaults.
There is no new reply, subscription, archive or mark-read action.

## Errors and qualification

The CLI accepts a positive numeric conversation ID. Invalid IDs or unsupported
CLI scopes exit 2 before requesting data. The shared Python/MCP reader also
requires a positive decimal integer or digit string. It rejects route, query and
fragment syntax before making a request, so URL parsing cannot hide the
unread-preservation flag.

Authentication, HTTP, malformed JSON or pagination failures append a JSON error
line to stderr and exit 1, with no success JSON on stdout. Existing HTTP-client
diagnostics may precede the error line. Successful reads exit 0 and return JSON
on stdout; an empty list remains `[]`.

Behavior follows the official [Conversations API](https://developerdocs.instructure.com/services/canvas/resources/conversations),
including its list scopes and single-conversation `auto_mark_as_read` parameter.
The native fixtures in `tests/test_inbox_review.py` model that documented default
using disposable loopback HTTP and real CLI subprocesses. They preserve the
pre-feature failures and challenge state, payload, pagination and error behavior.
Independent receiving covers the session and registered MCP paths. These are
software contract checks using authored data; they do not claim a live school,
browser session, notification or student outcome.
