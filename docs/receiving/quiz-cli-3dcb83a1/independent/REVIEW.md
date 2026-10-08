# Independent current-source quiz CLI receiving through the session broker

Reviewer: estate-3dcb83a1/root.

Accepted candidate CLI Git blob `9c0671937280e6830a58ea96b95bad2f25ea5a82`, SHA-256 `2c951207cf42ca0ddee33629c84eb561fab64ad1f62d552a059a6637b6c612fe`, composed on current main `a5ce672e5b3580c1f52e13c49eefee830f11346c` / tree `0661a7005e577864cb87bc41e0e715409c92ee76`. The separate inbox owner's current CLI/API/MCP additions are included. The source was read only.

## Actual receiving result

The frozen receiver ran six real `python -B -m canvaspilot.cli` subprocesses using the existing complete interpreter and a synthetic HTTP broker bound to an ephemeral 127.0.0.1 port. No CanvasAPI/client function was mocked, substituted or edited. The existing broker transport and its real HTTPX requests handled every admitted read. No personal API token or live Canvas account was used.

All **18 assertions** pass; the receiver exits 0 in 9.13 seconds. They cover two current-baseline missing-route refusals and four candidate CLI processes. These are not eighteen independent test cases.

- Current unmodified CLI `545ec52f31b694a351e9a41a68e52a34c49db532` rejects both `quizzes` and `quiz` with exit 2, empty stdout and zero broker requests.
- The candidate lists two actual broker pages, preserving the existing nine-field projection. It follows the opaque absolute continuation without reapplying the first page's filters.
- The returned list selects quiz 6407 in course 2189 for a subsequent real detail invocation. Exact metadata retains null dates/time limit, false flags, zero counts, unlimited attempts, lock information and supplied date offsets.
- A broker 403 yields exit 1, empty stdout and a structured `CanvasAuthError`. Restoring the synthetic response permits an ordinary retry to return the exact original detail.
- Five upstream fetch payloads are GET metadata reads. No question, attempt or submission route is invoked. The broker's local POST transport is distinguished from those Canvas GET operations.
- Deliberately unusable proxy environment values do not divert broker traffic. No authorization header or browser profile is created.
- All eleven baseline and twelve candidate source/config/test files remain byte-exact after receiving. The API and client were pinned before execution; the two existing quiz methods are character-exact across variants.

The complete 17,285-byte result has SHA-256 `5fb62b2887e9960805854680e07427eb6b9c4394587ccb96e701d7f404bb66af`. It retains actual commands, exit codes, stdout/stderr, HTTP payloads, source snapshots, fixture identity and resource admission. The receiver uses unchanged 768 MiB disk and 1.5 GiB available-memory floors, with bounded source/report sizes.

## Replay

Use the published current-parent source as baseline and the submitted CLI composition as candidate with their exact recorded dependencies. The receiver validates the exact baseline CLI, candidate CLI, API and client before any CLI subprocess.

```sh
python -B receive_broker.py \
  --baseline /path/to/current-baseline \
  --candidate /path/to/current-candidate \
  --python /path/to/existing/project/python \
  --out /path/to/fresh/broker-results.json
```

This accepts the recorded classic-quiz metadata CLI integration and existing broker path. It does not establish live-school authorization, browser login, New Quizzes support, a quiz attempt or a changed installed service. The author's token-mode tests and original fixture-expectation correction remain separately attributed.
