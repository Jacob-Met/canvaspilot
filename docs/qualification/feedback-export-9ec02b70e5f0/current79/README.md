# Feedback export on the current provider-identity parent

Qualified repository: `Jacob-Met/canvaspilot` at parent
`79a2f2b2cbb7e74128d731cf096c7e86f1942d4b`, tree
`0114a6230c473c1ee1d01b99c7121c754b781d54`.

Runtime read main once at `2026-10-08T13:22:46.566Z`. Its exact tree showed that
PR45 had changed the CLI, README and the exporter's client/broker dependency
context. This worker fetched seven files only from that immutable commit and
reused other native files only after matching their Git blob IDs to the observed
tree. No additional branch refresh or GitHub mutation was performed.

## Composition and ownership

The two previously qualified export CLI additions and the one feedback README
section are inserted verbatim into the new parent. Removing those additions
recovers both entire current before-images byte for byte, including the native
calendar error handling added by PR45. There are six owned paths: README, the
feedback export guide, the CLI, the new formatter and its two test files.

All 22 materialized unowned files match the current tree, including all 12 prior
runtime modules, the feedback reader, current client, session broker and calendar
exporter. The formatter remains the CSS-qualified `a0db41dc` source. The guide and
both authored test files also remain unchanged. The complete 28-file source
manifest and the exact insertion/removal proof are in `verification/`.

This receiving increment adds no authentication, broker, calendar, account or
storage behavior. The new command continues through the existing feedback
reader and its configured native authentication path.

## Native receiving on these exact bytes

The focused run passed **97 cases, zero skipped**, in 37.98 seconds: the same 65
export/feedback cases qualified on the original parent, plus 32 unmodified
current PR45 calendar-session/provider-routing cases. The 65 include the 40
authored export cases and 25 existing API, HTTP, CLI and MCP feedback cases. The
32 current owner tests exercise the actual broker handler and queue with
authored browser work, plus page-selection/provider controls; they do not launch
a physical browser. Ruff passes for the four owned Python files.

All 28 source pins are identical before and after this run. The new-command
receiver retained 20 native CLI process records, 34 authored loopback Canvas
GETs and eight newly produced HTML sheets. A preexisting 23-byte file is retained
separately and is not counted as an export. Read, validation and existing-path
refusals keep their raw stderr, including native HTTPX logging before the final
JSON error. The process index maps the exact outputs and refusal outcomes.

The repository's whole test suite was not rerun. This is local source receiving
with synthetic fixtures, with no school account, live Canvas request, production
deployment, browser/printer device or learner-outcome claim. Runtime owns a
separate independent current-parent receiver; its status is recorded in its own
frozen packet.

## Earlier evidence remains separate

The original 55fe authored packet contains the absent-command control, the first
driver's stderr-parsing failures and the passing 65-case qualification. Its
original 91 files and the independent 21-file semantic packet remain immutable.
The CSS successor keeps its one-byte repair, before/after actual HTML, bounded
native/DOM receiving and the failed obsolete-API checker startup. Their source
pins and results are not relabeled as current-parent runs.

The allowlist uses the existing exact files, including `.source` suffixes for
intentionally nonstandard JSON control receipts. It creates no second full
source tree or large duplicate evidence archive. Shared-inode source files are
frozen; future changes must use a separate copy.
