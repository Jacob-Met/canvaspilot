# Assignment calendar export — native receiving

CanvasPilot issue #38, estate-49f845d0dece/product.

The qualified publication composition is native
`6e2e58f4e28e09749f9f97162a8ce460eccdd4b1`, based on main
`e8cd1aecf8e5ca9ede0313b2576ddd71303b82ad`. It preserves newly merged
submission-feedback PR #40. All 185 other main leaves are exact; the existing
CLI and README receive only 29 and five inserted lines respectively.

Product source is a new calendar-export module and those additive CLI blocks,
with 40 focused tests, a usage guide and a README pointer. No API, client,
broker, MCP, bundle, dependency or workflow behavior is changed by this work.

## Qualified result

- Actual original baseline `72357053...`: the new command is absent, exits 2,
  and makes no HTTP request or output file.
- Corrected feature on that base: **232 native tests passed**.
- Current-main composition: **257 native tests passed**, including all new
  feedback and calendar cases; no skips. Full Ruff and product diff checks pass.
- Author actual-CLI receiving with independent `icalendar 7.3.0` parsing:
  **21 checks passed** across six child commands on corrected feature source.
- Separate independent worker: the **same receiver** reports 24 pass / 1 fail
  on initial source, 25/25 on corrected source, and **25/25 on the final
  current-main composition**. Each run invokes nine actual CLI processes.

The receiver verifies UTC deadline instants across clock rollback, Unicode
folding/escaping, stable source/course/assignment identity after edits,
distinct schools/courses, explicit undated omissions, malformed-date and
later-course failures, existing-file/symlink preservation and no invented
duration, invitation, alarm or busy block.

`composition-current/` holds the actual publication-base full-suite and
source-preservation receipts. `independent/INDEPENDENT_REVIEW.md` gives the
independent verdict; the three paired/composed receipts include all checks,
commands, source pins and request records. The independent receiver and its
configuration-only parameterization diff are preserved unchanged.

## Retained product rejection

Native initial source `7ff3518e9025c6d54899b01da21b378aebd01f3d`
accepted the invalid later-course date `2026-11-01T01:10:00+00:60`:
Python normalized its minute overflow to a one-hour offset. The actual CLI
reported success and published that incorrect deadline.

Native correction `553bce63f7febf2abc123d63e0023da6e1859b02`
narrows the accepted offset fields to hours 00–23 and minutes 00–59 before
conversion. The unchanged independent case now exits 1 and creates no file.
Four invalid-offset tests and one valid boundary control were added.
`offset-correction.patch` reconstructs this exact two-file change.
The independent baseline false-success calendar, logs, original source
manifest and complete negative receipt remain in the packet.

The initial source-native commit, corrected commit and composition commit
remain in the author's native Git history. `native-source*.json` records
the distinct freezes; older receipts retain their original source identities.

## Receiver-development corrections

These are separate from the substantive offset defect:

- The first authored test run was 34 pass / 1 test-oracle failure because it
  tried to parse all stderr as JSON despite inherited HTTP logging. The test
  now reads the final structured error line.
- `parser-receiving/` preserves a five-pass/one-failed author parser comparison
  that incorrectly expected literal CRLF inside decoded TEXT. The corrected
  expected LF normalization passes in `parser-final/` with identical product
  hashes. `parser-corrected/` repeats the same author receiver after the
  substantive offset fix.

The old 227-test receipt is retained under `author-validation-v1/`;
the corrected 232-test result is at the packet root; final composed 257-test
results are under `composition-current/`. None is relabeled as another source.

## Replay

Use Python 3.11+ with the project's declared runtime requirements and its
pytest/Ruff development tools. The separate calendar parser is receiving-only;
no runtime or project test dependency was added. Exact resolved receiving
versions are recorded in `requirements-receiving.txt`.

```bash
python -m pip install -e . pytest ruff icalendar==7.3.0
python -m pytest -q
python -m ruff check src tests scripts
git worktree add --detach /tmp/canvaspilot-calendar-baseline 72357053a1629c349f700030013559fa6d8130f2
python docs/evidence/assignment-calendar-49f845d0dece/receive_calendar.py \
  --source "$PWD" --baseline /tmp/canvaspilot-calendar-baseline \
  --out /tmp/canvaspilot-calendar-replay-new
```

The output directory must be new. This starts only a disposable loopback
fixture with an explicit synthetic token. The independent review documents
its separate receiver's run inputs and source-manifest format.

## Limits

Qualification covers native generation and independent format parsing,
not a live school or a particular calendar application's import behavior.
Existing transport pagination bounds returned rows. This is a snapshot,
not a subscription; repeated-UID reconciliation and deletion of old imports
remain application-specific. No account write, invitation, alarm or deployment
was performed. Publication requires hard-link support and makes no
directory-fsync or power-loss durability claim.
