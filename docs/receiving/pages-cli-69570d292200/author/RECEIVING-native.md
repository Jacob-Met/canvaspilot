# CanvasPilot terminal page discovery and reading

Candidate virtual product tree: `6d2bd132c4e8de5735cfeeb15ef2db35bcbbf608`.
Accepted source baseline: `56a72a2e2cee5ec04671d12ebe5bc2484afb8026`, tree `a07c3e941219ff80968e1ff20528a63541bb7400`.

A terminal learner can list page locators with `pages COURSE`, read one with `page COURSE LOCATOR`, then pass the same locator to the existing offline exporter. Before this addition, both actual native commands exited 2 with invalid choice. This adds CLI admission/dispatch, one test file, one guide and a README link. Existing API, client, HTML cleaner, search/exporter, MCP, current-quiz96, lockfiles and workflows are unchanged.

## Source and qualification

- `evidence/contract-before-candidate.json` predates candidate code.
- `evidence/maintained-source-patch.json` holds the exact four maintained files and their Git/SHA256 pins.
- `evidence/product-tree.json` is the complete computed canonical product leaf inventory; all 1,614 unrelated baseline leaves are exact, with 1,618 final leaves and no deletion.
- `evidence/source-proof.json` verifies native input preservation and strictly additive CLI/README modifications against the accepted source.
- `evidence/focused-tests-v3.stdout` and XML record 18 successful native pytest cases, no skips. They exercise 17 CLI subprocesses plus two in-process HTTP client calls, literal/Unicode locators, existing numeric-locator validation, pagination, null/false/empty semantics, failures and cleanup. Twenty invalid-argument controls plus both help commands prove no client creation.
- `evidence/focused-ruff-v3.stdout` records the focused Ruff pass.
- API/client/locator-validator dependencies are the 31 unchanged source files in this projection, with accepted Git pins. The existing Python environment was reused read-only; no dependency installation or copy occurred.
- After the full focused pass, the CLI's original terminal newline, trimmed by the read-file transport, was restored. The retained pre-normalization CLI plus explicit byte comparison prove the sole difference is that final LF, and Python ASTs are identical. The full suite was not repeated for this normalization. The final source tree/pins bind the normalized bytes; independent receiving remains pending.

## Retained unsuccessful stages

The initial quiet runner hit its 180-second timeout. It did not serialize `TimeoutExpired.output`, so its partial test output is unavailable and no count is inferred. The runner and derived timeout record are retained. The second runner writes live raw logs and catches its timeout, preventing that evidence loss.

The first completed run produced 13 passes and five failing HTTP path assertions. The unchanged client supplies `per_page=50` even on single-page and quiz GETs; those five tests incorrectly omitted that query. Successful JSON/body assertions passed. The test-only correction preserves the native query and fixes seven style findings; no product behavior changed. Original tests and logs remain.

Initial full-tree verification also treated the connector tree response's `sha` as a tree hash. That field echoed the requested commit SHA. Corrected verification computes the tree from every leaf and compares it with the exact accepted commit's tree pin, preserving both reference values.

The first additive proof detected the transport-trimmed final LF. It was restored and exact AST equivalence checked. No existing executable line changed.

## Native reproduction and boundary

Source projection: `candidate/`. The original counterpart remains at
`/home/jacob/canvas-attempt-69570d292200/original`, read-only.

Read-only dependency interpreter:
`/home/jacob/canvaspilot-enrollments-env-65ae877160f6/bin/python`.

Use a new private TMPDIR and `PYTHONDONTWRITEBYTECODE=1`; set `PYTHONPATH` to
this custody's `candidate/src`. A public command is:

```text
python -B -m canvaspilot.cli pages 42 --base-url http://127.0.0.1:FIXTURE_PORT --token synthetic-fixture
```

Qualification used only synthetic loopback responses. No live Canvas session,
student data, broker change, native goal/lease, installation or deployment was
accessed. This native Git repository stores the source/evidence projection; its
commit/tree is not the canonical upstream product commit/tree. No GitHub API,
immutable remote object, branch, PR, merge or Actions trigger was created after
the explicit API403 hold. Current-main refresh, independent receiving and normal
hosted integration gates remain pending.
