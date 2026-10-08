# Saved course-grade review

Save the same returned grades available through `canvaspilot grade-review` as a readable, printable local file:

```sh
canvaspilot export-grade-review 42 --out course-grades.html
```

Use the existing `--base-url`, `--profile` and `--token` options for the selected Canvas connection. The course ID must be positive. Choose a new output path: existing regular files, directories and symlinks are protected. A failed read or rendering limit creates no successful report; errors are JSON on stderr with a nonzero exit. Success prints the path, creation time, returned-row counts, byte counts and SHA-256 identities on stdout.

Open the saved HTML directly in a browser, including while offline. Each enrollment has its own role/context and supplied totals. Assignment groups retain their returned order, weights and drop rules. Each assignment shows its reported due date, possible points, submission score/grade, attempt and explicit excused/missing/late flags. Expand **All returned assignment and submission fields** for the remaining returned context. The browser's Print command includes that context for paper or PDF.

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

**Download complete report JSON** retains the complete normalized report, including all fields and list order, without adding grades or rewriting values. This is the report that the grade reader exposes, not the original HTTP response pages. Original source URLs and provider-supplied markup are inert text. The HTML contains no scripts or remote assets and makes no Canvas changes.

The file contains course and grade information from the selected authenticated caller. Keep or share it deliberately. The exporter uses the existing exclusive local-file writer and does not publish or upload it. Export limits are 4 MiB of normalized JSON and 16 MiB of complete HTML; an oversized report is refused rather than truncated.

Python callers can use `build_grade_review_report(api, course_id)` to obtain `(html_bytes, receipt)`, or `render_grade_review_report(normalized_report)` to render an already returned normalized review. Both accept an optional timezone-aware `generated_at` for deterministic creation. They return bytes without writing a destination.
