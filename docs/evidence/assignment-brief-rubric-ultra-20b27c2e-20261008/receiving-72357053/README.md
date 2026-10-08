# Current Canvas receiving with folder browsing

**The rubric contribution is qualified on the current folder-browser source.**
The earlier 55-path packet remains durable at
[`45671d275026d2f042fb5326fb9debe98c884f67`](https://github.com/Jacob-Met/CanvasPilot/commit/45671d275026d2f042fb5326fb9debe98c884f67).
This supplement retains that checkpoint and its evidence identities. The new
composition changes the same four production/documentation files and retains
the same two added rubric test/fixture files. All other 51 paths from that
checkpoint keep their exact blobs.

## Receiving source and composition

Current base: `72357053a1629c349f700030013559fa6d8130f2`; complete primary
Git tree: `919634af69c067e04f391fca84b3071ab8da9159`, **123 leaves**.
The complete applicable native source/test closure and product documentation
were materialized and verified against primary Git blobs: 67 baseline files
and 69 composed files. The 56 newly added, unexecuted owner-evidence leaves
remain referenced by their immutable primary-tree blobs and are preserved by
the Git tree composition. They were not recopied into the local test checkout.

The unchanged accepted six-path delta applies cleanly with native `git apply`;
no manual conflict resolution was needed. Reversing it restores every one of
the 67 materialized current files byte for byte. The three rubric helper/getter/
brief source spans remain identical to the accepted `f113a59b` API. Every other
current API span and its remaining AST structure are unchanged. The current
CLI/MCP source differs only in its accepted rubric-help/description line.
Folder browsing, the bundle inventory, HTTP fixture, folder tests, sync-summary
behavior and product documentation remain intact. Git integration must preserve
all **119 unowned current-base leaves**.

| Composed production file | SHA-256 | Git blob |
|---|---|---|
| `src/canvaspilot/api.py` | `0d69348d2d83c3c0e20ea8505f3f10b66787a751b715c5a2acf0ca33ddc747fe` | `f66138a880543b83997a8ec28488f148d944f274` |
| `src/canvaspilot/cli.py` | `aab6aaf0ac0a8fef9412ec4971e5934556ac3d548e8e8d6597067552b73c55ba` | `ceb33ce3ca1f9754a256684e47ae48e68a40702f` |
| `src/canvaspilot/mcp_server.py` | `2b82e62713d129c5a6c5b1a785f62b9eaa5ee83ab71d67a91b65ed8c4b1a8b16` | `ab823e5457f799c70eec9f294ef655a225215303` |
| `README.md` | `ae19477a68aa0b6ee8ed487cb10fee2be64e968866ae009c91d9f5587859e4d2` | `0df07863945caf49d3c6c2909bf1a4add4a97a39` |

## Results

Executed 2026-10-08 10:59–11:01 UTC in the existing Python 3.12.14 environment,
with no dependency installation. Bytecode and test caches were disabled, and
the receiver used a private temporary directory after the shared overlay filled.

| Check | Result |
|---|---|
| Complete current baseline suite | **192 pass**, zero failures/errors/skips |
| Complete composed candidate suite | **258 pass**, zero failures/errors/skips |
| Unchanged independent receiver on candidate | **20 methods pass**, normal and `-O` |
| Same receiver on current baseline | 3 passing controls and 17 failing methods per mode |
| Repository Ruff over `src tests scripts` | Pass, no diagnostics |
| Materialized source hashes before/after all seven runs | Unchanged |

All 192 baseline test IDs remain in the candidate suite, together with the same
66 rubric cases. This includes the folder-browser owner's 33 cases. The raw
complete-suite output is embedded in `verification.json`; both original JUnit
reports are retained as separate files.

Each independent run again captures 111 actual API/CLI/registered-MCP calls.
All four new public-output files are byte-identical to the corresponding
original files under `../independent-review/`. Their exact hashes and relative
references are retained in the verification JSON; identical output bodies are
not duplicated in this supplement. New individual source receipts, commands,
return codes and complete independent logs are retained. Each baseline has 111
failure entries (108 surface subtests and three direct failures), belonging to
17 methods. Repeated receiving runs are not extra unique methods.

## Replay and limits

From the pinned current base, the included `accepted-rubric.patch` reproduces
the six-path source delta. Run the repository pytest/Ruff commands and the
unchanged public harness from `../independent-review/`, supplying the composed
checkout to `--source` and a new `--output` directory. The composition and
receiving scripts preserve the original orchestration and source checks with
their original local paths; the verification JSON retains the full primary tree,
materialized/deferred source map and exact execution records.

This is source integration qualification. It does not demonstrate a live Canvas
account, SSO, an installed rollout or an end-user outcome. The rubric contract
and earlier receiving limits remain unchanged. This worker made no GitHub write;
the root integrator owns the final branch, PR and exact-head integration.
