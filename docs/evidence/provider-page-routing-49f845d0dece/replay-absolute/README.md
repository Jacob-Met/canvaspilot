# Absolute-target companion receiving

This companion differs from the previously frozen receiver only at the authored terminal Page.evaluate expression-admission seam. It admits exactly one of the old `fetch(path, opts)` and new `fetch(target.href, opts)` production statements. All three cases, baseline/candidate outcome oracles, source hash guards and artifact checks remain unchanged.

The original witness, the earlier companion, and the complete b666 pair remain immutable. The new companion is intended for the original baseline and absolute-target successor 8e1a1b87a1f7379b884310cf05cbad8129ea1bb8. The syntax-only checkpoint is native commit 4cd930582a722edff98817bf638423d739b6c649. Both completed executions and the acceptance limits are now recorded in [RESULTS.md](RESULTS.md).

The terminal Page seam still does not execute production JavaScript. The author's actual Chrome loopback receiver is the separate evidence for dispatch with a foreign HTML base element. This companion tests CLI-to-broker page refusal and identity preservation only.

Run using the existing project Python environment:

```sh
python replay-absolute/receive_provider_page_contract.py --source /path/to/frozen/source --source-pins /path/to/pins.json --expect baseline --output /new/baseline/output
python replay-absolute/receive_provider_page_contract.py --source /path/to/frozen/successor --source-pins replay-absolute/successor-source-pins.json --expect candidate --output /new/successor/output
```
