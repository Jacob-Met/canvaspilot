# Same three-case provider-page replay

The original receiver and negative artifacts remain unchanged at native commit
326a77e913ba031cb46f73e68e03d2643fb295e7 and public commit
b582b15754c675e2cf8c57ba6963fb27ba2a7541.

This separate companion changes only source-pin admission and the expected
baseline/candidate outcome. It uses the original three cases and unchanged
production CLI/Handler/_call/queue/_canvas_page/_run_job receiving boundary.
Only the terminal Page object is authored; there is no real browser or external
request. Source-pin files must contain exactly the original five path-to-SHA256
entries; an author must freeze and supply a candidate manifest before receiving.

Run the same companion bytes with explicit contracts and new output directories:

    python receive_provider_page_contract.py --source /path/to/baseline --source-pins baseline-source-pins.json --expect baseline --output /new/baseline-output
    python receive_provider_page_contract.py --source /path/to/candidate --source-pins /path/to/frozen-candidate-pins.json --expect candidate --output /new/candidate-output

Baseline mode requires the original successful misattribution counterexample.
Candidate mode requires both matching-provider exports to succeed with their
own source and distinct UIDs, and the mismatched-provider case to fail before
Page.evaluate with no output artifact/profile/temp file or success report.
The intentional broker refusal must be ValueError or RuntimeError, reported
through the existing CanvasAuthError CLI path with a provider/origin diagnostic.
These checks distinguish deliberate refusal from an accidental terminal-object
exception. The native source HEAD, exact five source hashes, manifest hash,
receiver hash, production job errors and each raw command result are recorded.

This companion has been frozen and syntax checked but NOT executed at this
checkpoint. Its eventual baseline/candidate executions must retain the same
receiver bytes and clearly name the source manifests. No original receipt is
relabeled. A new source-interface branch control should be added only if the
concrete correction introduces an uncovered behavior.
