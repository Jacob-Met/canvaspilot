# Independent receiving — CanvasPilot assignment calendar export

**Final verdict: ACCEPT for publication composition `6e2e58f4e28e09749f9f97162a8ce460eccdd4b1`.**

The corrected calendar source `553bce63f7febf2abc123d63e0023da6e1859b02` was first accepted in the paired receiving below. The final composition receives a separate unchanged-receiver acceptance at the end of this document.

Independent receiver: `/root/production_evidence/calendar_receiving`.
Product author: `/root/production_evidence`.
Native device: Mac `0e3d582f-e25b-44b2-8418-9639fc4e4e33`.
Only disposable receiving files were written. No product source, author tests, real Canvas/calendar account, broker, or protected storage was changed.

## Paired native result

| Source | Checks | Receiver exit |
| --- | --- | --- |
| Initial source `7ff3518e9025c6d54899b01da21b378aebd01f3d` | 24 pass, 1 fail | 1 |
| Corrected source `553bce63f7febf2abc123d63e0023da6e1859b02` | 25 pass, 0 fail | 0 |

Both paired runs use the **same receiver file**, SHA-256
`f29728013fa49e3923a3d7317b0f722d4a393dc4fd902ed2dcad60327875044b`.
Each run invokes **nine actual native CLI subprocesses** through the unchanged CanvasAPI/CanvasClient with two authored loopback HTTP endpoints. The independent parser is **icalendar 7.3.0**. No calendar parser or product function was substituted.

Initial discovery used a receiver with source hashes and output path embedded. That exact original is preserved as `receive_calendar_independent.initial.py`, SHA-256 `e3e8307143884539f4958f95f77f5e7b361947c3ed3a47d45503a9500af01730`. The configuration-only patch moves source path, expected hash manifest, output directory name, and source-head label to arguments. It changes no assertion, fixture, subprocess behavior, or parsing. The parameterized receiver was then run against an exact git-archived initial source before testing the corrected checkout. The original discovery run remains in `run-initial/` in the raw receiving root.

## Finding and correction

The initial source accepted the malformed later-course deadline
`2026-11-01T01:10:00+00:60`.
Its regex admitted minute 60; Python's datetime parser normalized that offset to one hour. The actual CLI returned exit 0, reported `ok: true`, and published an event with `DTSTART:20261101T001000Z`. This violated the promised refusal of malformed dated input. The retained baseline stdout, stderr, and generated calendar show the false success.

The author narrowed the accepted offset fields to hour 00–23 and minute 00–59. The unchanged independent fixture now yields exit 1 with `ValueError`, no stdout success report, and no destination entry after the earlier valid course was read. The other 24 checks remain passing.

## Successful receiving boundaries

- Long multibyte titles containing comma, semicolon, backslash, CRLF, CR, LF, and a literal `BEGIN:VEVENT` line round-trip through the independent parser as a single event title. Physical lines remain valid UTF-8, use CRLF, and do not exceed 75 octets.
- Aware offsets across the repeated fall-back hour and a quarter-hour zone reach the parser as the exact ordered UTC instants.
- Editing a title and deadline preserves event UID, including an equivalent source URL with normalized scheme/host case and trailing slash. The changed deadline reaches the parsed event.
- Equal assignment IDs in different courses remain distinct. Equal course/assignment IDs from different source origins remain disjoint.
- A null due date is explicitly reported and omitted. A naive dated row, malformed offset in a later course, all-undated result, and later-course HTTP failure refuse the entire output.
- Repeated course selection is normalized and read once. Default upcoming selection is retained; `--bucket all` omits that transport filter.
- Existing calendar bytes and a dangling output symlink remain unchanged, with no extra course reads. No profile or temporary publication residue is left.
- All observed requests are GET reads to the selected authored loopback course routes.
- No duration, end time, invitation, alarm, or busy block is invented. URL punctuation and reported content digest remain exact.
- All three source/test fingerprints match the provided manifests before and after each run.

## Exact corrected fingerprints

| File | SHA-256 |
| --- | --- |
| `src/canvaspilot/calendar_export.py` | `f3e06eb68d7f74bb757a28f9cdc9a229f2af9476d4a93ba709698b54ffed82a8` |
| `src/canvaspilot/cli.py` | `28d278a60ee0b5b036948071c0965f42ea3f36cc1892940406577491e2c3ef38` |
| `tests/test_calendar_export.py` | `0774869f562ab1bdff8d09df38216fab7cc44543ded02be620c2a4e5e3a9e17f` |

## Evidence and rerun

Raw root:
`/Users/me/workspace/estate/production-evidence-49f845d0dece/calendar-independent`.

The paired `run-baseline-frozen/receipt.json` and `run-candidate-frozen/receipt.json` include source fingerprints, receiver digest, each assertion, every CLI argument/exit/report, and authored HTTP request records. Whole-run stdout/stderr and per-process stdout/stderr remain alongside the output calendars. `portable-files.json` lists the concise publication selection and hashes; the full raw directories remain preserved.

The frozen receiver takes three positional arguments: a new run directory name, the source root, and a JSON manifest containing `head` and `hashes`. Its native ROOT constant identifies the receiving device path; relocate that constant when intentionally porting to another device and record the resulting receiver digest.

This verifies the native export workflow and independent iCalendar parsing. It does not claim a live Canvas read, a third-party calendar application import, transport coverage beyond returned assignment rows, support for filesystems without hard links, or power-loss durability. The author’s full suite was not rerun by this independent receiver.

## Final publication composition

Native composition `6e2e58f4e28e09749f9f97162a8ce460eccdd4b1` incorporates current main `e8cd1aecf8e5ca9ede0313b2576ddd71303b82ad`, including the separately owned feedback API/CLI feature. The exact same frozen receiver `f29728013fa49e3923a3d7317b0f722d4a393dc4fd902ed2dcad60327875044b` was run once more: **25 pass / 0 fail, receiver exit 0**, with nine actual CLI subprocesses. No baseline rerun or receiver change was needed for this composition.

Calendar module `f3e06eb68d7f74bb757a28f9cdc9a229f2af9476d4a93ba709698b54ffed82a8` and authored test `0774869f562ab1bdff8d09df38216fab7cc44543ded02be620c2a4e5e3a9e17f` remained unchanged. The composed CLI SHA-256 is `173df7056f7d86084aa2dc00ba129bf8c36aaf109cdbf9497e24ec436d90d47b`; inherited API SHA-256 is `546fd973330ffb3c95c81ba670b5ae2add751a23362c83a370254ea702eee1a0`. All four fingerprints were independently verified before and after receiving. The post-run native HEAD remained the stated composition.

`run-composed-frozen/receipt.json`, whole-run stdout/stderr, exit record, `source-composed.json`, and `composition-preservation.json` retain the final evidence. Raw calendars and individual process logs remain in the composed run directory. The earlier frozen-source review and manifest are retained separately in the raw receiving root. Final acceptance covers this composition under the same stated native/fixture/parser boundaries.
