# Independent Canvas pagination composition qualification

## Disposition

**PASS** for client SHA-256 `d3473b7805908c15b276689abff9dd0dbd8d428e8691d557a26a5b2285444797`, with unchanged broker SHA-256 `749e11c92d6d56d54ccf208dda6784cb2d43ac3b837188f5d82bfe73c3129e8e`.

Reviewer: research_integration, separate from composition author runtime_execution and policy/integration owner root. Recorded 2026-10-08 at 11:31 UTC. This packet qualifies the frozen local composition; publication and integration must bind these exact bytes. It does not claim a live Canvas account, browser session, deployment, full-suite replay, or complete RFC conformance.

## Independent HTTP receiving

The unchanged test `test_composed_receiving.py`, SHA-256 `2846e49c537bd48d9457da4cf8814f2110df6488b1174d5ec21169f1d2218709`, has six methods with 23 boundary/control cases. It uses the production token client constructor with authored HTTPX responses and the real, unchanged broker Handler over local HTTP with authored responses at its browser queue. All credentials and URLs in the tests are synthetic. Ordinary decoded broker requests are exercised through that Handler as a positive control.

| Source | Normal Python | Optimized Python |
| --- | --- | --- |
| PR35 e208 client `21aec589fc27f3a664dd6f844ac0762c496d2e68fa94b3052172f80b046c0d1b` | 15 assertion failures, 2 error escapes, 6 positive cases | Not repeated |
| Frozen composition `d3473b78` | All 6 methods / 23 cases passed | All 6 methods / 23 cases passed |

No skips occurred. The two baseline errors are HTTPX InvalidURL exceptions for a malformed port and a control character, escaping the required pagination error boundary. All raw outcomes are retained; the baseline failure was not rewritten into a successful result.

The independent cases check:

- Applicable continuation is identical whichever side of it contains an anchored foreign target; the entire anchored link is ignored in both transports.
- A missing or malformed relation on a later page cannot turn an accumulated prefix into a complete result.
- A terminal object is retained on the first page, while a later terminal object invalidates the collection in both transports.
- Invalid PAT initial paths are rejected before any HTTP dispatch, including network-path references, fragment/backslash forms, malformed ports and control characters.
- A broker capability of false, the string "true", integer 1, or null cannot establish collection completeness; ordinary decoded requests still work.
- Both transports preserve initial query bytes while adding native HTTPX filter encoding, leave the input filters unchanged, and send the opaque next URL without reapplying those filters.

Interpreter: `/workspace/scratch/ac386303dce2/runtime-execution/canvaspilot-env/bin/python` (Python 3.12.14, HTTPX 0.28.1). Each source ran in a separate process with `-B`, `PYTHONDONTWRITEBYTECODE=1`, and PYTHONPATH bound to this packet's baseline or candidate source capsule; the optimized run added `-O`. Test assertions are unittest methods, so optimized Python does not remove them. The exact baseline/candidate clients and broker/bootstrap source are included.

## Source composition

The new parser body is byte-exact to current [PR37](https://github.com/Jacob-Met/canvaspilot/pull/37) head `857a226d54c9784ca528bccc6ace7b4f02d90f4d`, client SHA-256 `5ab0c0cd579f82b89ace05be6e15b6d38844abe1d8bf6df5b0c35b906d09a1c8`, blob `3751f754348e340563015fbbf13dae48beb0f47e`. This current donor already preserves the owner's whole-anchor-ignore policy. Its older blanket-anchor refusal tests belong to its historical receipt.

Independent named-source comparison confirms the production broker fetch function, ordinary request method, broker Link traversal, configured-origin guard, token HTTP client constructor and other unaffected definitions remain byte-identical to e208. The broker source remains exact. The public pagination error class remains in the client module; its documentation broadens to both transports. Legacy numeric traversal and its private helper are intentionally retired under the root owner's explicit completeness policy. This qualification does not claim the old fallback acceptance still applies; its historical artifacts remain in the composition author's packet.

## PAT history and adopted authority

The exact unpublished PAT history is recoverable from `donors/pat-donor-history.bundle`, 46,354 bytes, SHA-256 `d6ac4960d263b376b4f9717e6711e8e68ebbfa44be7e43ae6be67c373caa7a55`.

The reviewer initialized a separate empty bare repository, fetched only e208 and its ancestry from a local source, verified both donor commit objects were absent, verified the bundle prerequisites, then fetched these two heads:

| Head | Commit | Client SHA-256 |
| --- | --- | --- |
| PAT composition | `2e51d58905d999e5fb8f3d34a7f56f17bf5f8c61` | `02ea5ff157a1fb310b35ed3b41d1fbc5a09a928987cabebd34bbc7cafc830222` |
| PAT increment | `e678faaa4809ac0eddfd17228c1e940d19865217` | `82ac737ec34259b42a1629ab40bddf5d54aaafe17d178cdcf56983ea5c440395` |

The received composition client matches the external owner's read-only checkout bytes. These are legitimate local Git objects, not a claim that the commit IDs exist on GitHub. The author's current GitHub lookup receipt reports 404 for these donor commits; the local bundle supplies the exact continuity.

Both adopted origin/path helper executable ASTs are exact to the recovered donor after function renaming. Only the path helper's docstring and one comment differ; the fixed error text is unchanged. The raw whole-function AST comparison intentionally remains false for that docstring difference, with the bounded executable-body comparison and textual diff recorded separately. The older donor broker envelope is not adopted. The final receiver uses the existing broker envelope and current shared parser, and strengthens the donor's later-page shape behavior to the accepted collection rule.

`independent-bundle-receiving.json` retains exact Git commands, results, received hashes and helper comparisons. `independent-source-preservation.json` retains the definition comparison. The final file manifest binds every included source, test, bundle and receipt.
