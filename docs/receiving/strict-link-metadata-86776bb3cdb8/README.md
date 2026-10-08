# Strict Link metadata: transfer to the existing pagination owner

**Use the existing 87ea broker/token implementation with PR #29, then apply this
one-file parser supplement.** The existing 87ea/a342 receiver retains integration
ownership. This packet contains only the transferable correction and its evidence.

## Why this combination

Both owner paths pass three of our eleven focused controls, but fail eight:
missing/invalid relation metadata or malformed bare parameter values can return
a collection successfully, and two anchored next links are followed while their
changed context is ignored. The supplement requires valid parameter and relation
syntax and refuses unsupported anchor contexts before another request.

Reciprocal controls also show four advantages in the owner's implementation.
It refuses foreign initial URLs before any request, preserves initial absolute
URL filters, retains an existing initial query alongside caller parameters, and
refuses a non-list page that still advertises next. All four pass there and fail
on our earlier whole composition. Their implementation is therefore the receiving
base; these parser controls are the contribution to transfer.

The contract basis is [RFC 8288 §§3, 3.2 and 3.3](https://www.rfc-editor.org/rfc/rfc8288.html)
and [Canvas's opaque pagination contract](https://developerdocs.instructure.com/services/canvas/basics/file.pagination).
The existing conservative refusal of repeated relations remains. Anchored
pagination is unsupported and explicitly refused; full RFC conformance is not
claimed. These are authored malformed-response controls, not observed malformed
Canvas traffic.

## Exact patch and controls

`link-metadata-supplement.patch` changes only `src/canvaspilot/pagination.py`
(27 additions, 10 deletions). It preserves the owner's URL admission, encoder,
opaque cursor handling, cap, single-object policy, error redaction and client
source. Its SHA-256 is
`88f75568d31c7f243525ba1a630994e77f81449c20e031015a2bcde44530d047`.

The byte-exact 22-case receiving test is archived as
`test_link_metadata_receiving.py.txt`, SHA-256
`82d880533c9b5be288cbc592088229ac5a2fae288c6d5fbbc2994f7bae2e42bb`.
Restore a `.py` filename to execute it. The maintained source copy removes only
one extra blank line at EOF for the whitespace gate; its AST is unchanged and
its SHA-256 is
`7504ae1555cda7b1a2d86799cff3d97c5f6157931e21228545d4505e5acf4c50`.

| Path | Exact owner base | Accepted supplement | Before → after |
| --- | --- | --- | --- |
| Broker + encoder | `9fb52df0fe5a6fc6d87b8f7869fd6e1e9b2e537a` | `6c922bd13528d4f5d78072b9d2147358ec652cf6` | 8 failed / 3 passed → 11 passed |
| Token | `e678faaa4809ac0eddfd17228c1e940d19865217` | `1f1188bff21ec194b46944aa1e9c4aab5ebe0a87` | 8 failed / 3 passed → 11 passed |

Independent receiving repeated both passes and verified all 39 other broker
leaves and 55 other token leaves unchanged. `source-preservation.json`,
`independent-review.md`, and the two receiving receipts retain that acceptance.
Raw negative and passing logs remain separate.

The unchanged owner suites pass 118 broker and 129 token tests. Actual fresh
Chromium through the production Handler/queue and assignment API retrieves all
three assignments across an empty intermediate page and exact opaque URLs.
The isolated two-file child on the owner's combined source
`0330e6176c300e6ddf4ab76a88d5555fce7e4e26` is
`a2fbc58fd4ff19651184d8d04658ed457d69b4f7`: its complete suite passes
167 tests. That owner base includes main `3d7a945` but predates latest main
`5b1780c` and module-items PR #31; it is not described as current-main adoption.

Ruff 0.13.3 passes both owner trees. Ruff 0.16.10 passes the changed parser and
receiving test, while flagging three unchanged owner spans: client import
formatting, a test-worker broad exception, and a static string join. Those
version-specific findings remain with the receiving owner.

## Apply and receive

Check the exact target source, apply the patch, and add the maintained controls
only after both broker and token paths use the owner's parser. On the final
combined source, all 22 controls must pass without a mode filter. The separate
broker-only intermediate uses `-k broker`; the token-only comparison uses
`-k 'not broker'`. The reciprocal archive selects only
`foreign_initial or same_origin_absolute_initial or initial_path_query or non_list_with_next`.

The final owner branch and current-main merge require exact source preservation
and their native gates. This packet advances no branch or main reference.
All data, tokens and browser routes are synthetic; no school account, existing
profile, live provider, installed broker or external message was used.
