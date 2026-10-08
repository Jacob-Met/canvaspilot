# Folder browser composed with the merged broker fix

The independently reviewed folder browser is composed on merged Canvaspilot
commit `874ad9c073fc5bab625e583849dbbe4eaf7fc6af` (tree
`de36f9d9ac3e8d93083b1ca8fba4ebc8b00fb62e`). The resulting 29-file source tree is
`b098eed93b0d26ac876b0282edccaa194069ce89`.

The same nine-file feature patch applied cleanly in an isolated Git worktree.
Compared with reviewed tree `fbc99e88b46328072ab8eaab23023b9b17dd1898`, 27 of 29
files remain byte-identical. The two differences are the inherited broker fix in
`client.py` and its composition with the folder command in `cli.py`. The client,
broker implementation and entire existing session CLI helper region are
byte-identical to the merged broker base. The folder helper, API, MCP wrapper,
tests, bundle entry and user documentation are unchanged from independent review.

## Actual receiving

| Receiving boundary | Result on composed source |
| --- | --- |
| Full existing and new pytest suite | 92 passed, 0 failures/errors/skips |
| Real client/CLI and native broker Handler under hostile proxy settings | 12 passed, 0 failed; native fixture exited 0 |
| Ruff across source, tests and scripts | All checks passed |
| Source identity after receiving | All 29 byte counts, SHA256 hashes and Git blobs matched |

The full suite includes the 33 folder cases: actual API/HTTP, public CLI
subprocesses, actual MCP stdio calls and the unchanged read-only broker Handler.
The twelve additional broker controls verify malformed `NO_PROXY`, a valid proxy
trap, public CLI status and shutdown, read-only and authentication refusals,
closed-broker behavior and preservation of direct Canvas proxy behavior. All
services and account-like values are authored loopback fixtures. No real Canvas,
normal browser, account, provider, deployed broker or downloaded file was used.

The independent review's seven normal and seven optimized tests apply to the
earlier exact reviewed tree and remain preserved in their original packet.
They are not relabelled as new independent executions of this composition.

`source-manifest.json` records this source; `runtime-receipt.json` records all
received source files, runtime versions, replay script hashes and counts.
`process-receipt.json` preserves the actual process completions. `full-suite.xml`
is the unmodified JUnit output and `proxy-receipt.json` retains the exact native
HTTP/job/proxy observations.

## Reproduce

Export base `874ad9c073fc5bab625e583849dbbe4eaf7fc6af` from an existing Canvaspilot
Git checkout into an empty directory and apply this directory's `candidate.patch`.
Check all 29 files against `source-manifest.json`, using the same SHA256/Git-blob
verification recipe in the author's receiving README. This patch changes only
the nine folder-feature files against the merged base.

Use the author's pinned receiving requirements in a fresh Python 3.12 environment.
From the reconstructed source, run `ruff check --no-cache src tests scripts`.
Then run pytest with the reconstructed `src` on `PYTHONPATH`, an unused
`CANVAS_PROFILE`, `CANVAS_BASE_URL=https://canvas.fixture.invalid`,
`CANVAS_SESSION_PORT=0`, and ambient Canvas token/proxy variables removed:

```sh
python -m pytest -q -p no:cacheprovider --junitxml=/absolute/path/to/new-result.xml /absolute/path/to/source/tests
```

The unchanged broker receiving helpers were already published at exact evidence
commit `483352a39560089121e30b78bae29508842148bf` under
`docs/evidence/broker-proxy-native-20261008/`. Extract `review_broker_proxy.py`
and `native_broker_fixture.py` into a separate replay directory with `git show`.
Their exact SHA256 values are recorded in this runtime receipt. With the same
neutral environment, invoke:

```sh
python /absolute/path/to/replay/review_broker_proxy.py \
  --source /absolute/path/to/reconstructed-source \
  --output /absolute/path/to/new-proxy-receipt.json
```

Receiving used the existing isolated Python 3.12.8 runtime read-only, HTTPX
0.28.1, MCP 2.3.0, Pydantic 2.13.5, pytest 8.4.2 and Ruff 0.16.10 on macOS 26.6.2
arm64. The scripts create their own listeners, authored broker worker, temporary
profiles and subprocesses. Neither captured source trees nor dependency trees
need to be published for reproduction.
