# CanvasPilot printable feedback export: final publication receipt

The six-file product increment is ready to receive on `Jacob-Met/canvaspilot`
parent `0d1898544a90079e2dcc7ceb3fa4bc6bca88a2bc`, tree
`de9fca025ebe325807bd53cd9b7f3b6be50c6d19`. Publication and current-parent readback
remain with the lead. This worker has made no GitHub mutation.

## Usable command

```sh
canvaspilot export-feedback COURSE ASSIGNMENT --out feedback.html
```

The native feedback reader supplies one local, self-contained HTML sheet. It
keeps reported grade applicability and attempt context separate, preserves
zero/unknown/empty distinctions and exact rubric/comment associations, displays
supplied authors and media/attachment references, and applies rubric point,
total and outcome-posting flags as distinct settings. It calculates no grade or
earned rubric total and infers no earlier graded attempt. Existing destinations,
including a path created during the read, are protected. The file has no scripts
or automatic resource elements and can be opened or printed by the user.

## Current product pins

| Product path | SHA256 |
| --- | --- |
| `README.md` | `18567e59318ebbb55556962fcdb9c0e947cd3a6812ad552cbd9737031b24dc29` |
| `docs/feedback-export.md` | `6529840db890019b488539ca5b488395ea2d50b4ccd63d336a16437d77afb938` |
| `src/canvaspilot/cli.py` | `223654cbd53c539b327dfb7399ed01953381044f387c205bb1a7eb21f6c1808f` |
| `src/canvaspilot/feedback_export.py` | `a0db41dca9cce28c9fb7594c88ea6dc103b0f3104d5ba4d061bd93aaed92a714` |
| `tests/test_feedback_export.py` | `046ce25f6bc03ae6ad23e65bb7f5cbe26a42a257f45cc9998701054fb1375de5` |
| `tests/test_feedback_export_native.py` | `3bd9cec9c6bcef89395f392498e883c3882f6cdcbe4257d4d210b17d99da6045` |

The final context has 29 files, including 14 runtime modules. The 23 unowned
native files remain outside the change set. The source manifest SHA256 is
`7ff1ec504102adf538801b2cb6a17b451cad7b0699d4e08ff858aa121cbfb4a3`.
It was frozen before the bounded receiver; the receiver's later result is
recorded separately rather than editing that historical pin document.

## Qualification by exact source generation

| Source generation | Authored receiving | Independent receiving |
| --- | --- | --- |
| Original 55fe / formatter `3bc3f44f` | 65 focused cases pass, zero skipped; 20 exporter CLI processes, 34 authored Canvas GETs, eight new sheets and 12 refusals | Seven methods pass in normal and optimized Python; 33 CLI processes and 57 GETs per mode |
| CSS-only 55fe / formatter `a0db41dc` | One native export passes; actual before/after DOM/CSS receiver passes seven controls | One fresh CLI export, two GETs; old invalid selector reproduced, all 35 final selectors accepted |
| Provider-identity 79a2 / CLI `223654cb` | 97 cases pass, zero skipped, including 32 incoming provider/session controls; Ruff passes; all 28 source pins unchanged | Two methods pass in both modes; eight CLI processes, six direct Canvas GETs plus seven broker GET intents and two actual sheets per mode |
| Assignment-list import 0d / same CLI and formatter | Exact source-delta qualification; no 97-case replay | One actual export per Python mode passes, two GETs each; all visible fields match prior qualified output apart from capture UTC; all 14 runtime and 29 author source files exact |

The 79a2 independent receiver exercises token and an authored local broker
envelope, preserves the native feedback command's JSON, and checks refusal and
existing-file behavior. Broker GET intents are the Canvas methods requested
through local broker IPC; they are not a claim that all local transport requests
use HTTP GET. The final 0d receiver closes the new import context and does not
claim additional behavior coverage for the incoming assignment-list helper.

The 79-to-0d API delta is exactly one import and three lines inside
`list_assignments`. Removing those additions reproduces the entire prior API;
the other 39 methods, including the constructor, `get_assignment` and
`submission_feedback`, remain byte-identical. The final README insertion is
verbatim from the earlier qualified versions and its removal recovers the whole
native 0d README. Existing client, broker, calendar and feedback projection bytes
are retained.

## Preserved failures and original evidence

The original CLI rejects the absent command with exit 2 before requests or
output. The first authored receiver reports 11 passing and nine failing
parameterized cases because it parsed the whole stderr stream as JSON; native
HTTPX diagnostics precede the CLI's final JSON line. That driver, source snapshot
and raw failures remain. The exact earlier formatter snapshot was reconstructed
from the two recorded view-only corrections, as the original receipt explains;
it is not presented as a source pin captured at the first run's boundaries.

The independent original review identified one invalid `+:root` selector. The
successor removes only its leading plus byte. The first optional DOM checker
failed at startup because it assumed the removed jsdom `ResourceLoader` export;
its archived driver and unchanged failure reproduction remain. The qualified
checker uses current documented constructor behavior. None of these failures
is relabeled as a passing earlier run.

All 91 original authored files and all independent packets remain byte-exact.
The six original qualified product files are mapped into a `.source` archive
namespace while the final six product paths receive the current versions. The
other 85 original authored receipt paths remain unchanged. The final preservation
map records those relocations, and the sparse manifest verifies every source
against the frozen hashes. Intentionally nonstandard JSON control receipts use
`.source` suffixes without rewriting their bytes.

## Publication and practical limits

Read each manifest entry's absolute `source_path` as its bytes and `path` as its
repository destination. No second full source tree or large evidence copy is
required. All entries are UTF-8, including lossless base64 raw-evidence capsules;
there are no binary uploads. Existing shared-inode sources remain immutable.

These are native local, synthetic-loopback and DOM/CSS qualifications. There is
no school account, live Canvas, physical browser/printer, deployment or learner
outcome claim. The whole repository suite was not rerun. The final native import
and export were tested in normal and optimized Python; earlier broad receipts
retain their original parent pins.
