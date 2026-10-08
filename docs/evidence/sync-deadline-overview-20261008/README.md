# Sync deadline overview verification

The native API, CLI, and MCP successor passes the repository's 106 tests and
lint. The 47 new author cases are included in that total. A separate receiving
review passes 12 methods against a private copy of the frozen source; those 12
are not included in the 106. Original failing ordering controls are preserved.

Read [the independent disposition](independent/REVIEW.md),
[the author result receipt](author-validation.json), and
[the payload manifest](independent/manifest.json). The independent packet is
retained without edits, including its before and after logs and exact probes.

The original upstream source is commit
[`b0655cfc6f298c956fcdd27fbba32e3c5609516f`](https://github.com/Jacob-Met/canvaspilot/tree/b0655cfc6f298c956fcdd27fbba32e3c5609516f).
Before the successor was frozen, it incorporated the complete unrelated PR26
merge at
[`874ad9c073fc5bab625e583849dbbe4eaf7fc6af`](https://github.com/Jacob-Met/canvaspilot/tree/874ad9c073fc5bab625e583849dbbe4eaf7fc6af).
The review independently verifies preservation of its client bytes and the
whole CLI `_session_cmd` span.

Commit `770e289be705414ff305d2b99cec3633085e2356` in the receipts identifies a
local source snapshot, not an upstream GitHub commit. The 27-path
[candidate manifest](independent/candidate-v1-source-pins.json) pins the reviewed
file bytes. Publication adds this evidence directory without changing those
functional files. The review's `baseline/` and `upstream-874ad9c/` references are
archived reviewer workspaces; baseline source is also recoverable from the
immutable GitHub commits above.

With the dependencies in the receipt installed, replay the author tests from
the repository root:

```bash
PYTHONPATH=src python -B -m pytest -q tests/test_sync_summary.py
```

Replay the standalone independent probe from the repository root:

```bash
PYTHONPATH=src python -B docs/evidence/sync-deadline-overview-20261008/independent/test_independent_sync.py
```

`independent/run_review.py` preserves the exact driver and local interpreter
path used to capture the original receipts. The standalone command above is
the portable replay entry point. Neither fixture run requires a Canvas account
or a browser. These checks establish the documented ordering, selection counts,
partial read failures, and invalid-input boundaries on Python 3.12.14/MCP 2.3.0;
they do not establish live institution behavior or exhaustive Canvas retrieval.
