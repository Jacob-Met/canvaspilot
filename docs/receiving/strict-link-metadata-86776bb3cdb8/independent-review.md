# Independent receiving: Canvas Link metadata supplement

## Decision and exact source

Accept the parser-only supplement for transfer to the existing pagination owners. No implementation defect was found in the reviewed delta.

| Mode | Independently tested source | Exact parent | Result |
| --- | --- | --- | --- |
| Broker | `6c922bd13528d4f5d78072b9d2147358ec652cf6` | `9fb52df0fe5a6fc6d87b8f7869fd6e1e9b2e537a` | 11 passed, 11 deselected in 1.01 seconds |
| Token | `1f1188bff21ec194b46944aa1e9c4aab5ebe0a87` | `e678faaa4809ac0eddfd17228c1e940d19865217` | 11 passed, 11 deselected in 0.67 seconds |

Each independent command exited zero. Both used the same retained control file, SHA256 `82d880533c9b5be288cbc592088229ac5a2fae288c6d5fbbc2994f7bae2e42bb`, against isolated frozen receiving copies with an explicit source path. The command, runtime selection, exact source and log hash are in the two independent receipts.

This acceptance covers the narrow supplement and preservation of each owner's existing implementation. It does not replace the owners' qualification of their complete source or authorize publication to their branches.

## Consequential behavior

The controls verify that missing relation metadata, malformed quoted or unquoted relation values, and malformed extension parameters produce an incomplete-pagination error after the first request. An unsupported anchored link context is refused before a second request. A valid quoted parameter containing comma and semicolon delimiters, HTTP and URN extension relation types, and an opaque target query still traverse the collection successfully. Equivalent-origin cycles are rejected before repeating a read.

The parser requires a relation on each Link entry, validates HTTP parameter syntax, and distinguishes valid registered-style relation names from absolute URI relation types. General bare extension parameters remain legal. The existing field splitter continues to preserve quoted delimiters and escapes. The client deliberately refuses anchored contexts because it does not implement alternate link contexts; this is a conservative pagination policy, not a claim of complete RFC conformance.

Primary interpretation references: [RFC 8288 sections 3, 3.2 and 3.3](https://www.rfc-editor.org/rfc/rfc8288.html) and the [Canvas pagination documentation](https://developerdocs.instructure.com/services/canvas/basics/file.pagination). The Canvas contract makes the advertised Link authoritative and requires preserving opaque target URLs.

## Exact preservation

Both parent-to-candidate changes contain only `src/canvaspilot/pagination.py`. All other 39 broker leaves and 55 token leaves retain their exact modes and Git blobs. Every file in the 40-leaf broker source and 56-leaf token source matches its frozen Git object after the independent tests; both worktrees remain clean.

Within the changed file, `CanvasPaginationError`, `_origin`, `_split_fields`, `broker_path`, and `with_query` retain their exact source text. Only `next_link` changes among named definitions. The other top-level changes are `import re` and four parser regular-expression declarations. The changed parser and added declarations are identical in both modes, although their inherited query encoder implementations differ.

Consequently, this transfer preserves the owners' initial-origin admission, request encoding, collection validation, URL and equivalent-origin cycle handling, and broker decoding source. The retained patch passes a reverse application check on both exact candidates.

The independent controls use native HTTPX. Broker cases cross an actual local HTTP server and the native client decoder against authored envelopes. Token cases use an authored MockTransport. These receiving receipts do not claim an actual browser run or live Canvas access. The author separately retained the original failing metadata controls, the complete owner suites and an actual Chromium production-broker run; those are distinct evidence.

## Packet

- `source-preservation.json`: exact parent, candidate, tree, parser hash and preservation assertions.
- `test_link_metadata_receiving.py`: unchanged selected controls.
- `broker-independent.log` and `token-independent.log`: raw receiving output.
- The two corresponding `*-receipt.json` files: commands, source pins and exit results.
- `link-metadata-supplement.patch`: byte-preserved transfer patch.
- `file-hashes.json`: packet file hashes.

No broad suite was rerun by receiving after these focused controls and exact preservation checks. Root and the existing source owners retain integration control.
