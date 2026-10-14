# Find assignments in a saved course-grade review

This increment adds local search, returned-group selection and explicit Canvas-flag filters to the existing saved course-grade report. It changes the visible assignment cards without changing the captured grades, group context, reported totals, warnings or complete normalized-JSON download. Hidden-grade and stale-submission decisions remain those of the unchanged reader.

## Open and use the received example

Download the [received fictional report](https://drive.google.com/file/d/1smyjSSATXmVSajg3wbJdqoXMABI1ibkJ/view) and open the HTML in a browser. The same exact file is retained as [mixed.html](independent/candidate-producer-v2/mixed.html). Its SHA-256 is `41e80d2270e2ee3a7e931d7f1cc555010d3c894fb46eb4b9706fdf6777a537c4` (53,421 bytes); the [saved-Drive receipt](independent/saved-drive-receiving.json) records HTTP 200, whole-byte equality and unchanged source custody.

Under **View returned assignments**, search the displayed name or exact textual assignment ID, choose a returned group, or select an explicitly true missing/late/excused flag. The criteria combine. **Reset view** restores all cards and retains any disclosure you opened manually. Repeated group names remain separate by their returned position. Unknown, absent, null and false flags are not treated as true. Search preserves textual IDs, including leading zeros and adjacent identifiers larger than JavaScript's exact-integer range.

**Download complete report JSON** always saves the complete normalized record, including when the visible view is filtered. This is the normalized record used by the renderer, not the original lexical Canvas response pages. With JavaScript disabled the full report remains available. Print media restores every card and the existing disclosure contents. No Canvas account, network request, grade edit or browser storage is required to read this example.

See the [product guide](../../grade-review-export.md) for the existing public renderer and ordinary project test command. [SOURCE.json](SOURCE.json) binds the original and corrected product trees; [MANIFEST.json](MANIFEST.json) binds every retained file here except itself.

## Source and independent receiving boundaries

The original base is `d567702f8a328320dad7d2eac74006cbe15cf0f8`. Corrected product commit `4935fc597956d39886258c39876e4805880d59e6`, tree `74b8d3786ea7fb6b1d9fee73be66adf619ab8817`, changes four paths: one renderer, the new focused test, a narrow existing inert-provider assertion and the guide. All 1,742 unrelated base tuples are preserved. No API/CLI, normalized-reader, dependency, workflow, adjacent comparison or worksheet source changes are included.

The author used CPython 3.12.14 and the documented stdlib-only `render_grade_review_report` function. Context froze its independent fictional normalized inputs and browser criteria before seeing candidate source. The independent producer used CPython 3.12.14; the browser driver used native MSI/Veria Python 3.11.9, Playwright 1.62.0 and Chrome 154.0.8037.97. These are separate producer and browser-driver qualifications, with no Canvas API or credential use.

| Epoch | Actual result | Retained evidence |
| --- | --- | --- |
| Original renderer, initial six author methods | Two passes, two expected failures and two expected absent-control errors | [Raw result](author/original/receiving.json), [stderr](author/original/stderr.txt) |
| First candidate, same six methods | 6/6 pass | [Raw result](author/candidate/receiving.json) |
| Original public producer | 8/8 explicit checks, two pages | [Raw result](independent/original-producer-v1/receiving.json) |
| Original native browser, before candidate exposure | 49/49 checks; two actual complete-JSON downloads | [Raw result](independent/original-browser-receiving.json), [process collection](independent/original-process-result.json) |
| First candidate public producer | 8/8 checks, two pages | [Raw result](independent/candidate-producer-v1/receiving.json) |
| First candidate browser | 19 preceding checks pass, then exact accessible labels fail: actual `[1,0,0]`, expected `[1,1,1]` | [Unchanged failed raw result](independent/candidate-browser-failed-v1.json), [process collection](independent/candidate-v1-process-result.json) |
| Preserved first candidate, new label regression | Six passes and one expected label failure | [Raw result](author/label-baseline/receiving.json), [stderr](author/label-baseline/stderr.txt) |
| Corrected sibling labels, same seven methods | 7/7 pass | [Raw result](author/candidate-v2/receiving.json), [source inverse review](author/label-source-review.json) |
| Corrected public producer | 8/8 checks, two pages | [Raw result](independent/candidate-producer-v2/receiving.json) |
| Corrected candidate's first intake | Two producer checks pass; `KeyError('exporter_blob')` before browser launch, zero downloads | [Failed raw result](independent/native-final/candidate-browser-v2/receiving.json), [process collection](independent/candidate-v2-intake-process-result.json) |
| Corrected envelope, unchanged product/pages/oracle/browser observer | 146/146 checks; three actual complete-JSON downloads | [Final raw result](independent/native-final/candidate-browser-v2b/receiving.json), [process collection](independent/candidate-v2b-process-result.json) |

The first browser finding was a product accessibility issue: wrapping the select inside its label included option text in the accessible label. The correction uses explicit sibling labels with the existing `for`/`id` associations. JavaScript, CSS and data logic did not change. All six older focused method bodies remain exact; the seventh checks those label associations.

The later intake failure was independent receiver metadata: its envelope used `renderer` where the unchanged observer required `exporter_blob`. The [correction record](independent/native-final/candidate-v2-envelope-correction.json) preserves the failed input and binds the corrected envelope. No product, generated page, criterion, observer or producer rerun was needed for that metadata correction. The same browser observer `b90e93fea00faefc842d6539f44989c56341f699` executed all actual browser epochs.

The label-baseline raw receipt retains the historical scope sentence “Six focused” because the original observer was reused; its actual stderr records seven executed methods. The final author observer changes that prose only. Raw receipts are retained without reserialization or backdating.

## What the final browser course establishes

The final course observes sixteen combinations of literal text, returned group and exact true flags, including duplicate group names, leading-zero and adjacent large textual IDs, no-match cases and all three flags. It checks the complete static content against the original, preserves manual disclosure state, exercises native Tab/Enter reset, reads the 390px view, and verifies full content with JavaScript disabled and under print media.

Three actual saved JSON files are included: [filtered mixed view](independent/native-final/candidate-browser-v2b/mixed-filtered.json), [390px mixed view](independent/native-final/candidate-browser-v2b/mixed-390.json) and [hidden-grade report](independent/native-final/candidate-browser-v2b/hidden.json). Each matches the complete normalized payload, and the corresponding original downloads are retained separately. All 146 recorded actual/expected comparisons pass, the complete ten-file staged input inventory is unchanged, and there are four local document requests, no external HTTP requests and no page errors.

The saved [390px image](independent/candidate-mixed-390.png) shows the controls, corrected labels, focus outline and count. The [desktop image](independent/candidate-mixed-desktop.png) shows the preserved capture context, warning and complete-JSON link. These are viewport excerpts, not full-page visual certification. [Visual scope](independent/candidate-visual-review.json) and the [derived source/evidence review](author/final-evidence-review.json) keep those limits explicit.

Managed browser disconnect and Playwright shutdown were observed. Browser operating-system process exit and physical printing were not measured. The inherited pytest module was not executed in the available author runtime because its project pytest/httpx dependencies were absent; its narrow trusted-script assertion delta was reviewed, and the new focused stdlib tests plus actual browser course provide the stated qualification. No older owner's full course was repeated.

## Evidence layout

`author/` retains the four focused test epochs, exact historical six-method witness, executed observers and derived source reviews. `independent/` retains frozen inputs/criteria, the unchanged producer/browser observers, all three pairs of generated HTML pages, raw successful and failed results, metadata correction, process collections, five actual downloads and four screenshots. The saved-Drive receipt is a later delivery check, distinct from browser acceptance. Native transfer/base64 carriers are omitted; their decoded payload bytes are retained and bound by the manifest.

Source publication and ordinary main adoption are separate steps. This record makes no hosted deployment, live Canvas account, changed grade or adjacent-owner adoption claim. Existing comparison and worksheet work remains under its respective owners.
