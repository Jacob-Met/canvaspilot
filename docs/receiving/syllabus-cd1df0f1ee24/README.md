# Syllabus reading packet — native receiving

This record supports [CanvasPilot issue #65](https://github.com/Jacob-Met/canvaspilot/issues/65). The product entry point is `canvaspilot export-syllabus COURSE_ID... --out NEW_FILE`; see the [user guide](../../syllabus-packet.md).

The existing course reader already returned syllabus HTML. This contribution lets an explicitly selected set of courses be retained as one passive, readable, printable HTML file. It keeps missing, unavailable and explicitly empty bodies distinct; marks resources that remain external; and provides exact UTF-8 source-text downloads. Collection and validation finish before the new destination is published. Existing files, directories and symlinks, including a destination created during collection, are protected.

## Readable evidence

- [Author receipt](author-receipt.json): exact runtime, source versions, commands, native outcomes and corrected lint diagnosis.
- [Independent receipt](independent-receipt.json): frozen fixtures, 29 CLI cases, real browser downloads and the final print acceptance.
- [Current-parent CLI receipt](current-6c4d-cli-receipt.json): bounded native receiving against the later `6c4d5d2e` source.
- [Final payload manifest](payload-manifest.json), [d15 preservation](source-preservation-d15.json), and [publication-parent preservation](publication-parent-preservation.json): the final six product files and the separately recorded static compositions.
- [Lead source review](root-review.json): independent review of the precise implementation and integration boundary.
- [Final three-page print PDF](selected-syllabus-reading-v4.pdf).
- [Desktop capture](normal-course-desktop-v3.png) and [phone capture](normal-course-phone-v3.png) from the qualified browser run. The v4 change affects print only.

All visual artifacts use fictional course fixtures. Their presence is a receiving artifact, not a saved live course.

## What was executed

| Gate | Exact source boundary | Outcome |
| --- | --- | --- |
| Missing-feature controls | Author baseline `a5ce672e`; independent baseline `c744bb5b` | Existing `get_course` succeeds; `export-syllabus` is absent and creates no file. Independent final control set: 2/2. |
| Maintained native tests and lint | v3 on `c744bb5b` | 76 tests pass; Ruff passes with the repository configuration. |
| Independent CLI receiving | Frozen v3, complete 20-file closure on `c744bb5b` | 29/29 cases pass, including exact requests/order, complete refusal, identity/type admission, byte budgets and existing/racing output preservation. |
| Independent native browser | Same v3 closure | 9 bounded groups pass; five actual source-text downloads match exact UTF-8 bytes; zero page HTTP attempts, runtime errors, console errors or dialogs. |
| Visual print inspection | v3 | Rejected: the generated navigation footer occupied a fourth page alone. The original PDF and inspection are preserved. |
| Current-parent native CLI | `6c4d5d2e` composition with the v3 core | Ordered two-course success, later 503 refusal with no output, all 22 inherited command names and six selected help bodies preserved. |
| Print-only successor | v4 on the complete 21-file `6c4d5d2e` closure | Original fixture and adapter make two ordered GETs; complete HTML differs only by timestamp and the two print substitutions. Final PDF has three A4 pages, all visually inspected; course pages 2 and 3 are pixel-identical to v3. |
| Intermediate source composition | `d15de13fb6fa39d3cace04bec0e218b4a2ed2ffd`, tree `a98d1f5ddc7bcd682968bea81f6394cdf8c91a53` | Static proof: remove the same two CLI spans and one README insertion to recover exact parent bytes. The four other payload files remain exact v4. Existing `get_course` source and client blob remain exact. |
| Reviewed source composition | `1bafdaa31f7789d8e561680cb6001bbe38b2da64`, tree `fc4c5cee949a3a15caf32111af9144cb7eb95b6d` | The later module-progress export is preserved by the same exact two CLI and one README insertions. Four other v4 payload files stay exact; all 1,203 other parent leaves are retained by the publication overlay. This is a static integration, not another native run. |
| Publication source composition | `f618c3ed13f191ea58642283c1f9cd45a0c1ca81`, tree `1bcfff90694cdb8358684ada58ff349562244de7` | The later page export is preserved by the same exact insertions. The four other v4 files remain exact, as do API/client/dependencies/workflow. All 1,331 other parent leaves are retained. This subsequent source check does not broaden the lead review or native execution claims. |

The later source composition is not relabeled as another native run. Hosted CI for the published pull request is a separate integration gate; its actual checkout and result belong to the PR record.

The v4 module change adds a class to the generated navigation footer and hides that class in the print stylesheet. Instructor-authored footer text remains printable because source classes are not copied. The guide changes one corresponding sentence. No reader, validation, download or file-publication logic changed after v3 receiving.

## Complete archives

Download and extract each archive into its own new directory. Paths in its internal records are relative to that archive or identify the original native execution directory. The inner independent README links to archive members; this outer index links only to separately committed files.

| Archive | Bytes | Regular members | SHA-256 |
| --- | ---: | ---: | --- |
| [Complete author packet](author-packet-final.tar.gz) | 378,045 | 94 | `286ff6ae97a9fbfd5b2a3ea7c93a9cde2435cfea32be1196957515d474bae077` |
| [Complete independent packet](independent-receiving-v4.tar.gz) | 1,312,437 | 298 | `20701c9700dba5fb26eeade7dfa23992a41bcaf9ff3520058242d08355438fc2` |

The [author archive manifest](author-archive-manifest.json) enumerates its exact source inputs, original negative stages, commands, raw outputs, v3 native qualification, current-parent receiving and print-only delta. The [independent archive manifest](independent-artifact-manifest.json) enumerates its complete source closures, independently frozen fixtures and receivers, raw CLI/browser results, five actual downloads, three captures, both PDFs and all seven rendered page images.

Both completed archives were read back on the native host. Their transferred bytes were independently hashed again before publication, without a local disk copy. The later d15, 1baf and f618 compositions happened after these native archives were sealed and are recorded separately in the payload and preservation records.

## Preserved failures and limits

Earlier source versions and harness failures remain visible. Author v1/v2 preserve the malformed-markup and malformed-URL counterexamples, duplicate-attribute and ordered-list-numbering counterexamples, original lint findings and the correction of an initial ambient-configuration hypothesis. Explicit repository configuration and isolated Ruff still reproduced those installed-runtime rules; the final source fixes passed without changing rule selection.

Independent receiving preserves its initial storage/transport failure, inherited HTTPX stderr calibration, a receiver-edit syntax failure before execution, the v3 footer-only print page, and an initial PDF renderer input failure. These are not counted as final successful gates.

Execution used existing native CPython 3.12.8 and Chrome 154.0.8037.98 with offline fictional HTTPX fixtures. The browser packet attempted no automatic HTTP requests. No live Canvas account, school data, Canvas mutation, browser installation or deployed service is part of this result. A saved packet is a sequential observation and cannot reproduce information present only in linked files, images or frames, or Canvas's separately generated course summary.
