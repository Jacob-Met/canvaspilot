# Find a classic quiz by title or instructions

Use a phrase you remember from a quiz's instructions, across the courses you
explicitly select:

```sh
canvaspilot find-quizzes 42 77 --text "primary evidence"
canvaspilot find-quizzes 42 --text "日本語"
```

The command reads each course's classic-quiz collection through the ordinary
CanvasPilot client. It searches titles and complete descriptions after the
existing `strip_html` text projection. Canvas's own collection `search_term`
matches partial titles, so this command performs its literal search after the
complete collection is returned. It does not send that title-only filter.
See the [Canvas Quizzes API](https://developerdocs.instructure.com/services/canvas/resources/quizzes).

## Read the result

Success prints one JSON object with schema `canvaspilot.quiz-search.v1`.
`quiz_count` counts returned records, and `matched_count` counts matching
occurrences. Each selection reports its course ID and counts, including an
empty successful collection.

Each match gives its one-based `selection_number` and `quiz_position`, selected
`course_id`, and `matched_fields` (`title`, `description_text`, or both). Source
order and duplicate occurrences remain; selecting the same course twice makes
two separate reads and keeps both observations. Equal quiz IDs from different
courses do not merge.

Matching uses Unicode casefold and literal substring comparison. It is not a
regular expression, ranking or accent-insensitive search. For example, `STRASSE`
matches `Straße`. Titles and descriptions are searched separately, so a phrase
cannot begin in the title and end in the description. Meaningful query spaces
remain literal. Description markup uses the existing text projection, which
collapses whitespace and decodes HTML entities once; the query is not HTML-decoded.

Matches include the existing quiz-list metadata plus `unlock_at` and
`locked_for_user`. The returned `id` and selected metadata retain their supplied
values, including null, zero and false. Missing selected metadata becomes null,
as in the existing list. No eligibility, adjusted deadline, extension, remaining
attempt count or current availability is calculated from those observations.
Access codes, permissions, IP filters and other unselected fields are not included.

`description_html` retains the complete supplied description as an inert JSON
string, and `description_text` contains its complete projected text. There is
no 400-character excerpt limit. The report's `description_counts` covers all
returned records, including nonmatches:

| State | Meaning |
| --- | --- |
| `missing` | The response did not contain a description field. |
| `null` | The response supplied a null description. |
| `empty` | The response supplied the empty string. |
| `no_text` | The supplied string had no text after the existing projection. |
| `text` | The projection contains text. |

A missing or empty description does not prove that no instructions exist.
This searches what was returned for the caller. It does not search quiz
questions, answers, submissions, attachments, unavailable content or New Quizzes/LTI.
It does not fetch individual quiz details, start an attempt or complete a quiz.

## Limits and failure behavior

Select one to ten course occurrences using positive ASCII decimal IDs of at
most 20 digits. Leading zeros are normalized for request paths. Supply a
nonblank query of at most 512 UTF-8 bytes. Invalid selections and queries fail
before constructing a client or opening a profile.

The command admits at most 1,000 returned quiz records and 8 MiB of JSON across
the decoded course collections. Its final indented JSON is limited to 16 MiB.
The input size is measured using Python's UTF-8 JSON serialization after each
collection is received; it is not a network-body or transport memory bound.
The ordinary client's pagination behavior, including its 40-page cap, is
unchanged.

A malformed record, invalid quiz identity, mismatched supplied course identity,
malformed title/description, non-finite JSON value, read failure or exceeded
limit refuses the complete result. A successful earlier page or course is not
printed as a partial report. Argument rejection returns status 2; runtime
rejection returns status 1 with a JSON error on stderr and no success report.
A successful empty search is status 0 with an empty matches list.

The read client closes and the caller's HTTPX logger level is restored before
the report is delivered. An output delivery error is reported as failure.
The existing `quizzes` and `quiz` commands are unchanged.

Python callers can use the same report logic with an existing client:

```python
from canvaspilot.client import CanvasClient
from canvaspilot.quiz_search import search_quizzes

with CanvasClient() as client:
    report = search_quizzes(client, [42, 77], "primary evidence")
```

The maintained tests use fictional fixtures and local HTTP servers:

```sh
python -m pytest -q tests/test_quiz_search.py tests/test_quiz_cli.py
```

They do not require a Canvas account and do not exercise a live school session.
