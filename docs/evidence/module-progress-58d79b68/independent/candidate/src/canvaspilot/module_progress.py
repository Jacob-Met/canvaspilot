"""Read a course study checklist without inferring Canvas completion or access."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from canvaspilot.api import CanvasAPI

_STATES = {"locked", "unlocked", "started", "completed"}
_ACTIONS = {
    "must_view": "View the item",
    "must_submit": "Submit the work",
    "must_contribute": "Contribute to the item",
    "must_mark_done": "Mark the item done",
    "min_score": "Meet the reported minimum score",
    "min_percentage": "Meet the reported minimum percentage",
}


class ModuleProgressError(ValueError):
    """Invalid query identity or unusable Canvas progress response."""


def _identity(value: Any, label: str) -> str:
    if type(value) is int and value > 0:
        return str(value)
    if isinstance(value, str) and value.isascii() and value.isdecimal() and int(value) > 0:
        return str(int(value))
    raise ModuleProgressError(f"{label} must be a positive numeric Canvas ID")


def _item(item: dict[str, Any]) -> dict[str, Any]:
    raw = item.get("completion_requirement")
    requirement = raw if isinstance(raw, dict) else {}
    kind = requirement.get("type")
    supported = isinstance(kind, str) and kind in _ACTIONS
    completed = requirement.get("completed")
    if raw is None:
        status = "not_reported"
    elif supported and type(completed) is bool:
        status = "completed" if completed else "incomplete"
    else:
        status = "unknown"
    return {
        "id": item["id"],
        "module_id": item.get("module_id"),
        "title": item.get("title"),
        "type": item.get("type"),
        "position": item.get("position"),
        "indent": item.get("indent"),
        "content_id": item.get("content_id"),
        "html_url": item.get("html_url"),
        "published": item.get("published"),
        "completion_requirement": deepcopy(raw),
        "completion_status": status,
        "requirement_type_supported": supported if raw is not None else None,
        "required_action": _ACTIONS.get(kind) if supported else None,
    }


def _module(module: dict[str, Any]) -> dict[str, Any]:
    items = [_item(item) for item in module["items"]]
    reported_state = module.get("state")
    state = reported_state if isinstance(reported_state, str) and reported_state in _STATES else "unknown"
    reported_rule = module.get("requirement_type")
    rule = reported_rule if isinstance(reported_rule, str) and reported_rule in {"all", "one"} else "unknown"
    counts = {
        status: sum(item["completion_status"] == status for item in items)
        for status in ("completed", "incomplete", "unknown", "not_reported")
    }
    count = module.get("items_count")
    if type(count) is not int or count < 0:
        coverage = "unknown"
    elif len(items) < count:
        coverage = "shorter_than_reported_count"
    elif len(items) > count:
        coverage = "more_than_reported_count"
    else:
        coverage = "matches_reported_count"
    sequential = module.get("require_sequential_progress")
    sequential = sequential if type(sequential) is bool else None
    prerequisites = module.get("prerequisite_module_ids")
    diagnostics = []
    if state == "unknown":
        diagnostics.append("Student-specific module state is missing or unsupported.")
    if rule == "unknown":
        diagnostics.append("The all-versus-one requirement rule is missing or unsupported.")
    if sequential is None:
        diagnostics.append("Sequential-progress policy was not reported as a boolean.")
    if not isinstance(prerequisites, list):
        diagnostics.append("Prerequisite module IDs are missing or malformed.")
    else:
        try:
            for prerequisite in prerequisites:
                _identity(prerequisite, "Prerequisite module ID")
        except ValueError:
            diagnostics.append("Prerequisite module IDs are missing or malformed.")
            prerequisites = None
    if not isinstance(prerequisites, list):
        prerequisites = None
    if coverage != "matches_reported_count":
        diagnostics.append("Returned items do not establish a complete match to a reported item count.")
    if counts["unknown"]:
        diagnostics.append("Some reported requirements have unsupported types or unknown completion.")
    if counts["not_reported"]:
        diagnostics.append("Some items have no reported requirement; this does not establish optionality.")
    # Canvas's module state is authoritative, including modules with a one-of
    # rule or requirements edited after a student already unlocked/completed it.
    kind = "module_completed" if state == "completed" else rule
    remaining = [] if state == "completed" else [
        item["id"] for item in items if item["completion_status"] == "incomplete"
    ]
    return {
        "id": module["id"],
        "name": module.get("name"),
        "position": module.get("position"),
        "published": module.get("published"),
        "state": state,
        "reported_state": deepcopy(reported_state),
        "completed_at": module.get("completed_at"),
        "unlock_at": module.get("unlock_at"),
        "requirement_type": rule,
        "reported_requirement_type": deepcopy(reported_rule),
        "require_sequential_progress": sequential,
        "prerequisite_module_ids": deepcopy(prerequisites),
        "reported_prerequisite_module_ids": deepcopy(module.get("prerequisite_module_ids")),
        "item_coverage": {
            "reported_count": deepcopy(count),
            "returned_count": len(items),
            "status": coverage,
        },
        "requirement_counts": counts,
        "remaining_work": {
            "scope": "reported_requirements_in_returned_items",
            "rule": kind,
            "incomplete_item_ids": remaining,
            "unknown_completion_item_ids": [
                item["id"] for item in items if item["completion_status"] == "unknown"
            ] if state != "completed" else [],
            "module_locked": True if state == "locked" else False if state in _STATES else None,
            "item_access": "not_assessed",
        },
        "items": items,
        "diagnostics": diagnostics,
    }


def module_progress(
    api: CanvasAPI, course_id: int | str, *, module_id: int | str | None = None,
) -> dict[str, Any]:
    """Project the existing full module reader for the authenticated caller.

    All counts refer to returned rows. No mark-read, completion, grade or other
    write is performed. Item access and whole-course completeness are not inferred.
    """
    course = _identity(course_id, "Course ID")
    selected_id = _identity(module_id, "Module ID") if module_id is not None else None
    modules = api.list_modules(course, detail="full")
    if not isinstance(modules, list):
        raise ModuleProgressError("Canvas returned a malformed module collection")
    seen_modules: set[str] = set()
    seen_items: set[str] = set()
    selected = []
    for module in modules:
        if not isinstance(module, dict):
            raise ModuleProgressError("Canvas returned a malformed module")
        identity = _identity(module.get("id"), "Returned module ID")
        if identity in seen_modules:
            raise ModuleProgressError("Canvas returned duplicate module IDs")
        seen_modules.add(identity)
        if "course_id" in module and _identity(module["course_id"], "Returned course ID") != course:
            raise ModuleProgressError("Canvas returned a module from a different course")
        items = module.get("items")
        if not isinstance(items, list):
            raise ModuleProgressError("Canvas returned a malformed module-item collection")
        for item in items:
            if not isinstance(item, dict):
                raise ModuleProgressError("Canvas returned a malformed module item")
            item_id = _identity(item.get("id"), "Returned item ID")
            if item_id in seen_items:
                raise ModuleProgressError("Canvas returned duplicate module-item IDs")
            seen_items.add(item_id)
            if "module_id" in item and _identity(item["module_id"], "Returned item's module ID") != identity:
                raise ModuleProgressError("Canvas returned an item from a different module")
        if selected_id is None or identity == selected_id:
            selected.append(_module(module))
    if selected_id is not None and not selected:
        raise ModuleProgressError("Requested module was not present in the returned course modules")
    return {
        "course_id": course,
        "mode": api.client.mode,
        "module_id": selected_id,
        "modules_returned": len(modules),
        "modules_included": len(selected),
        "modules_omitted_by_selection": len(modules) - len(selected),
        "collection_complete": None,
        "count_scope": "returned_modules_and_items",
        "state_source": "Canvas module.state for the authenticated caller",
        "module_state_counts": {
            state: sum(module["state"] == state for module in selected)
            for state in ("locked", "unlocked", "started", "completed", "unknown")
        },
        "modules": selected,
    }
