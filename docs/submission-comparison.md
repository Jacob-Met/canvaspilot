# Compare two submitted records

When revising an assignment, use an offline reading report to compare the submitted text, URL and returned file metadata for two records.

First inspect the history returned by Canvas:

```sh
canvaspilot submission-history 71 902
```

Then choose the two records explicitly:

```sh
canvaspilot compare-submissions 71 902 \
  --before history:1 --after current \
  --out revision-comparison.html
```

Open the new HTML file in a browser. It works offline and includes a **Save selected records (.json)** link. Use the browser's print command for a paper copy; expand any exact-source details you want to include before printing. The command uses the same token or session-broker authentication as the existing CLI.

## What the selectors mean

| Selector | Selected record |
| --- | --- |
| `current` | The `current_submission` returned by `submission-history`. |
| `history:1` | The first record in `history.records`, exactly as returned. |
| `history:2` | The second returned record, regardless of its attempt number or timestamp. |

Both `--before` and `--after` are required. Use two different selectors. A history position is a positive decimal number without leading zeroes. `history:0`, `history:01`, signs, spaces and alternative casing are rejected.

The labels **Before** and **After** describe your choices. They do not establish chronology. For example, two records can both report attempt `2`, and the first returned record can have a later timestamp than the second. Selecting `history:1` and `history:2` still selects those two distinct list positions; the report does not sort, deduplicate or merge them.

Missing history remains unavailable. An empty history list has zero selectable positions. An out-of-range position is an error; the command never substitutes another record.

## Read the comparison

The report shows each literal selector alongside its returned attempt, submitted-at, submission-type and identity fields. Supplied non-null course or assignment identities must agree with the requested IDs. Missing identities remain unknown.

**Submitted text** is a reading aid extracted from string body values. It preserves text and paragraph/line boundaries, decodes HTML character references, and shows added/removed lines with explicit markers. It excludes script, style, template and noscript content; it does not reconstruct formatting, images or embedded resources. Image alternative text, when supplied, is shown as text. This extraction is not a browser rendering of the submitted HTML.

The exact body is available under **Inspect exact body source and value states**. If readable text matches while markup differs, the report says so. A body that is omitted, null or another JSON type does not receive text highlighting; its exact returned value remains visible and downloadable.

**Submitted URL** compares the exact returned value. URL spelling, letter case, percent escapes and fragments are retained as inert text. The report neither opens the URL nor treats two different spellings as equivalent.

**Returned attachments** preserves the returned list order and all metadata fields in each entry. **Returned media metadata** displays `media_comment`, `media_comment_id` and `media_comment_type`. Unknown fields remain in the complete selected records. Matching metadata cannot establish that file bytes are equal, that linked files still exist, or that Canvas retained earlier file contents. No attachment or media content is downloaded.

| Returned state | Report label |
| --- | --- |
| Key absent | Omitted — key not returned |
| Explicit JSON `null` | Null — explicitly returned |
| Empty string `""` | Blank string |
| Empty list `[]` | Empty list |
| Empty object `{}` | Empty object |

Values are compared with JSON types intact: `false`, `0` and `"0"` remain distinct. Arrays retain their order. No current grades or top-level comments are joined to a historical record, and no grade calculation is made.

## Keep the exact selected data

The local JSON download contains:

- The requested course and assignment IDs.
- The normalized assignment summary and count of returned history records.
- Both literal selectors and their complete selected record values.

Unknown fields, nested record-local metadata, Unicode text and integer values remain intact. This preserves JSON values, not original HTTP byte formatting. The existing history reader normalizes absent assignment-summary fields to null; the comparison cannot recover their original key presence. Selected submission records retain omitted-versus-null distinctions.

Control characters and directional formatting controls are escaped for visible reading. Their exact values remain in the JSON download. The HTML executes no submitted markup and loads no external images, fonts, URLs or media. Treat this local report as a copy of the selected submission data when deciding where to store or share it.

## Bounds and output behavior

Line highlighting supports at most:

- 2,000 readable lines on each side.
- 250,000 combined readable characters.
- 1,000,000 possible line pairs.

If a changed text pair exceeds a highlighting bound, the complete readable text is shown in both columns and the report explicitly says highlighting was not computed. Text is not truncated. The complete selected-source JSON packet is limited to 2 MiB; a larger packet is refused before a report is published. `submission-history` remains available for inspecting the original returned JSON.

`--out` must name a new file in an existing directory. `.html` is recommended; an existing file, directory or even a dangling symlink is protected. Invalid selectors/IDs and output-path preflight errors occur before the history read. Unavailable history, contradictory identities, read errors and render/size failures leave no report.

The complete report is first written to an owned temporary file in the destination directory and then published without replacement. If another process creates the target during the read or write, that target survives unchanged and the command fails. No submission, grade, comment or Canvas read-state mutation is performed.

Successful output is JSON:

```json
{
  "ok": true,
  "output": "revision-comparison.html",
  "before": "history:1",
  "after": "current",
  "history_records_returned": 3
}
```

Expected errors are JSON on stderr with a nonzero exit. The existing history API is called once; its client performs the established assignment and self-submission GET requests with the existing history/comment include list.
