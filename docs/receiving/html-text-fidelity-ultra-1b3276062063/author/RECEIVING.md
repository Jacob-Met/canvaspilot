# Author source qualification

Claim: https://github.com/Jacob-Met/canvaspilot/issues/106.
Baseline: 56a72a2e2cee5ec04671d12ebe5bc2484afb8026.
Candidate api.py: Git5ae5adc71d265cfe1d6a09e6a7edec3e2bddfa45,31113UTF8bytes,
SHA2562b74be6bb9903b4d4e01ac8435afba02c3afbef37a753f28a980a64d2b4ae9e5.
An earlier coordination message incorrectly gave31110bytes; the exact source/hash and receipts are unchanged.

The actual complete API and its two exact standard-library dependencies executed
in local orchestration CPython3.12.14 with an explicitly authored transport
substituted at the unavailable CanvasClient import boundary. All17 helper and
assignment-brief cases pass candidate; original passes12 and fails5 meaningful
prompt-fidelity cases. Each brief makes exactly one authored GET and preserves
input metadata. No filesystem/process/network effects were attempted.

Ten unchanged maintained unittest methods pass candidate; the same tests detect
17 failed subchecks and zero errors on original. Five existing test functions
pass both versions with the explicitly substituted FixtureClient. Their source
is unchanged; this does not qualify actual CanvasClient/HTTP behavior. Every
other top-level API AST node is unchanged. The exact patch permits independent
bytewise two-seam inversion.

The first candidate witness output was truncated by the author's tool output
bound; its exact raw result is retained. The single unchanged rerun supplies
the complete17-case receipt. No lost output is reconstructed.

No installed estate, live Canvas, account/session, OS CLI, browser, full-repository
suite, Ruff, or Actions result is claimed. Original receipts remain historical;
independent root and Mac receiving are separately attributed in their directories.
