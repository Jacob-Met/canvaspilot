# Compare two recorded page revisions

Create a readable offline report from two explicit revision IDs:

```sh
canvaspilot compare-page-revisions 42 'week-one' --before 7 --after 9 --out week-one-7-vs-9.html
```

Use your existing CanvasPilot connection options and an account already allowed to edit the page. Canvas requires those rights to read revisions. This command performs exactly two sequential revision GETs, requesting content for the selected Before and After IDs. It never reverts or updates a page. It does not list history, choose the latest revision, download attachments, or inspect a current page.

Before and After are the direction you choose, not a claim about time. Both IDs must be explicit positive ASCII decimal numbers through 9223372036854775807 and canonically distinct; for example, `01` and `1` are the same ID and are refused. The current page locator is used literally for both reads. A historic title or URL is retained as an observation, not used to relocate a page. Two GETs are not an atomic historical snapshot.

## Read the report

Open the new HTML file in a browser. It has no executable JavaScript, external assets, forms, storage, or automatic network requests.

- Before and After cards show whether each body is absent, null, empty, or text, together with the original reader's cleaned text.
- The raw-body table retains CRLF, CR, LF, and missing final newlines. Each row is a complete quoted JSON line literal; other Unicode separators remain inside their line. Delete and insert rows have text labels as well as color.
- The complete-envelope disclosures retain every returned field, including unknown nested metadata, the original revision ID representation, and a server field named `body_text`. The reader's separate cleaned projection is preserved without recomputation.
- **Download complete comparison JSON** saves the full report in one explicit action. It is UTF-8 JSON with two-space indentation and one final LF. It is normalized reader data, not a copy of the original HTTP bytes or original JSON numeric spelling.
- Keyboard users can open each disclosure and activate the download link. Printing includes the visible comparison and cleaned text; full source disclosures and the download control are omitted. Keep the HTML or JSON for the complete source records.

Raw equality compares only two supplied string bodies. Cleaned-text equality compares only their inherited reader projections. Both comparisons are unavailable when either body is absent or null. Equal bodies do not establish matching attachments, rendering, permissions, authorship, or semantic meaning. Empty strings are comparable and contain zero lines.

## Bounded comparison and protected output

The command admits ordinary finite JSON only, with at most 64 nested container levels and 100,000 expanded values per envelope. Each compact envelope is at most 1 MiB and each raw body at most 512 KiB. The complete HTML is capped at 8 MiB. Invalid data, mismatched returned revision IDs, permission failures, or a failed second GET produce no report.

Line comparison runs only when the combined line count is at most 2,000, combined raw bodies are at most 131,072 UTF-8 bytes, and the two line counts multiply to at most 1,000,000. Above these work bounds, the report explicitly says the line comparison was not computed. Both complete admitted sources, exact equality results and line counts remain available; no partial diff or truncated source is substituted.

Choose a **new** output path in an existing directory. Existing files, directories, and dangling symlinks are protected. Publication uses CanvasPilot's unchanged complete-byte exclusive writer; unsupported hard links or a competing publisher cause refusal, with no overwrite fallback. A cleanup warning after successful publication remains a success and is reported separately on stdout.

Invalid selectors exit 2 before client construction. Operational failures exit 1 with a JSON error on stderr and no success output. Success prints only the output path, canonical selection, line-comparison status, and any publication cleanup warning. The HTML and explicit JSON download hold the full report.

## Python interface

```python
from canvaspilot.page_revision_comparison import (
    build_page_revision_comparison,
    validate_revision_comparison,
)

selection = validate_revision_comparison(42, "week-one", "007", 9)
html_bytes, report = build_page_revision_comparison(api, 42, "week-one", 7, 9)
```

The builder has no filesystem write and does not modify caller-owned envelopes. It detaches and admits the first response before making the second read. The original reader and create-only writer remain separate, unchanged components.

Qualification uses synthetic read-only fixtures and local browser receiving. It establishes no real-course access, complete history, or live-account behavior.
