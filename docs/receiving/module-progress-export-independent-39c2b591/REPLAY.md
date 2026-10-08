# Replay and interpretation

The accepted product tree is f17362750896b2834b4321151403b61e64429486; the author commit is dbb4a4fa04c25849a079f89a67b3049a2f55946f on public base a5ce672e5b3580c1f52e13c49eefee830f11346c. Obtain that exact source or the included closed full-source bundle. Do not treat our differently rooted snapshot commits as public ancestry.

Run `python3 unpack-receiving.py NEW_DIRECTORY` to decode the complete evidence. The target must not exist. Files, encoded parts, gzip and container hashes are all checked; the container includes original failures, not only the successful receipts.

The independent Python fixture uses only synthetic loopback HTTP. It does not import an author fixture. With project dependencies installed in an owned Python environment, reproduce the original observation once:

```bash
PYTHONDONTWRITEBYTECODE=1 python -s producer_receiver_v1.py --source BASELINE_SOURCE --out NEW_BASELINE_OUTPUT
```

Then receive the exact candidate. All paths below are fresh owned destinations; CHROME_BINARY is an already installed browser executable:

```bash
PYTHONDONTWRITEBYTECODE=1 python -s candidate_receiver_v2.py --source CANDIDATE_SOURCE --out NEW_CANDIDATE_OUTPUT --chrome CHROME_BINARY --original-cli-stdout NEW_BASELINE_OUTPUT/baseline-module-progress.stdout
node browser_receiver_v2.mjs NEW_CANDIDATE_OUTPUT/browser-config.json
```

The producer invokes the actual CLI and client in child processes. It supplies an explicit disposable profile path and an invented local token, removes inherited proxy/auth environment from the child, and never uses a real school session. The candidate receiver does not modify product source. Its own corrupted saved artifact is a deliberately separate negative control.

The browser needs Node with built-in WebSocket and an installed Chrome. It creates an exclusive output/profile, requires at least 512 MiB free, sets JavaScript disabled and page networking offline, consumes the saved files, performs the pointer download and normal Tab/Enter navigation, and captures raw data. It closes the browser and terminates only its owned child if still present. Retain stderr and the first failed receipt before making any receiver-only adaptation.

The recorded successful browser is native Mac Chrome154.0.8037.98 / Node26.3.0. A Windows Node24.21.0 attempt successfully received exact files but never opened a debugger endpoint and ran zero page checks. That result does not establish Windows browser support. The initial Mac storage refusal and Windows startup refusal must remain separate from the successful Mac consumer.

Existing authored test suites, old pagination/model matrices and current-main composition are outside this replay. The owner is separately reconciling later CLI/README changes. Do not repeat the settled browser gate when the exact report-producing closure is unchanged merely to obtain a newer timestamp.
