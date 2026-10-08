# Read your Canvas planner from the CLI

Use `canvaspilot planner` to read the current user's planner items through the
existing `CanvasAPI.planner_items()` method. This makes the same native planner
collection already available in Python and MCP accessible from the terminal.

## Usage

From an installed CanvasPilot checkout, with its existing session broker or PAT:

```bash
canvaspilot planner
canvaspilot planner --start-date 2026-10-08 --end-date 2026-10-15
canvaspilot planner --start-date 2026-10-08T09:10:11Z --end-date 2026-10-15T18:00:00Z
```

The common `--base-url`, `--profile` and `--token` options behave as they do for
other CanvasPilot reads. This command does not start a browser or create a new
login/session; use the project's existing authentication setup.

Both date options are optional. Canvas documents calendar dates (`YYYY-MM-DD`)
and ISO 8601 timestamps for the planner endpoint. Supplied values pass unchanged
to the native API. The CLI does not parse, convert, round, reorder or impose a
local timezone on them. Omitted or empty values retain the existing API's omitted
filter behavior; Canvas determines the resulting window. No new context or
completion filter is applied.

## Read the returned JSON

Standard output is the complete JSON list returned by the existing native
client, in its original order. A successful empty result is `[]`.

Planner items can include course work such as assignments and discussions, as
well as personal `planner_note` entries. Personal notes need not identify a
course. The command keeps all supplied fields and values, including unknown
future fields, literal HTML/text, zero, `false`, `null`, submissions metadata and
`planner_override`. It does not turn planner completion or dismissal into a
grade, submission decision or inferred deadline.

For example, these are different supplied states:

| Supplied field | What the CLI does |
|---|---|
| `planner_override.marked_complete` | Preserves the Canvas value; does not mark work complete |
| `planner_override.dismissed` | Preserves the Canvas value; does not change planner visibility |
| `submissions` or a missing/null value | Retains the native payload without inferring submission state |
| A personal note without `course_id` | Keeps it in the collection |
| An unknown field or item shape | Retains the existing client/API result without a new schema filter |

The native client also has a first-terminal-object convention: if the first
response is an object with no continuation, its existing collection method
returns that object inside a list. This command preserves that behavior.

## Pagination and errors

The existing client owns authentication, Link pagination, continuation-origin
checks and its 40-page cap. Date filters apply to the initial request; the client
follows the native continuation URLs without rebuilding them. A collection is
printed only after that read returns. A detected auth, HTTP, pagination or JSON
read error produces a nonzero exit with a structured error object on standard
error and no partial successful list on standard output. A malformed CLI option
is an argparse error (exit2).

The command uses the existing planner GET endpoint. It does not create, update
or delete notes, planner overrides, submissions or visibility/completion state.
It adds no local output file option; ordinary shell redirection has the shell's
normal overwrite behavior. As with other terminal commands, an output write
failure can leave partial output and a nonzero process status.

## Python, MCP and source

The unchanged Python call is:

```python
api.planner_items(start_date="2026-10-08", end_date="2026-10-15")
```

The existing MCP tool remains `canvas_planner_items`. Field and date semantics
follow the official [Canvas Planner API](https://developerdocs.instructure.com/services/canvas/resources/planner).
This addition changes only the CLI parser/dispatch and documentation; the API,
client, authentication, MCP and package bootstrap remain unchanged.

`tests/test_planner_cli.py` runs the actual package CLI against a disposable
loopback HTTP server with synthetic input and an explicit synthetic token. It
checks real native pagination, lossless output, default/empty results, native
error refusal and an unchanged identity command. It requires the project's
declared dependencies and is distinct from the dependency-limited local
fixture receiver recorded under `docs/receiving/planner-cli-e04ee971c817/`.
Neither fixture path demonstrates live school authentication or student outcomes.
