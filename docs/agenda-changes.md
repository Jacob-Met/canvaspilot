# Review changes between two saved agendas

A learner can compare two deliberately selected saved course-agenda reports before
planning a study session. The comparison shows changed record fields, unchanged
records, one-sided recorded presence and repeated-ID ambiguity.

First save reports with the existing authenticated reader, choosing the same
courses in the same order and the same inclusive date interval:

~~~sh
canvaspilot agenda 23 61 --start 2026-10-08 --end 2026-10-11 > earlier.json
# At a separately chosen later read:
canvaspilot agenda 23 61 --start 2026-10-08 --end 2026-10-11 > later.json
~~~

Check that each producer command succeeds before retaining its output. These
commands are examples, not automatically performed by the comparison tool.

From a source checkout, the offline command needs only Python 3.11 or newer:

~~~sh
python -B src/canvaspilot/agenda_changes_cli.py --before earlier.json --after later.json
python -B src/canvaspilot/agenda_changes_cli.py --before earlier.json --after later.json --format json
~~~

With CanvasPilot's declared package dependencies already installed, the equivalent
module interface is:

~~~sh
python -B -m canvaspilot.agenda_changes_cli --before earlier.json --after later.json
~~~

The direct-file route imports the new sibling standard-library module. The
package route also executes the existing CanvasPilot package initializer and its
declared dependencies. They are distinct receiving boundaries; a direct-file test
does not establish installed-package acceptance. No dependency is installed or
Canvas account contacted by this consumer.

## Interpret the result

The output schema is canvaspilot.agenda-changes.v1. Each key combines the exact
collection kind, canonical course ID, record-ID JSON type and record-ID value.
Integer 1 and string "1" remain different identities; IDs are never matched by
title, timestamp, source position or an inferred assignment override.

| Classification | Meaning |
| --- | --- |
| unchanged | Exactly one occurrence appears on each side and its full record values agree. |
| changed | Exactly one occurrence appears on each side and at least one top-level record field differs. |
| before_only | A unique key appears only in the caller-selected before document. |
| after_only | A unique key appears only in the caller-selected after document. |
| ambiguous | A key has more than one occurrence on either side. Every occurrence is retained without pairing duplicates. |

One-sided presence does **not** establish that Canvas created or deleted an
object, or that permission changed. Ambiguous groups can have occurrences on only
one side. Counts distinguish key classifications from the complete before/after
occurrence totals.

Each changed field carries either {"state":"missing"} or
{"state":"present","value":...} on each side. Present null, empty string/list,
false and zero remain distinct. Nested values are compared in full and displayed
as complete values of their top-level field, not a guessed deep patch.

Comparison uses explicit recursive decoded-value equality. Object-key order is
ignored; list order and scalar types/values are retained. Integer 1 differs from
floating 1.0, and false differs from zero. Finite floating values use decoded
binary64 semantics, so numerical spelling is not compared and floating signed
zeroes compare equal. Both raw-input byte counts and SHA-256 hashes remain visible.

The document_equal field uses that same decoded-value equality across the full
reports. It can be true while raw file hashes differ because whitespace or
object-key order changed. It can be false when only recorded source positions
moved, while all uniquely matched records remain unchanged. An identical report
containing repeated IDs still produces an ambiguous group; identical documents do
not create a justified per-occurrence correspondence.

Groups follow first occurrence in the before report's original collection/index
order (events, then assignments), followed by previously unseen after keys.
Occurrence arrays retain this order; changed field names use Unicode codepoint
order. Full source reports and every occurrence remain available in JSON.
The default readable text includes all groups, not just changes, and JSON-quotes
artifact text so control characters cannot become terminal formatting.

## Input and failure boundaries

Both complete documents are admitted before a success report is emitted. The
consumer requires exact v1 report fields, identical ordered course/date selections,
valid ISO date bounds, coherent counts, contiguous unique collection indices,
course/context agreement and supplied integer or nonblank string record IDs.
Boolean or floating IDs are refused. Unknown fields inside records are preserved.

Recorded grouping and timing issues remain literal metadata. Structural admission
does not recompute timing or prove that the original producer ran. The tool does
not infer durations, overlaps, recurrence, attendance, grades, availability,
capture time, provider/account identity or complete obligations. The original
producer does not retain host/account/capture identity. Before and after are
caller-assigned document roles; their names do not prove chronology or freshness.

Each input is limited to 8 MiB, 4,096 occurrences and 64 nested containers. Output
is limited to 32 MiB. Exceeding a bound refuses the complete report instead of
silently truncating. These are application bounds, not a whole-process memory
guarantee.

Inputs are strictly decoded UTF-8 JSON: BOMs, duplicate keys and nonfinite numbers
are rejected. The CLI opens only regular-file observations, including a symlink
whose target is a regular file; FIFO/device/directory inputs refuse. Two file reads
are not an atomic snapshot. Their hashes identify the bytes actually read.

Success exits 0 and writes the whole prepared report to stdout. Usage errors exit
2. Input, comparison or stream errors return 1 from main, with a JSON-quoted
diagnostic when stderr remains writable. Actual interpreter cleanup/flush errors
can replace process status, and a failing output stream may have accepted part of
a prepared report. No output destination file is opened, no parent is created and
no input is modified.

## Python API and receiving

~~~python
from canvaspilot.agenda_changes import compare_saved_agendas, render_agenda_changes

report = compare_saved_agendas(before_bytes, after_bytes)
text_bytes = render_agenda_changes(report)
json_bytes = render_agenda_changes(report, format="json")
~~~

The core module itself uses only the standard library; importing it through the
package retains the package's normal import requirements.

Maintained tests cover explicitly authored saved-report cases for scalar types,
missing/null fields, repeated IDs, reordering, malformed later input and ordinary
direct-file CLI delivery. Native receiving additionally consumes exact historical
producer artifacts, distinctly from newly authored derivatives. No live student
data or measured planning benefit is claimed. Source ownership: issue 110.
Existing producer/viewer and overlap consumers are unchanged.
