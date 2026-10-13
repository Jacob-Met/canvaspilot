# Compare two saved syllabus sources

Use this offline command when you have two explicit source-text downloads and want to review what changed in their saved bytes. It shows changed line occurrences with three unchanged context lines, preserves line-ending distinctions, and binds each input to a SHA-256 hash. The output is a plain UTF-8 text file that you can open in a text editor or share alongside the original inputs.

A source difference is not a finding that an instructor changed a policy. Markup, whitespace, a byte-order mark (BOM), or a final newline can change even when the rendered reading appears similar. The command does not parse HTML, identify a course, authenticate a download, assess grades, or contact Canvas.

## Save the inputs, then compare

The [syllabus reading packet](syllabus-packet.md) offers a `course-ID-syllabus-source.txt` download for each supplied syllabus body. That download retains the supplied UTF-8 bytes; its reading preview may normalize presentation. An empty supplied body has a zero-byte download. An absent or null body has no source download and must not be replaced with an invented empty file.

Explicitly save the two source downloads you intend to compare under separate names. Record their course/capture context yourself if needed. The command accepts any admitted source-text file, so selecting it is not evidence that Canvas produced it or that both files belong to the same course. Select the downloaded source text, not the complete packet HTML.

From this repository's root, with Python 3.11 or later:

```sh
python src/canvaspilot/syllabus_source_compare.py before-source.txt after-source.txt --out syllabus-source-review.txt
```

The primary direct-file command uses only Python's standard library. It does not require credentials, a configuration file, an installed CanvasPilot package, or an internet connection. The output parent directory must already exist. Choose a new output path on every run; the command never replaces an existing file, directory, or symlink.

For an already installed CanvasPilot environment, the optional package route is:

```sh
python -m canvaspilot.syllabus_source_compare before-source.txt after-source.txt --out syllabus-source-review.txt
```

That route first executes CanvasPilot's existing package initializer, which imports its existing API/bundle/client and declared third-party dependencies. The small standalone source handoff and independent file receiving qualify the direct-file route. No package initializer, dependency declaration, main CLI, exporter, search parser, or workflow was changed to make it work.

## Read the report

The header reports the explicitly supplied before/after path labels, byte lengths, SHA-256 hashes, source-line counts, leading-BOM flags and counts of `LF`, `CRLF`, `CR`, and `NONE` endings. The result is exactly one of:

- `Result: source bytes are identical.`
- `Result: source bytes differ.`

Equality means the selected bytes match. It does not establish origin, authenticity, current policy, capture time or course identity. The report contains the changed regions and context; it is not a complete archive. Preserve both original files because omitted unchanged lines are not embedded in the report.

Each hunk has before/after ranges using zero-based, end-exclusive source-line positions. Inside it, `B` and `A` labels instead use one-based **original occurrences** in the before and after files:

```text
Hunk 1: before [0, 2); after [0, 2)
  B1 A1 "<h1>Syllabus</h1>" ending=LF
- B2 "Read chapter 1." ending=NONE
+ A2 "Read chapter 1." ending=LF
```

This example reports a final-newline change. `NONE` means the original occurrence had no line terminator. An empty line's text is `""`; its ending remains explicit. Replacement rows show the before occurrences first, then after occurrences. Repeated equal lines retain their own occurrence positions. The selected alignment is deterministic for the qualified implementation/runtime, but is not claimed to be the unique or smallest edit explanation.

Quoted text is a reversible JSON string literal. Ordinary Unicode, such as `é` or `雪`, remains readable. Quotes, backslashes, C0/DEL/C1 controls, Unicode format characters (including BOM and bidi marks), and U+2028/U+2029 use escapes. Astral format characters use valid JSON surrogate pairs. This lets you distinguish source characters without putting their terminal control sequences into the text report. Path labels use the same convention. The intended reader is a plain-text editor; arbitrary applications may reinterpret markup-looking source strings differently.

The formatter uses Python's Unicode category database. Repeated calls with the same admitted bytes, labels and implementation/runtime produce the same report bytes; cross-version Unicode-database behavior is not promised to be byte-identical.

## Admission and cost limits

Each selected input must be a regular file, with at most **512 KiB** and **4096 physical source lines**. An explicitly selected symlink is refused, including one pointing to a regular file. Parent-directory symlinks follow ordinary filesystem resolution; this is not a containment feature. A FIFO, device or directory is not consumed as source text.

The 512 KiB limit matches the reading packet's per-body source limit. The 4096-line limit is an additional bound on this comparator's alignment work; some valid packet downloads may exceed it. Exactly either limit is admitted. Empty bytes are valid and have zero lines.

UTF-8 decoding is strict. A BOM is retained, not stripped. Only LF, CRLF and lone CR delimit physical lines. NEL, U+2028 and U+2029 remain characters inside a line. A terminator at end of file does not create a phantom empty final line. No trimming, case folding, Unicode normalization, entity decoding or HTML processing occurs.

Alignment uses standard-library `difflib.SequenceMatcher` over exact `(text, ending)` tokens with `autojunk=False`, then `get_grouped_opcodes(n=3)`. This preserves repeated-line comparisons without a character-level diff. Repetitive admitted inputs can take longer than short ones; the authored course records a 4096-line changed-repetition timing as a local observation, not a latency guarantee. The fully constructed report is limited to 32 MiB and is refused rather than truncated if that limit is exceeded.

