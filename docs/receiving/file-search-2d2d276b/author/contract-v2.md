# CanvasPilot: literal file-name search — frozen receiver contract

## Entry points and source
Base commit: 56a72a2e2cee5ec04671d12ebe5bc2484afb8026
Base tree: a07c3e941219ff80968e1ff20528a63541bb7400
Repository: Jacob-Met/canvaspilot
Native work root: /home/jacob/hamon-ultra-2d2d276b-canvas-file-search
CLI: python -m canvaspilot.cli find-files COURSE_ID [COURSE_ID ...] --text LITERAL
Python: canvaspilot.file_search.find_files(api, course_ids, text)
Preflight: canvaspilot.file_search.validate_request(course_ids, text) returns (canonical_course_ids, unchanged_text).
Existing --base-url, --profile and --token options retain their ordinary meaning. No new credential, transport or output-file option.

## Input admission, before constructing any client
Admit 1–10 unique positive decimal course IDs, each at most20 ASCII digits. CLI values are strings; the Python helper also accepts non-boolean integers. Reject signs, whitespace, non-ASCII digits, zero, booleans, other types and duplicate numeric identities (including01/1); normalize accepted identities to decimal strings while preserving selection order. The sequence must be a list or tuple.
Text must be a string with non-whitespace content and at most512 UTF-8 bytes; reject lone surrogates/encoding failure. Keep all accepted whitespace and code points unchanged. No regex, wildcard, accent folding or Unicode normalization.

## Reads and matching
Call unchanged CanvasAPI.list_files exactly once per selected course, sequentially in selection order. Its existing pagination and error contract stays unchanged. Search its complete returned normalized metadata list in memory; never traverse folders, call course metadata, request a returned URL or download a file.
Apply Python Unicode casefold substring matching independently to display_name and filename. Preserve fixed matched-field order [display_name, filename]. Never concatenate fields or coerce non-string values to text. Empty strings are searchable known-empty values; absent, null and unsupported-type names are unavailable.
Preserve each matching normalized file object, source position and duplicate occurrence exactly. Source positions are1-based within each selected course's normalized list. File and course order remains the returned/requested order; no sorting, deduplication or ranking.
The existing list_files projection exposes only id/display_name/filename/size/updated_at/url/content_type and discards nonobject rows. Therefore counts and retention describe that returned projection, not raw HTTP objects, every remote file, file contents, visible/accessibility state or freshness. The helper may preserve additional JSON fields if an API-compatible caller supplies them.

## Exact successful result shape
{
  "query": <unchanged string>,
  "match_rule": "unicode_casefold_substring",
  "searched_fields": ["display_name", "filename"],
  "source": "CanvasAPI.list_files",
  "content_searched": false,
  "courses": [
    {
      "course_id": <canonical decimal string>,
      "returned_files": <number of returned normalized rows>,
      "searched_files": <rows with at least one string name; empty string counts>,
      "matched_files": <number of matching occurrences>,
      "unavailable_names": [
        {"source_position": <1-based>, "fields": {
          <field name>: <"missing" | "null" | "unsupported_type">
        }}
      ],
      "matches": [
        {"source_position": <1-based>,
         "matched_fields": <ordered matching field names>,
         "file": <complete unchanged normalized row>}
      ]
    }
  ],
  "totals": {
    "courses": <selected count>,
    "returned_files": <sum>,
    "searched_files": <sum>,
    "matched_files": <sum>,
    "rows_with_unavailable_names": <sum of unavailable_names lengths>
  }
}
Only non-string name fields appear in unavailable_names. Keep row order and display_name/filename field order. An empty course gets all zero counts and empty arrays. A course with valid names and no match remains in the result. A row may match one name while the other is explicitly unavailable. No timestamps or nondeterministic metadata are introduced. The helper does not mutate input rows.

## Bounds and errors
Require a list of dictionary rows. At most2000 normalized rows per course, at most5000 across the selection, and at most8MiB of combined UTF-8 JSON row data. The byte sum is each complete row serialized by json.dumps(ensure_ascii=False, allow_nan=False, separators=(",", ":")); list separators/wrapping are excluded. Refuse unsupported JSON values, non-string mapping keys, nonfinite numbers and invalid Unicode. Limits are applied after the unchanged client has decoded a response, not to wire bytes. Do not truncate names, rows or results. If a course exceeds a bound, stop before reading later courses.
Input admission failures: CLI exit2 with argparse stderr and no client construction/request/stdout; helper ValueError.
Read, pagination, schema and budget failures: CLI nonzero(exit1), structured stderr object {ok:false,error:<exception class>,message:<string>}, no partial successful stdout. Helper propagates transport/auth/pagination errors and uses ValueError for admission/schema/budget errors. Complete the whole selection before printing success. Close the client through the existing finally path and restore the caller's exact HTTPX logger level. A failure after earlier courses has no partial success result.
CLI success: one JSON document, ASCII-escaped through json.dumps(indent=2, allow_nan=False), followed by one newline; stderr empty under normal operation. Repeated identical inputs produce identical successful bytes.

## Bounded native qualification
Freeze baseline missing-command/help behavior and exact unchanged source closure before edits. Use the real CLI/API/client with synthetic loopback HTTP and an explicit fake token, private HOME/profile/temp where needed, no live school/browser/model.
Exercise multiple selected courses and later pages; Unicode casefold including non-ASCII and sharp-s; literal punctuation/whitespace; no cross-field matching; duplicates/order; unavailable and empty names; zero/no-match courses; returned hostile URLs treated only as data; argument refusals before effects; whole-result failure on later HTTP, pagination, malformed JSON/schema and budget boundaries; client/log restoration; ordinary existing files command continuity.
Root owns an independently authored consumer oracle and will freeze it before candidate exposure. Preserve original failing witnesses and actual limits. Native code/tests/bundles/delivery stay native. No Actions, source push/PR/merge, service adoption, credentials, installed profile or LA7 effect.

## Revision note
Version2 corrects only the documented Python module entry point after the original native witness showed that canvaspilot has no __main__. Use canvaspilot.cli or the installed console entry point. Version1 and the failed baseline-01 invocation remain preserved. Product source is still untouched.
