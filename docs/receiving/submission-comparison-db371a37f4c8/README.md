# Submission comparison receiving

Issue [#67](https://github.com/Jacob-Met/canvaspilot/issues/67) adds `compare-submissions`: select two returned submission records explicitly and save a new offline reading report with an exact JSON download. See the [user guide](../../submission-comparison.md) for selection, metadata, output and size-limit semantics.

## Evidence and source boundaries

| Evidence | Result and input |
| --- | --- |
| Original CLI witness | The canonical history read preserves the authored records; the missing comparison command exits 2 before any additional request or output. |
| Native focused qualification | Ruff and 58 dedicated cases pass on the frozen composition over `6c4d5d2e7526cddc1aa6c90bfbef2d1188382ad3`. |
| Actual offline report browser | Four groups pass in Chrome for Testing 153: inert report, native-pointer exact JSON download, 390 px wrapping, and print-media/PDF production. Five screenshots were visually accepted. |
| Full native suite | **Incomplete: ENOSPC during pytest capture/temp-directory handling.** The complete failed log and classification remain in the archive; this is not a whole-project pass. |
| Current publication composition | The same renderer, fixture, tests, guide and exact additive CLI/README spans are composed over main `1bafdaa31f7789d8e561680cb6001bbe38b2da64` with grade review and offline module-progress export; all inherited work is retained. See [composition proof](current-composition.json). |
| Whole-project gate | The existing hosted CI workflow runs Ruff and the full offline pytest suite on the published PR composition. Its exact checkout tree and final result must be recorded before integration. |
| Independent receiving | **Pending at this initial publication.** Root froze an independent contract before candidate inspection. Its separate packet and disposition will be added before merge. |

The native whole-suite summary was `1 failed, 571 passed, 1 skipped, 545 errors, 34 subtests passed in 101.75s`. The first failure occurs in an inherited test's pytest capture/context-manager exit with `OSError: [Errno 28] No space left on device`; aggregate classification records the same environmental failure across the reported failed/error entries. It is preserved separately from the 58 focused passes and browser passes. There was no silent full native rerun.

## Packet

- [Author report](AUTHOR.md) explains the product, exact source boundaries, qualification and retained first failures.
- [Author archive](author-evidence.tar.xz) is 875,596 bytes, SHA-256 `f7d960c1778ea5670e0c27ea0edde1e1f4ed6d76e30bcf0ca8cbea69b71bc216`, Git blob `2de7f23f6e8d12b075cb97bf0debeceeb8dd985a`.
- [Member manifest](author-evidence.manifest.json) lists all 344 payload files; the archive contains those files and that manifest, 345 members total. Every member was verified after decompression.
- [Archive integrity receipt](author-archive-integrity.json) records sealing and transfer checks.

The archive preserves the original and corrected baseline receiver, first lint inputs and correction, focused CLI receipts and actual HTML reports, all browser outputs including the exact downloaded JSON, complete failed native suite log, source snapshots/manifests, and admission refusals. Disposable profiles, pytest temporary directories and Git internals are excluded.

Native qualification uses synthetic loopback Canvas responses and an existing read-only Python environment. It does not represent live school-account acceptance, historical attachment retrieval, an installed CLI release or deployment.

## Reproduce

```sh
python -m ruff check src tests scripts
python -m pytest -q tests/test_submission_comparison.py tests/test_submission_comparison_process.py
python -m pytest -q
```
