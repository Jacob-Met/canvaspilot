# Independent receiving: CanvasPilot planner CLI

Reviewer: fourth HAMON branch primary agent, independent of the implementation author.
Observed command date: 2026-10-08T16:52:36.856690+00:00.
Implementation PR: https://github.com/Jacob-Met/canvaspilot/pull/72.

## Outcome and useful boundary

PASS: **9 actual Python child processes, 123 evaluated conditions, zero failed conditions, zero harness errors**. All six before/after source pins remained exact. The command itself completed with exit 0. The original CLI rejects `planner`; the candidate exposes the already existing native planner API through a read-only CLI command.

The frozen run compiles the complete exact CLI and uses the actual native API/client fixture implementation plus its exact helper modules. It uses a bare package namespace because HTTPX and MCP are unavailable in this receiving interpreter. Strict unavailable-HTTPX, broker and network tripwires prohibit silently crossing that limitation. No real Canvas service, school data, profile or credential was used.

This independently qualifies argument flow, native fixture response handling, structured caught errors, logger restoration, closing the native client and refusal before side effects. It does **not** claim real HTTP transport, real package bootstrap, MCP initialization, or live Canvas acceptance. Those boundaries are distinct from the separately recorded hosted package/loopback CI run at https://github.com/Jacob-Met/canvaspilot/actions/runs/37809390738. The final composed PR must pass its own configured hosted gate before integration.

## Counterexamples and controls

- The native baseline parser refuses the new command.
- Offset-bearing dates, including a reversed interval, reach the native API unchanged. Unknown fields, false, null, zero, literal HTML, Japanese text, newline and NUL payload values remain intact.
- An empty start filter follows the native API omission rule while an end filter remains.
- A native terminal scalar zero retains the API's existing collection shape.
- Authentication, pagination, malformed-shape and HTTP-error cases are injected at the existing native client request boundary. They produce the intended structured error and no successful stdout payload.
- A missing parser argument refuses before constructing a client.
- Each applicable case checks exact GET parameters, one client and one close, logger restoration at multiple inherited or explicit levels, no HTTPX INFO contamination, no fixture mutation and no unintended profile/transport/broker effect.

The full per-case observations, child exit codes and all individual boolean decisions are retained in `results.json`; counts are not inferred merely from a zero process exit.

## Source and composition pins

The executed candidate CLI is `df01e112b3c7f525e99b3179176d57497391f16b`, and the API is `cd17584bed618fb4a42d7128d204b2683b889600`. Every complete source byte and exact two-block planner addition is retained in `input.json`. Removing those two additions reproduces native baseline CLI `226f3f7d502dd61ad03c59cd8212289d133a0190`, independently fetched from commit `6c4d5d2e7526cddc1aa6c90bfbef2d1188382ad3`.

Subsequent native grade-review and module-progress export additions are preserved through separate byte comparisons, retained in the two composition proof files. For current native commit `1bafdaa31f7789d8e561680cb6001bbe38b2da64`, removing the same exact planner blocks from composed CLI `99247f6d57c4eda52a99e32683ed8d33c56b8d9b` reproduces native CLI `8d6644d0e1b916ca38a578147db8392a2e92d226` byte for byte. Its native API remains exactly `3ec81dee60bc67d7a80d40b78e85d5c005441b99`. These composition checks do not relabel the earlier fixture run as a current full suite.

## Replay and storage

Use Python 3.12 with the standard library:

```sh
python receive_cli.py input.json > replay-results.json
```

Inspect the JSON verdict, all conditions and source pins; a process exit alone is insufficient. This exported driver differs from the executed inline driver only in its input-loading statement: it reads the same retained payload from the named JSON file.

The actual run used one ordinary unique mode-0700 directory on the existing `/dev` tmpfs. Setup, nine children, full before/after verification, result capture and cleanup occurred inside one bounded parent command. The environment does not preserve that directory across independent executor calls. No temporary path is offered as a durable checkpoint; this Git packet preserves the replay inputs and observed result.

Source-only receiving result. This packet does not install the command, publish school information or claim any live estate adoption.
