# Reviewing assignment lists from the CLI

After the normal token or local-session setup described in the [README](../README.md), run:

```sh
canvaspilot assignments 0042
canvaspilot assignments 0042 --bucket=
canvaspilot assignments 0042 --bucket past
canvaspilot assignments --help
```

A completed read prints the existing indented JSON assignment list to stdout and exits 0. The course identifier is passed through as supplied; `0042` remains a string. The default bucket is `upcoming`. An explicitly empty `--bucket=` removes the bucket filter, and other nonempty values are passed to the client unchanged.

The command retains the API's compact assignment projection, order, repeated entries, submission fields, and submission warnings. It does not include every arbitrary provider field or the full assignment description. Valid attempt 0, false flags, and supplied nulls retain their native meanings; an invalid submission field is omitted with its existing warning. Pagination completes before the command prints a list.

## Expected read failures

Authentication or setup errors, pagination errors, and HTTP transport/status errors exit 1, leave stdout empty, and print one JSON object to stderr:

```json
{"ok": false, "error": "CanvasAuthError", "message": "The native error message"}
```

The `error` value is the actual exception class and `message` is its full native message. This boundary handles `CanvasAuthError`, `CanvasPaginationError`, and `httpx.HTTPError` subclasses. A failure on a later page does not print the assignments accumulated from earlier pages. Routine HTTPX request logs are suppressed during the read, then the previous logger level is restored.

Argparse retains its ordinary help and argument-refusal behavior. Unrelated value, projection, or programming errors are not reclassified. This change does not qualify stdout/stderr destination failures, validate course identifiers or bucket values, change transport/authentication/pagination, retry requests, or establish live-account acceptance.

The maintained tests use synthetic loopback responses and disposable, uncreated profiles. The native receiving record separates successful output parity, expected read refusals, lifecycle checks, and the limits of the Windows test environment.
