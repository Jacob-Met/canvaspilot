# CanvasPilot pagination receiving — independent correction

## Result

Independent receiving reproduced the author's complete native suite at frozen
commit `fd3996aada3f34b7093fa361eb7e423c4c587d90`: 108 passing tests and two
mode-only skips, including the actual isolated Chromium browser path. This
commit composes on current main `874ad9c073fc5bab625e583849dbbe4eaf7fc6af`, which
includes PR #26's loopback proxy-environment isolation.

The receiver found an incomplete-result boundary in the new Link parser's
stated refusal contract. Missing relation metadata, invalid bare or quoted
relation values, and unsupported anchor contexts could return the first page
as complete or follow a link belonging to a different resource context.
These are authored counterexamples; they are not claims about observed school
traffic or a newly introduced regression in the previous numeric paginator.

A 2,536-byte source supplement now corrects that boundary in this receiver's
isolated worktree. The same 38 independent cases retain 18 failures and 20
passing controls on the frozen candidate; all 38 pass with the supplement.
The full native candidate suite still passes 108 tests with two skips after
the supplement, including actual Chromium. The author has received the exact
patch, new test source and immutable hashes for incorporation. This receiver
has not changed the author's files or published remotely.

## Defects and bounded source correction

`_LINK_VALUE` admitted arbitrary non-delimiter characters in bare values.
For example, `rel=<next>` and `rel=next/prev` parsed successfully but did not
match `next`; collection retrieval then returned only its accumulated rows.
The frozen candidate also accepted a Link value with no `rel` parameter.
Quoted malformed relations such as `rel="<next>"` or `rel="next/prev"` had the
same incomplete-completion result.

The supplement uses the existing HTTP token character grammar for unquoted
parameter values, requires a relation, and validates each relation word as a
registered-style relation name or an absolute URI extension relation. It
retains case-insensitive `next`, quoted parameters, quoted punctuation,
`title*`, multiple relation words and opaque URLs. The valid control includes
both an HTTPS extension relation and a URN; neither is dereferenced.

The candidate also followed `rel="next"; anchor="..."` without applying the
changed context. The supplement refuses anchored Link metadata explicitly
because this paginator does not implement that context selection. It does
not silently discard the anchor and follow the target. This is deliberately
a bounded Canvas pagination policy; no general RFC-conformance claim is made.

Primary contract references read during review:

- [Canvas pagination](https://developerdocs.instructure.com/services/canvas/basics/file.pagination): follow the returned Link metadata and preserve its opaque URL parameters; page size is not a completion signal.
- [RFC 8288, section 3](https://www.rfc-editor.org/rfc/rfc8288.html#section-3): parameter value serialization.
- [RFC 8288, section 3.2](https://www.rfc-editor.org/rfc/rfc8288.html#section-3.2): anchor changes the resource context; a link cannot be processed while ignoring that context.
- [RFC 8288, section 3.3](https://www.rfc-editor.org/rfc/rfc8288.html#section-3.3): relation presence and registered/extension relation syntax.

## Independent receiving coverage

`test_independent_link_receiving.py` uses the actual Canvas client in both
auth paths. Token requests use native httpx with an authored MockTransport.
Broker requests traverse actual loopback HTTP and the existing client broker
decoder, against authored response envelopes. This is distinct from the
author's actual Chromium-to-native-broker integration test, which the receiver
also ran as part of the complete native suite.

The independent cases cover malformed and absent relation metadata, changed
anchor context, quoted valid metadata and extension relations, repeated
query parameters and opaque punctuation, canonical host/default-port cycle
refusal before a duplicate request, invalid broker response URL metadata,
and original dictionary-after-list compatibility. Eight cases preserve the
public `broker_fetch` body contract, including false, zero, empty strings,
empty objects/lists, JSON null text, plain text and absent bodies.

An actual local-HTTP test supplies a malformed `NO_PROXY` value and proxy
variables pointing at an unused loopback port. Both collection retrieval and
ordinary body retrieval still succeed through the private fixture server.
The test therefore exercises the composed PR #26 proxy-isolation path instead
of clearing the environment and assuming compatibility.

`pr26-preservation.json` independently compares source spans and confirms that
`_broker_request`, `broker_health`, existing auth/default helpers and the
complete PR #26 `cli.py` are unchanged from the current main base. The
supplement only modifies the newly introduced Link parser span.

All fixtures are disposable. No existing browser profile, authenticated
school session, provider, task submission or production Canvas operation is
used. Existing raw scalar/dictionary behavior is preserved intentionally;
this repair does not redefine every endpoint as a homogeneous list.

## Exact files and reproducibility

| Item | SHA-256 |
| --- | --- |
| Frozen candidate client | `5f9668dccbacf760f2ade39135a227c00f9cdb1ea5c09bf4b0836bef29a0e24a` |
| Corrected client | `5eac822e4b2e6584b1d2e6a7ff24634cebfffd6635c859b6c075c9a3968c724a` |
| Source supplement | `9d0aff501a85feb25c5b3702e68638d71cde145291bc61b617725ff1a662d595` |
| Independent test source | `fa54a90e76b4f294349e486eed254dc0c5097aa1535c8a7c1f89fdb937fcd7a4` |

Corrected client Git blob:
`ab95d581541019f2c2fc4ba77f3f37b52f25a0a1`.
`review-source-receipt.json` retains all source, patch and raw-result hashes.

From an isolated checkout of the frozen candidate, apply
`link-metadata-review.patch` and place the independent test in that checkout's
test directory. The patch passed strict `git apply --check` against the exact
frozen candidate and the corrected worktree passed `git diff --check`.

```sh
PYTHONPATH=/absolute/checkout/src python -B -m pytest -q /absolute/test_independent_link_receiving.py
```

The recorded native invocation also set `CANVASPILOT_TEST_CHROME` to the
existing isolated Chromium executable and ran the complete project suite.
Logs: `candidate-suite.txt`, `final-before.txt`, `final-after.txt`, and
`corrected-native-suite.txt`. Earlier narrower successful correction trials
remain in `independent-before.txt` and `independent-after.txt`; the final
38-case results supersede those counts.

The author's eventual incorporation commit must be read back to confirm
these exact source bytes before final source acceptance. The existing GitHub
content-creation rate limit remains a separate publication blocker; this
receiver made no remote write retry or alternative-channel attempt.
