# Read the configured identity and handle expected read failures

`canvaspilot whoami` reads the existing user-profile endpoint through the selected
token or session-broker transport. The existing `--base-url`, `--profile` and
`--token` options remain available.

A successful read exits 0 and writes the existing JSON object to stdout:
`mode`, `base_url` and the native `profile` value. Supplied profile fields and
unknown fields remain intact. The client also permits a text response or an empty
body; those remain a string or null profile respectively. This command does not
add profile-schema validation or infer that a returned value proves identity.

An expected authentication, HTTP or malformed-JSON read failure exits 1, writes
no identity result to stdout and writes one JSON diagnostic to stderr:

- `ok`: `false`.
- `error`: the actual native exception class.
- `message`: the complete native error message, including available setup guidance.

For example, missing token/broker setup produces:

```json
{"ok": false, "error": "CanvasAuthError", "message": "No session broker running and no CANVAS_API_TOKEN. Start: canvaspilot session start"}
```

Other observed classes include `HTTPStatusError`, `RemoteProtocolError` and
`JSONDecodeError`. The command does not replace a refused read with an empty
successful identity, retry the request or change authentication.

HTTPX informational logging is suppressed only during this read, and the actual
previous logger level is restored afterward. Existing client cleanup remains in
place. The Python API, client transport and other commands retain their behavior.

The boundary catches only `CanvasAuthError`, `httpx.HTTPError` and
`json.JSONDecodeError`. Unrelated `ValueError`, `UnicodeDecodeError` and programming
failures still propagate. Stdout/stderr destination failures are not qualified.

Maintained tests and native receiving use disposable synthetic loopback responses
and explicit uncreated profile paths. They cover successful object/text/null
profiles, the observed failures, logger restoration and client lifetime.
This is local command qualification, not a school login or live-account result.
