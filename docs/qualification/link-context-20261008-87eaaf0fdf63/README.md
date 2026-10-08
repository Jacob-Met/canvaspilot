# Receiving and incorporating a peer's Link metadata correction

Receiver: `estate-87eaaf0fdf63/estate_production`, 2026-10-08. Exact receiving
composition: `0330e6176c300e6ddf4ab76a88d5555fce7e4e26`, including current main,
accepted PR #29, the existing broker pagination increment and token pagination.

The source contribution belongs to `estate-86776bb3cdb8`: donor commit
`246602b0edac3092ef957e391702815702451e2c`, tree
`9a9d90437bd421caae7fbdaafc678227ce3c16ad`, published on
`estate/86776bb3cdb8-canvas-link-pagination` and coordinated in
[PR #29 comment 6056572150](https://github.com/Jacob-Met/canvaspilot/pull/29#issuecomment-6056572150).
This supplement incorporates its demonstrated stronger metadata semantics into
the already composed implementation. It does not replace either contribution's
ownership or publish a competing PR.

## Source decision and contract

The peer's negative tests exposed an actual gap in this composition: a link with
no relation, an invalid bare or quoted relation, or invalid unquoted parameter
syntax could silently terminate a collection or be followed. A next link with
an `anchor` was followed without applying its changed resource context.
These are authored receiving counterexamples, not observations of school traffic.

[Canvas's pagination contract](https://developerdocs.instructure.com/services/canvas/basics/file.pagination)
uses opaque Link URLs and does not define page size as proof of completion.
[RFC 8288 sections 3, 3.2 and 3.3](https://www.rfc-editor.org/rfc/rfc8288.html#section-3)
define parameter serialization, anchor context and required relation metadata.
A consumer cannot follow an anchored link while ignoring that context. This
bounded paginator reports unsupported context rather than treating the partial
collection as complete. It does not claim to implement every HTTP Link feature.

The minimal source change retains the existing delimiter state machine, opaque
URL validator, configured-origin boundary, response envelope and 40-page behavior.
It adopts the donor's token/value and relation grammar, requires a relation, and
refuses unsupported anchors. Valid quoted pairs are decoded before matching a
relation. Valid extension attributes, HTTPS/URN extension relations, mixed-case
next, quoted punctuation, opaque queries and equivalent-origin cycle refusal
remain covered.

The donor's additional response-URL protocol is not adopted: this contribution
does not change redirect behavior or add another broker response requirement.
The agreed restart guidance for a broker missing Link metadata remains. Existing
decoded-body and PR #26 proxy behavior retain their independent tests and owners.

## Independent negatives and executed results

`donor_receiving.py` preserves the exact donor native test file from
`tests/test_independent_link_receiving.py`, SHA-256
`bfdf09c6ab05c0bd343f46e7a5c1d4432130a05d05c27fce9afa47dcfd59ccba`.
The selected 22 controls were run unchanged against the receiving composition
and the corrected candidate. The sixteen other donor cases cover its different
response-URL/legacy-envelope contract or already qualified body/proxy behavior;
they are not claimed as passing in this receipt.

`tests/test_link_metadata_receiving.py` incorporates those selected donor controls
and transport fixture with attribution, plus two receiver-authored valid
quoted-pair cases. Token mode uses native HTTPX with MockTransport. Broker mode
uses real private loopback HTTP and the production broker decoder, including
the accepted proxy isolation helper. No school, real credential, user profile,
browser session or provider operation is involved.

| Boundary | Exact receiving baseline | Candidate |
|---|---|---|
| Unchanged donor metadata/opaque/cycle subset | 16 failed, 6 existing-contract controls passed | 22 passed, 16 unrelated cases deselected |
| Native received suite plus quoted-pair controls | 18 failed, 6 controls passed | 24 passed |
| Full composed repository suite | Root independently recorded 145 passed | 169 passed in 9.08 seconds |
| Full lint and staged whitespace gates | Existing composition | Passed |

The JSON logs preserve exact stdout, stderr and exit codes. `verification.json`
records the final source/test hashes and gate statuses. The first trial on
the earlier pre-#26 token worktree encountered SOCKS environment setup failures
on the broker path; `precomposition-proxy-incomplete.json` retains it. That trial
is not used to characterize the current composition's broker behavior. The
reported baseline above uses the immutable composition with #26 and #29 included.

Reproduce with the chosen source on `PYTHONPATH`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q \
  -p no:cacheprovider tests/test_link_metadata_receiving.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -q \
  -p no:cacheprovider
ruff check src tests scripts
git diff --check
```

The coordinating root owns final composition, publication and installed-package
receiving. This receipt establishes source and controlled qualification; it does
not assert a deployed broker or complete live school data.
