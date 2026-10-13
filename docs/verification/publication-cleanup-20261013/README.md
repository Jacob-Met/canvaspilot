# Complete exports retain successful receipts when staging cleanup fails

The calendar, grade-review HTML and module-progress HTML commands share
`write_calendar`, the complete-byte publisher in
`src/canvaspilot/calendar_export.py`. Previously, a successful hard link could
be followed by a failed temporary-file unlink, causing the command to report
`ok: false` even though the requested complete output existed. A failed unlink
could also replace an earlier write, flush, close or link exception.

The publisher now closes and syncs its temporary file before publication. It
preserves the original prepublication exception when secondary close or unlink
operations raise `OSError`. After a successful hard link, an unlink
`OSError` becomes a nonempty warning return. Ordinary successful publication
continues to return `None`.

The three existing commands include this warning as `cleanup_warning` in
their normal success JSON. Their output path keys, counts, hashes, rendered
bytes, error routes and logger/API cleanup stay unchanged. An existing
destination or a destination created during the publication attempt is still
preserved. A warning identifies the leftover temporary basename in the same
output directory; it does not mean the completed destination should be exported
again.

## Received source

| File | Original Git blob | Received candidate Git blob |
| --- | --- | --- |
| `src/canvaspilot/calendar_export.py` | `ef74cfdf50fd894327dbe45a9a9d43042953bc31` | `9e4c05c88b53730414076fbc2069c9c293c64d76` |
| `src/canvaspilot/cli.py` | `ab071891721397a27ce87ce21a8380691bab365f` | `6bf38ebff1f0242be07f176050be39c7fae7890b` |
| `tests/test_calendar_publication_cleanup.py` | Added | `8e0c8064d7b7b06861d7611860e78ba4269869f3` |

The received originals and both real HTML renderer modules are unchanged between
independent baseline `b257cdda1fbb4358d79cbefb5641b5db86b445f5` and publication
parent `29eb015351a4614bd8b09c58a3ef943f4da3caba`.

## Validation performed on 2026-10-13 UTC

A separate worker froze and ran the independent receiver before reading the
candidate. The final comparison passed **554 assertions** on macOS with
Python 3.13.7. It executed both exact writer and CLI sources and the real calendar,
grade-review and module-progress renderers. All three injected cleanup-only
failures changed from exit 1 / `ok: false` to exit 0 / `ok: true` with a warning.
Normal before/after bytes matched for all three exports. Existing-file, symlink,
directory, competitor-path, allocation, write, sync, close, link and explicit
cancellation controls were also received.

The seven added standard-library unittest methods were run against both exact
writer modules. The original produced three assertion failures and two errors;
the candidate passed all seven methods. The test with write failure/cancellation
also uses two subtests. These tests retain real temporary files, disk writes,
descriptors and hard links, with explicit injected OS errors.

The native environment has no installed project dependencies. Both courses
therefore use an explicitly reported import/transport boundary stub; provider
methods refuse unexpected use or return synthetic data. These results qualify
the local publication and receipt behavior. They do not establish live Canvas,
installed-package, full pytest/Ruff, browser, Windows or deployment acceptance.
No GitHub Actions were run or changed.

The independent source reviewer found no blocker in the scoped OS cleanup
contract. Reconstructing the entire CLI candidate from its original requires
only the three assigned publisher returns and three conditional warning fields.
The existing `write_page_packet` pattern and every other command remain intact.

## Retained evidence and rerun

The adjacent files retain the independent receiver/receipt and the author
receipt plus original/candidate logs. The independent receipt SHA-256 is
`fdbd25c27436d8b5130660eb5c9464d41bcf4a0b1ae5ce6d52ebafaeed240544`.
The author receipt SHA-256 is
`9593539756fe371662d27d3e9c95e4b4b1aa4950194f4af80ccc181ddd53a25c`.

In a normal development checkout with the declared project dependencies
installed, run:

```sh
python -m unittest discover -s tests -p test_calendar_publication_cleanup.py -v
```

The independent receiver takes a JSON source bundle. The source manifest below
identifies the exact Git objects for reconstructing its shared modules and two
variants; each source entry is `{"sha": BLOB, "content": GIT_BLOB_UTF8_TEXT}`.
All source objects are reachable from this contribution and its parent history.

```json
{
  "shared": {
    "grade_review_export": "8a6281f62f99e18109f90a273a4c29da4929f3a3",
    "module_progress_export": "8ccb9f1262790a744418d4212e072ee43031ab88"
  },
  "variants": [
    {
      "label": "before",
      "revision": "b257cdda1fbb4358d79cbefb5641b5db86b445f5",
      "repaired": false,
      "sources": {
        "calendar_export": "ef74cfdf50fd894327dbe45a9a9d43042953bc31",
        "cli": "ab071891721397a27ce87ce21a8380691bab365f"
      }
    },
    {
      "label": "after",
      "revision": "detached-blobs-9e4c05c8-6bf38ebf",
      "repaired": true,
      "sources": {
        "calendar_export": "9e4c05c88b53730414076fbc2069c9c293c64d76",
        "cli": "6bf38ebff1f0242be07f176050be39c7fae7890b"
      }
    }
  ]
}
```
