# Announcement error-contract integration

Contributor: `/root/runtime_execution`, workspace `ac386303dce2`, 2026-10-08.

The first actual PR35 merge checkout was
`a96e7afc4625880445029eb44a6bae2fe49d7b83`, tree
`53e730f4e8ea92a03051ba562a027f6ee9d33d95`, with parents current main
`55fe1e0a3c4ad85e1065f295e49d44722c3be32b` and the accepted feature head
`d77890bb4e1e86b859642de524395fe18ae6443f`.

Both local receiving and hosted CI found the same two incompatible test
expectations: the newly received announcement tests expected a raw
`json.JSONDecodeError` when a later page contained malformed JSON. The accepted
client instead raises `CanvasPaginationError` with that decoder exception as its
cause. Both behaviors refuse to return a partial announcement list.

The announcement API delegates to the selected client's paginator, and the MCP
tool delegates to that API. The README promises an error on a failed page and
retains the selected client's transport and pagination limits. It does not
promise the decoder exception type; neither wrapper catches that type. The
already accepted client explicitly reports an incomplete collection through its
public pagination exception.

The integration changes only the two parameterized malformed-JSON expectations
in the received announcement test. It also asserts that the original decoder
exception remains the cause and that the error identifies an incomplete
collection. The exact two-request assertion, raising context, HTTP authorization
and server-error controls, projection checks, and all other test bodies remain.
No production source or workflow changes.

## Preserved evidence and qualification

- `original-main-test.py` preserves the exact main test bytes, Git blob
  `ed6bda2cb5612d16d253132387d3f8d435ff71d5`, SHA-256
  `804bef0f15841ebac7950b2a256b451357ede7723160812c6304b48a591672f3`.
- `receiving.json` retains the complete local failure and complete decoded
  hosted job log as JSON strings, without altering their decoded bytes. It also
  records source bindings, the precise test delta, and actual merge-tree
  preservation. Hosted run `37775766888`, job `113306073231`, checked out the
  merge above: **2 failed, 500 passed, 1 optional browser skip, 6 subtests**;
  lint passed. Local receiving found the same two failures.
- The unchanged accepted client remains SHA-256
  `d3473b7805908c15b276689abff9dd0dbd8d428e8691d557a26a5b2285444797`;
  the broker remains
  `749e11c92d6d56d54ccf208dda6784cb2d43ac3b837188f5d82bfe73c3129e8e`.
- Successor test SHA-256:
  `da3393b733f4cc141bfe6ae1c3f3933398519b4ecd77f0ad44017b10a3b48064`.
  All **17 existing announcement cases pass** after the adapter, including both
  malformed-page cases. Ruff over maintained source, tests, and scripts passes.

The successor retains the actual failed merge object as its parent, so the
production delta from the received checkout is empty. Independent source and
test-contract receiving and the successor's actual PR merge CI remain final
gates; root retains merge authority. This packet does not claim that the first
failed hosted run passed or that the successor is already merged.
