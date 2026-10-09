# Find a discussion by its opening prompt

Use `canvaspilot find-discussions` to locate a phrase in returned discussion-topic titles and complete cleaned opening prompts:

```sh
canvaspilot find-discussions 42 84 --text "field journal"
canvaspilot find-discussions 42 --text "Straße"
```

The command uses the same token or existing session provider and common `--base-url`, `--profile` and `--token` options as the existing CLI. It reads only the selected courses' discussion-topic lists. It does not open reply views, mark anything read, post messages, retrieve attachments or follow topic URLs. Use the existing `discussion COURSE_ID TOPIC_ID` command after selecting a result if you want to inspect its reply context.

## What a match means

Matching is a literal Unicode-casefold substring, independently in `title` and `message_text`. Casefolding lets `strasse` match `Straße`; it does not remove accents or normalize composed/decomposed Unicode. Punctuation is literal. Significant query spaces remain significant, so `" reef "` differs from `"reef"`. Blank queries are refused. Text in two different fields is never joined to create a match.

The existing `CanvasAPI.list_discussion_topics` supplies each opening prompt. Its unchanged `strip_html` removes literal tags, then unescapes HTML entities and collapses whitespace. Search applies to that complete normalized text, not raw HTML, comments, reply content or a reconstructed document. The reader already skips non-object raw rows and projects six fields. Empty normalized prompts cannot distinguish missing, null, empty or media-only raw content.

## Reading the result

Success prints one `canvaspilot.discussion-search.v1` JSON object. It contains the exact query and matching mode, returned/matched topic counts, empty normalized prompt counts, a summary for every selected occurrence, and matching topic objects.

Every match records:

- `selection_number`: the one-based position of the selected course argument.
- `course_id`: the positive decimal course ID, with leading zeroes removed.
- `topic_position`: the one-based position in that course's returned normalized list.
- `matched_fields`: `title`, `message_text`, or both, in that order.
- `topic`: the complete admitted normalized topic object, including its supplied metadata.

Order follows the explicit course arguments and the existing reader's topic order. Repeated course arguments are deliberately read and represented again. Duplicate IDs, titles and identical topics stay separate occurrences; a topic ID alone does not identify an occurrence across different courses. There is no ranking, deduplication or snippet truncation.

A valid no-match report has an empty `matches` array. It says nothing about inaccessible, omitted, attachment or reply content. Successful pagination uses the existing client's conventions and limits; it is not a claim of freshness or an unlimited historical archive. Any reader/pagination failure refuses the complete report instead of printing a successful subset.

## Limits and refusals

Select 1–10 course occurrences. Each course ID must be a positive integer represented by at most 20 ASCII decimal digits. Queries must contain a non-whitespace character and fit in 512 UTF-8 bytes.

The selected normalized lists may contain at most 1,000 topics and 8 MiB of compact UTF-8 JSON in total. Complete pretty-printed output is limited to 16 MiB. Container nesting is limited to 32 levels, counting the input selections root. These are post-normalization limits; they do not bound raw network response bytes. All selected rows, including nonmatching later rows, are checked before a result is returned.

Each normalized topic must include `id`, `title`, `posted_at`, `published`, `message_text` and `html_url`. Titles are text or null; normalized messages are text. Other JSON metadata remains unchanged. Invalid JSON values, nonfinite numbers, cycles, unencodable text and non-string object keys are refused, without input mutation or truncation.

Invalid course/query selection exits 2 before constructing a client or resolving a profile. Read, normalized-data, serialization, client-close or ordinary output-delivery failures exit nonzero. Diagnostics are JSON on stderr when it is writable. A short write or failed flush is not a successful delivery. The command closes only its own client, restores the original HTTPX logger level and never retries.

## Python use

```python
from canvaspilot.discussion_search import collect_discussions, serialize_discussion_search

# api is an existing CanvasAPI instance owned by the caller.
result = collect_discussions(api, ["42", "84"], "field journal")
text = serialize_discussion_search(result)
```

`collect_discussions` does not close a caller-owned API or client. The CLI wrapper owns and closes the client it constructs. The pure `search_discussions(selections, query)` helper consumes complete normalized `{"course_id": ..., "topics": [...]}` selections, makes no requests and detaches its result from mutable input objects.

## Qualification boundary

The initial source packet has focused in-memory helper, actual CLI-source dispatch and unchanged API-normalization checks with finite synthetic transport. These checks do not establish installed-package bootstrap, HTTPX/token/session transport, a live Canvas account or a physical terminal/browser outcome. Original source and absent-command evidence are retained separately. No source ref, deployment or workflow activation accompanies the detached contribution.
