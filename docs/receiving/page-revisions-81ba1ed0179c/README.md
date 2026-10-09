# Recorded page revisions — native receiving

This contribution lets an authorized Canvas page editor list returned revisions and read one historical revision without reverting the current page. See [the user guide](../../page-revisions.md) for API, CLI and MCP usage and permission limits.

The exact eight-file product source is native commit a317417a8a2c39fb23256102904c24fba16a969a, tree 6ccc165bf75cb27c822d19c59ea6dc126297bbc0, based on canonical 6d445c68a5fd47df9368bebb879f5e3c372998ec. All 1,697 other parent leaves and all original shared-file content are preserved.

Native evidence is partitioned by who performed it:
- author-native.zip contains the original absence witness, 18 unchanged page tests, first 78-pass candidate run and lint negative, corrected 60-pass focused run, private declared-backend wheel receiving, source manifest and incremental Git bundle.
- independent-native.zip contains expectations frozen before candidate access, four actual API/CLI/MCP receiving groups, full raw loopback outputs, source and cleanup checks.
- static-peer.zip contains the separate complete source/diff/permission review with no product execution.

The archive bytes are original closed packets; qualification.json records their SHA-256 values and limits. The Git bundle inside author-native.zip explicitly requires its canonical base commit; it is not a complete repository backup. The built wheel is also retained there. No live Canvas account, broad full-suite, hosted CI, deployment or main integration is claimed. The public scope is https://github.com/Jacob-Met/canvaspilot/issues/117 .

No GitHub Actions, PR, main, workflow or dependency change is part of this feature-only retention.
