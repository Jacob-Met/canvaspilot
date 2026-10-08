# Find announcement text

Use `find-announcements` when you remember a phrase from an announcement and
want to find its course and complete message:

```bash
canvaspilot find-announcements 42 77 --text "room change" --start-date 2026-10-01
```

Provide at least one positive course ID and a `--text` query containing a
non-whitespace character. The command uses the same credentials and optional
`--base-url`, `--profile`, and `--token` arguments as `announcements`.
Omit `--start-date` to retain Canvas's existing default date selection; a supplied
value is passed to the existing reader unchanged.

## Matching

The command asks the existing announcement reader for full cleaned message text,
including text beyond the compact command's 400-character preview. It searches
each title and message separately using Python's Unicode `casefold()` and a
literal substring comparison. For example, `strasse` matches `Straße`, and
`[x]+.*` matches those exact characters rather than a regular expression.

The exact query is retained. Leading and trailing spaces are significant:
`--text " room "` asks for the word surrounded by spaces. Titles and messages
are not joined together. Search adds no Unicode normalization, stemming, ranking,
or conversion of a missing or non-text title into invented text. The existing
reader still strips HTML, decodes entities, and collapses message whitespace.

## Result

The result is one JSON object:

```json
{
  "course_ids": [42, 77],
  "start_date": "2026-10-01",
  "query": "room change",
  "match_mode": "literal_casefold",
  "announcements_returned": 3,
  "announcements_matched": 1,
  "matches": [
    {
      "matched_fields": ["message_text"],
      "announcement": {
        "id": 7,
        "title": "Meeting details",
        "posted_at": "2026-10-08T12:00:00Z",
        "context_code": "course_42",
        "message_text": "Room change to Omega 204.",
        "html_url": "https://canvas.example/courses/42/discussion_topics/7"
      }
    }
  ]
}
```

`announcements_returned` counts the normalized rows returned by the complete
reader; `announcements_matched` counts matching rows. Each match preserves the
reader's full announcement object, including its course context, timestamps, URL,
missing values, and zero values. Rows keep their original order and duplicate
IDs. `matched_fields` lists `title`, `message_text`, or both in that order.

No matches is a successful result with an empty `matches` array. An empty
collection also has `announcements_returned: 0`.

## Complete reads and refusals

Search produces its result only after the existing paginated reader succeeds.
It preserves that reader's course/date filters, continuation validation, and
40-page limit. An authentication, HTTP, or incomplete-pagination error produces
structured JSON on stderr, exit status 1, and no partial search result on stdout.
It never treats earlier matching pages as a complete success.

Missing or whitespace-only queries and invalid course IDs are rejected by the
argument parser with exit status 2, before client or default-profile setup. This
is a read-only consumer: it does not post announcements, change read state, create
exports, or add an authentication route. The existing `announcements` command
and compact/full output remain available unchanged.
