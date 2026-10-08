# Independent receiving: CanvasPilot module progress

**Verdict: qualified source and public-contract correction, with an explicit normalized-reader limit.** Product_work retains publication, hosted CI and integration. No school account, learner data, broker or production installation was used by this review.

## Exact source

| Material | Revision or SHA256 |
|---|---|
| Original feature source | `a8ba4be26d09d287304ca12808a1867483efd040` |
| Initially reviewed current-parent composition | `51609ba3f93d20f69616b357c3c6bee19732dfd4` |
| Original module_progress.py | `42aee00dbc05e37b28942f6022e5eb23516589b7f07289f0d725e1d6c66e51d1` |
| Reviewed provenance correction | `96e4f3d37b4e2e222e30ff34a0bab96bed95b8cd` |
| Corrected module_progress.py | `974ee31925514a2e53b899888302a7fa357e280ab5f2461b754b814473653d99` |
| Final reviewed current-parent composition | `5173b24285e9e3e2dda6b1d8158adea74e03bd52` |
| Current canonical parent | `a03a8637efad8ff22103a0c5018c93f7ecbb7d8d` |
| Current CLI source | `1ce47f131de0152dfd494d7ce51f60cc505051809d5ae9bec0e21fea2176e509` |

Source was frozen through native Git reads as the repository owner. The correction changes the new helper's provenance fields, docstrings/error labels and documentation; twelve of fourteen frozen source/docs/package leaves remain byte-identical. Later calendar integration preserves the corrected helper and other reviewed source. Removing the two exact reviewed module-progress parser/dispatch blocks from the new CLI reproduces its current canonical parent's CLI byte-for-byte. The current tree preserves 284 of 289 parent leaves, changes the five intended shared source/README leaves, and removes none.

## Finding and correction

The new workflow sees CanvasAPI.list_modules(detail=full), not raw HTTP pages. The existing generic paginated reader wraps a non-list JSON page as a one-element list, and the full module reader may replace unusable inline items with a successful fallback. Consequently, a singleton upstream Module or ModuleItem object can become a valid digest. The digest cannot certify the original page's array shape or inspect inline rows already replaced by the reader.

Independent real CLI and registered MCP calls reproduced both singleton cases. Three tests deliberately preserve the original, broader refusal expectation and fail against that expectation. This is retained negative evidence; their expected results were not rewritten. The product owner preserved the reader/client/broker/pagination ownership fence and made the observation boundary explicit:

- `reader_source: "CanvasAPI.list_modules(detail=full)"`
- `upstream_response_shape: "not_observed"`

Documentation and error wording now identify normalized reader data. Shape, identity, parent and duplicate checks apply to the rows reaching that boundary. Raw singleton acceptance is unchanged and openly characterized; this review does not claim that it became a strict upstream admission check.

## Independent receiving results

Five consequential controls passed on the original reviewed composition:

1. A real 40-page CLI read follows the retained Link query through page 40, stops at the inherited cap and leaves collection_complete null.
2. Selecting a module from the first page does not hide a later HTTP 503: the CLI exits 1, emits no partial successful stdout, and ends stderr with the JSON error.
3. The same selected later-page failure through registered MCP remains a tool error and preserves the protocol boundary.
4. Explicit completed, locked and unknown module states take precedence over contradictory local requirement counts or a past unlock date. Unknown requirements remain visible; the completed one-of module has no manufactured outstanding list.
5. Selecting one module does not hide an explicit foreign-course module elsewhere in the returned reader data.

The registered MCP inventory contains 36 tools, including the existing feedback and assignment-brief tools. Progress is annotated read-only. All observed Canvas traffic is GET, no student identity override is sent, source hashes remain unchanged, and no profile is created.

Two additional controls qualified only the changed provenance output on exact correction96e4: a real CLI singleton-module response and a real MCP singleton-item response contain the new markers and otherwise exactly equal their preserved pre-correction projections. Both passed with zero errors or skips. No settled product suite was repeated.

| Evidence | SHA256 |
|---|---|
| Initial CLI/receiver raw log | `20eb88bb72f2e4abeed6cbba8a2a28fb9810754c47f7825142d0b94d252173a7` |
| Initial structured observations | `738d34e8f6db52f902d43b6bb5d401f2daef516dd3d629cdcb7c3d3de2735e2f` |
| Corrected MCP adapter raw log | `b9e5aa52b3142293d6bc56ee0f239dc0d052fca80e72bb22bdc52b2238aa5f43` |
| Corrected MCP wire observations | `760e3b4f0bb6f6d4d116f04274035ff1e21a06f4928482ab0dc46d383ae7298c` |
| New marker receiving raw log | `2bc643e5609b31bd589f1ca5db16cafed132b0665c9e6d0dea5c4f92c1c38340` |
| New marker wire observations | `48a8bc8a181ab16c5278623affc99a2ab91cf1b07ff3a1c5cf419649b2ed1b8c` |
| Independent current-parent preservation | `f0b522db1ef154c680b159236c537555316604ba52060fa88fa8cda868fd5d84` |

## Reviewer adapter correction

The initial two MCP probes stopped before tool calls because the reviewer used camelCase SDK attribute names. This installed SDK exposes snake_case Python attributes and camelCase wire aliases. The corrected adapter uses model_dump(by_alias=True). Only the two blocked MCP probes were rerun. The original adapter, errors and correction note remain; this was not a product source failure.

## Limits and provenance

Primary contract context was checked against the current Instructure Modules reference: https://developerdocs.instructure.com/services/canvas/resources/modules. Tests use independently authored fictional HTTP responses and actual CLI/MCP entrypoints. They establish neither a particular school's permissions nor a live learner's progress. Counts cover returned data; module completion and item availability are not inferred. Existing transport pagination limits remain owned by their original maintainers.

The product owner separately reported its current-parent routing groups, calendar parser and Ruff passing. Those owner results are not represented as independent reruns. This verdict qualifies exact source/provenance behavior and current-parent composition, not hosted CI, merge, deployment or strict raw-response validation.

The immutable manifest covers the packet except itself and the later native conscience-receipt.json. The readable publication copy is /home/jacob/canvaspilot-module-progress-review-58d79b68. The runnable receiver is /srv/hamon-estate/canvaspilot-module-progress-independent-review-58d79b68c9e4. Only this reviewer's own registration and evidence were written; other-owner source and records remain untouched.
