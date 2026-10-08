# Independent Canvas folder-browser receiving review

**No unresolved blocker was found in the reviewed scope.** Seven independently
authored unittest methods pass in normal Python and seven under `-O`, with zero
failures, errors or skips. The tests execute the actual API/client, CLI
subprocesses, MCP stdio server and unchanged read-only broker Handler on the
Mac receiving runtime. No source implementation was edited by this reviewer.

## Source and runtime identity

| Item | Reviewed identity |
|---|---|
| Base commit | `b0655cfc6f298c956fcdd27fbba32e3c5609516f` |
| Frozen candidate tree | `fbc99e88b46328072ab8eaab23023b9b17dd1898` |
| Independent test SHA-256 | `98ba706a7d1cba13ab1740ab54ace7ee326815b1d2fd9dad0ec8f4911a7a85ca` |
| Owner source-manifest SHA-256 | `8f534de89c36c59248328db68a569a0a9ccdff689e3aa190e0b816660f38f415` |
| Runtime | Python 3.12.8; httpx 0.28.1; MCP 2.3.0; Pydantic 2.13.5 |
| Native device | Mac.lan, `0e3d582f-e25b-44b2-8418-9639fc4e4e33` |

An isolated copy was constructed from the owner's already captured Mac source
at `/tmp/canvaspilot-folders-cf5799f6d38b-FIWmPE/source`, copying only the 29
manifest-listed files. Every copied byte count, SHA-256 and Git blob matched the
frozen candidate before execution. All 29 source blobs and SHA-256s still match
after both runs. See [expected-source.json](expected-source.json) and
[source-checks.json](source-checks.json).

Native review directory:
`/tmp/canvas-folder-review-cf5799f6d38b-g_fgiv9w`. The existing runtime was used
read-only at
`/tmp/canvaspilot-receiving-cf5799f6d38b-9VQmAF/venv/bin/python3`.
CLI and MCP child processes explicitly receive `-O` during the optimized run;
this is not merely optimized execution of the outer test harness.

The reviewed nine-path product delta changes the API, CLI, MCP registration,
bundle inventory, folder helper, docs and authored fixture/tests. It leaves the
existing client/authentication and broker implementation outside the write set.
This review adds no T66/rubric, broker, authentication or unrelated product edit.

## Independent receiving controls

The test uses a separately authored loopback HTTP service. All requests and
their exact query maps are retained in the JSON receipts. For the broker case,
the actual `session_broker.Handler` runs in a fresh local process with
`read_only=True`; an authored queue worker supplies metadata at its existing
browser-job seam. No browser worker or real provider runs.

| Independent challenge | Observed result in both modes |
|---|---|
| Leading-zero course/folder IDs and independently selected child pages | Canonical endpoint IDs are used; original metadata representations are preserved; folder page 2 and file page 1 reach their exact separate query maps. |
| Same numeric context ID under `Group` or `User`, or invalid Boolean/missing course identity | Folder metadata is refused after one course-scoped request, before either child endpoint. |
| Duplicate numeric aliases within a child page; selected folder returned as its own child | The page is refused after the folder-page request, before file retrieval. |
| One valid file followed by a foreign-folder file | API raises; CLI and MCP return errors without a valid prefix or foreign private name. |
| A server caps a requested 100-item page to one; later page is empty; maximum page is reached | Separate page probes work, `has_more` stays unknown, and the maximum-page flag does not imply completeness. |
| File permission changes after folder metadata was accepted | The CLI returns a nonzero error and no result, without exposing the authored private error body or relabeling refusal as emptiness. |
| Actual read-only broker and MCP stdio | Native API/CLI broker dispatch keeps the course guard and exact page queries; all queued provider operations are GETs with no body. MCP exposes its read-only/non-destructive annotation and rejects Boolean, floating-point, string, null and out-of-range page values before any HTTP request. |

The positive controls also retain Unicode metadata and omit download, preview,
response-supplied child URLs and embedded file bodies. They verify a usable
result, so successful refusal alone cannot satisfy the suite.

## Evidence and negative cases

- [test_independent_folders.py](test_independent_folders.py) contains the seven
  independently written methods and the authored HTTP/broker fixture.
- [normal.log](normal.log) and [optimized.log](optimized.log) retain native test
  output: 7/7 passes in each mode, zero skips.
- [review-0.json](review-0.json) and [review-1.json](review-1.json) retain the exact
  HTTP queries, broker jobs, wire MCP catalog and metadata-refusal response.
- The `mcp-review-*` logs retain native server output from both modes, including
  the deliberately invalid page types and foreign-file refusal. These expected
  error responses are the negative controls; no unsuccessful source repair is
  hidden or replaced by this packet.

The suite succeeded on its first executed normal run and on the unchanged
optimized run. The review does not count the author's 92-method suite as
independently authored work. The base did not have this folder-browse public
feature, so running these new feature assertions against it would establish
missing entry points rather than a comparable bug count.

## Contract and remaining limits

The official [Canvas Files API](https://developerdocs.instructure.com/services/canvas/resources/files)
documents the course-scoped folder lookup, its `root` alias, and the separate
folder/file child-list endpoints. The candidate binds the selected folder's
course and requested identity before using the folder-ID list endpoints.
Children must agree with their parent/context. These checks establish response
consistency with the requested course under the existing client, not independent
authentication of the Canvas server or a new account-selection protocol.

The official [pagination contract](https://developerdocs.instructure.com/services/canvas/basics/file.pagination)
uses opaque Link continuations and permits a server-side page-size cap. The
current body-only client/broker does not expose those links. The new feature is
therefore correctly scoped to explicit bounded page probes and direct children;
it supplies neither authoritative continuation nor a complete recursive
inventory. Source-reported counts and an empty page do not change that limit.

This review qualifies the actual receiving implementations against authored
loopback responses. It does not claim a live Canvas course browse, a logged-in
browser, provider permissions, file downloads, deployment, task benefit, or
qualification of unrelated escape-hatch/write endpoints. No API credentials,
real course records or live account state were used.

## Replay

Place the exact reviewed 29-file source tree in a `candidate/` directory beside
this script, checking every path against `expected-source.json`. With the
recorded dependencies installed in an isolated runtime, run:

```sh
PYTHONDONTWRITEBYTECODE=1 python test_independent_folders.py
PYTHONDONTWRITEBYTECODE=1 python -O test_independent_folders.py
```

Use a new copy of the review directory for each replay to retain its output. The
test removes ambient token/proxy variables from its own process, selects only
loopback test endpoints, and supplies an unused profile path. It asserts that
the profile path is never created. No package installation or provider contact
is performed by the test.
