# Folder browser composed with current broker parameter encoding

Canvaspilot main advanced while the preceding broker composition was being
packaged. PR29 changed broker query/form encoding in `client.py`, moved imports
in `scripts/readonly_sweep.py` and added sixteen encoding tests. This receiving
stage preserves all three landed files and tests the folder feature against
that exact current client.

| Identity | Value |
| --- | --- |
| Current base | `3d7a9453fb0cbdf08312320d71c648462592b217` |
| Base tree | `2b38a186887b7ed5dc5a4020dc26e51636a6ab1f` |
| Composed source tree | `9bf3697e5d577227caeb3117d1b4d7cbc96772ab` |
| Previous received source | `b098eed93b0d26ac876b0282edccaa194069ce89` |
| Original independent review | `fbc99e88b46328072ab8eaab23023b9b17dd1898` |

All nine feature files are byte-identical to the prior received composition.
The broker client, sweep script and new encoding tests are inherited exactly
from current main. The recorded source tree contains 30 tracked files before
adding the publication evidence.

## Native receiving result

- **108/108 pytest cases passed**, zero failures/errors/skips. This includes the
  33 folder cases, 59 earlier inherited cases and sixteen newly landed broker
  encoding cases. Actual public CLI/MCP/API and read-only broker paths run in the
  folder suite.
- **12/12 native broker/public CLI hostile-proxy controls passed**, including the
  direct-network positive control, explicit read-only/authentication refusals
  and actual disposable broker shutdown. The native fixture exited zero.
- **Ruff passed** across source, tests and scripts.
- **All 30 native source files were checked after tests** against their byte
  counts, SHA256 hashes and Git blob IDs. All source hashes in the proxy receipt
  match the same manifest.

`full-suite.xml`, `proxy-receipt.json`, `runtime-receipt.json` and
`process-receipt.json` preserve the exact received observations and process
completions. No original author, independent-review or preceding composition
receipt is overwritten or relabelled as this run.

## Reproduce

Use the [preceding composition's reconstruction and execution instructions](../broker-composition/README.md),
substituting the current base above, this directory's `candidate.patch` and
`source-manifest.json`, and a fresh output directory. Verify all 30 source files.
The patch still changes only the nine folder-feature files against current main.
Run the full pytest suite and the same two exact broker receiving helper scripts;
their SHA256 pins remain recorded in this runtime receipt. Expected counts are
108 pytest cases and twelve proxy controls, with zero skips or failures.

The unchanged Python 3.12.8, HTTPX 0.28.1, MCP 2.3.0, Pydantic 2.13.5,
pytest 8.4.2 and Ruff 0.16.10 runtime was used read-only on macOS 26.6.2 arm64.
All API responses, proxy traps, worker jobs and profiles were authored disposable
fixtures. No live Canvas account, provider, normal browser, deployed broker or
file download was used. This is receiving of the exact composed source, not a
production-installation or live-permission claim.
