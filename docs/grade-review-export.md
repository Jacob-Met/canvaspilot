# Saved course-grade review

Save the same returned grades available through `canvaspilot grade-review` as a readable, printable local file:

```sh
canvaspilot export-grade-review 42 --out course-grades.html
```

Use the existing `--base-url`, `--profile` and `--token` options for the selected Canvas connection. The course ID must be positive. Choose a new output path: existing regular files, directories and symlinks are protected. A failed read or rendering limit creates no successful report; errors are JSON on stderr with a nonzero exit. Success prints the path, creation time, returned-row counts, byte counts and SHA-256 identities on stdout.

Open the saved HTML directly in a browser, including while offline. Each enrollment has its own role/context and supplied totals. Assignment groups retain their returned order, weights and drop rules. Each assignment shows its reported due date, possible points, submission score/grade, attempt and explicit excused/missing/late flags. Expand **All returned assignment and submission fields** for the remaining returned context. The browser's Print command includes that context for paper or PDF.

## Find returned assignments

Use **View returned assignments** to narrow the visible assignment cards in the saved file. **Find returned assignments** matches a literal, case-insensitive substring of the displayed assignment name or its textual ID, ignoring whitespace at the ends of the search. Punctuation is literal; large IDs and leading zeros are not converted to numbers. A missing or empty name uses the displayed `Assignment <id>` fallback.

**Returned group** selects a group by its numbered position in the returned list. Repeated group names remain separate choices. **Canvas reported flag** selects only an explicit `true` for `missing`, `late` or `excused`. A false, null or absent flag, or a missing submission object, does not match. The search, group and flag criteria combine; words such as “missing” in an assignment name do not establish a Canvas flag.

The count reports visible cards out of all returned assignment cards, not course completeness. A no-match message offers a way back. **Reset view** clears all three criteria and restores every card. Opening a card's native disclosure is independent: filters and reset preserve its open or closed state. Group headers, weights, drop rules, unknown/empty-list notices, reported totals and reader warnings remain in place even when a group's cards are hidden.

These controls change only the on-screen view. **Download complete report JSON** always preserves the entire normalized record. Printing includes every returned assignment and closed disclosure content, regardless of the current search or filters; the controls are omitted from print. With JavaScript disabled, the complete report remains readable and the inactive controls are hidden. The controls do not save their state, use browser storage, refresh Canvas or calculate grades.

## Interpreting the values

The export calls the existing `CanvasAPI.grade_review` once and preserves its normalized result. It does not retrieve extra pages, scores or attachment content of its own. The normal reader and its current pagination/error boundaries remain authoritative; its sequential GETs do not create a simultaneous Canvas snapshot.

- Current, final and grading-period totals keep their original field names, with no choice of a preferred enrollment and no recalculated grade, percentage or GPA.
- The grade reader's hidden-course, unposted-submission and assignment-visibility decisions remain intact. A withheld field is not recovered from raw or neighboring data.
- A reported `grade_matches_current_submission=false` receives a visible warning. Absent/null applicability remains unknown.
- Explicit zero, false, empty text, null and not-returned values remain distinct. A missing submission object is not called missing work; the `missing` flag means only what Canvas supplied.
- Group drop rules are context. The report does not select dropped assignments or infer a final-grade contribution.
- Counts cover returned rows. Unknown whole-course completeness and all reader warnings remain visible. Empty lists do not establish the absence of work outside the returned scope.

Course, caller and source fields are the values supplied by the reader. The export does not add an inferred Canvas host or a provider identity that the report did not contain. The UTC creation time records local file generation, not Canvas's observation time. This saved file does not refresh after grades change.

## Portable data and local handling

**Download complete report JSON** retains the complete normalized report, including all fields and list order, without adding grades or rewriting values. This is the report that the grade reader exposes, not the original HTTP response pages. Original source URLs and provider-supplied markup are inert text. One local view script is permitted by its exact content hash; there are no remote assets or Canvas changes.

The file contains course and grade information from the selected authenticated caller. Keep or share it deliberately. The exporter uses the existing exclusive local-file writer and does not publish or upload it. Export limits are 4 MiB of normalized JSON and 16 MiB of complete HTML; an oversized report is refused rather than truncated.

Python callers can use `build_grade_review_report(api, course_id)` to obtain `(html_bytes, receipt)`, or `render_grade_review_report(normalized_report)` to render an already returned normalized review. Both accept an optional timezone-aware `generated_at` for deterministic creation. They return bytes without writing a destination.
