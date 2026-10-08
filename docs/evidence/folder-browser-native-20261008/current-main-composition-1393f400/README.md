# Folder browser composition with current Canvaspilot main

This receiving packet composes the independently reviewed folder browser with both later product merges: optional module-item retrieval and the deadline overview. It replaces four earlier folder-branch source blobs while preserving the original 43-file handoff and every earlier receipt.

## Exact source

| Item | Pin |
| --- | --- |
| Repository / PR | `Jacob-Met/canvaspilot` / #36 |
| Published folder PR head before this composition | `f74ca72c42cccc5a3d4c5468ae88e35ba74f0c95` |
| Previous folder source parent / tree | `3d7a9453fb0cbdf08312320d71c648462592b217` / `9bf3697e5d577227caeb3117d1b4d7cbc96772ab` |
| Current main parent | `1393f40047297147029d8571bfd824f74e58e1dc` |
| Current main tree | `cb758a4d82431552ab9dc35755c04a12b15b2f2a` |
| Current composed source tree | `76a9f5c4523df2f2affc75e050e53cf9fb652845` |
| Exact current source inventory | 67 tracked files |

Main `1393f400` includes module-items merge `5b1780ca4fcdce3d5f997cee401c86806ece822a`, the sync deadline selection feature, and the previously received broker proxy/parameter-encoding changes. The full current main tree was retrieved through the authorized GitHub connector and its 63 blobs verified before composition. No repository AGENTS.md was present in that exact tree.

The source patch still has nine paths. Five are byte-identical to the previously qualified folder feature: the folder implementation, the bundle inventory addition, folder documentation, the HTTP/broker fixture and the 33-case folder suite. README, API, CLI and MCP were composed with current main. The only textual conflicts were adjacent README sections and MCP imports: both full sections remain, and `Field`, `StrictInt` and `ToolAnnotations` are all retained.

All 41 inherited API definitions and 36 inherited MCP definitions are structurally identical to current main, with only `CanvasAPI.browse_files` and `canvas_browse_files` added. The CLI diff consists of the folder parser and folder command branch; current sync parsing and dispatch remain unchanged. All 58 current-main files outside the five modified paths remain byte-identical. `composition-preservation.json` records the complete comparison.

The core source tree above is current main plus the same nine-file folder delta. The prior 34 folder evidence files and this new receiving packet are additional publication documentation, excluded from that core tree. Their exact bytes are retained in the handoff manifest. The full published tree is therefore expected to differ from the qualified core tree.

## Native results

| Receiving | Result |
| --- | --- |
| Entire current native pytest suite | 192 passed; zero failures or skips |
| Ruff over src, tests and scripts | Passed |
| Existing hostile-proxy receiver | 12 of 12 groups passed |
| Additional public composition journey | Six actions passed |
| Actual broker operations in that journey | 17 GETs, no request bodies |
| Proxy trap requests in that journey | Zero |
| Source verification after receiving | All 67 files unchanged |

The complete inherited module-items and sync tests run alongside all 33 folder tests. The folder tests retain actual public CLI subprocess and MCP stdio coverage for root navigation, chosen folders, separate child pages, empty and forbidden results, foreign course identity, strict query validation and the native read-only broker Handler.

`replay-composed-public.py` adds a focused integration journey through one actual MCP stdio server: module contents omitted inline are fetched, deadline selection and omission counts are preserved, and folder navigation selects the requested second file page. Both strict numeric schemas refuse booleans before any broker job. Separate public CLI processes then run sync and browse-files against that same disposable broker. The old and new commands share the real current API/client and unchanged Handler.

The proxy environment deliberately points HTTP/HTTPS/ALL_PROXY at an isolated loopback trap and sets malformed `NO_PROXY=[::1]`. No request reaches the trap. The actual native Handler returns authored metadata at its browser-worker queue boundary. No browser worker, live Canvas account, provider, file body, download, production profile or installed broker participates. These are source-composition results, not a claim of live-account or estate rollout completion.

## Replay

Use a fresh authorized checkout of the exact current main parent and apply `current-main-folder.patch` from this directory:

```sh
git checkout 1393f40047297147029d8571bfd824f74e58e1dc
git apply --index /absolute/path/to/this/packet/current-main-folder.patch
git write-tree
```

The result must equal `76a9f5c4523df2f2affc75e050e53cf9fb652845`. Source-only copies can instead be checked against all file hashes in `source-manifest.json`. Keep the original folder evidence and this packet outside the core checkout when reproducing the exact Git tree.

The reference runtime is Python 3.12.8 on native macOS arm64, HTTPX 0.28.1, MCP 2.3.0, Pydantic 2.13.5 and pytest 8.4.2. The already inherited `docs/evidence/broker-proxy-native-20261008/requirements-receiving.txt` pins the complete native receiving environment. Ruff 0.16.10 was run from a separate tool environment. No dependency or lockfile changed.

Set `CANVAS_SOURCE`, `CANVAS_RECEIVING` and `CANVAS_PYTHON` to absolute paths for the fresh source, a new output directory, and the receiving interpreter:

```sh
env -u CANVAS_API_TOKEN -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u NO_PROXY \
  -u http_proxy -u https_proxy -u all_proxy -u no_proxy \
  PYTHONDONTWRITEBYTECODE=1 CANVAS_BASE_URL=https://canvas.fixture.invalid \
  CANVAS_SESSION_PORT=0 CANVAS_PROFILE="$CANVAS_RECEIVING/unused-profile" \
  PYTHONPATH="$CANVAS_SOURCE/src" \
  "$CANVAS_PYTHON" -m pytest -q -p no:cacheprovider \
  --junitxml="$CANVAS_RECEIVING/full-suite.xml" "$CANVAS_SOURCE/tests"

"$CANVAS_PYTHON" /absolute/path/to/this/packet/replay-composed-public.py \
  --source "$CANVAS_SOURCE" \
  --manifest /absolute/path/to/this/packet/source-manifest.json \
  --output "$CANVAS_RECEIVING/public-composition"
```

Run the inherited broker-proxy receiver from `docs/evidence/broker-proxy-native-20261008/review_broker_proxy.py` with its normal `--source` and `--output` arguments against that same source. The receiver creates its own native Handler processes and loopback ports. Run Ruff with `ruff check --no-cache src tests scripts` from the source directory. Preserve the reference outputs when replaying.

`validation-receipt.json` records exact executed commands, elapsed times, exit codes, runtime versions, environment neutralization and source verification. The JUnit file and stdout/stderr logs retain the complete suite results. `public/receipt.json` retains all six actions and 17 native queue jobs; its sibling CLI/MCP logs preserve actual public-interface output and expected validation errors. `current-main-folder.patch`, the 67-file manifest and the three-way preparation/preservation notes make the source composition reconstructible without captured dependency trees.
