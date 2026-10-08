"""Independent four-module observation fixed before the export candidate was read."""
from copy import deepcopy

COURSE = "731"
COMPLETED_NAME = "Finished — preserve earlier status <&> 日本語"
CHOICE_NAME = "Choose one: score ≥ 0 or contribute"
LOCKED_NAME = "Sequenced study — lock is a reported state"
UNKNOWN_NAME = "Policy awaiting provider detail — " + "long-title-" * 18
D_INCOMPLETE = "Some reported requirements have unsupported types or unknown completion."
D_NOT_REPORTED = "Some items have no reported requirement; this does not establish optionality."
D_COVERAGE = "Returned items do not establish a complete match to a reported item count."

def row(identity, module, title, kind, position, requirement, **extras):
    value = {"id": identity, "module_id": module, "title": title, "type": kind,
             "position": position, "indent": 0, "content_id": None,
             "html_url": None, "published": True, **extras}
    if requirement != "ABSENT":
        value["completion_requirement"] = requirement
    return value

FINISHED_ITEMS = [
    row(93031, 9103, "Old requirement <script>globalThis.notAllowed=1</script> 日本語",
        "Assignment", 2, {"type": "must_submit", "completed": False, "points": 0},
        indent=1, content_id=7731, html_url="javascript:alert('saved')"),
    row("93032", 9103, "Imported check", "Page", 1,
        {"type": "future_gate", "completed": True, "minimum": 10}, published=None),
]
CHOICE_ITEMS = [
    row(93011, 9101, "Earn at least zero — 0 points remains a supplied threshold",
        "Quiz", 3, {"type": "min_score", "completed": False, "min_score": 0},
        content_id=7732, html_url="https://unreachable.invalid/courses/731/quizzes/7732"),
    row(93012, 9101, "Contribution already reported complete", "Discussion", 1,
        {"type": "must_contribute", "completed": True}),
    row(93013, 9101, "No requirement supplied ≠ optional", "Page", 2, "ABSENT"),
]
LOCKED_ITEMS = [
    row(93021, 9102, "Read after prerequisites", "Page", 2,
        {"type": "must_view", "completed": False}, published=False),
    row(93022, 9102, "Percentage threshold 0%; completion unknown", "Quiz", 1,
        {"type": "min_percentage", "completed": None, "min_percentage": 0}),
    row(93023, 9102, "Unreported requirement", "File", 3, None),
]
MODULES = [
    {"id": 9103, "course_id": 731, "name": COMPLETED_NAME, "position": 30,
     "published": True, "state": "completed", "completed_at": "2026-10-01T09:00:00Z",
     "unlock_at": None, "requirement_type": "all", "require_sequential_progress": False,
     "prerequisite_module_ids": [], "items_count": 2, "items": FINISHED_ITEMS},
    {"id": 9101, "course_id": "731", "name": CHOICE_NAME, "position": 10,
     "published": True, "state": "started", "completed_at": None, "unlock_at": None,
     "requirement_type": "one", "require_sequential_progress": False,
     "prerequisite_module_ids": [9103], "items_count": 4, "items": CHOICE_ITEMS[:1]},
    {"id": 9102, "course_id": 731, "name": LOCKED_NAME, "position": 20,
     "published": False, "state": "locked", "completed_at": None,
     "unlock_at": "2026-10-12T08:00:00Z", "requirement_type": "all",
     "require_sequential_progress": True, "prerequisite_module_ids": ["9101"],
     "items_count": 3, "items": LOCKED_ITEMS},
    {"id": 9104, "course_id": 731, "name": UNKNOWN_NAME, "position": 5,
     "published": None, "state": "waiting_external", "completed_at": None, "unlock_at": None,
     "requirement_type": "threshold", "require_sequential_progress": "yes",
     "prerequisite_module_ids": [0], "items_count": None, "items": []},
]

# Each outcome/action/count below is explicit fixture evidence, independent of
# the product's normalization and renderer. No CanvasPilot import is used here.
def fixed_item(value, status, supported, action):
    return {**deepcopy(value), "completion_requirement": deepcopy(value.get("completion_requirement")),
            "completion_status": status, "requirement_type_supported": supported,
            "required_action": action}

