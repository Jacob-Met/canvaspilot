# Independent receiving: CanvasPilot deadline overview

## Disposition: approve the exact read-only successor

The owner's frozen v1 passes all **12 independent native methods**, with zero
skips. Approve local candidate
`770e289be705414ff305d2b99cec3633085e2356`, tree
`e1ccc4d7a6eb1081092aab59382691a22c090ac5`, against upstream
`874ad9c073fc5bab625e583849dbbe4eaf7fc6af`. The exact 27-file source manifest has
SHA-256 `71af66067300197dedda3e9c619c36cdfd94f261e3f58eca175475a98b017cdb`.

| Changed production path | SHA-256 |
| --- | --- |
| `src/canvaspilot/api.py` | `0446e7ee34942d19cf93461a3f9fa9a43383dce4390b4bd037e94b0f33dff222` |
| `src/canvaspilot/cli.py` | `1af004e5d5e3ca4aa23ac1f4e3f49eae7ab9b290c1f250705e040af9d3421897` |
| `src/canvaspilot/mcp_server.py` | `b765930008d1d1123f351771d6edab182af9228617a3b7a9791103a66ba43452` |

The receiver independently copied and verified every source file, inspected the
six-file diff, then executed only its private copy. The scope is these three
production files plus a sync guide, its README entry and the author's dedicated
tests. All 21 unmodified upstream files remain byte-identical. PR26's client blob
and the full CLI `_session_cmd` byte span are preserved. No implementation
correction or edit to owner source/tests was made by this reviewer.

## Exact source and scope

The original 25-file tree is retained under `baseline/`, archived before the
implementation owner edited it. All 25 file bytes independently match GitHub
Git-tree blob IDs for upstream main
`b0655cfc6f298c956fcdd27fbba32e3c5609516f`, tree
`e343e76039947e15674b098867275ac463ef6a84`. Local snapshot HEAD is
`3fad2392f1283a98ce40e7fc77fb744a3c32b5b1`.

An independent main-ref read found merge PR26 at
`874ad9c073fc5bab625e583849dbbe4eaf7fc6af`, tree
`de36f9d9ac3e8d93083b1ca8fba4ebc8b00fb62e`. Its only source changes are
`client.py` and CLI `_session_cmd`, where session status and shutdown use the
broker request helper. Sync source is unchanged. The implementation owner was
notified to preserve that peer contribution before freezing the successor.
`source-origin.json` records the independent full-tree verification and this
two-file delta; the exact current CLI blob and commit/tree metadata are under
`upstream-874ad9c/`.

The receiving scope is the read-only `CanvasAPI.sync_summary`, CLI `sync`, and
registered MCP `canvas_sync_summary` path. Client authentication, brokers,
profiles, account state, and all Canvas write operations are outside it.

## Original behavior reproduced

Three independent native methods fail on the original source:

| Authored fixture | Original result |
|---|---|
| Eleven returned courses, each with six unsorted deadlines; default limits | Nearer sixth-row deadline is omitted; course rows remain concatenated |
| Equal instants expressed with different offsets and an earlier cross-course deadline | Returned order is not chronological |
| Aware year 0001/9999 timestamps, including offset extremes and adjacent microseconds | Returned order is not chronological |

Exact failure output, source hashes before/after, runtime executable hash,
command, and the original probe/driver bytes are retained under
`evidence/baseline-ordering/`. Production source remained unchanged.

## Independent successor controls passed

`test_independent_sync.py` contains 12 methods using only authored data and the
existing native `CanvasClient` fixture transport. It checks earliest selection
before per-course limits; cross-course ordering; stable equal-instant order;
original `due_at` values and fixture immutability; timezone-naive and malformed
dates; extreme dates without UTC overflow or floating-point precision loss;
default course/assignment limits; selected-course-only fetches; honest returned
and omitted counts; unknown-date counts before selection; empty versus failed
course counts; the original per-course error row; and top-level lookup failure
propagation.

The actual CLI dispatcher delegates explicit limits and closes its client.
The actual registered MCP schema and tool manager expose/delegate both
limits. Invalid limits fail before client/API lookup in the CLI,
programmatic API, registered MCP tool, and direct MCP function. Broker/default
profile lookups and socket connections are guarded, and the fixture transport
retains every request and rejects writes.

`runtime.json` pins Python 3.12.14, MCP 2.3.0, httpx 0.28.1, and Pydantic 2.13.5
from the existing owner-provided dependency environment. No dependency install,
real LMS call, token/profile read, browser action, or Canvas mutation is part of
this review. Counts are qualified as counts of rows returned by the existing
client, not as a complete inventory of Canvas.

`evidence/candidate-v1/receipt.json` records the exact command, interpreter hash,
probe/driver hashes and source hashes before/after. Its stderr retains every
method result and the final `Ran 12 tests` / `OK` result. The authored 47-case
suite and full 106-case owner run are separate evidence and are not included in
this independent 12-method count.

The implementation uses direct aware-datetime comparison, avoiding both UTC
conversion overflow and floating-point timestamp loss. It validates strict
positive integer limits before source lookup, retains the existing selected
course order and per-course error rows, and documents the distinction between
returned-row counts and a full Canvas inventory. This is a bounded qualification
of the offline native API/CLI/MCP receiving path, not a live Canvas deployment or
an authentication/broker qualification.

Replay with the exact candidate and the already configured dependency runtime:

```bash
PYTHONPATH=/absolute/path/to/candidate/src python -B test_independent_sync.py
```

The owner and root retain publication/integration ownership. Existing source
pins and PR26 preservation must carry through any receiving branch; a changed
production successor needs a corresponding review of its changed behavior.
