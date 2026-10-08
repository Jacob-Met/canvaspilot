# Selected course-page packet: receiving evidence

This packet accompanies [CanvasPilot #54](https://github.com/Jacob-Met/canvaspilot/issues/54).
The command `canvaspilot export-pages COURSE PAGE... --out reading.html` creates one new
offline reading file from explicitly selected Canvas pages. See the
[recipient guide](../../page-export.md) for selection and output behavior.

## Source and receiving boundary

The production contribution is exactly seven paths: the page module, two regression
files, one authored fixture, the CLI parser/dispatch insertions, the guide, and a small
README pointer. The final source-only native commit is
`0ef6b368ba9a21bfb93e8a513ad12a19e232219a`, composed on current
`6c4d5d2e7526cddc1aa6c90bfbef2d1188382ad3`.
All 1,131 unowned current leaves and their modes are preserved.
The CLI and README reduce exactly to current source when the 8-line parser,
21-line dispatch, and 5-line guide pointer are removed.
The page module remains SHA-256
`8800e959ee620438273c3291fd24c51b9ed567430b28093cd3f8bef52bff5015`
through all current-source compositions.

Qualification uses an isolated Mac Python 3.13.7 environment and authored local
fixtures. No Canvas account, browser login, broker, provider write, shared installation,
or live service was used or changed. The private installed wheel is a receiving
artifact; it is not a claim of a global CLI deployment.

## Recorded phases

| Phase | Exact boundary | Recorded result |
| --- | --- | --- |
| ThinkPad baseline | Original `79a2f2b2` | Command unknown, exit 2, no output or HTTP; baseline suite 536 passed, 1 skipped, 6 subtests passed. |
| Initial source | Historical files and tool transcripts in `historical-native/` | 63 module controls passed; two Ruff findings retained and corrected. |
| First process harness | Original native phase | 67 module controls passed; 10 of 18 process controls failed on harness expectations about existing stderr logs, `per_page=50`, and read-induced atime changes. |
| Corrected process harness | Same page behavior | 18 process controls and Ruff passed. One later child-only OS write-limit control brings the maintained process suite to 19. |
| First Mac installed source | `dbcad81a` on `a5ce672e` | Wheel/source/installed 15 package leaves identical; 756 passed, 1 skipped, 6 subtests passed; Ruff passed. |
| Announcements/discussion/agenda composition | `b881d4ac` on `0480cbce` | Wheel/source/installed 17 leaves identical. First suite transcript lacked a summary and its wrapper hit errno 28; this phase remains inconclusive. |
| Bounded replay of that interrupted suite | Unchanged `b881d4ac` and wheel `498b8819` | Actual pytest exit 0: 851 passed, 1 skipped, 45 subtests passed. Ruff exit 0. Complete stdout, stderr, XML, and receipt retained. |
| Final quiz/file-listing composition | `0ef6b368` on `6c4d5d2e` | Wheel `d5fc2e44` matches all 17 source and installed package leaves. Actual 19 process controls and Ruff pass. Full published-head hosted CI is a separate gate. |
| Actual offline browser | Original installed console packet `c9511af4` | Chrome 154: 13/13 controls, desktop and 390px screenshots, no automatic HTTP requests, script dialogs, page errors, or console errors. |
| Final installed-console readback | Final packet `c44ada3f` | Four exact authored GETs and three selected page identities; no profile/input/temp changes. Entire output equals the browser-qualified packet after only the recorded fixture origin and generation timestamp replacements. |

The 851-pass result belongs to the announcements composition. It is not relabeled as
a full native result for the later quiz/file-listing composition. The latter changes
separate command branches and `list_files`, which the page packet does not call.
Its current entry point was qualified with the actual installed process tests.
Independent source reviews in `peer-review/` retain each source version separately.

The first incomplete Mac suite keeps its original E/F progress and wrapper traceback.
No exact pytest exit code or summary survived that phase, so neither a product
failure nor a passing run is inferred from it. The later replay is independently
complete. Earlier ThinkPad raw logs remain at the precise native custody paths in
`historical-native/custody-index.json`; transport was unavailable when the Mac
packet was assembled. Included historical tool transcripts and source bytes are
identified as such, without claiming a new read of those unavailable raw files.

## Reading and failure guarantees

The main body is extracted plain text, with line breaks, list bullets, code indentation,
image-alt text, and inert link references. It is not a rendered reproduction of the
Canvas page. The exact original supplied HTML is separately escaped into a disclosure,
with identity, UTF-8 byte count, and SHA-256. Local contents/back links work offline;
the only outgoing links require a deliberate click.

The maintained controls cover selected course/page identity, numeric URL versus
explicit `page_id:ID`, duplicate/missing/locked pages, provider identity changes,
body and packet bounds, Unicode/CR/LF preservation, inactive hostile markup, and
input immutability. Publication uses a fully written and fsynced same-directory
temporary file followed by an exclusive hard link. Existing and raced output entries
are preserved. Primary write/flush/close/link failures stay primary; a cleanup failure
after successful publication yields a truthful warning. A real child-only
`RLIMIT_FSIZE` control exercises an OS write failure without changing parent or host
limits. No power-loss directory durability, atomic course backup, or changed
transport streaming/redirect behavior is claimed.

## Replay

Install the repository's declared development dependencies, then run:

```sh
python -m pytest -q tests/test_page_export.py tests/test_page_export_process.py
python -m ruff check src tests scripts
```

The historical native drivers retain their original absolute private paths so their
receipts can be interpreted exactly. To reuse them elsewhere, create an equivalent
owned layout and update those paths deliberately. The authored fixture, HTML packets,
raw result files, XML, wheel bytes, screenshots, and driver source are preserved.
`evidence-manifest.json` lists every copied evidence leaf except itself.