def fixed_module(raw, *, items, counts, state, rule, sequential, prerequisites,
                 coverage, remaining_rule, incomplete, unknown, locked, diagnostics):
    return {
        "id": raw["id"], "name": raw["name"], "position": raw["position"],
        "published": raw["published"], "state": state, "reported_state": raw["state"],
        "completed_at": raw["completed_at"], "unlock_at": raw["unlock_at"],
        "requirement_type": rule, "reported_requirement_type": raw["requirement_type"],
        "require_sequential_progress": sequential, "prerequisite_module_ids": prerequisites,
        "reported_prerequisite_module_ids": deepcopy(raw["prerequisite_module_ids"]),
        "item_coverage": {"reported_count": raw["items_count"], "returned_count": len(items), "status": coverage},
        "requirement_counts": dict(zip(("completed", "incomplete", "unknown", "not_reported"), counts)),
        "remaining_work": {"scope": "reported_requirements_in_returned_items", "rule": remaining_rule,
                           "incomplete_item_ids": incomplete, "unknown_completion_item_ids": unknown,
                           "module_locked": locked, "item_access": "not_assessed"},
        "items": items, "diagnostics": diagnostics,
    }

EXPECTED_MODULES = [
    fixed_module(MODULES[0], items=[
        fixed_item(FINISHED_ITEMS[0], "incomplete", True, "Submit the work"),
        fixed_item(FINISHED_ITEMS[1], "unknown", False, None)],
        counts=(0, 1, 1, 0), state="completed", rule="all", sequential=False, prerequisites=[],
        coverage="matches_reported_count", remaining_rule="module_completed",
        incomplete=[], unknown=[], locked=False, diagnostics=[D_INCOMPLETE]),
    fixed_module(MODULES[1], items=[
        fixed_item(CHOICE_ITEMS[0], "incomplete", True, "Meet the reported minimum score"),
        fixed_item(CHOICE_ITEMS[1], "completed", True, "Contribute to the item"),
        fixed_item(CHOICE_ITEMS[2], "not_reported", None, None)],
        counts=(1, 1, 0, 1), state="started", rule="one", sequential=False, prerequisites=[9103],
        coverage="shorter_than_reported_count", remaining_rule="one", incomplete=[93011],
        unknown=[], locked=False, diagnostics=[D_COVERAGE, D_NOT_REPORTED]),
    fixed_module(MODULES[2], items=[
        fixed_item(LOCKED_ITEMS[0], "incomplete", True, "View the item"),
        fixed_item(LOCKED_ITEMS[1], "unknown", True, "Meet the reported minimum percentage"),
        fixed_item(LOCKED_ITEMS[2], "not_reported", None, None)],
        counts=(0, 1, 1, 1), state="locked", rule="all", sequential=True, prerequisites=["9101"],
        coverage="matches_reported_count", remaining_rule="all", incomplete=[93021], unknown=[93022],
        locked=True, diagnostics=[D_INCOMPLETE, D_NOT_REPORTED]),
    fixed_module(MODULES[3], items=[], counts=(0, 0, 0, 0), state="unknown", rule="unknown",
        sequential=None, prerequisites=None, coverage="unknown", remaining_rule="unknown",
        incomplete=[], unknown=[], locked=None, diagnostics=[
            "Student-specific module state is missing or unsupported.",
            "The all-versus-one requirement rule is missing or unsupported.",
            "Sequential-progress policy was not reported as a boolean.",
            "Prerequisite module IDs are missing or malformed.", D_COVERAGE]),
]
EXPECTED = {
    "course_id": COURSE, "mode": "token", "module_id": None,
    "modules_returned": 4, "modules_included": 4, "modules_omitted_by_selection": 0,
    "collection_complete": None, "count_scope": "returned_modules_and_items",
    "state_source": "Canvas module.state for the authenticated caller",
    "reader_source": "CanvasAPI.list_modules(detail=full)",
    "upstream_response_shape": "not_observed",
    "module_state_counts": {"locked": 1, "unlocked": 0, "started": 1, "completed": 1, "unknown": 1},
    "modules": EXPECTED_MODULES,
}

def expected_selected():
    value = deepcopy(EXPECTED)
    value.update(module_id="9101", modules_included=1, modules_omitted_by_selection=3,
                 module_state_counts={"locked": 0, "unlocked": 0, "started": 1, "completed": 0, "unknown": 0},
                 modules=[deepcopy(EXPECTED_MODULES[1])])
    return value
