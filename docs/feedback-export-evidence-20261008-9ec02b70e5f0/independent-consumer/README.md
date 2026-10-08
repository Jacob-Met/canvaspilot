# Independent printable feedback receiving review

Seven independently authored consumer methods pass in normal and optimized
Python, with zero failures, errors or skips, on the frozen CanvasPilot feedback
export candidate below. Each mode launches **33 real native CLI processes**
against an authored loopback server and observes **57 GET requests**, including
13 successful exports and eight existing JSON-reader invocations. The twelve
expected refusal commands per mode exit nonzero. These are the same seven
behaviors in two execution modes, not fourteen distinct behaviors.

## Exact source and preserved native behavior

The published receiving parent is
`55fe1e0a3c4ad85e1065f295e49d44722c3be32b`, tree
`7c1bd0a858a3fda82a4d5e69076801ae65a73ea1` in `Jacob-Met/canvaspilot`.
The author manifest contains 26 exact source/document/test files; all were
verified before the independent run and again afterward. Only the 13 necessary
candidate runtime modules and 12 original runtime modules were copied into
the reviewer's private namespace.

| Component | SHA-256 |
|---|---|
| Frozen formatter | `3bc3f44f9d8f682fbf8442fed88e05d6148ecbf889e41c941ce65f067f59904b` |
| Additive CLI | `a29e755832cec76a07178d1afffd245c07b665bc990e8bb99c84cbfdc737bf16` |
| Existing API | `fe147e5d3943e7299f400e7607385a7c8f02a68aeff07f72b3219f5c70c7bb5b` |
| Existing feedback projection | `55454598effea598474a21f67e36d5bc5bea84aaefeefc18e4d8c49804ab9869` |
| Existing client | `6368329745216f473204995c101c912d9070fdd310def150bdbee927f9872de4` |

All eleven existing runtime modules other than the CLI remain byte-identical.
The CLI contains exactly two inserted blocks; removing them reconstructs the
entire original CLI byte for byte. The independent controls compare original
and candidate `feedback` JSON on identical loopback responses, including all
supplied comment/author metadata and unmatched rubric entries. The formatter's
helpers are never used as the consumer's expected-output oracle.

Every successful export and JSON read uses the native `CanvasClient` and
`CanvasAPI.submission_feedback` path: assignment GET, then self-submission GET
with the two existing include values and native `per_page=50`. No `read_status`,
attachment fetch, broker, live account or non-GET request is used. Child
processes receive a literal synthetic token and explicit loopback base URL and
unused private profile path. No existing authentication state is accessed.

## Consumer boundaries

The independent HTML parser reads actual output files, semantic fields,
criterion/comment containers and element/attribute structure.

- **Zero and attempt context:** the separately returned score, grade and
  assignment possible points stay zero. A false applicability flag warns that
  grading preceded the current submission; no numbered prior attempt is
  invented from current attempt seven. Missing flags remain unknown.
- **Unknown versus empty:** absent rubric/settings/comments and explicitly
  empty containers have different visible explanations. A missing score stays
  unknown even when rubric assessments contain numeric points.
- **All eight rubric-flag combinations:** `hide_points` suppresses rubric,
  criterion, rating and unmatched assessment points. `hide_score_total` alone
  suppresses only the supplied rubric total. `hide_outcome_results` does not
  hide returned outcome criteria or feedback. None masks the separately supplied
  submission score, grade or assignment possible points; no grade is computed.
- **Ambiguous joins:** two criteria with the same ID both remain unassessed.
  Their single ambiguous assessment is shown once in the unmatched area, never
  duplicated onto either description.
- **Authorship and literal text:** distinct top-level and nested names/IDs are
  visible, including a nested-only author and an unknown author. Media-only
  comments and supplied attachment names remain represented. Unicode,
  line breaks and literal markup survive. Authored script/image/iframe text
  creates no active elements or event attributes; an unsafe assignment URL
  remains text. This is offline structural consumption, not a browser render.
- **No overwrite:** existing regular files, directories, dangling symlinks and
  FIFOs are refused before reads. A different local writer creates the output
  during the second GET; its bytes win, and temporary publication files are
  cleaned up.
- **Failure boundaries:** authored HTTP 403/503, malformed rubric data,
  contradictory course identity, non-Boolean visibility, invalid JSON and a
  missing output parent produce no partial sheet. HTTP diagnostics are retained
  before the CLI's terminal JSON error; the reviewer does not pretend stderr
  contains only JSON.

The visibility interpretation is independently checked against Instructure's
[rubric association documentation](https://developerdocs.instructure.com/services/canvas/resources/rubrics)
and [Canvas DAP dataset reference](https://developerdocs.instructure.com/services/dap/dataset/dataset-namespaces/dataset-canvas),
specifically the `rubric_associations` fields. The posting behavior of
`hide_outcome_results` is distinct from hiding criterion feedback.

## Minor presentation finding and qualification limit

The frozen formatter emits `<style>+:root` at the start of its stylesheet.
The leading `+` makes that initial root selector invalid. Other rules and the
print root rule remain present, and this issue does not invalidate the semantic
receiving results above. The author confirmed the actual output defect and is
preparing a separately pinned one-character successor. This packet deliberately
retains the original source and does not claim that successor has been tested.
No browser layout, print pagination, school-account behavior or educational
benefit is inferred from this offline review.

## Evidence and replay

`review.json` and the normal/optimized logs summarize the exact runs.
`raw-evidence.tar.gz.base64` preserves every original CLI command, stdout and
stderr stream, authored response, HTTP request record, actual HTML file,
original/candidate runtime source and source map. The archive also includes
the independent probe and support module. `raw-evidence-index.json` names and
hashes every member; the archive was checked against every original member
without extracting source copies.

Verify or extract the lossless packet into a new directory:

```sh
python3 -B unpack_evidence.py
python3 -B unpack_evidence.py --output /path/to/new-review-copy
```

From that extracted copy, use new output directories to run the preserved
native receiver:

```sh
python3 -B verify_feedback_consumption.py --output /path/to/new-normal-run
python3 -B -O verify_feedback_consumption.py --output /path/to/new-optimized-run
```

The observed runtime is Python 3.12.14. Its native HTTPX dependencies were reused
read-only from `/dev/shm/hamon-afe225d6c6be-product/canvas-deps`; the preserved
helper records that path. A replay environment must supply the same native
dependencies there or through the selected Python interpreter's installed
packages. No dependencies, browser profiles or live services were installed.
All 25 copied runtime files match before/after hashes in both modes. No product
source, peer workspace or GitHub state was modified by this reviewer.
