# Independent CanvasPilot grade-value receiving

**Disposition: APPROVE exact PR50 head `0bbb29a9eb04cca3a3a8b362c891ef6db7607d8e` for the bounded grade-value contract reviewed here.** No production change is requested from this lane.

The source tree is `4d994e2a71009c1b1c245e92ccb0069c57830830`, with parent `ca2318fe7c56d2e4ec1b363ff8a945ab78bf4a0c`. The PR head remained unchanged at final readback. Its receiving contract is the published [grade-review guide](https://github.com/Jacob-Met/canvaspilot/blob/0bbb29a9eb04cca3a3a8b362c891ef6db7607d8e/docs/grade-review.md). Nineteen native source, fixture, test and documentation paths were independently matched to the published Git blobs; all bytes and modes remained unchanged after execution.

## Actual native boundary

The three independently authored unittest methods exercise `CanvasAPI.grade_review`, a real `python -m canvaspilot.cli grade-review` subprocess, and the registered `canvas_grade_review` tool over an actual MCP stdio session. Each uses the owner's unchanged `GradeReviewHTTPFixture` as the terminal HTTP responder, with an independently authored value matrix. The production client, paginator, API, CLI, MCP tool and projection remain in the call path.

Each method receives five scenarios and asserts expected fields, values, types, omissions and counts directly. Entry-point parity is not used as an oracle. Each view traverses exactly four GETs: self-profile, course, assignment groups and the fixture's explicit next page. No other Canvas route is requested.

| Run | Methods | Complete views | GET requests | Failures/errors/skips |
|---|---:|---:|---:|---|
| Normal CPython | 3 | 15 | 60 | 0 / 0 / 0 |
| Optimized CPython | 3 | 15 | 60 | 0 / 0 / 0 |

Runtime: CPython 3.12.14, HTTPX 0.28.1, MCP 2.3.0 and Pydantic 2.13.5, imported from the existing environment. The independent assertions use unittest and remain active with `-O`. The owner's 45-test suite was not repeated.

## Receiving cases and implications

1. **Separate enrollment roles and totals.** A teacher enrollment comes first, followed by active and completed student enrollments. All three rows, role spellings, user-ID representations and enrollment states survive separately. A missing current total, explicit nulls, integer zero, a 105.25 final score, empty grade text and current-period fields keep their own meanings. Unposted and override fields are absent from the output.
2. **Grade values are reported without replacement arithmetic.** A zero-point assignment with a 7.5 extra-credit score remains representable. A genuine integer zero and grade string `"0"` remain distinct types. A prior-attempt score remains beside the false current-submission flag. Group weights of 0 and 150 and the supplied drop rules are retained without normalization.
3. **Explicit withholding survives neighboring scores.** A null posting timestamp suppresses every grade field despite supplied nonzero values. Explicit assignment invisibility also suppresses a supplied zero. Explicit null grade fields remain null when no withholding condition applies; absent grade/posting fields remain absent. Course-level hiding clears all enrollment totals while preserving reported posted assignment values.
4. **Unknown data is not missing work.** An absent submission, null submission and an unsubmitted object without a missing flag do not increment missing-work counts. Only the explicitly true flags count, including overlapping missing/late/excused flags. All eight assignment rows and the resulting counts are checked.
5. **Absent, null and empty containers remain separate.** Enrollment and grading-period state fields distinguish all three forms. Missing/null assignment lists remain unknown, while an empty list remains an observed empty list. No case changes `collection_complete=null` or claims an observed upstream response shape.

## Custody and limits

- Source manifest SHA256: `2f25b493b43dc795a221e4579b8ac542ec459643f15ac5545a13f6b276b894c6`.
- Independent probe SHA256: `8d6010f81176ddc4aa6268d7d1c943132b626de383fd341d10f0f8d1a6a53f21`.
- Child connection/source guard SHA256: `b2f03c4c29cabab0e1a4b031ead256edaf3e9b6aa56f13b56705c8a5c1b73bf3`.
- Normal native receipt SHA256: `f61848d1495b5db75dfd133344935da6d37478c37dde4450ab8764f7e4009fa8`.
- Optimized native receipt SHA256: `a1450b2c33e280ade9a7f555d3e0859fda81654b2b3dabc79bef642765bd6b8e`.

Every child process records its actual loaded source paths and hashes. Audit guards allow socket connections only to the explicitly supplied authored loopback fixture; parent and child receipts report no blocked or other destinations. No profile directory was materialized. Input matrices, full returned reports, CLI/MCP wire observations, request traces, native tool-output chunks and all guards are retained.

This review uses synthetic token authentication to the local fixture. It does not exercise a school account, browser session, real grade, submission, grade write, calendar effect or academic outcome. The separate receiver owns broker identity, malformed visibility, pagination refusal and recovery; its [accepted receiving comment](https://github.com/Jacob-Met/canvaspilot/pull/50#issuecomment-6061557312) remains a separate subject and source of evidence.

The observed head is a draft and may require composition with newer main before integration. Approval here is for the exact frozen source and this value boundary. Current-main composition, the repository's hosted gate and final integration stay with the existing owner/root.

## Reproduce

Use an isolated checkout of the exact head and the existing runtime dependencies. From this packet directory, give the source root, this source manifest, and a fresh output directory:

```sh
python -B test_grade_value_receiving.py /path/to/exact-checkout source-manifest.json /path/to/fresh-normal-output
python -B -O test_grade_value_receiving.py /path/to/exact-checkout source-manifest.json /path/to/fresh-optimized-output
```

Keep `guard/sitecustomize.py` alongside the probe. The runner refuses source drift and existing output directories. Only the synthetic fixture is contacted. The source tree itself is excluded from this compact packet because all inputs are available by immutable repository commit and Git blob.
