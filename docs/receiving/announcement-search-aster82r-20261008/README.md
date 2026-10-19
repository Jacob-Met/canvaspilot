# Composed announcement-search receiving

Worker: **HAMON-Aster-82R-20261008**. This test-only contribution receives the composed product in PR #82 without modifying the feature author's branch, existing runtime, dependencies, or workflow.

## Tested source and outcome

Actual checkout: `730c9d50a46842acd1af7bb12ad938030f8557de`, tree `e9f13cb0086c7b3ce88da6b9dde8ea1ad93ca647`. Current composition parent: `cf47942b395a6196e6f5dcb02b3865f64aa1c89b`. Independent Git-tree verification preserves all **1,431 unselected parent leaves**, deletes no prior leaf, recovers the original CLI by removing three insertions, and finds README additions only.

Evidence-only successor `6a551a765b538d8aec910c68778fc2cf006c4d70` changes no existing tested leaf and adds nine prior independent-receiving files. Runtime and maintained-test bytes are identical; this is source correspondence, not a claim to have rerun a different checkout. Earlier native_engine ZIP receiving is retained and is not counted as this worker's execution.

The original independent receiver was frozen from the public contract and unchanged baseline before inspecting candidate implementation or authored tests. The freeze is recorded in PR #82 at 2026-10-08T19:42:29Z with SHA-256 `568d518b551e6a34f4bc0e16bd0dccb59976343c09fc6c8abe59579bcb2eac4e`.

The initial candidate run had **19 methods: 14 passed, no assertion failures, five 25-second subprocess timeouts**. That original run remains unsuccessful. Only the five timed-out methods were repeated, with the sole change being the child deadline from 25 to 120 seconds; **all five passed**. No fixture, semantic assertion, or product byte changed. Acceptance is explicitly the union of these successful methods, not one fabricated green run. Source hashes were unchanged before and after execution.

The unchanged baseline's three full/compact/later-error controls passed. New-command absence and initial timeouts remain in the retained baseline evidence. Observed host load averages during the timeouts were 54.64/39.78/30.83; unchanged paths also timed out. This is not a general performance claim. Timed-out subprocesses retain their exception traces, not complete per-request effect histories.

Actual CLI subprocesses and real HTTPX against private numeric-loopback fixtures cover complete messages beyond 400 characters, literal and Unicode-casefold matching, significant whitespace, no joining of title/body fields, no invented numeric text, exact order/duplicate/null/zero/date/course custody, argument admission, empty success, auth/later-page/repeating-page/40-page refusals, and logger restoration.

## Maintained regression tests

[`tests/test_announcement_search_page_boundary.py`](../../../tests/test_announcement_search_page_boundary.py) uses the real CLI entry function and real HTTPX, not a replacement API or transport. Exactly 40 complete pages must succeed with all matching rows preserved. When page 40 advertises another page, the same 40 matching pages must produce exit 1, structured CanvasPaginationError stderr, no partial stdout, and no request 41. Both cases verify ordered requests, initial filters, duplicate ID 0, alternating course context, null metadata, and absence of a created profile.

These two tests were authored after candidate inspection, separately from the frozen receiver. They do not claim subprocess coverage. Native results: candidate **2 passed in 8.77s**, baseline **2 expected missing-command failures in 5.69s**, Ruff passed. Each candidate case performs 40 loopback GETs. No live Canvas account, provider, installed service, or deployment participates.

Exact test: 5,780 bytes; SHA-256 `02a885f32b8f65e61219cceb38d37ab5323fd60d80e803b23cad014f74bfbcee`; Git blob `8ca797cad97f8a72c8fdccbe7babc4d40e423049`. Published test commit `ea98b2311819cb2d6ade48fbbc823e995b29a89a` was fetched and its test blob equals the locally tested blob.

```bash
python -m pytest -q tests/test_announcement_search_page_boundary.py
ruff check tests/test_announcement_search_page_boundary.py
```

## Durable raw evidence and publication state

[receiving.json](receiving.json) records source pins, results, limitations, and the producing-runtime storage location. The complete native packet retains both oracle versions, timeout-only adapter, original unsuccessful runs, accepted follow-up, stdout/stderr from completed CLI processes, source-custody verifier, boundary logs/JUnit XML, dependency versions, and sealer. All 25 archive members were read back exactly.

**The binary packet is retained on hamon-thinkpad, not uploaded in this GitHub commit.** Native path: `/home/jacob/hamon-aster-82r-20261008/aster82r-native-receiving.tar.gz`. It is also committed in the isolated native repository `/home/jacob/hamon-aster-82r-20261008/source` at local commit `77ef845d4135f4d66bb642a302cd87b02c7a5a88`, path `docs/receiving/announcement-search-aster82r-20261008/aster82r-native-receiving.tar.gz`. That local commit is not presented as GitHub-fetchable.

Archive: **28,715 bytes**, SHA-256 `859b7724308dd599427f5f8ba64f8026344f7fe6e024ba560686658a1f6340e7`, Git blob `93fdb07dcda212cc2c798be11b286337e481b814`. Direct native git push returned 128 because no terminal credential was configured; GitHub CLI is unavailable. No credentials were inspected or changed. The connected GitHub tool publishes the maintained test and this readable summary. The original artifact bytes remain intact rather than being silently reconstructed.

This evidence is not a deployment package. Credential-shaped fixture strings are synthetic. Retained absolute paths identify the producing Linux filesystem; reruns require a fresh evidence output directory.

## Integration handoff

PR #82's author retains implementation and integration ownership. Receive this test-only contribution through the existing branch/PR process and qualify the exact combined source through the maintained main-targeted workflow. The earlier hosted CI inspected directly was run `37830043573`, job `113492717141`, checkout `b44606e50b3a607a5e4a7518bf80f2e59f527ab2`, composed from 730c9d50 and `92e9f1b500a15dd61d4c74539dedbf880afde30b`: Ruff passed; pytest reported **1,097 passed, one skipped, and 93 subtests passed**. It did not include these two new tests.

The existing workflow triggers for main pushes and PRs targeting main, not stacked PRs targeting the feature branch. No workflow modification or claimed hosted acceptance substitutes for that gate. No author-owned branch or main integration is claimed by this packet.
