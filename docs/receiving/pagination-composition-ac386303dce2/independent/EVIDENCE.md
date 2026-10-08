# Independent packet storage

The reviewer supplied 21 files plus `file-manifest.json`. All 22 originals,
226,928 bytes in total including that manifest, are preserved byte-for-byte in
`evidence.tar.gz`. The archive is 85,494 bytes, SHA-256
`b991b7daaf8c7e557e45d3b6b175c7b98c12674937523412f0048f27d13581e9`.
It contains the 22 original relative paths plus `MANIFEST.json`.

`archive-members.json` duplicates the archive's own manifest and hashes every
original, including the reviewer's unmodified manifest. The original
`file-manifest.json` has SHA-256
`0a7783477978c4bb5a8fa55a97734aeb8adb97da73ec6fa11406d7a76ad88503`.
Every archive entry was compared byte-for-byte with the received file. The
readable qualification, test, native transcripts, source/bundle receipts and
original manifest alongside the archive are exact copies of their members.

The unchanged baseline and candidate broker capsules contain the source's
original extra blank line at EOF. A new-file whitespace check rejects those
raw duplicates, so the complete received packet is archived without changing
the originals. The integrator's failed staging output is retained one directory
above. This packaging does not alter the independently accepted source or
replace an unsuccessful behavioral result.

To restore the complete source capsules, original helper diff and independently
received Git bundle, extract into a separate directory from the repository root:

```sh
canvas_independent=docs/receiving/pagination-composition-ac386303dce2/independent
canvas_independent_review=$(mktemp -d)
tar -xzf "$canvas_independent/evidence.tar.gz" -C "$canvas_independent_review"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$canvas_independent_review/candidate/src" python -B "$canvas_independent_review/test_composed_receiving.py"
```

The test requires the dependencies stated in `QUALIFICATION.md`; it uses authored
HTTP responses and synthetic credentials. Select `baseline/src` to replay the
original negative result, or add `-O` to replay the optimized candidate control.
The extracted `file-manifest.json` retains the reviewer's original source, test,
receipt and bundle pins.
