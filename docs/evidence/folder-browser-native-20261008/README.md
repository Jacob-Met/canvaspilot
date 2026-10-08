# Course-folder navigation: source and receiving

Canvaspilot can start at a course's root, select a child folder and read bounded
pages of child-folder and file metadata through the public API, CLI and MCP.
The course context and selected folder identity are checked before the two
folder-ID child endpoints are used. The feature excludes file bodies and access
URLs; empty pages and source counts do not imply a complete inventory.

```sh
canvaspilot browse-files 42 --per-page 20
canvaspilot browse-files 42 --folder-id 110 --files-page 2 --per-page 20
```

The MCP tool is `canvas_browse_files`; Python callers use `CanvasAPI.browse_files`.
The existing `files` command and `list_files` behavior are unchanged. Public
examples, exact arguments, response semantics and official Canvas references
are in [the feature documentation](../../folder-browser.md).

## Exact receiving stages

| Stage | Source identity | Result |
| --- | --- | --- |
| Author receiving | Base `b0655cfc6f298c956fcdd27fbba32e3c5609516f`, source tree `fbc99e88b46328072ab8eaab23023b9b17dd1898` | 33 new cases, 92 total pytest cases and Ruff passed; all 29 source files verified |
| Independent review | Same exact `fbc99e88` source, no source edits | Seven independently authored methods passed normally and seven under `-O`, zero skips; actual CLI/MCP child optimization propagated; no unresolved finding in scope |
| Merged-broker composition | Base `874ad9c073fc5bab625e583849dbbe4eaf7fc6af`, source tree `b098eed93b0d26ac876b0282edccaa194069ce89` | All 92 pytest cases, twelve hostile-proxy native broker/public CLI controls and Ruff passed; all 29 composed source files reverified |
| Current encoding composition | Base `3d7a9453fb0cbdf08312320d71c648462592b217`, source tree `9bf3697e5d577227caeb3117d1b4d7cbc96772ab` | All 108 pytest cases, twelve hostile-proxy controls and Ruff passed; all 30 current source files reverified |

The first composition preserved merged PR26's proxy handling: 27 reviewed files
remained byte-identical, with the inherited client fix and composed CLI as the
only differences. Main then landed PR29's parameter encoding and sixteen tests.
The final composition preserves those changes too; all nine folder-feature files
remain byte-identical to the preceding composition. The current client, broker
implementation, session CLI helpers and landed encoding tests remain inherited.

The tree IDs above identify source before this evidence directory is added.
The publication manifest records every shipped feature and evidence file;
receipts keep their original source pins and are not relabelled as later runs.

## Reproduction packets

- [Author receiving](author/README.md) includes its source patch, source and
  runtime manifests, exact JUnit/process output and pinned dependencies.
- [Independent review](independent/README.md) includes the separately authored
  HTTP/broker fixture and seven methods, original normal/optimized logs, exact
  request/job/MCP observations and source checks before and after execution.
- [Merged-broker composition](broker-composition/README.md) preserves the first
  merge composition, its patch, source/runtime pins, repeated 92-case JUnit
  result and twelve native proxy-control observations.
- [Current encoding composition](encoding-composition/README.md) includes the
  final patch against current main, all 30 source pins, the 108-case JUnit result
  and repeated native proxy controls after the parameter-encoding merge.

All receiving uses authored loopback metadata, fresh temporary paths and native
public clients or servers. No live Canvas course, account, provider, normal
browser, file download or deployed broker was used. These are source and native
fixture qualifications; they do not establish live account permission or
production installation. No captured source or dependency tree is shipped.
