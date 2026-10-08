# Submission comparison receiving

Issue [#67](https://github.com/Jacob-Met/canvaspilot/issues/67) adds `compare-submissions`: select two returned submission records explicitly and save a new offline reading report with an exact JSON download. See the [user guide](../../submission-comparison.md) for selection, metadata, output and size-limit semantics.

## Evidence and source boundaries

| Evidence | Result and input |
| --- | --- |
| Original CLI witness | The canonical history read preserves the authored records; the missing comparison command exits 2 before any additional request or output. |
| Native focused qualification | Ruff and 58 dedicated cases pass on the frozen composition over `6c4d5d2e7526cddc1aa6c90bfbef2d1188382ad3`. |
| Actual offline report browser | Four groups pass in Chrome for Testing 153: inert report, native-pointer exact JSON download, 390 px wrapping, and print-media/PDF production. Five screenshots were visually accepted. |
| Full native suite | **Incomplete: ENOSPC during pytest capture/temp-directory handling.** The complete failed log and classification remain in the archive; this is not a whole-project pass. |
| Current publication composition | The exact comparison additions are now composed over actual main `cf47942b395a6196e6f5dcb02b3865f64aa1c89b`, retaining separately integrated page export, grade export and planner reads. The five standalone product files and three comparison spans are unchanged. See [current composition proof](post-initial-publication-composition.json). |
| Whole-project gate | Initial publication passed Ruff and 923 tests plus 54 subtests, with one skip, on exact tree `f27133206e362b677e4ae8c664aafcc0810b6b75`. The [receipt](hosted-ci-r1.json) and [full log](hosted-ci-r1.log) retain that boundary. The ordinary final hosted gate must qualify the new composition before integration; its exact checkout and disposition are recorded in PR #77. |
| Independent receiving | **Accepted.** Root froze its contract before candidate inspection, passed three real CLI groups and three native Chromium groups, and visually accepted five captured regions. The [unchanged disposition](ROOT.md) retains the exact native source boundary and the Mac-only raw-log exclusions. |

The native whole-suite summary was `1 failed, 571 passed, 1 skipped, 545 errors, 34 subtests passed in 101.75s`. The first failure occurs in an inherited test's pytest capture/context-manager exit with `OSError: [Errno 28] No space left on device`; aggregate classification records the same environmental failure across the reported failed/error entries. It is preserved separately from the 58 focused passes and browser passes. There was no silent full native rerun.

## Packet

- [Author report](AUTHOR.md) explains the product, exact source boundaries, qualification and retained first failures.
- [Author archive](author-evidence.tar.xz) is 875,596 bytes, SHA-256 `f7d960c1778ea5670e0c27ea0edde1e1f4ed6d76e30bcf0ca8cbea69b71bc216`, Git blob `2de7f23f6e8d12b075cb97bf0debeceeb8dd985a`.
- [Member manifest](author-evidence.manifest.json) lists all 344 payload files; the archive contains those files and that manifest, 345 members total. Every member was verified after decompression.
- [Archive integrity receipt](author-archive-integrity.json) records sealing and transfer checks.

The archive preserves the original and corrected baseline receiver, first lint inputs and correction, focused CLI receipts and actual HTML reports, all browser outputs including the exact downloaded JSON, complete failed native suite log, source snapshots/manifests, and admission refusals. Disposable profiles, pytest temporary directories and Git internals are excluded.

Native qualification uses synthetic loopback Canvas responses and an existing read-only Python environment. It does not represent live school-account acceptance, historical attachment retrieval, an installed CLI release or deployment.

## Independent receiving and publication recovery

- [Independent root archive](root-receiving-r1.tar.gz): 476,609 bytes, SHA-256 `49dab56fda4ef75d6ebffa5789148606dc298485974e7c4ed0fb975baf937f42`, Git blob `550dd5246c9a712f169ec01f820228f1e0788047`. It contains 25 payload files plus the embedded [manifest](root-receiving-manifest-r1.json), all 26 members verified after decompression.
- [Root custody receipt](root-custody.json) preserves the first independent byte/member checks. Recovery rechecked the original archive, unchanged ROOT.md and all archive members without executing the product.
- [Earlier page-export preparation](post-page-export-composition.json) retains its source boundary and the two prepublication receiver refusals. That preparation was never represented as published.
- [Publication recovery](publication-recovery.json) records the observed open PR, unchanged original branch, absent archive blob and current-source reconstruction before this update.

The three native CLI groups include an actual competing output-file creation during the second HTTP request. The Chromium groups exercise exact pointer-triggered JSON downloads without parsing large IDs through JavaScript Number. Visual acceptance is limited to the captured desktop, 390-pixel emulated viewport and print-media regions; no physical phone, root PDF-pagination or paper-output claim is made.

The independent native source remains the frozen composition over `6c4d5d2e7526cddc1aa6c90bfbef2d1188382ad3`. The additional raw Mac CLI logs remain at their original namespace because the Mac was offline when the packet was sealed. ROOT.md documents those exclusions; no missing files have been reconstructed.

## Reproduce

```sh
python -m ruff check src tests scripts
python -m pytest -q tests/test_submission_comparison.py tests/test_submission_comparison_process.py
python -m pytest -q
```
