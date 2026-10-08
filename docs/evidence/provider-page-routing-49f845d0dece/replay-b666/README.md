# Frozen first broker correction receiving (b666)

This packet preserves the first broker correction as an intermediate result. It is not final browser-routing acceptance.

The exact same companion receiver (SHA256 `4650abbddcc0d74307f66424ec14c2d4d1c6645ce26b5af83d1018d463278a98`) was executed under the existing native Python 3.13.7 project environment against baseline native commit `3e251e5e1de71d56042daa76e2109cdd977b97a6` and candidate native commit `b6661032ca5654e6e672d287b86d99a7fe1e01ee`. All five production hashes were checked before and after each run. The baseline hashes correspond to the published PR45 source at `1748e52ed1533c102e04525f96c3d76d4141d30c`.

## Observed outcomes

| Configured provider / selected page | Baseline | First correction |
| --- | --- | --- |
| A / A | Success, source A and A identity | Same source, UID and assignment URL |
| A / B | Wrong-provider success: report/UID A with assignment URL B | Exit 1, CanvasAuthError with explicit provider mismatch, no Page.evaluate, no calendar |
| B / B | Success, source B and distinct B identity | Same source, UID and assignment URL |

The baseline receiver status is `counterexample_reproduced`; this means the expected defect was observed. The candidate status is `candidate_contract_passed`; this means the narrow three-case contract passed. Both have seven true witness assertions. No profile or temporary calendar was created for the refusal. Raw CLI output, calendars and receipts remain in the sibling `replay-baseline` and `replay-candidate` directories, including original line endings.

## Boundary and remaining blocker

The run used the actual CLI, client/API, Handler, _call, queue, _canvas_page and _run_job, with only the terminal Page object authored. It made no browser, account, credential or external school request. Its Page.evaluate seam checks and records the production expression but does not execute JavaScript.

Independent source review then found that b666 checks `new URL(path, location.href)` but dispatches `fetch(path, opts)`. The latter honors `document.baseURI`, so a foreign HTML base element can dispatch elsewhere before response-origin refusal. This remains an explicit overall blocker and requires the author's guarded absolute-target successor plus actual local-browser receiving. Nothing in these three cases qualifies base-element dispatch, redirects or JavaScript navigation races.

The full-index broker patch and exact candidate pins preserve source custody without duplicating the repository. Apply the patch only to the original broker blob recorded in source-custody.json. The original negative witness and the pre-execution replay checkpoint remain unchanged.
