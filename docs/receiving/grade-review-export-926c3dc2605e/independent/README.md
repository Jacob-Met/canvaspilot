# CanvasPilot grade export: independent native receiving

Receiver: ChatGPT runtime_execution, session 926c3dc2605e.

Verdict: **qualified for the tested semantic boundary**. Thirteen independent cases passed 188 assertions through the actual CanvasClient HTTPX request path, CanvasAPI grade-review normalization, export builder, and static HTML renderer. All sources are fictional records served from a temporary loopback HTTP server on ThinkPad. No live Canvas account or profile was called, and no producer source was modified.

## Frozen source

Producer checkout: `/home/jacob/canvaspilot-grade-review-export-926c3dc2605e`.

The `source/src` snapshot was copied before receiving and checked unchanged afterward. Renderer SHA-256: `7d8df22447642cb5ac2588b144c18b3b2dde14ab7ca4b7fc085b17d60eb874be`. CLI SHA-256: `ecf9ba68b45591df9400932e4e982e84f060937c6d7957316de1e0102533d238`. This independent run does not exercise CLI argument parsing; the producer owns CLI and real browser/download/print receiving. Future formatting-only source changes require the producer's AST-equivalence receipt.

## Observations

- The rich case retains three separate enrollments with TeacherEnrollment first, then StudentEnrollment and ObserverEnrollment. Each role retains its own reported values. Zero, negative, over-100, empty-string, false, and null values remain distinct without recalculation.
- Assignment groups retain reported order, identities, weights, and drop rules. Assignment grades, scores, attempts, and flags stay attached to the corresponding assignment. Missing, null, and empty assignment/submission collections remain distinguishable.
- Hidden totals, not-posted work, and invisible work do not recover withheld grade values. Unknown applicability and unknown collection completeness remain explicit. Stale reported grades retain the mismatch warning.
- Recursively reversing source dictionary key order leaves the complete generated HTML identical. Arrays retain their supplied order.
- Source text containing HTML/script markup, JavaScript-like URLs, NUL/control characters, and unpaired surrogates remains data. There are no active payload elements, event attributes, or remote resource links. The static data-URL JSON download decodes to the entire actual normalized API report, including exact normalized values and a matching digest.
- Absent, null, and empty enrollment and grading-period collections each have a separate case; the empty-assignment-group case preserves the uncertainty about course completeness.
- Three negative controls reject restricted course access, caller identity mismatch, and invalid assignment visibility data through the actual existing GradeReviewError boundary. Each builder invocation calls grade_review once and produces no export report on these rejected inputs.

## Files and reproduction

`receive_semantics.py` contains the independent fixture server and all assertions. `observations/receipt.json` records 13 cases, 188 checks, source hashes, normalized observations, and HTTP route evidence. Its SHA-256 is `53ab22abc070d028fe01600fff740447a0e251ab17e8e3d2f2f05f6415efb3b4`. The observation directory also contains each successful HTML export and decoded JSON report. `receiving.log` retains the actual native process output; the receiving process exited 0.

Reproduction command, using the existing dependency environment read-only:

```sh
/home/jacob/canvaspilot-announcements-3dcb83a1/.venv/bin/python -B /home/jacob/canvaspilot-grade-export-independent-926c3dc2605e/receive_semantics.py
```

The receiver intentionally pins the renderer hash. Re-executing against a changed producer source must first assess that change and preserve this existing evidence. `MANIFEST.json` hashes every sealed file except itself and Git metadata. This packet is independent receiving evidence; it does not claim live Canvas acceptance, production deployment, browser rendering, printing, or publication.
