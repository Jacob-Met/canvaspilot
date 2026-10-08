# Native module-progress qualification

CanvasPilot now exposes a course study checklist through `CanvasAPI.module_progress`,
`canvaspilot module-progress` and `canvas_module_progress`. The feature source is
native commit `a8ba4be26d09d287304ca12808a1867483efd040`, tree
`18895f08360bc6f5138eb1cf59555bed75af8260`, on parent
`72357053a1629c349f700030013559fa6d8130f2`.

## Evidence

- The unchanged parent passes 192 native tests; invoking the new command there
  exits 2 because it is absent.
- The candidate passes all 263 native tests, including 71 new tests. Ruff and
  the Git whitespace check pass.
- The four new receiving groups include actual loopback HTTP, CLI processes
  and the registered MCP stdio server. Both module and item reads follow a short
  first page with an explicit Link continuation. The reader's existing item
  fallback is used unchanged.
- A changed quiz completion removes that quiz from reported unfinished work
  while preserving Canvas's still-started module state. One-of alternatives,
  completed and locked modules, missing student fields and unsupported
  requirement types retain their different meanings.
- A denied later page and a foreign item/module identity produce no successful
  CLI digest. MCP returns a tool error. Query-identity failures make no reader
  request. Every request observed by the new HTTP receiving fixture is GET.
- All 118 unrelated parent leaves remain byte- and mode-identical. The ten
  declared source/documentation/test leaves are pinned in `source-freeze.json`.

`native-http.json`, `cli-receiving.json` and `mcp-receiving.json` contain the
actual fictional-course outputs and request traces. `full-suite.xml` names all
executed tests. `runtime.json` and `requirements-receiving.txt` identify the
Linux/Python receiving environment.

## Retained first receiving result

The first new-suite run passed 69 tests and failed two receiving assertions:
the harness treated the entire stderr stream as one JSON document. The existing
HTTPX logger writes request lines before the CLI's final JSON error. The failed
operations already kept stdout empty. The receiver now parses the final error
record while retaining the error-code, empty-stdout and GET-only checks.
The original output and JUnit are retained as `initial-focused.*`.

Initial Ruff reported four generic external-data type checks. The helper now
uses an explicit `ModuleProgressError(ValueError)` for unusable Canvas progress
data and invalid identities, following the repository's existing custom
folder-browse error convention. The initial lint output is retained.

## Scope and reproduction

The implementation leaves the full module reader, token/broker transport,
authentication, pagination, existing tool bodies and dependency declarations
unchanged. Earlier feedback, assignment-brief, calendar and folder owners retain
their regions. The source reservation is
[CanvasPilot #39](https://github.com/Jacob-Met/canvaspilot/issues/39), with native
Conscience claim 3913 / `cev_78160b5cf3d04f2bb1c4965f`.

From the checkout with its dependencies installed:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider
ruff check src tests scripts
```

The counts describe returned rows. No locally calculated percentage, prerequisite
satisfaction, item access or whole-course completion is claimed.
`collection_complete` remains null under the existing reader's limits. A matching
reported item count establishes only that comparison. The code uses fictional
records and disposable loopback services for receiving; it has not accessed a
school account or changed learner state. Independent review, hosted CI, source
merge and installed adoption are separate subsequent gates.
