# CanvasPilot selected-course file-name search receiving

Product commit: `94fb3a02a06b235dc46e25dab5c03012f202eec9`.
Product tree: `721a263dedbb1ad8a2d230eed536cbad35dbe89a`.
Canonical base: `56a72a2e2cee5ec04671d12ebe5bc2484afb8026`.

The feature searches returned file display names and filenames using literal Unicode
casefold substring matching across explicitly selected courses. It retains course and
row order, repeated occurrences, unavailable-name accounting and complete normalized
matching rows. It uses the unchanged paginated file metadata reader. The public
contract is frozen in `author/contract-v2.md`; user documentation is `../../file-search.md`.

## Accepted evidence

- `author/qualification-02/receipt.json`: 74 maintained native tests passed and changed-file Ruff passed. Product file hashes remained unchanged during qualification.
- `independent/oracle-freeze.json`: root froze its independent oracle before candidate exposure, using its own immutable baseline package from canonical Git.
- `independent/baseline-run/receipt.json`: the requested command was absent (exit 2, no HTTP request); the existing files command passed its actual two-page native HTTP and client lifecycle control.
- `independent/candidate-intake.json`: exact candidate source and all 1,614 unrelated base leaves independently received.
- `independent/candidate-run/receipt.json`: all 18 native CLI/client/private HTTP groups passed once, with zero failures, unchanged 33-file runtime source and the owned listener closed.

The independent tests cover selected-course pagination, normalized metadata,
argument validation before effects, empty/unavailable names, literal Unicode,
transport error identity, complete schema refusal, inclusive row and strict UTF-8
byte bounds, whole-result CLI failure, client closure/log restoration and byte
stability. Raw command stdout, stderr, lifecycle receipts and frozen controllers
are retained alongside their primary receipts. All receiving used synthetic private
HTTP; it does not establish a live school account or current remote file access.

## Preserved original failures

`author/baseline-01` retains the original incorrect `python -m canvaspilot`
invocation. The package entry point is `python -m canvaspilot.cli`; only that
invocation was corrected in contract v2. `author/qualification-01` retains the
original 73-pass/1-fail test run and seven Ruff findings. The test had incorrectly
required the existing files command to suppress its inherited HTTPX informational
logs. The existing command was preserved; the new test expectation was corrected.
Type-check boundaries and formatting were reconciled without changing the contract
or lint policy. The final distinct qualification run is retained in full.

`author/delivery-preparation-01/receipt.json` retains the inherited older-history
traversal failure (missing d33d54f50266e6ab9e7d13647a006d52a0f9ffd4). The complete
current tree and canonical base are present and pinned. Delivery therefore uses a
complete current source-tree archive and a bounded integration carrier with the
explicit canonical base prerequisite. It does not claim complete historical Git
custody. Donor refs and historical boundaries remain unchanged.

`copied-evidence.json` records every original native evidence path, size and SHA-256.
This directory adds evidence only; the six qualified product paths remain byte exact.
There were no live Canvas writes, file-content downloads, profile/service changes,
GitHub Actions, GitHub source writes, or LA7 calls in this task.

## Independent source acceptance

`independent/root-review.json` records root acceptance of the exact product after
reading the complete helper, the three additive CLI blocks and the guide. The
CLI inverse restores the original bytes, the README preserves every original
byte, and all 1,614 unrelated base leaves remain exact. The independently sealed
70,732-byte receiving ZIP and its manifest are retained without alteration.
