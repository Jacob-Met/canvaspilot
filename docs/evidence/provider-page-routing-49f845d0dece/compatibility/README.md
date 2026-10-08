# Final broker compatibility and composed-source receiving

## Verdict

ACCEPT the remaining old-broker compatibility seam and the final composed source at native commit `7452703ec4f55e7f63c11276a92dbfd647f6e718`. The calendar helper SHA256 is `b92948c438063438bf9b8ef01b0b0c067802ddb06354f00e8ee18749f3c5e2fa`; the broker SHA256 is `e6f550988cfa3882e8b5b4a711bdf9bb10d958a1bbb5d85a1f6006c3dbf695f1`. All five final source pins, including the composed API and CLI, are in capable-source-pins.json. The implementation author and lead retain source publication, final hosted checks and integration ownership.

The guarded broker advertises the exact boolean `provider_origin_checks: true` in health. The session calendar helper validates the provider and requires `health.get("provider_origin_checks") is True`; missing, false or nonboolean values produce the explicit instruction to restart the broker with updated CanvasPilot before export. The existing token/fixture return path precedes this session-only check. The five maintained missing/false/nonboolean unit cases were inspected, without duplicating the author's test matrix.

## Mixed-version native receiving

The same receiver SHA256 `e48456f822ca8861374641f4fa698f62d15c099e955cef2de354c26f78c6b75f` was executed against the original baseline CLI and the final composed CLI. Both talked to the exact original broker Handler loaded from the preserved legacy source: SHA256 `2a106130c344aefebb23b078cd93b5d3ca3afd7f5325ae5fac2fb8a7251780cc`, Git blob `ba23543f62e6be9f611ae06260b91f239206cb23`.

| CLI source | Observed legacy health | Broker POST /fetch | Queued jobs | Outcome |
| --- | ---: | ---: | ---: | --- |
| Baseline 3e251e5 | 2 responses, capability absent | 1 | 1 | Missing capability does not stop dispatch |
| Final 7452703 | 1 response, capability absent | 0 | 0 | Exact restart ValueError, no artifact or profile |

This uses the actual CLI, client, calendar helper, legacy Handler, _call and queue. The Handler wrapper only records health replies and POST paths. A deliberate fail-fast queue responder terminates a forbidden fetch if reached. The baseline therefore establishes entry into the old broker's dispatch path; it does not claim a successful calendar export. The candidate refuses before that responder can run. No browser, external school request, credential, live account or existing profile is used.

The native project Python 3.13.7 runs each completed with receiver exit 0, and all five current source hashes plus the legacy broker hash were preserved. Exact commands, raw CLI output, observations and receipts are in the sibling compatibility-baseline-qualified and compatibility-candidate-qualified directories.

## Final capable-broker composition

The already-frozen three-case receiver `f2684d1046843da7533a41086da73421e4a1cb1abc84da1b417bb7be799ca587` also ran unchanged against the final composed source and its actual new Handler. It passed all seven candidate assertions: matching A/A and B/B exports retain the exact source, UID and assignment URL previously qualified; configured A with selected page B is refused before Page.evaluate with no calendar. The raw receipt is in the sibling capable-composition-qualified directory. All five production hashes were checked before and after.

The extracted JavaScript expression remains SHA256 `11190219dc24f939d0fcf31d65482e0a628c58b738809de2d8a0562bac7ce54e`, identical to the accepted absolute-target successor. Existing actual Chrome evidence therefore continues to qualify that exact expression; no browser checks were rerun. The prior browser evidence and its redirected-network-contact limit remain unchanged in ../replay-absolute/RESULTS.md.

## Preserved infrastructure failures

The first compatibility/composition launches were blocked by ENOSPC while zsh attempted to create a heredoc temporary file. Python and the receivers did not execute, and all three intended output directories were absent. Those exact tool outputs are preserved in ../compatibility-shell-enospc/receipt.json with no product or receiving verdict. Fresh runs used separate qualified output paths after available space was verified. The earlier inconclusive successor attempt in ../replay-absolute-enospc/receipt.json is also unchanged.

## Reproduction

Use the existing project Python environment and frozen source paths; every output directory must be new:

```sh
PYTHONDONTWRITEBYTECODE=1 python compatibility/receive_legacy_broker_capability.py --source /path/to/final/source --source-pins compatibility/capable-source-pins.json --legacy-source /path/to/original/legacy/source --expect candidate --output /new/compatibility-output
PYTHONDONTWRITEBYTECODE=1 python replay-absolute/receive_provider_page_contract.py --source /path/to/final/source --source-pins compatibility/capable-source-pins.json --expect candidate --output /new/composition-output
```