Regular-file identity, size and modification time are checked around the bounded read. Observable changes are refused. The inputs are captured separately: the command does not promise an atomic two-file snapshot or detection of every possible concurrent mutation.

## Safe publication and receipts

After both inputs and the complete report are admitted, the command writes a private adjacent staging file using a short fixed prefix, flushes/closes it, and exclusively hard-links it into the requested destination. It does not fall back to overwriting if hard links are unsupported or another writer occupies the destination during work. Input aliases and hard links to input files are protected by the existing-destination rule. No parent directory is created.

Ordinary success exits `0` and emits one ASCII-escaped JSON object plus LF to stdout. Its exact keys are:

```text
ok, schema, output, status, before, after, hunks, report_bytes, warnings
```

`schema` is `canvaspilot.syllabus-source-comparison.v1`; `output` is the supplied output argument string; `before` and `after` each contain `bytes`, `sha256`, and `lines`. `warnings` is normally empty. The report is UTF-8 even when the receipt is printed through a legacy redirected stream.

With functioning streams, a pre-publication operational refusal exits `1`, produces no stdout, and emits this stderr envelope:

```json
{"ok":false,"error":{"kind":"input","message":"before: source is not valid UTF-8"}}
```

The message wording depends on the failure; `input` covers file/read/symlink, size, UTF-8 and line-count admission. `comparison` covers report construction or report-size refusal. `output` covers staging, publication and receipt delivery. Argument syntax errors retain argparse's normal usage behavior and exit `2`.

A successfully published report remains saved if staging cleanup fails; the success receipt includes a warning identifying that outcome. If receipt writing or flushing fails after publication, the command preserves the report, exits `1`, and attempts an output-error diagnostic saying `report published; receipt undelivered`. Stdout can then be partial. A failure of stderr itself cannot guarantee delivery of a diagnostic. Handled operational stream faults are `OSError` and `UnicodeError`. Closed, absent, replaced or custom streams raising other exception types, and argparse's own stream failures, are outside this envelope.

## Pure API

Importing this file directly exposes:

```python
compare_sources(before: bytes, after: bytes) -> dict
quote_display(value: str) -> str
```

`compare_sources` performs no I/O or clock access. It requires actual `bytes` and raises `TypeError` or `ValueError` for admission failures. Its result has exactly `schema`, `status`, `context_lines`, `before`, `after`, and `hunks`. Each side's metadata contains `bytes`, `sha256`, `lines`, `leading_bom`, and `endings` (the four ending counts).

Each hunk contains `before_start`, `before_end`, `after_start`, `after_end`, and `operations`. Each operation has those same four ranges plus `tag`, `before_lines`, and `after_lines`; tags are `equal`, `replace`, `delete`, or `insert`. The line arrays contain exact `{text, ending}` records in original order, with no normalization or deduplication. Ranges are zero-based and end-exclusive. API strings remain literal; `quote_display` supplies the reversible human presentation separately.

## Qualification and scope

The public v2 contract was reserved in [issue 163](https://github.com/Jacob-Met/canvaspilot/issues/163) before implementation. It is anchored in the unchanged reading-packet guide/exporter at `36130bd6ef01681f276de8b7d8bb4649f6f59b7f`. An independent original-only witness executed that exporter with a local fictional API and extracted generated base64 download data. It verified empty/missing/null and control/BOM/line-ending/Unicode distinctions. This was generated-packet byte evidence, not a physical browser download or a live Canvas response.

Focused author tests run directly with the standard library:

```sh
python -B -E -S tests/test_syllabus_source_compare.py -v
python -B -E -S -O tests/test_syllabus_source_compare.py -v
```

Nine methods passed in each course. Each includes three actual direct-file CLI children, with one explicitly optimized `-O` child; `-E` means those children do not rely on inherited `PYTHONOPTIMIZE`. Focused in-process injections cover a competing destination, partial staging-write failure, post-publication cleanup warning, and both receipt-write and receipt-flush failure. Real regular-file/symlink/FIFO selection, an observable source change, a long output basename, admission boundaries and repetitive alignment are also covered. These are bounded authored tests, not a full repository suite. A separate focused actual child was then run with stdout bound to a real read-only file descriptor: it preserved the published report, inputs and source, exited `1` (not interpreter-shutdown status `120`), and delivered one honest output-error JSON diagnostic without a traceback. This one-child descriptor check is separate from the two nine-method authored courses and the independent counts below.

Two independent expectations were frozen before candidate exposure. The semantic course passed 11 exact API cases, eight reversible display cases and four refusal cases, totaling 51 grouped checks and zero product CLI executions. The real-file consumer course passed 11 actual direct-file CLI children and 64 checks, including a true optimized repeat, literal source rows, exact limits, refusal envelopes and source/input/prior-report preservation. Its generated report was also read by eye for the source-only notices, metadata and occurrence ranges. These courses executed in the cloud Python runtime, not on a native installed application or in a browser.

Only the new module, focused test and this guide belong to the product increment. Existing exporter #65 and live phrase-search #99 retain their source and ownership. No HTML interpretation, live-provider request, institutional policy conclusion, account access, package installation or broad cross-platform guarantee is part of this qualification.
