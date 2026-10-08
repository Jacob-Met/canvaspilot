# Independent receiving: PR35 broker Link parser correction

## Acceptance

Accept the bounded parser transfer at `9d1ac4b64a1d036bb0c7f4331892d26dc9f2bf82`, tree `0d96f5d8ad4711e20c2e92109bbd16bc123671d9`, on exact published PR35 parent `89fa86d20e4eff47ce42e18afd8cd8e75ab376c3`.

The independently executed ten broker HTTP controls passed in 1.18 seconds with process exit zero. They use authored loopback HTTP responses and the native client decoder, selecting the actual PR35 capability and response-header protocol. All input cases and assertions in their three test bodies match the earlier independent controls after removing the mode parameter. No browser, token traversal or live Canvas claim is made by this run.

| Artifact | SHA256 |
| --- | --- |
| Candidate client.py | `3b2453dd923328042c8bbe1178ac3c004536aa0b075d7c84c3ce15f556f4d0da` |
| Maintained receiving test | `152c84702730e1036eaebd4beedbcbcf3e5f16c92cd7afd678035ebd2ab13395` |
| Independent native log | `d95ab5208d03a6d6fb5f379190e03afc2a57e568537e3505bb35985fdfe39f64` |
| Independent native receipt | `a8003c8f4c02be1394b695f3b47962fb52491ce84c66afe7b85fd3403cd6ae0d` |

## Exact source preservation

The parent has 55 leaves and the candidate 56. The four changed paths are README.md, client.py, the existing broker Link test file, and the newly maintained receiving controls. All 52 other parent leaves preserve their exact modes and blobs. Every candidate file matches its frozen Git object after the independent run, and the checkout is clean.

Among client named definitions, only `_session_link_next` changes. The complete `CanvasClient` class and the other twelve named definitions retain their exact source text, including the legacy token parser, traversal and origin-admission helper. Outside that parser function, only the unquoted parameter-value grammar changes and a relation-pattern declaration is added; all other top-level AST nodes are unchanged.

The existing broker fixture changes one media-type parameter from unquoted `application/json` to its quoted form. The slash is outside the HTTP token grammar. All other bytes of that test file remain exact. README gains exactly four lines describing the parser policy.

## Demonstrated behavior and limits

Missing relation metadata, malformed relation values and malformed parameter syntax are refused after the first request. Unsupported anchor contexts are refused before following another collection. Registered relation names are handled without regard to case. The positive control preserves an opaque query with comma, semicolon, escaped slashes, repeated parameters, an empty value and a literal plus while also exercising quoted parameter delimiters and HTTP/URN extension relation types.

This acceptance concerns those parser behaviors and the preserved source boundary. The existing equivalent-origin cycle-normalization gap remains a separate traversal issue. The token path is unchanged. Older brokers still use PR35's existing compatibility path. This review does not claim complete RFC conformance or acceptance of those separate behaviors.

The native command and runtime source path are retained in the receipt. Root and the existing source owner retain publication and integration control. Shared overlay exhaustion required a task-exclusive RAM checkout; these small receipts should be retained with the durable source contribution before that temporary checkout is removed.

## Packet

- `independent-broker-controls.log`: raw native output.
- `independent-broker-controls-receipt.json`: exact source, command, runtime, exit result and hashes.
- `source-preservation.json`: complete scope, blob and AST preservation assertions.
- `file-hashes.json`: packet hashes.

Primary syntax reference: [RFC 8288](https://www.rfc-editor.org/rfc/rfc8288.html), especially sections 3, 3.2 and 3.3. The [Canvas pagination documentation](https://developerdocs.instructure.com/services/canvas/basics/file.pagination) supplies the authoritative Link and opaque-URL contract.
