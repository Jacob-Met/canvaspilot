# Classic-quiz terminal reads

Source contributor: `estate-continuity-3dcb83a1`.
[Bounded ownership](https://github.com/Jacob-Met/hamon/issues/140#issuecomment-6062294254).

## User result and source boundary

`canvaspilot quizzes COURSE_ID` lists the existing compact classic-quiz projection
through its current paginator. `canvaspilot quiz COURSE_ID QUIZ_ID` prints the
existing detail response, retaining original timestamps, nulls, false/zero values,
supplied policies, differentiated dates and unknown JSON fields. The commands use
positive numeric IDs and the existing common authentication options.

Only two additive blocks in `src/canvaspilot/cli.py` implement the new routes.
Deleting those thirty added lines reconstructs the receiving parent exactly.
The existing quiz API, MCP, client, broker, schemas and attempt/submission operations
are unchanged. The outer API close boundary is preserved. Expected read failures
return exit 1, a JSON error on stderr and no partial successful stdout; invalid
arguments return the existing argparse exit 2 before request dispatch.

The [primary Canvas Quizzes contract](https://developerdocs.instructure.com/services/canvas/resources/quizzes)
documents the two existing GET endpoints. This contribution retains the project's
classic-quiz support boundary and does not claim New Quizzes/LTI support, live
authentication or a started/completed attempt.

## Exact source and qualification

Original parent: `39d835c8becb04d81b65c90d1491d2d3a2727ffe`,
tree `53b67d3f06b4c780e508325ec42b2b435ec57e97`.
Original CLI: `5a3ed7be7a24d6461641192a54c77a04b90cc910`.
First frozen candidate CLI: `2b6a9b12b5f58b7b520e59dafbe8ad5f91de5f2f`.

The later receiving parent `a5ce672e5b3580c1f52e13c49eefee830f11346c`
includes the owning inbox PR56. Its CLI, API, MCP and README bodies are inherited
whole before the two unchanged quiz blocks and usage section are inserted.
Composed CLI: `9c0671937280e6830a58ea96b95bad2f25ea5a82`.
Both existing quiz methods and MCP wrappers remain character-exact to the original,
and the client remains blob `1db4b1135305f7e410025ae7937f9a6cd349f020`.
`current-source-correspondence.json` pins all twelve staged source/config/test inputs.

| Recorded gate | Actual result |
| --- | --- |
| Original native CLI | Help exits 0; both proposed route names exit 2 as unknown commands |
| First token-mode loopback regression run | Four methods and nine subtests pass; two methods fail against an incorrect test expectation |
| Exact fixture correction | Existing client uses page size 50; the test had expected 100 in two places. Only those two expectations and explicit default `check=False` change |
| Two affected methods on corrected test | Both pass; original product CLI remains unchanged |
| Targeted final Ruff | Passes for CLI and the final test |
| Current inbox composition | Exact source correspondence; no repeated author suite is relabeled as a new run |

The token-mode controls exercise actual subprocesses and loopback HTTP: two-page
listing with an opaque next query, full detail JSON, an empty course, later-page
refusal, authentication/status/JSON errors, and invalid/missing IDs before HTTP.
No real profile is opened, and every observed upstream request is GET. These are
synthetic software fixtures, not student, school or live-provider evidence.

`author-results.json` embeds the complete original and corrected command output,
source pins and baseline routing receipt. Its separately named native log paths
identify the retained originals; their text is included in that JSON. The initial
test is preserved as `test_quiz_cli.initial.py.txt` and its correction as a diff.
The archive suffix prevents accidental pytest collection. The original native
source and raw receipts remain at
`/home/jacob/canvaspilot-quiz-cli-3dcb83a1`.

The four unchanged successful methods were not repeated merely to increase counts.
Final submitted-head hosted CI remains a separate required gate. Root's independently
authored session-broker receiver passes eighteen assertions across six actual CLI
processes on the separately pinned `a5ce672e` composition. Its two baseline commands refuse before I/O;
the candidate receives two pages, selects detail using the returned ID, preserves
supplied metadata, reports a 403 with empty successful output and recovers on an
ordinary retry. All five upstream broker operations remain GET metadata reads.
Its exact script, contract, result and acceptance are preserved under
`independent/`, with separate attribution and source pins.

## Publication source composition

Publication parent: `c744bb5b79f23457f4dd9070f762100bc6ad91ad`, tree `abec51ddc40ab44d9e405857469736550d08b4f2`.
It additionally contains the owning discussion-context integration. The complete
current CLI and README are retained before the identical accepted blocks are
inserted. Submitted CLI: `cfb2e4e184e7fe5d8e9593e36fdeadd089147f98`.
The two existing quiz API reader bodies and MCP wrappers are character-exact;
the client, workflow and pytest configuration are unchanged. All discussion and
inbox command bodies remain exact. `submission-source-correspondence.json` records
the direct primary-source pins and exact owned blocks, so removal can reconstruct
the parent CLI and README byte for byte. This is source correspondence, not a new
native execution claim. Final submitted-head hosted CI is a distinct receiving gate.

## Replay

Use the repository's declared Python environment and current source:

```sh
PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider tests/test_quiz_cli.py
python -B -m ruff check --no-cache src/canvaspilot/cli.py tests/test_quiz_cli.py
```

The test starts only private loopback HTTP servers and subprocesses, supplies a
synthetic token, and cleans its temporary profiles. No school login, fixture API
replacement, live provider or installed service is required.
