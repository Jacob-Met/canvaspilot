# Canvas collection pagination composition

Author/receiver: HAMON contributor `/root/runtime_execution`, workspace
`ac386303dce2`, 2026-10-08. This composition receives the current parser and PAT
contributors into the frozen session-link owner and applies root's explicit
older-broker policy. Root owns independent acceptance and publication.

## Source and contribution identities

| Contribution | Exact identity | Received behavior |
| --- | --- | --- |
| Session-link receiver | `e20890089f6338de655a7c6ea7f0ada6d5c8fe6b`, tree `99814b52eab606219931f504a677246ed1e62eb3` | Existing health capability, `response.headers.link` envelope, configured broker school origin, opaque absolute continuations, whole-anchor exclusion, later-page shape refusal, module-items and sync integrations |
| Original parser supplement | PR37 `dcf1bc02aa490c5e9ac79e3f486d9e2f2e34c2db` | Required valid relation metadata and strict parameter/relation grammar; original source, tests, failures and receiving retained |
| Current owner-compatible parser supplement | PR37 `857a226d54c9784ca528bccc6ace7b4f02d90f4d`, parents `dcf1bc02...` and `e2089008...`; qualified local source `348a42b88c1fcd329be0132519a20d27e933900d` | Exact parser retaining the receiver's whole-anchor exclusion; eight maintained metadata controls; one MIME fixture quoted correctly |
| PAT/completeness donor | `2e51d58905d999e5fb8f3d34a7f56f17bf5f8c61`; original PAT increment `e678faaa4809ac0eddfd17228c1e940d19865217` | Same-origin initial and next URL admission, opaque starting-query preservation, native HTTPX parameter encoding, cycle and forty-page completion guards |
| Root's explicit receiving policy | PR35 coordination comment [6058453998](https://github.com/Jacob-Met/canvaspilot/pull/35#issuecomment-6058453998); immutable two-method probe SHA-256 `e7d779a4fc913dafcc3e1b593e940b66103e3acc94f967d4e06257f74d419852` | An older broker without Link capability raises an actionable incomplete/restart error; ordinary decoded requests remain supported |

The frozen composed `src/canvaspilot/client.py` SHA-256 is
`d3473b7805908c15b276689abff9dd0dbd8d428e8691d557a26a5b2285444797`.
The broker stays at SHA-256
`749e11c92d6d56d54ccf208dda6784cb2d43ac3b837188f5d82bfe73c3129e8e`.

The current parser's Git blob `3751f754348e340563015fbbf13dae48beb0f47e`
was read back from published PR37. Its eighteen newer receiving files were also
fetched by the exact published commit and checked against their Git blob IDs.
The original parser and PAT commits were fetched read-only from their existing
local Git object stores. No donor workspace or published branch was edited.

## Concrete adaptation decisions

The current PR37 parser is received directly. Its `_session_link_next` function
is byte-identical in this composition and is shared by both traversal modes.
An applicable Link requires one valid relation; registered `next` comparison
ignores case. Whole anchored links remain excluded before relation interpretation,
as accepted by the session-link owner. The original donor tests that required
blanket anchor refusal are retained as history; they are not silently treated as
the current policy.

The PAT donor's URL helper is received into the existing client module as
`_token_pagination_path`, with `_origin` renamed `_url_origin`. It retains the
donor's same-origin checks and opaque query handling. The PAT loop retains the
donor's native HTTPX scalar/list/boolean/null parameter encoding, appends initial
filters once without replacing an authored starting query, and never hands a
foreign initial or next target to the authenticated HTTP client. Existing HTTPX
redirect behavior is unchanged.

The PAT donor's `include_response` and top-level `response.link` broker protocol
are not adopted. The receiving broker protocol remains `with_response=True`
plus `response.headers.link`, with the existing advertised capability and the
broker's actual configured school origin. `_get_broker_link_pages`,
`_assert_pagination_origin`, `broker_fetch`, `_ensure_http`, and ordinary
`request` are byte-identical to e208. Consequently session continuations retain
their accepted absolute-URL requirement and exact dispatch spelling, while the
PAT donor continues to support same-origin absolute or root-relative inputs.

