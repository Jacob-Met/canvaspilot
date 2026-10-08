# Current Canvas receiving after sync-summary integration

**The combined rubric and sync-summary source is qualified at the pins below.**
This supplements the earlier author and independent receipts without changing
their source identities, test counts, failures or public outputs.

## Exact current source

Receiving base: `1393f40047297147029d8571bfd824f74e58e1dc`, complete tree
`cb758a4d82431552ab9dc35755c04a12b15b2f2a`. All **63 primary Git blobs**
were fetched or recovered from previously verified identical bytes and checked
before composition. The same six accepted rubric paths are applied: four
existing files and the same two additive test/fixture files. All **59 unowned
current baseline blobs** remain unchanged; the local composed source has 65 files.

| Composed file | SHA-256 | Git blob |
|---|---|---|
| `src/canvaspilot/api.py` | `f113a59bac2cc25f4e9b380be4011add99b115eee3d3b7e4b270fe93afb9a1e8` | `bf7929ff5be89b23a75a880d077149be8c12533d` |
| `src/canvaspilot/cli.py` | `f03046a41118601e81f30baae4e55681223f0088042441bad118a11c883ef7af` | `0337db81791b13386c61f2fcb1c27ed6a97065d6` |
| `src/canvaspilot/mcp_server.py` | `305bfc685976911edb4c45e7047c76bcfb9994193479608e2971501b8604aade` | `4f42a91547a62d642a55dcaf2703d6f84312a5ab` |
| `README.md` | `32466d3db345824b913e5a69b8b19fc7962329a49abccccf486bd210b88c0c59` | `1e6fc524ffdc5e4651b0c8163be07d29a2912f4a` |

The accepted rubric test and fixture remain exactly `cc4bdb56034b32e08a63d4b1ae193e364bfc9b9b4b2a506cf2ef08f43000158c`
and `1c7eebf96e3a09b40b934fab219e9c8b7a6258fe881560f53a1c38a8e1b4bc4b`.

## Composition and preserved failure

Applying the unchanged accepted six-file diff to current main failed its normal
native patch check at the API import block. The raw failure is retained in
`composition-initial.json`. Native three-way merge proposals were clean for the
other five paths; the API proposal had one conflict between current
`from datetime import datetime` and accepted `from copy import deepcopy`.
`api-import-conflict.txt` preserves that original proposal. The composition
retains both imports and the accepted `isfinite` import.

Exact source-span comparison confirms `_brief_rubric`, `get_assignment` and
`assignment_brief` are unchanged from the earlier accepted `e35290d0` API.
Every other current API function/method span is identical. Removing only the
accepted rubric additions and restoring the two original methods also restores
the entire current API AST, so the new sync helpers and deadline logic remain
intact. The CLI and MCP files differ from current main only in their single
accepted rubric-help/description lines. Reversing the accepted README-only
patch restores the exact current README bytes, including its sync documentation.
The complete checks and file mappings are in `composition-final.json`.

## Executed receiving checks

Executed 2026-10-08 10:34 UTC with the existing Python 3.12.14 environment;
no dependency installation was performed. The native repository tests and
the unchanged independent public harness ran on isolated current source.

| Receiving check | Result |
|---|---|
| Complete current baseline suite | **159 pass**, zero failures/errors/skips |
| Complete composed candidate suite | **225 pass**, zero failures/errors/skips |
| Unchanged independent harness on current baseline | 3 passing methods, 17 failing methods, normal and `-O` |
| Unchanged independent harness on composed candidate | **20 passing methods**, normal and `-O` |
| Repository Ruff over `src tests scripts` | Pass, no diagnostics |

The candidate full suite includes every one of the baseline's 159 test IDs and
the same 66 rubric test IDs. The current sync-summary owner's 47 added cases
are preserved. Full native logs and JUnit reports are retained separately.
Every source file in the 63-file baseline and 65-file candidate remained
unchanged before/after all seven subprocess runs.

Each independent run captures 111 actual API/CLI/registered-MCP calls, using the
unchanged `0d4f352f` harness and `b0185efd` fixture. All four newly generated
public-output files are **byte-identical** to their corresponding earlier
independent outputs. Their exact hashes and relative links are recorded in
`verification.json`; the original complete outputs remain at
`../independent-review/`. The new source receipts and full new failure/success
logs are embedded in this supplement's verification JSON. Each baseline still
has 111 failure entries (108 surface subtests plus three direct failures),
belonging to 17 methods; repeated receiving checks are not additional unique
methods. Existing original evidence files are unchanged.

## Replay and scope

The primary input files preserve the exact fetched current sources and tree.
The preparation, composition and receiving scripts preserve the original
commands and local paths; `accepted-rubric.patch` is the unchanged six-file
delta. For portable public-path replay, use the unchanged harness in
`../independent-review/` with `--source` pointing at the composed checkout and
`--output` at a new result directory. The complete native commands, environment
roots and return codes are retained in `verification.json`.

This is current-source integration qualification, not a live Canvas/session or
deployment claim. The rubric JSON semantics and earlier receiving limits remain
unchanged. This worker made no GitHub mutation during this receiving task; the
root integrator owns publication and must preserve any later unrelated changes.
