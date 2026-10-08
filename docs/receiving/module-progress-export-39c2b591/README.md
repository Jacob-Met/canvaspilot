# Offline module-progress export: source and receiving

This contribution implements
[CanvasPilot issue 59](https://github.com/Jacob-Met/canvaspilot/issues/59):
`canvaspilot export-module-progress COURSE_ID --out NEW.html [--module-id ID]`.

The local HTML report preserves the existing reader's normalized observation,
including module and item order, declared states, raw unsupported values,
all-versus-one rules, prerequisites, thresholds, diagnostics and coverage. Its
JSON download retains the complete original normalized object. The report uses
no scripts or external resources and provides local module navigation and print
styling. It calls the existing progress API once, uses the existing new-file
publisher, and changes no reader, client, MCP, authentication or dependency code.

## Exact qualified source

The original product is native commit
`dbb4a4fa04c25849a079f89a67b3049a2f55946f`,
tree `f17362750896b2834b4321151403b61e64429486`, on public
`a5ce672e5b3580c1f52e13c49eefee830f11346c`.

The current composition is native merge
`2fada92331765b70a7c7ec3864d3ed261901c06f`,
tree `056e1f28301c0a9e0de497284aaf512d119f5a60`, with ordered parents
the original product and public current
`0480cbce421bae532e3e909899fc8fb83789e878`
(tree `f9ecaa4311d93cfe3a1fd1c9cc140834e2449341`).

The six product/test/doc paths remain the complete feature scope. The renderer,
guide and both tests are byte-identical to the accepted original product.
Removing the frozen CLI spans and README paragraph from the composed files
restores the exact current-main files. Every other current-main blob, including
the new discussion, agenda, announcement, API, MCP and bundle work, is retained.

The current API differs from the original API only by the added
`discussion_thread` and `course_agenda` methods. Removing those additions
restores the complete original API AST. The progress reader, client, publisher,
package/dependency specification, module fixture and CI workflow are byte-exact.
The product tree has 1,111 leaves, from 1,107 at the current base.

## What ran

[Authored results](author-results.json) retain the initial native failure and
corrections, final gate, actual browser observations and original runtime pins.

- The final original source passed 34 new tests and strict Ruff. The initial
  relevant run also passed 144 unchanged module-reader, item and publisher
  controls. Its sole failure was an authored 403 exception-class expectation;
  the existing client correctly raised CanvasAuthError and preserved refusal.
- Five authored actual browser groups passed at desktop and 320 px, including
  the real JSON download, module navigation and print media. Visual inspection
  moved navigation before the lengthy metadata; the original receipt remains.
- The [independent receipt](../module-progress-export-independent-39c2b591/REVIEW.md)
  accepted the frozen product after five native groups (four product children,
  eleven GETs) and 19 actual offline Chrome assertions with JavaScript disabled.
  Every displayed data value and diagnostic matched an independently frozen
  original-reader observation. The actual 10,438-byte download was identical
  to that baseline stdout. Its authored fixture, raw failures, screenshots,
  observations and executable receiver are retained unchanged in the adjacent
  namespace.
- The current-source composition ran four bounded CLI children: help, full
  export, selected export and the existing progress command. All passed with
  twelve GETs. Complete and selected JSON bytes match the original qualified
  observations; the full JSON also matches the actual current original command.
  Holding the original recorded creation times reproduces both previously
  browser-qualified HTML files byte-for-byte. Current strict Ruff passes.
  The new export commands emitted no stderr; the unchanged original command
  retained ordinary HTTPX logs.

[Current composition](current-composition.json) contains the exact command
streams, source correspondence and deterministic artifact comparison. No
browser or broad suite was repeated for unchanged renderer and reader inputs.
The independent original-source receipt is not relabeled as a later-current
execution.

## Preserved failures and limits

The normal current merge initially conflicted in the CLI. The frozen additive
spans were applied to the exact current CLI and verified by byte inversion.
An initial whitespace check over the entire incoming merge reported context
spaces in already integrated discussion evidence patch files. Those owner
blobs are unchanged. The six-file delta against the current base passes.

The original native test failure, first strict-lint findings, helper parse
failure, ThinkPad intake timeout, independent Mac capacity stop and unsuccessful
Windows debugger startup remain recorded. The independent browser later passed
on Mac after capacity was externally restored. It retains allocator/display
and teardown stderr; no warning-free browser claim is made.

These are synthetic read and local-file results. They establish no live school
session, learner outcome, raw-provider-page completeness, Windows browser pass,
physical printing, PDF production, deployment or integration. Counts describe
returned rows and the UTC timestamp describes report creation. Product use and
limits are in the [export guide](../../module-progress-export.md).

## Durable complete artifacts

[Artifact custody](artifact-custody.json) binds the original full native source,
author's 113-file sealed packet and complete independent raw container to their
exact manifests and bundles. The author packet remains at
/Users/me/hamon-canvas-module-export-39c2b591-v1/receiving-v1.

The independent packet remains at
/Users/me/hamon-canvas-module-independent-39c2b591-2gsod2r2/receiving-v1.

Its 29 publication entries are preserved byte-for-byte here, including all
72 raw files and original failed attempts in the verified lossless container.