The donor PAT loop allowed a later terminal object to be appended to an already
read collection. The receiver's stronger page-index rule is applied to PAT too:
later objects, scalars and JSON null raise an incomplete-collection error. A
first terminal single-resource response retains its convention. A malformed or
non-JSON PAT page produces `CanvasPaginationError` rather than exposing a JSON
decoder exception as an unclassified traversal failure.

The previous older-broker numeric fallback is explicitly replaced by root's
policy. The six legacy numeric-fallback tests and the owner's short-page
compatibility method are preserved byte-for-byte in the historical inputs. They
are removed from active collection acceptance because they assert behavior that
the new policy forbids, including successful truncation after forty pages. The
root's new two-method policy probe is included, with its exact original retained
and replayed independently of the style-normalized maintained copy. The unused
numeric-page helper and old token Link splitter are removed.

Production `api.py`, `cli.py`, `mcp_server.py`, `session_broker.py`, module-items
logic, and sync behavior are unchanged. The existing module-items broker test
used the superseded numeric-only transport fixture. Its fixture now advertises
the current capability, returns `headers.link`, and supplies an opaque second
item-page cursor; its public API result still contains all 51 items across the
same three requests. The original test and the actual failed first full run are
retained. No module-items implementation was weakened to make this pass.

## Native qualification

All test exchanges use authored local HTTP/MockTransport responses and synthetic
tokens. No school account, user credential, existing browser profile, live broker
session, or Canvas mutation was used. Python is 3.12.14, HTTPX 0.28.1, pytest
9.1.1, and Ruff 0.16.10 on the local Linux runtime.

| Probe/gate | Exact e208 beforeimage | Composed source |
| --- | --- | --- |
| PAT donor 26 cases, current parser 8 cases, exact root policy 2 cases | 25 failed, 11 controls passed | All 36 pass in the focused/full run |
| Eleven additional PAT receiving boundaries | 9 failed, 2 controls passed | All 11 pass |
| Assembled focused suite | See two preserved negative logs | 47 passed in 1.46 s |
| First full run before module-fixture adaptation | — | 246 passed, 1 stale-fixture failure, 1 optional browser skip, 6 subtests passed |
| Final complete repository suite | e208's prior complete receipt remains unchanged | **247 passed, 1 optional browser skip, 6 subtests passed in 10.41 s** |
| Exact original root policy probe, separately replayed | Original failing policy receipt retained | **2 passed** |
| Ruff over source, tests and scripts | Prior receiving records retained | Passed |
| Maintained source/test/API-doc whitespace gate | Prior receiving records retained | Passed |

The eleven additional boundaries cover later JSON object/scalar/null bodies,
malformed or non-JSON later bodies, PAT anchor exclusion with and without an
applicable next link, and byte-preserved initial opaque query plus filters.
The PAT donor's 26 test bodies are unchanged; only the exception import is adapted
to the receiver's existing public `canvaspilot.client` location. The eight
current PR37 cases are received unchanged. Maintained root/additional test copies
have import/`with` style normalization only; their exact beforeimages remain
available for comparison.

Reproduce from the composed repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider
python -B -m ruff check --no-cache src tests scripts
git diff --check -- README.md docs/API.md src tests
```

`source-preservation.json` identifies every intentionally changed definition and
the seventeen named functions/methods preserved byte-for-byte from e208.
`native-source-binding.json` records the actual imported module paths and hashes.
The original negative outputs, preliminary test-harness import cleanup, stale
module-fixture failure, donor evidence and corrected final output are retained
without rewriting the failed evidence. Historical raw logs include native
whitespace; their bytes are preserved in the lossless publication archive.

## Receiving and publication bounds

The composed production source is frozen while independent cross-transport
receiving runs. Root owns final acceptance, current-head/source reconciliation,
GitHub publication and CI gates. No claim is made here of a merged PR, an updated
installed broker, live school completeness, or a new browser receiving result.
The prior browser qualification remains bound to the unchanged broker source.
