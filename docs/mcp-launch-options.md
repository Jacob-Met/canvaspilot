# Canvas connection options for the MCP server

`canvaspilot mcp` uses the same connection options as the other CanvasPilot
commands. Explicit options reach the client used by every MCP tool during that
server invocation:

```sh
canvaspilot mcp --base-url https://canvas.example.edu --profile ./canvas-profile
```

`--token TOKEN` is also supported. Omitted values retain the normal client
defaults: `CANVAS_BASE_URL`, `CANVAS_API_TOKEN` and `CANVAS_PROFILE`, with the
client's existing fallback behavior. An explicitly empty token (`--token ''`)
disables an environment token, as it does for other commands. Token whitespace
and trailing URL slashes keep the client's existing normalization. Profile
paths are passed as paths without creating a directory or logging in.

The launcher creates one client for the MCP server invocation. Tools share that
client, which closes when the server returns or raises an error. Starting the
server itself performs no Canvas request. It does not change the process's
connection environment. A prior in-process MCP API binding is restored after
the invocation; it is not closed by this launcher.

The direct Python `canvaspilot.mcp_server.main()` entry point still accepts no
arguments and uses the usual defaults. It also accepts keyword-only `base_url`,
`token` and `profile` (`pathlib.Path`) overrides. The direct module entry point
`python -m canvaspilot.mcp_server` continues to use environment configuration;
use `canvaspilot mcp` for command-line options.

## Receiving

`tests/test_mcp_launch.py` covers each option, omitted and empty values, relative
profile paths, unchanged environment, parser refusal, actual tool dispatch,
normal/error cleanup and restoration of a prior API binding. The separate
receiving record also exercises the actual Python CLI and MCP stdio handshake
and tool call against an owned local HTTP server with synthetic credentials.

These checks establish source behavior. They do not qualify a live Canvas
account, an installed native session, broker authentication or a school profile.
The client, transport, auth precedence, pagination and MCP tool bodies retain
their existing behavior.
