# Calendar provider identity and downstream pagination receiving

Issue #43 corrects a real calendar identity mismatch at main
a03a8637efad8ff22103a0c5018c93f7ecbb7d8d. Two different session brokers, each
serving the same numeric course/assignment IDs, produced the same UID when the
CLI kept its default base. Both receipts falsely named canvas.instructure.com
although the actual assignment links identified different authored providers.
Supplying the correct explicit base also changed the same provider's UID.

Native product source: af26c9bca55e05f261c021fb167876e7a7cc32c0.
Only calendar_export.py changes in production. The calendar guide and 14 new
focused regression cases accompany it; all 287 other existing main leaves are
exact. The API, client, broker, authentication, CLI, feedback and brief owners'
source remain unchanged.

The calendar now selects session identity from the existing broker health
provider; fixture/token identity remains the configured client base. It refuses
an unknown/invalid provider and an observed provider change after any selected
course read. This does not lock the broker, detect every transient switch or
provide an atomic server snapshot.

## Actual receiving boundary

The frozen receive_calendar_pages.py, SHA256
c79e6708ba582830dc0084b08ec992e2fe4efdc33158c7ff89c81e7c0860dd64, runs eight
actual native CLI subprocesses for each source. It imports that exact source's
production broker Handler, _call and job queue. Only browser response work is
replaced with authored JSON responses. The independent icalendar 7.3.0 parser
reads generated .ics bytes; this is a receiver-only dependency.

The same unmodified receiver exposes both already-owned pagination gaps and
this newly owned calendar issue. Its failures remain individually visible:

| Source | Native identity | Passed / failed checks |
|---|---|---|
| Landed main | a03a8637efad8ff22103a0c5018c93f7ecbb7d8d | 9 / 18 |
| Main + published PR35 e2089008 | 2eb8676a8975cbe0d2d49dae3d12b418bd940186 | 21 / 6 |
| Main + published PR37 857a226d | 4b93d471d546600257e0f41b1a357c8b5d402d62 | 22 / 5 |
| Main + calendar identity correction | source bytes later committed af26c9b | 13 / 14 |
| PR37 composition + same correction | c8a50218d534dbaac5c416cc2e84e37cdf6dd2c0 | 26 / 1 |

The identity-main run preserves its actual recorded HEAD a03a: it executed
corrected working bytes before their native commit. Its production hashes
match af26c9b's frozen source. No receipt was relabeled or rerun merely to change
that HEAD field. The complete native test suite then ran on committed af26c9b.

All four provider identity failures pass after correction on both landed and
proposed-reader source. The main-only run's remaining 14 failed checks are
unchanged reader pagination consequences: short-page truncation prevents
second-page values/errors/duplicates from being observed.

The PR35/PR37 consumer improvements are observable: later deadlines and null
omissions reach the calendar and receipt; changed page-two values reach the
next export with stable UIDs; global UTC order and exact opaque continuation
survive; later HTTP errors and duplicates refuse output. PR37 also refuses
malformed later relation metadata.

The single remaining PR37-composition failure is separate: CanvasPaginationError
prevents the new file correctly but reaches the calendar CLI as a traceback
instead of structured JSON. It is handed back in PR35 comment 6059080195 for
final reader/CLI composition. This correction does not integrate those open
proposals or fix their error presentation.

## Native gates

- Python 3.13.7, existing isolated calendar venv.
- Existing 40 calendar cases + 14 new provider cases: 54 passed.
- Complete current-main candidate suite: 271 passed in 24.29 seconds.
- Configured ruff check src tests scripts: passed.
- Product-source whitespace check: passed.
- Three new tests execute real CLI processes through production Handler and
  queue with missing initial, changed later and missing later providers.
  They require no file, no success report, structured error, no profile and
  bounded requests.
- Token and fixture tests reject any broker probe; equivalent provider spelling
  remains stable.

An initial Ruff invocation from outside the checkout classified package imports
differently and reported 13 import-order findings, including unchanged owner
files. The configured command from the checkout passed without import edits.
A first receiver write failed with transient Mac ENOSPC; the same write
succeeded after a native free-space check. No cleanup was performed.

## Portable exact raw files

Each *-run.json is a lossless UTF-8 container. For every original native file
(including .ics CRLF bytes, stdout/stderr and receipt.json), its files entry
contains relative path, SHA256 and original text. Encode the utf8 field as
UTF-8 to recover bytes and compare its digest. Do not normalize line endings.

The receiver, full JUnit/plaintext result, source preservation, source freeze
and composition records are separate. SHA256SUMS covers the raw packet.
README-only conflicts in isolated owner compositions retain both documentation
additions; production reader files remain exact owner blobs. Original native
checkouts and outputs remain under production-evidence-49f845d0dece/
calendar-pagination-receiving.

Replay with the project's declared dependencies plus receiver-only icalendar:

    python receive_calendar_pages.py --source /path/to/pinned/checkout --out /new/receiving-directory

Nonzero replay status is expected for known pagination/presentation checks at
the above pins. Inspect named checks and exact artifacts.

No live Canvas, student profile, browser login, calendar account or invitation
was used. Independent calendar review supplied consumer oracles and independently
identified provider/presentation blindspots. This worker authored the frozen
executable receiver; a second execution by that reviewer was not obtained
because reactivation hit the collaboration thread limit. Final source review
and merge remain with the execution lead.
