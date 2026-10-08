# Read your Canvas enrollments from the CLI

Use `canvaspilot enrollments` to read the current user's enrollment collection
through the existing `CanvasAPI.list_enrollments()` method. The command makes
that Python and MCP capability available from the terminal.

## Usage and state filter

From an installed checkout with its existing session broker or PAT:

```bash
canvaspilot enrollments
canvaspilot enrollments --state completed
canvaspilot enrollments --state=
```

The common `--base-url`, `--profile` and `--token` options use the same
configuration as other CanvasPilot reads. Follow the project's existing
authentication setup before reading enrollment data.

| CLI input | Initial native request |
|---|---|
| No `--state` | Sends the existing API default, `state[]=active` |
| `--state completed` | Sends that exact string as `state[]` |
| `--state=` | Omits `state[]`, preserving the API's empty-string behavior |

The CLI forwards a supplied state unchanged. It does not invent an `all` value,
restrict the API to a local list of choices, or trim or split the string. Canvas
determines the meaning of the supplied or omitted filter. `--state` requires an
argument; `enrollments --help` describes the option without connecting to Canvas.
Use the `--state=` spelling for an explicitly empty filter so shells that drop
separate empty arguments pass the intended value to the command.

## Returned JSON

Standard output contains the complete list returned by the native client. An
empty successful result is `[]`. Rows stay in their returned order, with all
fields retained, including role and enrollment state, supplied grades,
observed-user metadata and future fields. Zero, `false`, `null` and missing
fields remain distinct. Literal text and markup remain data in the JSON output.
The command does not calculate a course grade or infer a state from a missing
field. It preserves the existing client's response-shape conventions.

The existing client handles authentication and Link pagination. The state
filter is sent on the first request; subsequent native continuation URLs are
followed as supplied within the client's existing checks and limits. The
command prints the collection only after the read returns. Detected auth,
HTTP, pagination and JSON read errors exit with status 1, a structured error
object on standard error, and no partial success list on standard output.
Invalid CLI options retain argparse's status 2. As with other terminal output,
a failed output write can leave partial bytes and a nonzero exit status.

This is a read through `/api/v1/users/self/enrollments`. It does not accept an
invitation or change an enrollment, role or grade. Use ordinary shell
redirection if you want to save the JSON; its normal file overwrite rules apply.

## Python, MCP and verification

The existing Python method remains `api.list_enrollments(state="active")` and
the existing MCP tool remains `canvas_list_enrollments`. Their implementation,
the client, authentication and package setup are unchanged by this CLI addition.

`tests/test_enrollments_cli.py` runs the actual CLI in separate processes against
a disposable loopback HTTP server, using synthetic rows and an explicit
synthetic token. It checks native pagination and query forwarding, complete
output, default and empty state handling, read errors, parser admission and an
existing identity-command control. These local checks do not demonstrate live
school authentication or the completeness of a school's enrollment data.
