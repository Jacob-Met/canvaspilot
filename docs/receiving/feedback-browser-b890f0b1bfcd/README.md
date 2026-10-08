# Keep returned feedback headings readable on screen and paper

Independent receiver: `estate-b890f0b1bfcd / integration`. Original feature/source owner: `estate-9ec02b70e5f0`, [PR60](https://github.com/Jacob-Met/canvaspilot/pull/60). [Receiving scope and original failure](https://github.com/Jacob-Met/canvaspilot/pull/60#issuecomment-6065554064) were published before this product edit. The exact fixture's criterion label is 254 characters; the original coordination comment's 253-character prose count was an error. Its 194-character unmatched ID and all fixture/source bytes were always exact.

## Result

One existing `h3` rule now includes `overflow-wrap: anywhere`. It wraps a long unbroken returned criterion description or unmatched criterion ID within its existing article, retaining every literal character and the original report structure.

| Actual receiver | Original PR60 source | Exact corrected source |
| --- | --- | --- |
| Ten CLI commands / twenty authored loopback GETs | Pass | Pass |
| Browser checks |43/46 pass; three specified failures |46/46 pass |
| Long-heading document at 1200px |3417px wide |1200px wide |
| Long-heading document at 390px |3380px wide |390px wide |
| Printed complete heading/ID and long comment | Refused by exact text checks;3 pages | Complete;6 pages |
| Automatic page requests | Five local file navigations only | Five local file navigations only |
| Page exceptions | None | None |

The original document's unwrapped headings forced a wide page and caused print scaling/clipping. The corrected PDF keeps its complete 254-character criterion label, 194-character unmatched ID and the full long comment. Both phone captures were inspected, and the corrected PDF's actual rendered second page was inspected. No physical printer is claimed.

The other 43 controls are preserved: requested/returned identity, prior-attempt warning, zero versus unknown/empty values, exact native rubric joins and unmatched feedback, all three independent visibility settings, literal Unicode/markup, explicit assignment-link focus, ordinary desktop/phone presentation, offline reading and original-file preservation. The five pages are `ordinary`, `long-headings`, `points-hidden`, `total-hidden` and `both-hidden`. Their source producer had already shut down before Chromium opened the local documents.

## Exact source and receiving scope

Parent commit: `8c8d3b846f3c80f19ae5f37f9f35adf51ec081fc`; tree: `c2fc27a47a233725b93880587f4e9551b764cfae`.

| `src/canvaspilot/feedback_export.py` | Git blob | SHA256 |
| --- | --- | --- |
| Original |`9cab55d141484309f5511b857957888d7b040dda` |`3b0d685031ec6d9a364200c11bd265fb642e686c5de4d0cb249c041c5a6b177f` |
| Corrected |`b6fd566d132aedc30f1e754dfee4c74e533d910e` |`fb5bff28dbede008512f0738e15c2af56fde5a115e5c66ddb72a2fb05d962bf5` |

[Source proof](source-proof.json) verifies the entire file is exactly the one declaration substitution, function/module AST is unchanged apart from that exact style constant, and the 17 other source inputs remain exact. For all five cases, original/corrected input JSON and native feedback JSON are byte-identical. Each generated HTML differs only by this CSS declaration and its uniquely located capture timestamp. Eighteen source inputs were pinned before/after each producer run.

Corrected native execution used this exact working-tree change atop the pinned parent; the producer's `source_head` field identifies that parent. Its `source-before.json`/`source-after.json` identify the actual corrected bytes. The later publication commit is not relabeled as having executed earlier. Root independently recomputed the whole source substitution and accepted this exact change in [root-review.json](root-review.json).

## Retained evidence

- [Frozen acceptance](BOUNDARY.md), [dependency clarification](BOUNDARY-ADDENDUM.md), [producer](receive_producer.py), and [unchanged actual browser/print receiver](receive_browser.cjs).
- Original [producer receipt](original-producer-v2/producer-result.json), [browser result](original-browser/browser-result.json), [phone capture](original-browser/long-headings-390.png), [PDF](original-browser/long-headings.pdf) and [extracted printed text](original-browser/long-headings-print.txt).
- Corrected [producer receipt](corrected-producer/producer-result.json), [browser result](corrected-browser/browser-result.json), [phone capture](corrected-browser/long-headings-390.png), [PDF](corrected-browser/long-headings.pdf) and [extracted printed text](corrected-browser/long-headings-print.txt).
- [Exact patch](source.patch), [installed private dependency versions](runtime-requirements.txt), and the complete original 94-file [native packet manifest](manifest.json).

The source publication retains this compact selection. The complete6,051,242-byte original 94-file packet remains in the private receiving checkout at `/home/jacob/hamon-b890f0b1bfcd/integration/canvaspilot/docs/receiving/feedback-browser-b890f0b1bfcd`, with original native inputs/commands, all five documents, all desktop/phone captures, all PDFs, browser DOM/results and both original/current source pins. It contains no browser profile or environment binaries. Later root review and this README are outside that original manifest.

The initial producer launch failed before any HTTP request because the isolated environment lacked the package's required MCP import. Its original stderr and partial receipt remain in the full native packet; no product failure or passing command is attributed to that attempt. Installing the project's ordinary declared dependencies in the private environment resolved it. The unchanged producer and browser scripts then completed; no receiver assertions were weakened after the original 43/46 result.

Runtime: ThinkPad Linux as its ordinary user; Python 3.14.4, HTTPX 0.28.1, MCP 2.3.0 and Pydantic 2.14.0 in a private environment; installed Chromium 153.0.8010.47 with Playwright 1.64.0. Browser launch explicitly sets `chromiumSandbox:true` and `--disable-dev-shm-usage`. The frozen script retains the actual local dependency path; another receiver can supply the same dependency at that path or record a path-only adaptation separately.

Replay the producer with `<python> receive_producer.py <source-checkout> <new-output-directory>`, then `node receive_browser.cjs <producer-output> <new-browser-output-directory>`. Existing output directories are refused. The browser receiver requires the installed `pdftotext` and explicitly uses `/snap/bin/chromium`. It writes and compares real PDF bytes and requires no app server after production.

## Integration boundary

This child changes one product declaration and adds receiving evidence. PR60's source owner retains final composition and integration. The original feature's hosted run 37812765374 is historical: 905 tests passed, 1 skipped, 54 subtests and clean Ruff on synthetic merge `a96364c6f04f32cef9ecd011e71e29d85b597a70` / tree `8e1bac9d27b09496b3d4bae993ab598b83f743da`. It is distinct from this child and its pending normal hosted receiving gate.

All responses are authored loopback fixtures. No live Canvas account/course/broker, private learner data, provider call, feedback-read mutation, grading/submission operation, deployment or observed learner benefit is claimed.
