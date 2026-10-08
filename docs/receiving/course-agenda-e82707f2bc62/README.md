# Course agenda — receiving record

Native scope: [CanvasPilot issue 55](https://github.com/Jacob-Met/canvaspilot/issues/55).

The new API, CLI and curated MCP tool read two Canvas calendar collections for an
explicit selected-course/date range, preserve every returned record, and combine
timed entries in exact UTC order. Declared all-day dates and unavailable timing
stay separate. The feature performs no Canvas writes, deduplication, recurrence
expansion or learner-state inference.

## Exact source and current composition

Original receiving starts at main `39d835c8becb04d81b65c90d1491d2d3a2727ffe`, tree
`53b67d3f06b4c780e508325ec42b2b435ec57e97`. The initial new reader was Git blob
`24d1e37a1031a05162c28ba89c9566df76d539fc` and remains preserved in the original
candidate and source freeze.

A narrow standards correction is frozen as reader
`82ab4fa8f9b92b8d9e5d4c74962d138e1d882ebd`: RFC 3339 section 4.3 gives a known UTC
instant for `-00:00` while leaving the local offset unknown. The successor removes
only the explicit rejection of that marker and corrects its comment. The complete
original timestamp remains unchanged. The guide and one authored value assertion
were corrected; all four API/CLI/MCP/bundle files and all HTTP process fixtures and
tests retain their received bytes. The original source and all original results
are preserved separately.

Current-main source composition was prepared over inbox PR56 merge
`a5ce672e5b3580c1f52e13c49eefee830f11346c`, tree
`0661a7005e577864cb87bc41e0e715409c92ee76`. Removing the exact authored API, CLI and
MCP blocks yields the current parent's bytes. Reversing the three README additions
also yields its exact bytes. No inbox method, client, broker, paginator, dependency
or workflow is changed. The final expected tree and actual native CI receipt are
recorded separately at publication; original local evidence is not backdated to
this later composition.

## Behavioral evidence and corrections

| Frozen receiving | Original source | Candidate | Interpretation |
| --- | --- | --- | --- |
| Real package/module import, existing raw calendar fixture and MCP catalog | Exit 0; 37 tools, no agenda | Recorded before implementation | Establishes the original native reader and missing public capability. |
| Real original CLI `--help` / `agenda …` | Exits 0 / 2 | Recorded before implementation | Missing argument routing is distinct from a failed Canvas request. |
| First 45 authored cases | 44 fail, one existing-reader control passes | 38 pass, seven fail | The seven candidate failures share an incorrect authored `per_page=100` expectation; the unchanged client uses 50. |
| Same seven affected process cases with only that expectation corrected | Seven fail | Seven pass | Actual native reports, opaque continuation reads, refusals and same-process MCP recovery are accepted. The prior failure and test remain preserved. |
| Same focused `-00:00` counterexample | Initial reader misses the timed row | Standards successor passes | Retains the literal marker and exact ordering against Z and a nanosecond-earlier record. |

The final value test replaces the one incorrect `-00:00` negative expectation
with the focused positive case; the suite still contains 45 cases. The preceding
records are separate runs over their stated source/test snapshots. They are not
claimed as one full final-source run. Existing hosted CI must run the complete
final suite and all existing regressions on the actual PR composition.

Value and selection cases use the real CanvasAPI and CanvasClient with HTTPX's
authored MockTransport. Process cases run the actual CLI and registered MCP stdio
server against an authored loopback HTTP server, including both calendar types
and two pages each. They check literal records, field types, course/section
binding, exact fractional/offset ordering, no successful partial report after a
late failure, request-free invalid selection and same-session recovery. Fixture
records and unused profiles remain unchanged. Only synthetic tokens and authored
loopback responses are used.

The received runtime is Python 3.12.14, HTTPX 0.28.1, MCP 2.3.0, Pydantic 2.13.5
and pytest 9.1.1 in an isolated declared-dependency target. Retained Ruff 0.16.10
accepts the source/tests. No browser, real school account, live PAT, provider
mutation or measured learner outcome is claimed.

## Reuse and boundaries

With the repository's declared development dependencies installed:

```sh
pytest -q tests/test_course_agenda.py tests/test_course_agenda_process.py
```

The tests derive imported source normally and allocate their own temporary
loopback server and profile paths. They contain no estate-specific source path.
`CANVAS_AGENDA_RECEIPTS_DIR`, when explicitly set to a new directory, preserves
full native process output and request traces; it is optional for ordinary CI.

The underlying paginator's accepted terminal-single-object convention remains
explicit. Collection counts describe returned rows, not original wire shape or
universal course visibility. Date filtering belongs to Canvas; the two reads are
sequential and cannot establish an atomic snapshot. All-day dates are never
converted to invented midnight instants. See the [course guide](../../course-agenda.md)
for the student-facing behavior and primary source links.

The archive records original discovery/ownership, both original and corrected
test runs, stdout/stderr/JUnit, process observations and exact source/test freezes.
Its internal manifest binds every archived payload. Independent root receiving
and final native CI have their own receipts.
