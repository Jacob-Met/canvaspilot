# CanvasPilot collection receiving and composition

Owner: `estate-87eaaf0fdf63`. Receiving baseline is canonical main
`3d7a9453fb0cbdf08312320d71c648462592b217`, including the existing owners'
PR26 proxy isolation and PR29 HTTPX query/form encoding. This directory records
the composed source separately from the earlier frozen qualification packets.

## Preserved contributions

| Contribution | Exact source | Disposition |
|---|---|---|
| Existing proxy isolation, PR26 | Main `874ad9c073fc5bab625e583849dbbe4eaf7fc6af` | Preserved in the real broker request helper and CLI callers |
| Existing parameter encoding, PR29 | Head `69314fd04dd1704358d62fe714b7608bba91d241` | Preserved; received into canonical main by its existing owner |
| Initial broker Link implementation | `a6df7758262266a0fae0f045049f46e334c0935c` | Composed with native HTTPX query encoding |
| Historical two-import lint repair | `5b4616b` | Already present through PR29; no duplicate change to the sweep script |
| Independent real broker HTTP receiving | `640bca994bd98f2c4b1759e450ebeda0e0b92dab` | Twelve independently authored controls retained |
| Token collection completion/origin handling | `e678faaa4809ac0eddfd17228c1e940d19865217` | Composed without changing credential acquisition or redirect policy |

The original broker and token qualification directories retain their original
source hashes, successes, counterexamples and disk failures. Statements about
unmodified token code or blocked GitHub writes in those packets describe their
historical snapshots. They do not describe the complete successor tree.

## Necessary receiving adaptations

The query helper now uses PR29's public `httpx.QueryParams` encoder, including
array expansion, boolean/null representation and omission of an empty query.
The PR29 form encoder and JSON-body priority remain intact. Only its old
pagination fixture changed from invented page numbers and missing metadata to
advertised opaque Link URLs; its array-preservation assertions remain. The
other fifteen PR29 tests, including the new malformed-proxy composition case,
retain their authored behavior.

An initial composed run had **27 failing tests and 91 passing tests** because
the authored broker pagination fixture intercepted `httpx.post`, while the
accepted proxy fix calls `_broker_request`. The production HTTP receiver and
encoding tests passed. The repair changes that one fixture's transport hook
and signature, preserving its response decoding and every outcome assertion;
it does not revert the accepted proxy implementation.

After that fixture adaptation, broker composition passed **118 tests** in
8.64 seconds. After adding the token contribution and the newly accepted
PR29 proxy/encoding composition test, source
`0330e6176c300e6ddf4ab76a88d5555fce7e4e26` passed **145 tests** in 8.92 seconds.
These are source-specific intermediate gates, before the separately attributed
peer Link-relation/context refinement.

## Scope and reproduction

The receiving tests use fictional data, synthetic token strings and disposable
HTTP servers or in-memory transports. The browser receipt uses a fresh context
with intercepted requests. They do not access a school, existing browser
profile, student record, submission, provider or write API. The live sweep is
not executed. Source integration is distinct from updating a running broker;
an old broker must restart with the updated package to provide Link metadata.

Run the repository's normal gates with its declared development dependencies:

```sh
PYTHONPATH=src python -m pytest -q
ruff check src tests scripts
git diff --check
```

Shared overlay exhaustion was observed during this execution. Later receiving
runs used an invocation-owned temporary directory, disabled disposable Python
bytecode and disabled pytest's cache. Only owned reproducible outputs were
removed; other workers' source, evidence and environments were preserved.
