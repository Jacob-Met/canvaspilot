# Session broker Link pagination qualification

## Scope and source identity

Contributor: ChatGPT HAMON execution, session `ac386303dce2`, runtime execution lane.
Claim: [CanvasPilot issue 33](https://github.com/Jacob-Met/canvaspilot/issues/33).
Receiving source: `Jacob-Met/canvaspilot`, exact baseline
`3d7a9453fb0cbdf08312320d71c648462592b217`, tree
`2b38a186887b7ed5dc5a4020dc26e51636a6ab1f`. This includes the existing broker
query/form encoding and proxy isolation fixes. The current tree contains no
`AGENTS.md`. Auth and separate CI/docs proposals remain outside this claim.

The candidate implements session pagination in the actual Python client and
browser broker. It preserves the default decoded shape of ordinary fetches,
advertises the new protocol through `/health`, forwards only Link metadata, and
follows each server continuation without reconstructing its query. The receiving
origin is the broker's configured Canvas URL, which matters when a caller uses
the default client with a broker started for a school-specific hostname.

`provenance.json` records the frozen production and regression source SHA-256
identities. This is source qualification. No running Canvas broker was upgraded,
no real school account was accessed, and no production usage improvement has
been measured by this packet.

## External contract and demonstrated failure

The primary [Canvas pagination documentation](https://developerdocs.instructure.com/services/canvas/basics/file.pagination)
requires clients to inspect Link even when they request a page size, and to
retain the server's complete opaque continuation URL. It does not promise that
a short response means completion. Header names are case insensitive. The
[original API documentation](https://canvas.instructure.com/doc/api/file.pagination.html)
describes the same contract.

Before editing production source, five tests exercised the real local broker
HTTP handler and public `CanvasAPI.list_assignments`/`CanvasClient` calls. Only
the browser worker was replaced with an authored response provider. On the
baseline, four tests failed and one ordinary-request control passed:

| Case | Baseline result | Required result |
| --- | --- | --- |
| Short first assignment page with opaque next | Returned assignment 1 alone | Return assignments 1, 2 and 3 |
| Full terminal page without next | Invented a numeric request that received HTTP 400 | Return the full terminal page without another request |
| Repeated next URL | Returned the first page as successful completion | Refuse the incomplete traversal |
| Foreign-origin next URL | Returned the first page as successful completion | Refuse the continuation before another browser dispatch |
| Ordinary decoded request | Returned the original object | Preserve that existing shape |

The exact failure output is in `baseline-probe.txt`. The foreign/cycle cases
demonstrate the missing continuation contract; the old broker did not dispatch
the foreign URL in that probe.

## Receiving behavior and checks

The initial HTTP suite has 39 contract cases. It uses a real ephemeral loopback HTTP
server, the production `Handler`, HTTPX transport, and the public Python client.
Cases cover short pages, exact opaque URLs, comma/semicolon cursor punctuation,
quoted Link parameters, repeated includes, Unicode, caller input non-mutation,
broker-configured school origins, malformed metadata, ambiguous continuations,
and rejection before a foreign or malformed URL reaches the browser worker.

Completeness is explicit: exactly 40 terminal pages succeed; a known next after
page 40 raises `CanvasPaginationError`. A later HTTP 401 or 503 raises rather
than returning accumulated pages. A first terminal object remains a one-element
list; a continuing or later non-list page is refused. Brokers without the capability flag keep
the existing numeric fallback and its warning; inherited fallback tests remain
in the suite. The existing encoding test fixture now models the advertised Link
protocol while preserving its repeated-parameter assertions.

From the candidate repository, using an isolated editable Python environment:

```bash
python -m pytest -q
python -m ruff check src tests scripts
```

Results: **114 passed, 1 skipped in 9.83 seconds**, and **all Ruff checks passed**.
The skipped case is the opt-in native Chromium test, separately executed below.
Outputs are `candidate-pytest.txt` and `candidate-ruff.txt`; the actual Python and
installed package versions are in `provenance.json` and `python-environment.txt`.
The editable-install line in the latter names the then-current baseline commit
plus the local worktree; frozen file hashes identify the tested working source.

### Composition with current main

Before publication, main advanced to
`5b1780ca4fcdce3d5f997cee401c86806ece822a`: PR 30 added proxy receiving
evidence and PR 31 added retrieval of omitted module items. The candidate was
composed onto that exact main. Both frozen production file hashes are unchanged;
the new module behavior and evidence remain intact. README changes composed
without a conflict.

One additional real-Handler test exercises the concrete interaction: a short
module page continues through an opaque URL, then the new missing-items fallback
follows its own short item page and opaque URL. The caller receives both modules
and both items with metadata preserved. This makes 40 HTTP contract cases.
The complete combined suite passed **152 tests with one optional local browser
skip in 9.59 seconds**; Ruff passed. Exact outputs are `composition-pytest.txt`
and `composition-ruff.txt`. The publication parent and final test hashes are
recorded in `provenance.json`; the earlier 114-pass receipt is retained above.

### Independent receiving and the narrow successor

Independent receiving reviewed the published head
`89fa86d20e4eff47ce42e18afd8cd8e75ab376c3`, whose client SHA-256 was
`45a60b2c31a3c95914dca9d563958422bc346478a9d70f0058f9c5c623f20ada`.
The original immutable probes and output are under `independent/`; the
[review at that exact head](https://github.com/Jacob-Met/canvaspilot/pull/35#pullrequestreview-5454974316)
identified three receiving defects:

| Boundary | Result on the first published candidate | Successor behavior |
| --- | --- | --- |
| Registered `next` relation written as `NEXT`, `NeXt`, or `prev NEXT` | Silently stopped after the first page | Compare decoded relation tokens case-insensitively |
| A Link value with an `anchor` for another resource | Followed the other course, or treated its next as ambiguous with the applicable next | Ignore the entire anchored Link value before choosing the current collection's continuation |
| A terminal second page containing an object, HTML, or empty text | Appended that value to the collected rows and reported success | Refuse non-list values after collection traversal has begun |

The first two decisions follow the registered-relation and alternate-context
rules in [RFC 8288, sections 2.1.1 and 3.2](https://www.rfc-editor.org/rfc/rfc8288.html).
This application does not implement alternate anchor contexts. It retains its
existing stricter ambiguity and Canvas-origin checks; this packet does not claim
a general-purpose implementation of every Link-header feature.

The client-only correction is frozen at SHA-256
`21aec589fc27f3a664dd6f844ac0762c496d2e68fa94b3052172f80b046c0d1b`.
The production broker and native browser probe are byte-identical to the
previously qualified versions. The independent first-terminal-object control
continues to pass, preserving single-resource compatibility.

Before the successor freeze, main advanced to
`1393f40047297147029d8571bfd824f74e58e1dc` with the independently received
sync deadline overview. Its API, CLI, MCP, documentation and tests were merged
without a conflict; it did not change either pagination production file.
The complete composed suite passes **207 tests and 6 subtests**, with one
optional local Chromium skip. Ruff passes. Exact final output is retained in
`successor-pytest.txt` and `successor-ruff.txt`.

Both independent probes remain byte-for-byte under `independent/`, together
with their negative logs and original source pins. Their eight methods are also
collected in the ordinary test suite. Those two CI copies differ only in import
ordering, an equivalent combined context-manager statement, and explicit default
bindings for loop values captured by a synchronous test callback. The original
copies ran successfully before this lint normalization; that full-suite output
and the initial lint refusal are retained as `successor-prelint-pytest.txt` and
`receiving-probe-lint-before.txt`. The normalized copies were then replayed in
the final complete suite. `provenance.json` distinguishes both sets of hashes.

The independent probe can be replayed without modifying its bytes:

```bash
PYTHONPATH=src python -B -m unittest discover \
  -s docs/qualification/session-links-ac386303dce2/independent \
  -p 'test_*_receiving.py' -v
```

The immutable eight-method receiving replay and hosted checks on the final
published successor remain the independent integration gate.

## Real browser boundary

The optional `tests/test_browser_link_metadata.py` extracts the exact production
in-page fetch expression from `session_broker.py` and executes it in native
Chromium. It uses a fresh temporary profile and an authored loopback provider.
The provider sets an HttpOnly fixture cookie, returns a mixed-case Link header,
and adds unrelated response headers and a second fixture cookie. The test
checks the actual JSON/status, that the browser sends the fixture session
cookie, and that the caller receives precisely the Link header metadata.

On `hamon-thinkpad`, existing Chromium `153.0.8010.47 snap` ran the same test
against the original and frozen candidate expressions:

| Production expression | Result |
| --- | --- |
| Baseline broker `2a106130c344aefebb23b078cd93b5d3ca3afd7f5325ae5fac2fb8a7251780cc` | One expected failure: JSON/status were valid but Link metadata was absent |
| Candidate broker `749e11c92d6d56d54ccf208dda6784cb2d43ac3b837188f5d82bfe73c3129e8e` | One pass, including cookie and header-isolation assertions |

Exact outputs are `native-legacy-browser.txt` and `native-candidate-browser.txt`.
The test hash is
`e7bb134adebdaaf9fda596f79b853d0c42bd42ff9aafb4958c1e07a6a0de90d3`.
The native command used these settings, varying only the source file:

```bash
CANVASPILOT_CHROMIUM_BIN=/usr/bin/chromium-browser \
CANVASPILOT_CHROMIUM_PROFILE_ROOT=/home/jacob/snap/chromium/common \
CANVASPILOT_BROKER_SOURCE=/dev/shm/hamon-canvas-links-ac386303dce2/candidate-session_broker.py \
python3 -B /dev/shm/hamon-canvas-links-ac386303dce2/test_browser_link_metadata.py
```

The profile-root setting allows the existing confined Chromium package to read
its own temporary profile; it does not select an existing profile. The test
cleans up its process group, server and temporary profile. It skips only when
`CANVASPILOT_CHROMIUM_BIN` is absent; an explicitly empty or invalid executable
fails. The native check proves the production fetch expression and the HTTP
suite proves its receiving boundary. This is not an end-to-end school login or
a qualification of Playwright browser startup.

## Negative evidence and refinements

The initial HTTP probe preceded production edits. Later author self-review
identified two meaningful parser risks before the source freeze:

1. Reusing the existing token-mode helper split a valid opaque URL at a raw
   comma and could silently stop pagination. Two punctuation probes failed,
   while the semicolon control passed. HTTPX 0.28.1's parsed Link helper was also
   inspected: it retained commas but truncated a raw semicolon in a URL. The
   candidate therefore uses a session-specific parser that distinguishes URL
   brackets and quoted parameters; the existing token-mode helper is unchanged.
2. The first custom parser accepted an unterminated quoted relation through its
   unquoted-value alternative and treated the page as terminal. The new malformed
   quote probe produced one failure with 38 other contract cases passing. The
   unquoted alternative now excludes quote/backslash characters; the final full
   suite above includes that unchanged rejection assertion. These intermediate
   observations are recorded here as an author narrative, not reconstructed raw
   execution logs.

An attempted local Playwright Chromium download failed with a truncated/invalid
archive and installer lock error. The installed ThinkPad Playwright Python
package also lacked its expected system Node driver. Neither runtime was
repaired globally. The existing native Chromium binary provided the actual
browser execution proof with the portable opt-in test.

## Integration gate

Publish this exact source with its receipts, obtain bounded independent review,
and qualify the exact PR head through the repository's existing checks. Any
composition with a changed main must preserve the encoding/proxy changes and
replay the affected contract suite. Running older brokers retain the documented
fallback until restarted through their existing operator procedure. This packet
does not authorize or assert a live broker restart or any Canvas write.
