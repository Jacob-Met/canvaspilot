# Course-folder browser receiving

This package preserves the native receiving result for the bounded course-folder
browser. The public CLI, actual MCP stdio server and existing session-broker
Handler were exercised with authored loopback metadata. No live Canvas account,
browser profile, provider or file download was used.

## Source and result

| Item | Exact value |
| --- | --- |
| Repository | `Jacob-Met/canvaspilot` |
| Base commit | `b0655cfc6f298c956fcdd27fbba32e3c5609516f` |
| Frozen candidate tree | `fbc99e88b46328072ab8eaab23023b9b17dd1898` |
| Source set | 29 tracked files; 9 changed or added |
| Python | 3.12.8 |
| Host | macOS 26.6.2, arm64 |
| HTTPX / MCP / Pydantic | 0.28.1 / 2.3.0 / 2.13.5 |
| Pytest / Ruff | 8.4.2 / 0.16.10 |
| New receiving cases | 33 passed |
| Complete suite | 92 passed, 0 failed, 0 skipped |
| Ruff | All source, tests and scripts passed |

`source-manifest.json` records the Git blob ID, SHA256 and byte count of every
candidate source file. All 29 files were re-read on the native receiving host
after qualification and matched those identities. `runtime-receipt.json` records
that comparison and the installed dependency versions. `process-receipt.json`
preserves native process completion and exit status. `full-suite-final.xml`
preserves the exact JUnit output (SHA256
`cc3f0c0724a707a63112f7d9c90f4f547bcb0c6170252c72c58610989f7c89a5`).

The candidate tree is the source before independent review and before any later
composition with other work. A later receiving result must name its own source
pins. These receipts do not claim live-account behavior or deployment.

## Reconstruct the frozen source

Use an existing checkout of the public repository that contains the base commit,
or clone `https://github.com/Jacob-Met/canvaspilot.git`. The base file and commit
objects originally came from the connected GitHub API; their object IDs were
verified while reconstructing an isolated shallow checkout. No captured source
or dependency trees are needed here. The compact `candidate.patch` includes all
nine candidate changes against that exact base.

Set these paths to an existing repository, this evidence package and a fresh
empty receiving directory:

```sh
canvas_repo=/absolute/path/to/canvaspilot
canvas_evidence=/absolute/path/to/this/package
canvas_receiving=$(mktemp -d)
mkdir "$canvas_receiving/source"
git -C "$canvas_repo" archive b0655cfc6f298c956fcdd27fbba32e3c5609516f | tar -x -C "$canvas_receiving/source"
git -C "$canvas_receiving/source" apply "$canvas_evidence/candidate.patch"

python3 - "$canvas_evidence/source-manifest.json" "$canvas_receiving/source" <<'PY'
import hashlib, json, pathlib, sys
manifest = json.loads(pathlib.Path(sys.argv[1]).read_text())
source = pathlib.Path(sys.argv[2])
for row in manifest["files"]:
    data = (source / row["path"]).read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    assert len(data) == row["bytes"], row["path"]
    assert hashlib.sha256(data).hexdigest() == row["sha256"], row["path"]
    assert blob == row["git_blob"], row["path"]
print("Verified", len(manifest["files"]), "source files for", manifest["candidate_tree"])
PY
```

## Repeat native receiving

Use Python 3.12 in a new virtual environment. `requirements-receiving.txt`
contains the exact runtime distribution versions plus Ruff. The project still
declares its existing dependency ranges in `pyproject.toml`; this evidence file
does not change them.

```sh
python3.12 -m venv "$canvas_receiving/venv"
"$canvas_receiving/venv/bin/python" -m pip install -r "$canvas_evidence/requirements-receiving.txt"

(
  cd "$canvas_receiving/source"
  "$canvas_receiving/venv/bin/ruff" check --no-cache src tests scripts
)

env -u CANVAS_API_TOKEN -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u NO_PROXY \
  -u http_proxy -u https_proxy -u all_proxy -u no_proxy \
  CANVAS_PROFILE="$canvas_receiving/unused-bootstrap-profile" \
  CANVAS_BASE_URL=https://canvas.fixture.invalid CANVAS_SESSION_PORT=0 \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$canvas_receiving/source/src" \
  "$canvas_receiving/venv/bin/python" -m pytest -q -p no:cacheprovider \
  --junitxml="$canvas_receiving/repeated-suite.xml" "$canvas_receiving/source/tests"
```

The received run used an isolated existing Python environment read-only and
installed Ruff separately under the receiving directory. The tests create their
own unused profiles, loopback servers and MCP subprocesses, and restore the
broker fixture's global state. An installed browser is unnecessary.

## What the new cases establish

The 33 new cases are in `tests/test_folder_browser.py`, using
`tests/folder_http_fixture.py`. They establish root-to-child navigation,
independent folder/file page requests, nested file metadata, empty results,
foreign-course and mismatched-parent refusals, permission errors, query
validation before a request, bounded result arrays, literal names and exclusion
of access URLs. Public CLI subprocesses and MCP initialization, tool discovery
and actual tool calls are covered. A receiving case routes the public API and
CLI through the unchanged read-only broker Handler and verifies all seven
dispatched Canvas operations and their page query strings.

The unchanged native transport exposes response bodies without `Link` metadata.
The feature therefore returns explicit bounded pages, `has_more: null` and
`next_page_to_try`; it makes no recursive-inventory or completeness claim. The
official endpoint and pagination references, public examples and response
semantics are documented in the candidate's `docs/folder-browser.md`.

Earlier qualification identified a receiving-test SDK attribute spelling issue
and authored test lint issues. They were fixed before the frozen tree above;
the final complete run and lint result both passed. No unresolved product
failure was known at this receiving freeze.
