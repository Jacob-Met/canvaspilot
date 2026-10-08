# Course file-listing error propagation

Source base: `0480cbce421bae532e3e909899fc8fb83789e878`, complete tree `f9ecaa4311d93cfe3a1fd1c9cc140834e2449341`.
Scope: [CanvasPilot #69](https://github.com/Jacob-Met/canvaspilot/issues/69).

The original native CLI returned the root-only decoy (ID99) with exit0 after each second-page403,404,500 and non-list failure. The same five-process driver on the candidate preserves the healthy IDs1,2 and returns exit1, empty stdout and exactly two course requests for each failure. No folder route is requested. The two full JSON receipts retain actual outputs and errors.

The unchanged focused regression gives12 failures/3passes on original source. Candidate native receiving gives18passes: those15cases, the existing fixture smoke, and two existing explicit folder-navigation controls. Ruff passes for the changed runtime/test source. All16 native production source blobs were verified against the complete base tree; only api.py changes. Its entire prior text is recovered by reversing the one list_files replacement. The inherited paginator, authentication, broker, folder browser and CLI/MCP bodies stay exact.

The changed production behavior includes the first page: an initial403/404/500 or transport failure propagates rather than falling back to root-folder contents. Those cases are exercised through the native API. The project already provides explicit scoped folder navigation. No change to the normal successful projection or page order is intended.

## Replay

With the repository's declared dependencies and development tools installed:

```sh
PYTHONPATH=src python -m pytest -q tests/test_files_completeness.py tests/test_fixture.py tests/test_folder_browser.py::test_real_client_root_chosen_folder_next_pages_and_nested_file tests/test_folder_browser.py::test_empty_folder_is_scoped_without_a_false_completeness_claim
python -m ruff check src/canvaspilot/api.py tests/test_files_completeness.py
```

`original-cli-driver.py.txt` is the exact historical loopback driver. Its staging layout is the driver beside `source/` (repository checkout), `deps/` and `mcp-deps/` (the two isolated dependency-install destinations). Run it as Python with one new output-JSON path. It invokes the actual CLI five times and observes requested routes. Dependencies are setup, not source modifications.

The first CLI run raced the unfinished MCP installation and all five processes failed before HTTP. `setup-cli.json` retains it separately. The later original and candidate observations used Python3.12.14, HTTPX0.28.1 and MCP2.3.0; `receipt.json` records exact source identities. No original failure was replaced by a success receipt.

Tests of `canvas_list_files` here call the registered async function; they do not claim stdio-wire acceptance. Independent receiving and exact submitted-head hosted CI remain separate integration gates. All data, URLs and tokens are authored fixtures; no school account, saved browser profile or installed service is involved.
