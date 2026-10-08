# Receiving with the current calendar export parent

Canonical main advanced to `a03a8637efad8ff22103a0c5018c93f7ecbb7d8d` through calendar export PR42. Native composition `5173b24285e9e3e2dda6b1d8158adea74e03bd52` has that parent plus the reviewed module-progress correction `96e4f3d37b4e2e222e30ff34a0bab96bed95b8cd`.

Git found adjacent parser and dispatch conflicts in `cli.py`. The resolved file was reconstructed from the exact current canonical CLI and the two exact reviewed module-progress blocks. Removing those blocks reproduces the entire canonical CLI byte for byte. The unresolved file and additive blocks are preserved here.

All **284 unrelated parent leaves** remain exact. Eight of the ten reviewed source leaves remain byte-identical; README retains the current calendar paragraph and the module-progress additions, and CLI retains both complete workflows. Client, session-broker, module reader and dependency configuration are unchanged.

To resolve the concrete routing risk, two existing CLI/MCP receiving groups were run against this exact composition and passed. They cover course/selection/errors/empty results and a real CLI/MCP normalized singleton response. The calendar parser's help route and repository Ruff also pass. The earlier 288-test full suite and 70-test correction suite remain separately pinned; no new full native suite on this parent is claimed. Hosted CI is the remaining whole-composition gate.
