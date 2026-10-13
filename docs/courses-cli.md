# Read courses and handle expected read failures

`canvaspilot courses` returns the existing active-course list as JSON. It uses
the selected token or session-broker transport and the existing pagination rules.

A successful read exits 0. Course order, the existing projected fields, null
values and the empty-list result are preserved.

For an expected authentication, HTTP or incomplete-pagination failure, the
command exits 1, writes no course list to stdout, and writes one JSON object to
stderr. Its fields are:

- `ok`: `false`.
- `error`: the native exception class, such as `CanvasAuthError`,
  `CanvasPaginationError` or `HTTPStatusError`.
- `message`: the native error message, including available setup guidance.

For example, when neither a token nor a running session broker is available:

```json
{"ok": false, "error": "CanvasAuthError", "message": "No session broker running and no CANVAS_API_TOKEN. Start: canvaspilot session start"}
```

Follow the reported cause before retrying. A read that fails after an earlier
page does not emit the courses accumulated so far or replace the failure with
an empty successful list. The command does not retry requests automatically.

HTTPX informational request logging is suppressed only while this command reads
courses, and its previous logger level is restored afterward. Client cleanup
retains the existing command lifecycle. The Python API still raises its original
exceptions; other CLI commands and authentication behavior are unchanged.

This boundary handles `CanvasAuthError`, `CanvasPaginationError` and
`httpx.HTTPError`. It does not convert unrelated programming or value-validation
errors, or qualify stdout/stderr destination failures.

The maintained tests use synthetic loopback responses through the actual CLI,
including missing setup, authentication failures, HTTP errors, malformed pages,
later-page refusal and successful collection controls. This verifies local
error handling, not a live school login or account operation.
