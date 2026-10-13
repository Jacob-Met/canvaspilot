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
| `src/canvaspilot/cli.py` | `3bf4dffee67f2c1c9129f6dc6247eeb53ff37561` | `faf550a1c3c1ff8d1d131c4feb7867e642d749c8` |
| `tests/test_calendar_publication_cleanup.py` | Added | `8e0c8064d7b7b06861d7611860e78ba4269869f3` |

The first independent comparison used baseline
`b257cdda1fbb4358d79cbefb5641b5db86b445f5`, original CLI
`ab071891721397a27ce87ce21a8380691bab365f` and repair CLI
`6bf38ebff1f0242be07f176050be39c7fae7890b`. Those original modules and both
real HTML renderers remained identical at original repair parent
`29eb015351a4614bd8b09c58a3ef943f4da3caba`.

The table above identifies the subsequent composition onto main
`d96beb2a1b4de6ef5864446f78d9a3c56b2521a1`. It preserves that main's separate
MCP launch-options change. The final CLI is exactly the earlier repair plus the
existing five-line `mcp_main(base_url, token, profile)` call. No other CLI byte
changes in this composition, and the writer and test are unchanged.

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

## Received composition onto newer main

The separate receiver executed the composed CLI
`faf550a1c3c1ff8d1d131c4feb7867e642d749c8` with the unchanged accepted writer
and real renderers. All **284 after-side assertions** passed on the same Mac
with Python 3.13.7. The initial before course was not repeated. All three
cleanup-only CLI scenarios remain exit 0 / `ok: true` with a warning, and
after-side publication, no-clobber, primary-error and receipt controls pass.
This course qualifies those export paths; it makes no new MCP launch claim.

An independent reviewer also established exact full-file equality in both
directions: applying the six original cleanup edits to current main's CLI gives
the composed CLI, and adding current main's isolated MCP call to the previously
accepted CLI gives the same result.

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

The exact frozen comparison bundle is included as `comparison-bundle.json`.
Its SHA-256 is
`ad7552fb20d100b52410f59369da505e43f31f69afec415b74f9cdf2cc99fb56`.
It includes the exact original and candidate sources with their Git blob
identities and the unchanged real renderers. Run this independent course on
Python 3.11+ on POSIX/macOS without installing project dependencies. The receiver
uses POSIX user-ID, permission and symlink checks; Windows is outside this
receiver's portability contract:

```sh
python3 docs/verification/publication-cleanup-20261013/independent-receiver.py docs/verification/publication-cleanup-20261013/comparison-bundle.json
```

The receiver verifies each source blob before executing it. Its explicit
synthetic transport boundary and qualified scope are unchanged from the retained
acceptance receipt.

For the received newer-main composition, use the same receiver with its
separately retained after-only bundle:

```sh
python3 docs/verification/publication-cleanup-20261013/independent-receiver.py docs/verification/publication-cleanup-20261013/composition-bundle.json
```

Composition bundle SHA-256:
`d2f247a09e11fffa0e8ff7573fe66b1caf5c5657574071eb497b0d25a5c528f3`.

Composition receipt SHA-256:
`5b6ff882b8892a469c8a72e132e91f502d5f8c83ddb5900b7e90f61642f576a7`.
