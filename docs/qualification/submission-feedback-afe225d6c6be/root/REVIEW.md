# Independent submission-feedback receiving

Root reviewer `chatgpt-afe225d6c6be` accepts the bounded submission-feedback behavior in local immutable commit `a98da7dce9f4839a20a21a6973d7cc7e6fa635a2`, tree `8abeb42ccb66263841ade748cc33103b4fe4c4fe`, direct parent `72357053a1629c349f700030013559fa6d8130f2` (tree `919634af69c067e04f391fca84b3071ab8da9159`). This is native source qualification; publication, hosted CI, integration and installed Canvas-account use are separate states.

## Actual interfaces and independent inputs

`cases.json` was frozen before candidate inspection, SHA-256 `7ce2ff38268b7caf0b5eb80620546b6bb24d41c38c95ed767bfe0ff7f4fe6652`. Its four cases challenge:

1. Reordered criterion IDs, a zero mark, prior-attempt grading, a negative grader ID, advisory/non-scoring rubric metadata, orphan feedback, and student/media-only comments.
2. Missing assessment, comments and grade-applicability metadata, preserving unknown values rather than inventing zero or completion.
3. A current grade without a rubric, retaining the original comments.
4. Returned assessment comments without available definitions, preserving unmatched feedback, null points and an explicitly empty comment list.

The unchanged receiver at SHA-256 `b10c9735bcf4f8c4d9bd340662851b68364b523ff8c2373a132c120a5bcf651f` exercised the actual Python API, four CLI subprocesses and an initialized MCP stdio session. **All 12 interface checks passed**, with **exactly 24 GET requests** to a disposable loopback HTTP server. Each interface requested the assignment followed by its `submissions/self`, preserving the client's `per_page=50` and both include-array fields. The MCP tool advertises exactly the two required string identifiers. All outputs and request inventories are retained under `candidate-r1/`.

The fixture used a literal synthetic token, a minimal subprocess environment and no browser profile. No profile was created. All 127 files in the independently materialized Git archive remained byte-identical after receiving; all runtime source pins match the source manifest. Source archive SHA-256 is `38cb55d683cb74394b1e28c4c6c35a0a05b1eede6f53164e369eded302832efa`. Raw passing receipt SHA-256 is `5c5786cfc96cbe65049eff8edefdf0b5151a1b4732ae36dbdbac8c41e140c678`.

## Baseline and harness limits

The earlier exact 42-file `5b1780ca4fcdce3d5f997cee401c86806ece822a` baseline has no `CanvasAPI.submission_feedback`. The retained baseline witness therefore exits with the expected `AttributeError` before any HTTP request. It is a missing-capability witness, not an assertion that an existing supported command regressed. Sync and folder changes subsequently moved the receiving parent to `7235705`; the successful interface run uses that complete composition.

The disposable receiver clears inherited proxy variables only in its own process and subprocess environment so the isolated loopback fixture does not instantiate an unrelated SOCKS backend. The installed MCP 2.3 models expose Python snake_case fields; inspection uses `model_dump(..., by_alias=True)` for the actual wire schema. Neither adjustment changes the candidate, authentication, client behavior, dependencies or production error policy. Runtime timestamps in raw artifacts are retained as emitted; authoritative coordination time is recorded separately where available.

## Independent semantic binding

The separate `coordination_review` receiver froze its driver before viewing the candidate and accepted six semantic groups on the immutable original `5b1780` composition: six duplicate-ID orders, missing and non-string IDs, exact Unicode/case/whitespace matching, nested output isolation, missing-versus-empty feedback, and all six assignment/submission auth/HTTP/timeout exception paths. Its receipt SHA-256 is `43ae81a525c8fb7b87e7f8ab36b1c74ac7fdc1ba152de46ad88ae94d7e02e359`.

Root independently confirmed that the final feedback module is byte-identical to that reviewed module (`7cbedb04d0f0fedb684a1cb49d2a2616d5393210b1b4a17cb3d0bffa24001eb9`), that the final `submission_feedback` method has an identical parsed AST, and that `client.py` is byte-identical. The peer semantic qualification therefore retains its original source pin, with an explicit binding to the final composition; it is not relabeled as a new execution. Its extracted method source is also retained at SHA-256 `b4abacdcbaa3cf33769207adae97e8e306dc36a93f145a95923b3621b7bda990`.

## Replay

Install the repository's declared dependencies in an isolated environment. The executed environment used Python 3.12.14, httpx 0.28.1, mcp/mcp-types 2.3.0 and pydantic 2.13.5. Check out the source identified above, or verify the five production source hashes in the final published manifest before replaying an evidence-only descendant.

```sh
PYTHONDONTWRITEBYTECODE=1 python verify_feedback.py \
  --source /absolute/path/to/qualified/canvaspilot \
  --dependencies /absolute/path/to/installed/site-packages \
  --output /absolute/path/to/new/receiving-output
```

The output directory must not exist; prior failures and successful runs are retained. Keep `cases.json` beside the receiver. No Canvas account, school data, browser, broker, grading action or submission write is needed.
