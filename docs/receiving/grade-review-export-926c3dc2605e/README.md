# Offline course-grade export: native receiving

## Outcome and scope

The contribution adds `canvaspilot export-grade-review COURSE --out NEW.html` as a readable, printable, self-contained view of the existing grade reader's result. The saved file retains each enrollment, reported totals, assignment groups, returned submission context, visibility boundaries, reader warnings and a complete normalized JSON download. It does not recalculate a course grade, choose an enrollment, infer missing work, retrieve hidden values or change Canvas.

Source commit: `ed86b59fd5e619a33a3e99d4c6ea44948fb3c922`.
Source tree: `e946599c811a2e288396139e1abf38ac4adc415b`.
Base: `1bafdaa31f7789d8e561680cb6001bbe38b2da64` (tree `fc4c5cee949a3a15caf32111af9144cb7eb95b6d`).
Native checkout: `/home/jacob/canvaspilot-grade-review-export-926c3dc2605e`.
Branch: `work/926c3dc2605e-grade-review-export`.

The source change is limited to one renderer, one focused test module, one guide, and additive CLI/README entries. The existing API, grade normalization, client, pagination, profiles and other workers' feature scopes remain unchanged. The source's actual receiver is the CanvasPilot CLI and its saved HTML, using the already integrated course-grade reader. At the base commit this export command failed argument parsing without creating output; `baseline-command.*` preserves that observation.

## Qualification

| Boundary | Native evidence | Result |
| --- | --- | --- |
| Repository gate | `pytest-full.log` | 874 passed, 1 skipped, 54 subtests passed in 441.68 seconds |
| Focused export suite | `pytest-first.log` | 9 passed in 42.05 seconds |
| Whole repository lint | `ruff-final.log` | `ruff check src tests scripts` passed |
| Patch whitespace | `diff-check.log` | `git diff --check` passed |
| CLI and real local HTTP | `cli-receipt.json` | Four-GET paginated success; JSON equality; existing file and dangling symlink protected before network; later-page 403 produced no file; invalid course rejected |
| Independent semantic receiving | `independent/receipt.json` | 13 cases and 188 assertions passed through real HTTPX, CanvasClient, CanvasAPI normalization and the export builder |
| Real browser | `browser-receipt.json` | Chrome 153.0.8010.47; 13 checks passed, including desktop/mobile, keyboard disclosures, actual JSON download, closed-detail printing and zero external page requests |
| Final source correspondence | `source-correspondence.json` | Final renderer recreates the browser-qualified HTML bytes exactly from the preserved normalized report and creation time |

The repository suite and independent receiver ran on ThinkPad's existing Python 3.14.4 dependency environment. The repository's configured hosted CI environment was not run by this native receiving. One existing repository test was skipped; no live Canvas account was exercised. All records in this packet are synthetic.

Independent semantic cases keep teacher-first, student and observer enrollments separate; retain zero, negative, over-100, false, null and empty values without arithmetic; preserve list order and drop-rule context; distinguish absent/null/empty collections; withhold hidden/unposted/invisible grade fields; retain unknown and stale-grade applicability; keep hostile markup, control characters and unpaired surrogates inert; and reject restricted access, caller mismatch and invalid visibility. The receiver does not claim CLI or browser qualification; those are separate observed boundaries above.

## Exact-source correspondence

The first focused CLI/browser artifact used renderer SHA-256 `1dc6f8aac7069f0e2506586f03f53b4b30b4d985248519ef392823e838af1b53`. `grade_review_export.pre-format.py` and `format-receipt.json` preserve the formatting transition to renderer `7d8df22447642cb5ac2588b144c18b3b2dde14ab7ca4b7fc085b17d60eb874be`, which the full suite and independent receiver used.

After the full suite finished, seven intended multiline string elements received explicit parentheses to satisfy Ruff's ISC004 rule. The test module's import was wrapped and its intentionally naive datetime rejection was documented. `lint-receipt.json` records byte hashes and identical Python syntax trees before and after each change. No tested behavior changed. Final renderer SHA-256: `0f16c805d57bf9aa8eba09b6bde2afde033bf09fe64b4525adf22de3b248c351`. CLI SHA-256 remained `ecf9ba68b45591df9400932e4e982e84f060937c6d7957316de1e0102533d238`.

The browser receiving harness initially used an incomplete warning phrase and then an incomplete keyboard event sequence. Their failed receipts/logs are retained with `initial-assertion` and `keyboard-probe` suffixes. The accepted run corrected only the harness: it used the actual warning text, focused its isolated browser target, and delivered a complete Enter key sequence. The product needed no behavioral correction.

## Browser artifacts

`synthetic-source.json` contains the fictional HTTP fixture. `synthetic-normalized.json` is the actual reader result. `synthetic-review.html` is the successful CLI output. `downloaded-course-grade-review.json` was obtained by clicking the saved file's real download link; it has exactly the normalized report's values, types and order, and its SHA-256 matches the value displayed in the HTML.

Desktop and assignment screenshots were observed at 1100 × 900; mobile screenshots at 390 × 844. Both had no horizontal overflow. Tab reached the native disclosure summary and Enter opened and closed it. `print-review.pdf` is the actual 10-page browser print result with all details closed before printing; `print-review.txt` confirms the full assignment/submission context was printed. `print-first-page.png` records visual inspection of the printed layout. Desktop, mobile assignment and print images were visually inspected without clipping or unreadable fields.

The browser ran in a private temporary profile and the target blocked all HTTP/HTTPS/WS/WSS resource URLs. Its only observed page request was the local HTML file. No provider resource was contacted and there were no page runtime exceptions. `browser-receiving.mjs` uses Node's built-in WebSocket with local Chromium; no browser package or dependency was installed. Raw browser stderr is retained byte-for-byte as `chromium.log.gz`; `raw-log-binding.json` records its identity and lossless compression.

## Independent packet

The independent receiver is sealed at native path `/home/jacob/canvaspilot-grade-export-independent-926c3dc2605e`, commit `d0058740eb582bfe7f6b69952b63fff88570a0ad`, tree `309a183fcc2379c6e6105c79533fd26b448e9080`. Its manifest SHA-256 is `2ba9815a15e9b6ec69963c97a7477b1604ee4beba6bbb23cc40d50becebe2b67`. All 43 manifest leaves were received and hash-verified before packaging.

`independent/evidence.tar.gz` preserves that complete packet, including its frozen production source, fixture server, observations, receipt and manifest. The copied receipt, reader, manifest and explanatory README remain directly reviewable. `independent/archive-binding.json` binds the archive digest to the independent clean commit and the final renderer's AST-equivalence receipt.

## Coordination and integration boundary

`scope.json` is the original external contribution claim. The native coordination record is `/srv/hamon-estate/coord/estate-926c3dc2605e-production-canvas-grade-export.json`. The source was implemented only in this isolated clone. The earlier feedback-export opportunity was relinquished before edits when its existing owner's claim was found; the grade-reader owner had explicitly completed and released the reader scope.

A GitHub issue creation at 17:11:36 UTC returned HTTP 403 with an explicit secondary rate-limit response (request ID `E278:209586:3F1B53:CF26AC:6AC7CEC8`). No hosted creation was retried or routed through another transport. This packet qualifies the source locally and supplies concrete reviewable integration material; it does not claim a hosted PR, hosted CI pass or merged release.
