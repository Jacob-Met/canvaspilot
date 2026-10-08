# Feedback export stylesheet successor

This is a bounded qualification of the CSS-only successor on CanvasPilot parent
`55fe1e0a3c4ad85e1065f295e49d44722c3be32b`. The separate `current79` packet owns
composition onto the later provider-identity merge. This receipt does not extend
the original parent's test results to that later source.

## Exact correction

The initial formatter's static stylesheet begins with `+:root`. The leading plus
makes that selector invalid. The successor removes only that byte, at UTF-8 byte
offset 392. Its formatter SHA256 is
`a0db41dca9cce28c9fb7594c88ea6dc103b0f3104d5ba4d061bd93aaed92a714`;
the original remains
`3bc3f44f9d8f682fbf8442fed88e05d6148ecbf889e41c941ce65f067f59904b`.

All other 25 materialized source files remain byte-identical. The Python syntax
trees are identical after replacing only the stylesheet constant. The original
91-file authored publication packet was rechecked against its frozen manifest.
Both formatter versions are retained as source evidence.

## Bounded receiving

One unchanged native CLI consumer passed, with the real feedback reader, two
authored loopback GETs and one newly written HTML file. The exact command,
stdout/stderr, process record and actual sheet are retained.

The DOM/CSS receiver reads that actual successor file and the original run's
actual file. Its seven controls pass: the original has exactly one invalid
`+:root` selector; all 35 successor selectors are accepted; the root receives the
expected foreground, background and light color scheme; the files differ only
by this stylesheet byte and their independently captured UTC save time; neither
contains automatic-resource elements or scripts. This uses cached jsdom 30.1.2
and Node 24.19.0. Default constructor settings disable automatic resource
loading and script execution. It is DOM/CSS evidence, with no physical browser,
layout engine, printer or live Canvas session qualification.

## Receiver correction retained

The first optional receiver assumed an older jsdom `ResourceLoader` export and
failed before inspecting either document. The same immutable driver was replayed
to capture its complete startup failure. The archived driver and raw failure
remain. The qualified driver uses the documented current constructor defaults
and checks actual DOM resource elements. This was a checker repair; it made no
additional product change and is not represented as a passing earlier run.

`verification/candidate-pins.json`, `verification/preservation-proof.json` and
`change.json` state the source boundary. `packet-files.json` is the allowlist for
this small successor receipt; its paths refer to existing exact files rather
than making another full source or evidence copy. Files shared by hard link with
older frozen packets remain immutable.
