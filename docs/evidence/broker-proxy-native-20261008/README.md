# Canvaspilot broker proxy receiving — 2026-10-08

The unchanged PR #26 candidate passes **12/12 receiving groups** and the inherited **59-test suite**. The unchanged main baseline passes the five controls and fails the seven proxy-sensitive groups, as expected. The native client, public CLI, and real broker `Handler` are exercised over disposable loopback HTTP. No real Canvas account, browser, provider, or installed broker participates.

## Source and runtime

| Item | Exact value |
| --- | --- |
| Repository | `Jacob-Met/canvaspilot` |
| Candidate / PR #26 | `68a9a931c4b5c69fe0930dfb23b36919209818f0` |
| Baseline main | `b0655cfc6f298c956fcdd27fbba32e3c5609516f` |
| Candidate client blob | `ef2dd3f418242b02edae49a1d37a516101a30cf8` |
| Candidate CLI blob | `c00f7d12f52ba162b10930b965298b6364d4dab3` |
| Shared native Handler blob | `ba23543f62e6be9f611ae06260b91f239206cb23` |
| Native Python | `3.12.8`, Clang 16, macOS arm64 |
| Qualified httpx | `0.28.1` |
| MCP / Pydantic | `2.3.0` / `2.13.5` |
| pytest | `8.4.2` |

Both source manifests cover every tracked file: 25 files per source tree. Only `src/canvaspilot/client.py` and `src/canvaspilot/cli.py` differ between candidate and baseline. The native `Handler`, all seven inherited test files, and all other project files are identical. Complete tree retrieval checked each Git blob before execution; `runtime-receipt.json` verifies all 50 files again afterward and records every installed distribution and the exact authored test hashes.

The project declares `httpx>=0.27`; it does not lock httpx to the qualified version. This receipt demonstrates the reported httpx 0.28.1 failure and the repair at the stated runtime. Importing the public package eagerly imports MCP, so the qualification installs real declared MCP/Pydantic dependencies instead of substituting a module. An initial minimal environment lacking MCP stopped during import, before a native listener was created; the completed runs use the full dependency set recorded here.

## Results

| Receiving group | Baseline | Candidate |
| --- | --- | --- |
| Dependency reproduces `InvalidURL` with `NO_PROXY=[::1]` | Pass | Pass |
| Native health and fetch with no proxy configuration | Pass | Pass |
| Native health with malformed `NO_PROXY` | Fail | Pass |
| Native fetch with malformed `NO_PROXY`, duplicate query keys and Unicode | Fail | Pass |
| Public `canvaspilot whoami` with malformed `NO_PROXY` | Fail | Pass |
| Public `canvaspilot session status` with malformed `NO_PROXY` | Fail | Pass |
| Broker bypasses a valid proxy configuration | Fail | Pass |
| Actual native read-only rejection | Pass | Pass |
| Authored upstream 401 retains `CanvasAuthError` | Pass | Pass |
| An unavailable broker returns cleanly under malformed `NO_PROXY` | Fail | Pass |
| Direct Canvas token mode retains proxy support | Pass | Pass |
| Public `canvaspilot session stop` reaches native shutdown under malformed `NO_PROXY` | Fail | Pass |

Candidate receiving made 14 native HTTP requests and dispatched seven authored queue jobs. No broker HTTP request reached the proxy trap. Its sole proxy request was the deliberate direct-token-mode control with a synthetic token and a loopback destination. Baseline receiving made four native HTTP requests and dispatched two authored jobs; its broker health request incorrectly reached the proxy trap under otherwise valid proxy configuration. The other baseline proxy request was the direct-token control.

The native read-only rejection does not enqueue the authored write. Native upstream-auth refusal remains an error. The candidate's final CLI stop invokes the actual native `/shutdown` route, which exits only its disposable child process. The baseline child is closed by the authored fixture cleanup because the broken CLI cannot reach that route. Both children exit zero, with empty native stderr. Test-driver exit codes are candidate 0, baseline 1, and inherited pytest 0. Baseline exit 1 is the expected negative-control result, not a passing candidate qualification.

## Reproduction

Retrieve both commit objects through an authorized existing git repository. If either object is absent, fetch the repository's PR #26 head and main through the normal authorized GitHub path first. The preparation script performs local `git show` and `git ls-tree` reads only; it does not fetch, move refs, check out branches, or replace differing files.

From this evidence directory:

```sh
python3 prepare_sources.py --repo /path/to/authorized/canvaspilot-checkout
python3 -m venv receiving-venv
receiving-venv/bin/python3 -m pip install -r requirements-receiving.txt
receiving-venv/bin/python3 review_broker_proxy.py --source head --output actual-candidate-receipt.json
receiving-venv/bin/python3 review_broker_proxy.py --source base --output actual-baseline-receipt.json
```

The second receiving command should exit 1 and report precisely the seven failures above. Each run removes any inherited `CANVAS_API_TOKEN`, supplies an unused temporary `CANVAS_PROFILE`, creates its own ephemeral broker/proxy/direct-fixture ports, and restores proxy variables within its own process. It never alters the system home directory or a user profile. Every CLI command is executed through the real `python -m canvaspilot.cli` entry point.

Run the inherited suite with an absolute path to this evidence directory stored in `RECEIVING_DIR`:

```sh
RECEIVING_DIR="$(pwd)"
env -u CANVAS_API_TOKEN -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u NO_PROXY \
  -u http_proxy -u https_proxy -u all_proxy -u no_proxy \
  CANVAS_PROFILE="$RECEIVING_DIR/pytest-unused-profile" \
  CANVAS_BASE_URL=https://canvas.fixture.invalid PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="$RECEIVING_DIR/head/src" \
  "$RECEIVING_DIR/receiving-venv/bin/python3" -m pytest -q -p no:cacheprovider \
  "$RECEIVING_DIR/head/tests"
```

The reference run reports `59 passed in 7.36s`. `process-receipt.json` preserves the three receiving process outputs and exit codes. `verify_receiving.py` checks the two generated trees and records distributions; pass `--output` to preserve the reference runtime receipt:

```sh
receiving-venv/bin/python3 verify_receiving.py --output actual-runtime-receipt.json
```

`candidate-receipt.json`, `baseline-receipt.json`, and `runtime-receipt.json` are the reference evidence. Preserve them when replaying. The generated source trees, temporary venv, profiles, bytecode, and actual replay output are excluded from publication. The manifests and preparation script reconstruct the sources from their immutable Git objects without shipping captured dependency trees.

## Qualification boundary

The broker's `Handler` and its HTTP methods are unchanged. An authored queue worker supplies status, fetch responses, upstream 401, and shutdown acknowledgment at the point where the real browser worker would normally respond. The test never calls `_browser_loop` and does not qualify SSO, a live Canvas service, browser-cookie custody, broker authentication design, or installed estate rollout. It confirms that PR #26 repairs loopback proxy handling and retains the exercised existing behavior; these results support source integration while keeping those separate receiving obligations explicit.
