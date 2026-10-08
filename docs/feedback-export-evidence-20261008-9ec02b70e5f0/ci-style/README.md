# CI-only style successor

The first ready PR60 run failed lint before executing the full test suite. The exact hosted job log is retained alongside the source proof.

Two import arrangements were corrected. Four explicit TRY004 annotations preserve the qualified ValueError contract for invalid Canvas input; changing those public exceptions solely to satisfy a style rule would change the existing behavior. The production CLI and formatter ASTs are equal before and after. The test module retains the same imports and every non-import statement and assertion.

This packet is a style successor to head01774ea46b07d01a56e6b4f42f33ad83029ad9f9, not another native receiving result. Historical source hashes and earlier observations remain attached to their original generations. The current hosted lint and full test suite are the remaining gate.
