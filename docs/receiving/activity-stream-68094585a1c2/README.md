# Activity-stream API and CLI receiving

The source in this commit lets a learner run `canvaspilot activity` to collect
the available current-user global activity stream through CanvasPilot's existing
paginator. The Python method and existing MCP delegate keep their no-argument
interfaces. See the [activity guide](../../activity-stream.md) for usage and
returned-data limits.

Source owner: `chatgpt:68094585a1c2 / levenshtein_receiving`.
Independent receiver and source reviewer: `chatgpt:68094585a1c2 / root`.
Ownership and later integration status:
[CanvasPilot #94](https://github.com/Jacob-Met/canvaspilot/issues/94).

## Qualified source

Original main: `56a72a2e2cee5ec04671d12ebe5bc2484afb8026`.
Original tree: `a07c3e941219ff80968e1ff20528a63541bb7400`.

Only the existing activity API body, two additive CLI spans, one README paragraph,
a new guide and the maintained activity tests change. Exact inverse checks
recover the original API, CLI and README. All other inherited leaf identities
and modes are preserved when preparing the source tree.

| Native gate | Result |
| --- | --- |
| Original behavior | One-page API and missing-command CLI witnessed before candidate; original negative witnesses retained. |
| Original focused regression | 39 tests and 14 subtests passed. |
| Candidate authored qualification | 30 new + 39 existing tests and 14 subtests passed; all inputs exact. |
| Independent root receiver | 13 frozen groups passed through 27 real loopback GETs; all protected inputs exact. |
| Independent full source review | Exact inverses verified; product documentation accepted. |
| Native lint | Existing Ruff 0.16.10 passed the complete src/tests/scripts path set. |
| Exact patch admission | Native git apply --check passed on the untouched original checkout. |

The native runtime was the existing Python 3.14.4 / HTTPX 0.28.1 / MCP 2.3.0
environment. All qualification traffic used synthetic data and owned loopback or fixture
routes. No installation, user Canvas action or user browser session was used. Synthetic broker testing used its normal local POST transport
to carry Canvas GET jobs.

## Evidence

`author/` and `independent/` contain separate, unchanged capsules and manifests.
The author archive has 166 members; the root archive has 83. The author capsule
contains 134 materialized original files and all five candidate paths. Root's
contract, fixtures and receiver froze before candidate exposure; author tests
were withheld until its independent execution finished.

Standalone native receipts, root source review, the workflow guard, frozen
public contract and exact five-file patch provide direct entry points. Capsule
manifests record sizes, SHA256 identities, computed Git blob identities and modes.
Archive metadata timestamps are not execution timestamps.

The entire maintained test suite, hosted Python 3.12 CI, wheel/browser workflow and
live-school authentication remain unrun for this increment. The guide preserves
the endpoint's feed/history and message-truncation limits.

Current no-Actions direction:
[HAMON #143/comment6067592767](https://github.com/Jacob-Met/hamon/issues/143#issuecomment-6067592767).
Preparing these Git objects changes no ref or PR. A branch, merge, dispatch,
rerun or workflow change is outside this custody step. Required hosted gates
remain unrun; any subsequent publication is recorded separately in issue 94.
