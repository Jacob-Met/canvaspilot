# Find course file names

Run `canvaspilot find-files 42 77 --text "lab notes"` to find a literal phrase in the file names returned for explicitly selected courses. The usual --base-url, --token and --profile options remain available. This command prints one JSON report and does not download files or follow their URLs.

Select 1–10 unique positive decimal course IDs. Leading-zero aliases count as the same ID and are refused. Search text must contain a non-whitespace character and fit within 512 UTF-8 bytes. Matching uses Unicode casefold independently in display_name and filename. Query whitespace is literal; there is no regex, accent folding, compatibility normalization or match spanning both fields.

Each course retains every returned normalized row in order. `source_index` identifies an occurrence, even when IDs repeat. `source` preserves that row; `matched_fields` and `unavailable_fields` explain the result. A match is true when any supplied name matches, false only when both supplied names are known nonmatches, and null when there is no known match but at least one name is unavailable. Empty strings are known names. Counts distinguish these three outcomes. A supplied matching filename can therefore be true even when its display name is unavailable.

The unchanged list_files reader skips non-object raw entries, projects a fixed set of metadata fields and turns missing fields into null. Search is over this normalized returned collection, not file contents or inaccessible resources. A no-match result does not prove there are no relevant files in Canvas. The sequential course reads are observations, not a simultaneous snapshot, access check or download-permission guarantee.

The command refuses malformed names, unsupported JSON metadata, more than 5,000 normalized rows, more than 4 MiB of compact ASCII-escaped source JSON across courses, more than 16 nested containers within a row or more than 16 MiB of complete report JSON. Limits apply after the existing reader decodes its responses. No truncation is used. Invalid selection is rejected before client/profile setup; a later course or pagination failure emits structured stderr and nonzero status without a partial successful report. The client closes and the caller's HTTPX logger level is restored.

This receiver was qualified with synthetic HTTPX transport and disposable native inputs. No school account, live Canvas request, file download, installed CLI deployment or learner outcome is implied.
