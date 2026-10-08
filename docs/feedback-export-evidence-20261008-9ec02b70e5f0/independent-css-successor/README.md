# Independent CSS successor receiving

The one-byte repair is qualified on the frozen CanvasPilot `55fe1e0a3c4ad85e1065f295e49d44722c3be32b` source. The formatter changes from SHA-256 `3bc3f44f9d8f682fbf8442fed88e05d6148ecbf889e41c941ce65f067f59904b` to `a0db41dca9cce28c9fb7594c88ea6dc103b0f3104d5ba4d061bd93aaed92a714` by deleting exactly the literal `+` at byte offset 392. Its size changes from 20,918 to 20,917 bytes. All other 25 files in the original author manifest are byte-identical. All 26 donor pairs and 13 privately copied runtime modules match their before/after hashes.

## Actual receiving result

One fresh native `python -B -m canvaspilot.cli export-feedback` process completed successfully against the independently authored loopback fixture. It issued exactly the two unchanged assignment and self-submission GETs and created an actual 12,466-byte HTML file. The CLI digest receipt matches those bytes. Its supplied Canvas feedback fields equal the earlier reviewed file's fields; only the fresh capture timestamp is excluded from that equality.

The original review's actual 12,467-byte export is retained as a negative control. Existing cached jsdom 30.1.2 parses both actual documents with script execution and subresource loading disabled. It walks every CSS style rule, including the print rules, then passes each selector through the document's native `querySelectorAll` parser. The predecessor has exactly one rejected selector, `+:root`, with `SyntaxError`. All 35 successor selectors are accepted; its first `:root` selector selects exactly the document root. The actual stylesheet text differs only by the leading plus, and its root declarations are preserved.

This is structural HTML/CSS and source custody evidence. It does not claim a rendered print-layout inspection, a live Canvas account result, or receiving on the newer `79a2f2b2` parent. Current-parent overlap and receiving are recorded separately. No broad seven-method semantic rerun was performed for this one-byte change.

## Evidence and reproduction

`run/review.json` summarizes the result. The command, full stdout/stderr, authored responses, two observed GETs, both actual files, all parsed selectors, and source maps remain beside the two runnable probes. `execution.json` gives the exact invocation; pass equivalent paths to `verify_css_successor.py` for the frozen original author checkout, its CSS successor, and the original independent review. The review reuses the original independently authored loopback/HTML support after checking its SHA-256. It makes regular private copies of the 13 runtime modules before invoking the CLI.

`predecessor-preservation.json` verifies all 21 original independent packet files remain exact. The original author's 91-file packet was not edited. An initial small probe write failed during shared-storage exhaustion before any test invocation; `materialization-note.json` preserves that boundary. The successful run is the sole new native export invocation and finished in 2.92 seconds including the wrapper.
