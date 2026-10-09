# Assignment text fidelity qualification

Issue [106](https://github.com/Jacob-Met/canvaspilot/issues/106) repairs comparison
text loss and quoted-attribute leakage in the existing shared text helper.
Only its recognizer constant and function body change in the existing API.
All other API methods/imports and existing tests remain exact.

| Evidence | Actual result | Boundary |
| --- | --- | --- |
| Author original/candidate witness | 12/17 then17/17 | Complete API and authored fixture transport; no real CanvasClient |
| Ten maintained methods | Original17 failed subchecks/0errors; candidate allpass | Exact tests and full API executed in localCPython3.12.14 |
| Five inherited test functions | Both pass | FixtureClient explicitly substituted; not HTTPX/realclient qualification |
| Independent consumer | Candidate15/15 | Complete API + exact sibling modules, one fixtureGET/close each, full metadata/custody |
| Independent compatibility | Original13/14 thencandidate14/14 | Frozen helper cases, exact two-span byte inversion |

The root's first baseline execution transport never returned a PID/exit/output;
its result remains UNKNOWN and was not retried. Its checkpoint reconstruction
and candidate-preparation failure are preserved in the consumer source record.
The author's first candidate output was truncated by its tool-output budget;
only the single unchanged complete rerun supplies the17-case receipt.

- [Author evidence](author/RECEIVING.md)
- [Independent consumer acceptance](independent-consumer/ACCEPTANCE.json)
- [Independent compatibility review](independent-compatibility/REVIEW.json)
- [Integration preflight](integration/PREFLIGHT.json)
- [Contribution custody](CONTRIBUTION.json)

No full repository suite, Ruff, installed estate, real CanvasClient/HTTP, CLI,
browser, live Canvas or beneficial real-task use is asserted. Historical source
and raw receipts retain their actual pins and outcomes. Archived harnesses have
.py.txt names; their bytes are unchanged and they are not new lint/test targets.
No GitHub Actions execution is part of this contribution.
