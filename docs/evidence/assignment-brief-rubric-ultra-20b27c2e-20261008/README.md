# Supplied rubrics in CanvasPilot assignment briefs

## Outcome

The native assignment brief now includes the rubric already returned by Canvas.
The Python API, CLI `brief` command and registered MCP tool return the same
canonical criteria, ratings and supplied grading/display metadata. Missing rubric
data stays unknown; malformed optional data produces a path-specific warning and
does not remove the ordinary brief or healthy neighboring rubric entries.

Current-source qualification passed all **112 baseline tests** and **178 candidate
tests**, with no errors or skips. Full Ruff checks passed. The receiving baseline
is `5b1780ca4fcdce3d5f997cee401c86806ece822a`, tree
`5d3b9b7b8f3cca5f3940f31e020ad4310078dd70`.

## Source and receiving

The first before witness ran on main
`874ad9c073fc5bab625e583849dbbe4eaf7fc6af`. It used the real CanvasClient fixture
backend, actual CLI argument parsing/JSON output and MCPServer.call_tool. The
getter retained two supplied criteria worth 20 points. All three brief paths
omitted them while preserving the instruction to follow the attached rubric.

The candidate was then reconciled with current main, which had received the
module-items and broker-encoding work. The complete 42-blob remote tree was
retrieved and every source blob verified. The original six-file rubric patch
passed `git apply --check` and applied to a fresh copy. API member comparison
confirmed that only `get_assignment`, `assignment_brief` and the added
`_brief_rubric` differ. The module-items method and every unowned file remained
identical to the receiving baseline.

`source-pins.json` identifies the final six source/test files. The final API
SHA-256 is `e35290d0899a88cd5fe03178218b2d7e9f8318cb800a09c18180efef33a1150c`,
Git blob `bcc564bd293966deff85a10164e4daca4daeb935`.

## Public contract

The brief retains every existing ordinary field and adds `rubric`,
`rubric_settings`, `use_rubric_for_grading`, and `rubric_warnings`. Canonical
criterion/rating IDs, text, points, range/scoring flags and outcome identifiers
are preserved when supplied. Description text is not rewritten; criterion and
rating order is unchanged. The complete supplied settings object is retained.
Missing fields are not invented. No scores, totals or grading requirements are
inferred. Advisory false is distinct from unknown null. Display flags are raw
metadata for consumers; these JSON paths do not render a Canvas rubric UI.

The meanings are grounded in the official [Assignments API](https://developerdocs.instructure.com/services/canvas/resources/assignments)
and [Rubrics API](https://developerdocs.instructure.com/services/canvas/resources/rubrics).
The full original rubric remains available from `get_assignment()`.

## Evidence and replay

`complete-suite-receipts.json` records the exact complete-suite commands, exit
codes, results, duration and temporary-space limits. The XML and logs are kept
alongside it. With the declared dependencies already installed, the scoped
regressions run from the repository root with:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_assignment_brief_rubric.py
```

The tests use `tests/fixtures/assignment_rubric.json`, explicitly synthetic input.
They invoke actual API, CLI and registered MCP receiving paths; HTTP client and
broker entry points are forbidden. They cover ordinary absent/null/empty rubrics,
malformed containers and neighboring entries, invalid typed fields, advisory and
display flags, missing qualitative details, zero/fractional/large points, Unicode,
input custody and exactly one unchanged assignment GET per brief.

`discovery-before.json` and `discovery-probe.py` retain the first public witness.
The probe's default baseline label refers to the discovery commit above; use an
explicit `--checkout` pointing to that immutable source and `--output` pointing
to a new report path when replaying it. The initial focused negative and positive
receipts are retained separately. The final test differs from the initial tested
test file only by removal of one import blank line; the current 178-test complete
run uses the final test bytes.

## Environment incident and limits

Two earlier complete-suite attempts exited 120 with empty output while the
shared overlay had zero free space. A follow-up failed before test startup with
`FileNotFoundError: No usable temporary directory found`. These are preserved as
environment failures in `environment-failures.json`, not interpreted as test
results. Root authorized a private tmpfs fallback after overlay exhaustion
recurred. The complete receiving namespace peaked at 757,760 allocated bytes,
below its 30 MB budget; bytecode and pytest cache writes were disabled. No new
installation or download was used for that receiving run.

The checks qualify source behavior with synthetic data and ephemeral local test
listeners. They do not qualify school authentication, a live Canvas account,
student outcomes, an installed broker, or estate deployment. No school account,
submission, service, database, authentication policy or installed host was changed.

Independent review and serialized publication are tracked in the outer
publication manifest. Source qualification alone does not assert merge or rollout.
