# Read a discussion with its reply context

Use the existing topic list to select a discussion, then open that topic:

```bash
canvaspilot discussions 42
canvaspilot discussion 42 71
canvaspilot discussion 42 71 --unread-only
```

The commands use the same configured Canvas client as the other CLI operations.
The new reader is also available as
`CanvasAPI.discussion_thread(course_id, topic_id, unread_only=False)` and the MCP
tool `canvas_discussion_thread`. The MCP flag is a JSON boolean.

## Reading the result

The JSON response keeps the topic and lists entries in the order of Canvas's
returned reply tree. Each entry has a cleaned `message_text` beside its original
fields, and a participant record when its author ID has one unambiguous match.

| Field | Meaning |
| --- | --- |
| `topic` | The original topic response, including its declared counts, visibility, locks, attachments and source HTML when supplied. |
| `topic_message_text` | The topic body through CanvasPilot's existing HTML-to-text helper; missing/non-text bodies stay null. |
| `entries[].entry` | Original entry fields, with the nested `replies` array represented by separate rows. No entry IDs, parent IDs, timestamps or source messages are rewritten. |
| `entries[].path` / `parent_path` | Positions in this returned tree. For example, `[0, 1]` is the second reply to the first root entry. These positions identify this view only. |
| `replies_supplied` / `reply_count` | Whether the source entry supplied a replies array and how many direct children that array contained. Together with paths, these retain the original tree structure, including an explicit empty replies array. |
| `read_state` | Read, unread or unknown, derived from the supplied unread identifiers and an unambiguous entry ID. |
| `forced_read_state` | Whether the entry is in the supplied forced-state list; null when this association is unknown. |
| `context_only` | True when an entry is included solely to explain a descendant selected by unread focus. |
| `view_metadata` | All original view fields other than the reply tree, including participants, unread/forced identifiers, ratings and any separate new-entry stream. |
| `counts` | Entries actually observed in this tree, returned rows, known unread entries, and entries whose read state is unknown. |
| `unmatched_unread_entries` | Supplied unread identifiers that could not be located in the cached tree. |
| `warnings` | Missing or ambiguous read/author associations. |

The returned tree positions and the original `parent_id` serve different purposes.
A conflicting source parent ID remains visible; it does not move an entry to a
different branch. Deleted and media-only entries remain present. The reader does
not invent body text or author attribution for deleted entries.

## Focus unread replies

`--unread-only` keeps entries known to be unread and every ancestor needed for
their context. Each ancestor appears once, in the original tree order. Read
siblings and unrelated read roots are omitted. Counts continue to describe the
whole observed tree as well as the selected rows.

An explicitly empty unread list produces an empty selection. A missing or null
unread list is unknown and makes unread focus unavailable; the full reader still
shows the entries with unknown read states. An entry whose ID cannot establish a
unique association remains unknown. Such an entry can appear as an ancestor, but
it is not itself selected as known unread. If a supplied unread identifier matches
multiple returned entries, unread focus refuses the ambiguous selection.

Identifier matching preserves numeric versus string values. Duplicate participant
IDs cannot establish an author. Original lists and identifiers remain in
`view_metadata` so these conditions are inspectable.

## What the view represents

Canvas's [full-topic API](https://developerdocs.instructure.com/services/canvas/resources/discussion_topics#method.discussion_topics_api.view)
returns a cached, eventually consistent tree. It describes `unread_entries` as
the current user's unread entry identifiers and `forced_entries` as manually
forced read-state markers. The report identifies its source as
`canvas_cached_discussion_view`.

The reader reuses the existing raw `get_discussion()` operation: one topic GET
and one view GET. It does not request a separate new-entry stream or merge one
into the tree. If the server supplies such metadata anyway, it remains separate
in `view_metadata`. Topic counts and tree counts can differ; neither is rewritten
to agree with the other. Unread filtering happens locally after the view is read.

An access refusal, an unavailable cache or malformed response is an error, not an
empty discussion. The CLI exits nonzero and writes its error to stderr without a
success report; MCP returns a tool error. The existing client's error
classification is retained, including its treatment of HTTP 403. No automatic
retry or initial discussion post is made. Reading does not send any post,
mark-read, rating or subscription request.

Qualification uses synthetic fixture data, actual CLI/MCP processes and local HTTP.
It does not establish access to a particular school, browser session or live
discussion, or guarantee that a server cache contains its latest changes.

## Development

The new tests are collected by the existing test command:

```bash
pytest -q
```

Focused checks:

```bash
pytest -q tests/test_discussion_thread.py tests/test_discussion_thread_native.py
```

The existing raw discussion API, topic-list method, posting method, client,
authentication and session-broker source are preserved by this contribution.
