# Browse course folders

`browse-files` lets you start at a course's root, choose a child folder and inspect
file metadata inside it. It fills the navigation gap left by `files`: that older
command offers a flat course list and its fallback lists only root-folder files.
The existing command and its return shape are unchanged.

## CLI journey

Use the numeric course ID returned by `canvaspilot courses`. These example IDs
are synthetic:

```sh
# Read the root folder, its first child-folder page and its first file page.
canvaspilot browse-files 42 --per-page 20

# Choose a child folder by the ID returned above.
canvaspilot browse-files 42 --folder-id 110 --per-page 20

# Request another file page while keeping the first child-folder page.
canvaspilot browse-files 42 --folder-id 110 --files-page 2 --per-page 20

# Child folders have an independent page selection.
canvaspilot browse-files 42 --folder-id 110 --folders-page 2 --files-page 1
```

The command uses the existing token or session-broker mode and accepts the same
`--base-url`, `--profile` and `--token` options as the other read commands. It does
not start a browser or log in. Invalid parameters and permission/transport errors
produce no result on stdout, a structured error on stderr and a nonzero exit.
Normal HTTP client logs may precede that final stderr error.

## MCP and Python

The registered MCP tool is `canvas_browse_files`; its read-only annotation
reflects the implementation's three Canvas GETs. It has the same folder/page
arguments as the CLI:

```json
{
  "course_id": "42",
  "folder_id": "110",
  "folders_page": 1,
  "files_page": 2,
  "per_page": 20
}
```

```python
from canvaspilot.bundle import make_api

with make_api() as api:
    root = api.browse_files(42)
    child = api.browse_files(42, 110, files_page=2, per_page=20)
```

| Argument | Default | Accepted values |
| --- | --- | --- |
| `course_id` | required | Positive numeric Canvas ID, integer or ASCII decimal text in Python; text in MCP |
| `folder_id` | `root` | `root` or a positive numeric Canvas folder ID |
| `folders_page` | `1` | Integer from 1 through 10,000 |
| `files_page` | `1` | Integer from 1 through 10,000 |
| `per_page` | `50` | Integer from 1 through 100 |

IDs accept at most 32 decimal digits and are normalized before constructing a
path. Boolean values, path/query fragments, special IDs such as `media`, and
invalid page/size values are rejected before a client request. MCP page and size
arguments use strict integers, so JSON `true` does not silently become page 1.
SIS identifier syntax is not part of this new interface; use a canonical numeric
ID from the existing course list.

## Result and pagination limits

A result contains `course_id`, the selected `folder`, and `folders`/`files` page
objects. Each page has `items`, `page`, `per_page`, `returned_count`, `has_more`,
`next_page_to_try` and `page_limit_reached`. The result's `scope` is
`direct_children`: descendants are reached by choosing their folder IDs, not by
an automatic recursive crawl.

The existing `CanvasClient.request()` returns response bodies without `Link`
headers, including on its session-broker path. This feature therefore sends
explicit page requests, as the existing broker pagination does. It always leaves
`has_more` as JSON `null`. A short or empty page does not establish completeness.
`next_page_to_try` is only the next bounded integer a caller may request; it is
not evidence that another page exists. At page 10,000 that field is `null` and
`page_limit_reached` is `true`, while `has_more` remains unknown.

Canvas's [pagination documentation](https://developerdocs.instructure.com/services/canvas/basics/file.pagination)
requires opaque `Link` headers for authoritative continuation and notes that a
server may cap the requested page size. Automatic opaque-cursor traversal and a
complete recursive inventory are not supplied by this feature. The caller must
not treat its page probes as either. No response-supplied URL is followed.

## Course and metadata boundaries

The [official Files API](https://developerdocs.instructure.com/services/canvas/resources/files)
documents the course-scoped folder lookup, including `root`, and the two
paginated child-list endpoints. The browser first requests:

```text
GET /api/v1/courses/{course_id}/folders/{folder_id_or_root}
```

It requires the returned folder to match the selected course and requested ID
before issuing either child-list request:

```text
GET /api/v1/folders/{verified_folder_id}/folders?page=N&per_page=M
GET /api/v1/folders/{verified_folder_id}/files?page=N&per_page=M
```

Child folders must retain that course and parent; files must retain the selected
folder ID. A mismatched identity, malformed page, duplicate identity within a
page, or oversized page fails the operation without returning a partial browse
result. An inaccessible folder remains an error; it is never relabeled empty.

Metadata preserves names, stable IDs, parent/context relationships, reported
counts, timestamps, content type, size and available lock/visibility fields.
Missing optional fields remain absent, and the selected folder's reported counts
are source metadata rather than proof of an accessible complete inventory.
Download, preview and thumbnail URLs, embedded file bodies, and response-supplied
child-list URLs are excluded. No file is downloaded, marked read, edited or
submitted. The current Canvas permission/authentication behavior remains in the
existing client.

## Receiving

`tests/test_folder_browser.py` exercises the real `CanvasClient`, public CLI
subprocesses and the actual MCP stdio server against an authored loopback HTTP
fixture. It covers root-to-child navigation, independent next-page requests,
nested files, empty and forbidden folders, foreign course/folder responses,
literal Unicode names, omitted access URLs, bounded pages and parameter
rejection before network access. No live account, provider, browser or downloaded
file is used.

A separate receiving case routes the real API and CLI through the unchanged
read-only broker `Handler`, with an authored queue worker supplying the metadata
responses. It verifies exact folder/file page queries, nested selection and a
foreign-folder permission refusal while all dispatched Canvas operations remain
GET requests.
