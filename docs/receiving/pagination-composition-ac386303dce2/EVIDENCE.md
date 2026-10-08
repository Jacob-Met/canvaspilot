# Publication evidence and ancestry

The maintained source is frozen at `d3473b7805908c15b276689abff9dd0dbd8d428e8691d557a26a5b2285444797`
for `src/canvaspilot/client.py`. `QUALIFICATION.md` records the exact source
adaptations, failed controls, final 247-test result and receiving limits.
This index adds packaging details without rewriting that qualification or its
archived copy. [Independent acceptance](independent/QUALIFICATION.md) binds the
same frozen client and unchanged broker bytes.

## Published ancestry and received donor history

The final GitHub composition is intended to retain these published parents:

- Session-link receiver: `e20890089f6338de655a7c6ea7f0ada6d5c8fe6b`.
- Current parser supplement: `857a226d54c9784ca528bccc6ace7b4f02d90f4d`,
  whose parents already include the original parser increment and e208.
- Current main receiving: `a03a8637efad8ff22103a0c5018c93f7ecbb7d8d`,
  whose folder, feedback and calendar additions are preserved as described in
  [current-main/QUALIFICATION.md](current-main/QUALIFICATION.md).

The PAT source objects `2e51d58905d999e5fb8f3d34a7f56f17bf5f8c61` and
`e678faaa4809ac0eddfd17228c1e940d19865217` are genuine objects received read-only
from the contributing checkout. Both exact GitHub commit lookups returned 404;
the returned errors are retained in `pat-github-lookup.json`. They must not be
described as published GitHub parents. The `pat_parent` field in the earlier
`source-preservation.json` identifies the local donor source; it is not the
parent list for the final published commit.

`pat-donor-history.bundle` preserves both original object histories without
publishing or rewriting a donor-owned branch. It is 46,354 bytes, SHA-256
`d6ac4960d263b376b4f9717e6711e8e68ebbfa44be7e43ae6be67c373caa7a55`.
Its two heads are `refs/heads/received-pat-composition` at `2e51d589...` and
`refs/heads/received-pat-increment` at `e678faaa...`. Its four prerequisites are
ancestors already reachable from the published e208 receiver:

- `9c2b29b6152e40e45401511d0f80160ba22f18ea`
- `3d7a9453fb0cbdf08312320d71c648462592b217`
- `874ad9c073fc5bab625e583849dbbe4eaf7fc6af`
- `b0655cfc6f298c956fcdd27fbba32e3c5609516f`

`pat-bundle-receiving.json` records an author replay in a separate e208-only
repository: both donor commits were absent before the bundle fetch, then both
exact commit identities and source bytes were recovered. In an isolated
repository containing e208 history, `git bundle verify` and `git bundle
list-heads` inspect the bundle without changing a branch. The final composition
receives the PAT origin/query/completeness behavior described in the
qualification; the donor's different broker envelope is not adopted.

## Lossless source, test and negative evidence

`evidence.tar.gz` is 99,600 bytes, SHA-256
`34d1ee8de8b44f1105d303c56fa86e63d4858c0b0d01643ffaeb442c3267c60d`.
It contains 106 original files plus its internal `MANIFEST.json`.
`archive-members.json` is the same manifest in readable standalone form; each
entry records the original repository-relative path, size and SHA-256. Every
entry was compared byte-for-byte with its source before the archive was frozen.

The archive retains the original donor packets, all 18 current published parser
receiving files, the original parser packet, exact e208 source and superseded
compatibility tests, the immutable root policy probe, source pins, baseline
failures, first full-run fixture failure, final test logs and qualification.
Historical logs retain their original whitespace. Their old assertions and
success claims remain bound to their original source and policy; they do not
override the explicit older-broker policy or current anchor handling.

The selected publication tree presents these newly received raw packets through
the archive and its path manifest. The published parser parent also retains its
original packet paths in Git history. Existing e208 evidence paths are unchanged.
The separate Git bundle, GitHub lookup errors, bundle replay, this index and
subsequent independent receiving are not members of the already-frozen archive.

## Independent final receiving

The separate `independent/` directory provides readable qualification, test and
run receipts, plus a lossless archive preserving all 21 files and the exact
`file-manifest.json` supplied by the independent reviewer. That manifest's
SHA-256 is `0a7783477978c4bb5a8fa55a97734aeb8adb97da73ec6fa11406d7a76ad88503`.
All 22 received files were copied byte-for-byte and verified in the archive.
They include complete baseline/candidate source capsules, the unchanged
23-case authored-HTTP challenge, its original failures, normal and optimized
PASS transcripts, the independently recovered donor bundle and helper checks.
The two unchanged broker source capsules retain the original blank EOF, which
the new-file whitespace gate rejects. The failed staging output is retained in
`independent-staging-whitespace.txt`; [independent/EVIDENCE.md](independent/EVIDENCE.md)
explains how to extract the original bytes. No source or failure output was
normalized to satisfy that gate.

The independent qualification is SHA-256
`899ac0eb72fa253f844a85e828aaf5743ec2e2fb2f86a66cab3b254de808411b`.
It accepts the current source for the stated cross-transport and donor-history
boundaries, without claiming a live account, broker deployment or full RFC
conformance. `parser-parent-receiving.json` additionally records the author's
full-tree comparison with published PR37: all 32 newly received raw parser
receipt files remain byte-exact inside the archive and no unexpected source
delta was found. That comparison binds the prepared author tree before the
independent packet was attached; the frozen production source is unchanged.

## Inspecting the packet

To inspect the raw packet without overlaying a working checkout, run from the
composed repository root:

```sh
canvas_packet=docs/receiving/pagination-composition-ac386303dce2
sha256sum "$canvas_packet/evidence.tar.gz" "$canvas_packet/pat-donor-history.bundle"
canvas_review_dir=$(mktemp -d)
tar -xzf "$canvas_packet/evidence.tar.gz" -C "$canvas_review_dir"
```

The extraction directory contains the original relative paths and the internal
manifest. The publication whitelist and exact tree/source pins supplied to the
integrator identify the selected maintained files and standalone receipts.
No broker deployment, school-account access or live pagination success is
claimed by this packet.
