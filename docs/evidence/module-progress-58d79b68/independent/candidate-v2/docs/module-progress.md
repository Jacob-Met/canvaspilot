# Review course module progress

`module-progress` turns Canvas's full module response into a study checklist for
the authenticated caller. It shows the module state Canvas reports, the
requirements on each returned item and their reported completion. It works
through the existing token, session-broker and fixture clients.

## Use it

```bash
canvaspilot module-progress 42
canvaspilot module-progress 42 --module-id 7
```

The first command includes every module returned by the existing reader. The
second keeps one module while reporting how many returned modules the selection
omitted. It accepts a positive numeric module ID; an ID absent from the returned
course data produces an error. IDs in the result retain their original Canvas
representation and modules/items retain their returned order.

Python:

```python
from canvaspilot.bundle import make_api

with make_api() as api:
    report = api.module_progress(42, module_id=7)
    module = report["modules"][0]
    print(module["name"], module["state"])
    print(module["remaining_work"])
```

MCP clients can call `canvas_module_progress` with
`{"course_id": "42", "module_id": "7"}`; omit `module_id` for the course view.
The tool is annotated read-only. These calls only read the existing module and
module-item routes. They never mark an item read/done, submit work or change a grade.

## Read the checklist

- `state` is Canvas's `locked`, `unlocked`, `started` or `completed`
  module state. Missing and unsupported values become `unknown`, with the
  original value retained in `reported_state`.
- `requirement_type` preserves `all` versus `one`. A `one` rule describes
  alternatives, so an incomplete alternative in a completed module does not
  become an outstanding work item. Module completion is never inferred from
  locally counted requirements.
- `require_sequential_progress`, prerequisite IDs and `unlock_at` retain the
  reported ordering context. The digest does not calculate prerequisite
  satisfaction, item availability or unlock times.
- Each item includes its identity, title, Canvas link, original
  `completion_requirement` and a readable action for recognized requirements:
  view, submit, contribute, mark done, minimum score or minimum percentage.
  Score/percentage thresholds remain in the original requirement object.
- `completion_status` is `completed` or `incomplete` only for a recognized
  requirement with an actual boolean completion value. Unknown types, malformed
  values and missing completion stay `unknown`. An absent/null requirement is
  `not_reported`; it does not establish that the item is optional.
- `remaining_work.incomplete_item_ids` identifies reported unfinished
  requirements. `rule` gives their all-versus-one context; `module_locked`
  comes only from the module state. It is a review list, not a claim that each
  item can be opened now. A completed module has an empty remaining-work list.

For example, a started module with a completed reading and an unfinished quiz
shows the quiz in its remaining-work list. If the next read reports that the quiz
is complete, it leaves that list. The module stays `started` until Canvas itself
reports `completed`.

## Coverage and errors

All counts describe **returned modules/items**. `collection_complete` is always
`null`, because this adapter does not establish completeness beyond the existing
reader's pagination behavior. `item_coverage` compares the number of returned
items with a reported integer `items_count`; it distinguishes a match, a shorter
list, a larger list and an unknown count. A matching count is not a course-wide
completeness claim. The current token reader follows Link pages up to its
existing cap; broker behavior remains subject to its existing numeric-page and
page-cap boundaries. This workflow changes neither transport.

The digest validates the **normalized output of the existing full module reader**.
`reader_source` names that boundary and `upstream_response_shape` is always
`not_observed`. The existing token reader wraps a non-list JSON page into a list,
and the full module reader can replace malformed inline items with a fallback
response. A singleton HTTP module or module-item object can therefore produce a
valid digest after normalization; this workflow does not certify that the raw
HTTP pages obeyed Canvas's array response contract. Identity, parent and duplicate
checks apply to the rows that reach this boundary. Raw inline rows replaced by a
successful fallback are not independently inspected by the digest.

The existing full module reader fetches omitted or short inline item lists.
Read failures remain failures. Invalid module/item identities, duplicate
identities, or explicit course/module mismatches refuse the digest. The CLI
returns exit 1 with a JSON error on stderr and no successful result on stdout;
the MCP call returns a tool error. Empty returned courses remain an explicit
zero-row view with unknown overall completeness.

The Canvas contract distinguishes caller-specific state/completion from module
structure and documents all/one and sequential rules:
[Modules API](https://developerdocs.instructure.com/services/canvas/resources/modules).
This implementation does not request another student's identity.

## Native receiving

```bash
python -m pytest -q tests/test_module_progress.py tests/test_module_progress_process.py
```

The maintained suite includes actual loopback HTTP, CLI subprocesses and MCP
stdio calls. Its fictional course covers explicit Link continuation for modules
and item fallback, changed completion, locked and one-of modules, missing student
fields, unsupported values, empty courses, malformed identities and denied later
pages. It asserts that every HTTP operation is GET. No account or real learner
record is used; fixture behavior is not evidence of a particular school's access
or live session.
