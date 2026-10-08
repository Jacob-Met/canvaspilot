# Hosted lint receiving addendum

The first PR #40 hosted run, [37767836872](https://github.com/Jacob-Met/canvaspilot/actions/runs/37767836872), failed its lint step and skipped pytest. It used Python 3.12.15 and Ruff 0.16.10, while the recorded local source gate used Python 3.12.14 and Ruff 0.11.4. The original installed dependency set and decoded job log are retained losslessly in hosted-ci-37767836872.json.

The three diagnostics were TRY004 on the top-level malformed-response ValueError and SIM117 on two nested context managers in the new native tests. The correction preserves the existing ValueError response contract with a narrow explanatory annotation and combines the test context managers in their original enter/exit order. It does not change the workflow, dependency declaration, API output, original exception identities, or incoming source.

The complete feedback production AST is identical to native a98da7d; the complete native-test AST is identical after normalizing nested single-child context managers into the equivalent multi-context form. The hashes and comparison results are in hosted-lint-repair-ast.json. All 25 affected semantic/API/CLI/MCP tests pass (8.220 seconds), and the existing explicit-path Ruff 0.11.4 source gate passes. Hosted Ruff 0.16.10 and the complete hosted suite remain a separate gate after publication.

One local orchestration attempt completed all 25 tests, then found that ruff was absent from PATH. Only lint was repeated with the existing tool's absolute path. This is retained in hosted-lint-repair-local-results.json and is not reported as a product test failure.

The original author, root and peer packets continue to describe their exact original freezes. The initial native archive and its d5b161eac824c23e9af8a437875bbc7fc6edae84 tree remain immutable historical receiving. This addendum documents the narrow descendant and does not relabel earlier execution as a run on new bytes.
