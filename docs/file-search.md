# Find a course file by name

Use an explicit list of course IDs to search the file names Canvas returns:

```sh
canvaspilot find-files 42 77 --text "lab notes"
# From a source checkout with the package dependencies installed:
PYTHONPATH=src python -m canvaspilot.cli find-files 42 77 --text "lab notes"
```

The command reads each selected course's file metadata through the existing
`CanvasAPI.list_files` reader, including its normal pagination, and prints one
JSON result. It searches `display_name` and `filename` separately. It does not
download files, traverse folders, fetch course details, follow returned links or
change Canvas state. The existing `--base-url`, `--profile` and `--token`
options work as they do for the other read commands.

## What matches

Search uses a literal Unicode casefold substring. For example, `STRASSE`
matches `Straße.pdf`; `cafe` does not match `café.pdf`. Accents and Unicode
normalization forms remain distinct. Punctuation such as `[1]`, `.*` and
`?` is ordinary text. Query whitespace is retained: `" lab "` searches those
spaces too. A match cannot span the end of the display name and the start of
the filename.

Each course remains in the result, including an empty course or a course with
no matches. Matching occurrences retain their original course order and row
order, their 1-based `source_position`, the matching field names and the whole
normalized file object. Repeated identities remain repeated occurrences.
Nothing is sorted, ranked or deduplicated.

`unavailable_names` records missing, null and unsupported-type name fields.
An empty string is an available, known-empty name. A row can match one name
while the other name is unavailable; a no-match result cannot establish the
contents of an unavailable name.

`returned_files` counts the normalized rows supplied by the existing reader.
`searched_files` counts rows with at least one string name, including an empty
string. `matched_files` counts matching occurrences, even when both names match.
The totals repeat these counts across the selected courses and report how many
rows had an unavailable name.

## Scope and limits

The existing reader projects `id`, `display_name`, `filename`, `size`,
`updated_at`, `url` and `content_type`. It omits nonobject source rows and
maps an absent projected field to null. The search describes this returned
projection, so it cannot recover omitted source fields or distinguish their
original absence from null. Returned URLs remain literal metadata. A name
match says nothing about file contents, current access or remote freshness.

Select 1–10 unique positive course IDs, each containing at most 20 ASCII decimal
digits. Leading zeros normalize to the same numeric identity, so selecting
both `01` and `1` is refused. Search text must contain a non-whitespace
character and fit within 512 UTF-8 bytes.

The command accepts at most 2,000 normalized file rows per course, 5,000 rows
across the selection and 8 MiB of combined UTF-8 JSON row data. Byte accounting
uses each complete row with compact JSON separators and literal Unicode;
list wrapping is excluded. These bounds apply after the existing client has
decoded its response. Excess rows or names are refused without truncation.

Invalid input exits with status 2 before constructing a client. A later read,
pagination, schema or budget failure exits with status 1 and a structured JSON
error on stderr. There is no partial successful stdout from earlier courses.
The existing client is closed and the caller's HTTPX log level is restored.
Success prints one deterministic JSON document followed by a newline.

## Python use

```python
from canvaspilot.file_search import find_files

# api is an existing CanvasAPI instance managed by the caller.
report = find_files(api, ["42", "77"], "lab notes")
```

The helper also accepts non-boolean integer course IDs. It validates the whole
selection before making a read, calls `list_files` once per selected course,
propagates its read errors and raises `ValueError` for invalid input, schema or
budget. It does not mutate the rows returned by the reader. The caller keeps
ownership of its API/client lifecycle.

The maintained native tests use authored metadata and synthetic HTTP only;
they do not require or establish a live Canvas school session.
