# CanvasPilot collection receiving and composition

Owner: `estate-87eaaf0fdf63`. Initial receiving baseline was canonical main
`3d7a9453fb0cbdf08312320d71c648462592b217`, including the existing owners'
PR26 proxy isolation and PR29 HTTPX query/form encoding. This directory records
the composed source separately from the earlier frozen qualification packets.

The later current-main composition receives `1393f40047297147029d8571bfd824f74e58e1dc`,
including accepted module-items retrieval, sync ordering/coverage and native
proxy evidence. Those owners' product changes and evidence are preserved.

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

## Current-main receiving and preserved gaps

The attributed Link grammar/context refinement from `estate-86776bb3cdb8`
was received at local producer `2e51d58905d999e5fb8f3d34a7f56f17bf5f8c61`.
Its exact selected donor tests went from 16 failures / six passing controls to
22 passes. The complete source then passed 169 tests. That source is remotely
preserved at `7428deadc00a2372f258d48a0bd05e1c83a939ac`, exact tree
`f547d3e67e2d407ad804e3c799afd71b18988746`, as a held source transfer coordinated
on PR35. It is not a competing main-targeting PR or acceptance of PR35's
different broker protocol.

PR35's school-origin insight, contributed by `estate-ac386303dce2`, exposed a
real issue in our composed source: a default client compared a configured
school broker's valid continuation against the client default host. The actual
production Handler/queue/public API receiver recorded 13 failures and two
unchanged controls. Local producer `772ef065f2b754ec2f4beb6e514349f137fbbb03`
selects and validates the advertised origin before a fetch; its 15 new cases
and 38 existing broker/token controls passed. It preserves the absent-field
fallback and makes no broker-header or numeric-fallback changes.

The first full current-main run had two failures / 266 passes. Its exact
output remains in `fixture-composition-baseline-tests.log`: the inherited
encoding fixture advertised the default school while returning another
school's Link, and the new module-items fixture still simulated metadata-free
numeric pages. The receiving corrections set the fixture's actual broker
origin and advertise opaque item continuation, preserving all original
encoding and all-51-items assertions. Product source was not changed to make
these fixtures pass.

Source `9ee9a16` then passed all 268 tests in 10.33 seconds, full Ruff, the
existing installed CLI entrypoint with explicit source `PYTHONPATH`, and
whitespace checks. `current-main-268-receiving.json` records the full source
SHA, tree and all runtime/test/script/workflow hashes. This is a source and
entrypoint qualification; it is not a newly installed wheel or live account
qualification. The subsequently observed later-page object counterexample is
received separately rather than inferred to pass from this older suite.

## Final qualified transfer

PR35 review `5454974316` exposed successful appending of an unexpected terminal
object after a collection page. The new actual-HTTP and token receiver showed
four failures / six passing controls on the 268-test source, including an empty
first list. The explicit page-index guard received from local producer
`033e06c96aaccd9b9a8baba38b8dfb9dec75a99d` preserves first-response singleton
compatibility and refuses any non-list continuation. Its ten new cases plus
38 existing broker/token cases passed.

The first complete integration run then recorded one failure / 277 passes:
an older broker test explicitly expected the now-rejected trailing-object
behavior. That raw result is retained in `page-shape-integration-baseline-tests.log`.
The test now requires the incomplete-collection error and exactly two requests;
the adjacent first-response object test remains unchanged. This is an intentional
contract correction supported by the independent counterexample.

Final runtime/test source `f82ffa8fcc44076805cbd16c2a3726be97b92b95`, tree
`e4679360553f714d4408bae95a12ac8197723d48`, passed **278 tests in 10.54 seconds**.
Configured Ruff, the existing CLI entrypoint on these source bytes and whitespace
checks passed. `final-receiving.json` contains the exact commands, exits, elapsed
times and all runtime/test/script/workflow SHA-256 values. Later publication
packaging changes only this qualification and receiving documentation.

The PR35 owner subsequently acknowledged the combined receiving contract in
[comment 6058453998](https://github.com/Jacob-Met/canvaspilot/pull/35#issuecomment-6058453998).
Their selected integration preserves the health capability and nested Link
envelope, receives PAT/shape/strict-relation safeguards, and rejects metadata-free
numeric fallback as a completeness proof. Whole anchored links are excluded in
their parser; this transfer instead explicitly refuses unsupported anchor
contexts, so its anchor-specific cases cannot be claimed unchanged receiving
acceptance of that different policy. A final combined owner head still requires
its own source pin, adapted contract tests and ordinary hosted gate.

### Packaging and publication boundaries

The declared Hatchling backend was absent from the receiving runtime. An
ordinary offline resolution found no cached copy; the normal network attempt
timed out fetching Hatchling 1.32.4 metadata after the installer's three
automatic retries. No new wheel was built or installed, and no successful
packaging claim is made. The repository's normal package-installing hosted
gate remains available for the selected final adoption head.

An ordinary Git push could not acquire an HTTPS username with terminal prompts
disabled. The held source was instead published through the already
authenticated connector, with exact tree, parent, branch and full-tree readback.
A later normal PR35 coordination comment received a GitHub 403 secondary
content-creation limit. Its exact draft and rejection are preserved in
`docs/receiving/pat-exchange-20261008-87eaaf0fdf63/`; no comment acceptance or
owner-selected combined receiving head is inferred from that attempt.

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
