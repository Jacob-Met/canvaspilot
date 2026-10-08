"""Read Canvas's cached discussion tree without marking its entries read.

The report keeps source entry fields separately from derived reading aids. Paths
identify positions in this returned view only; they are not persistent entry IDs.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from canvaspilot.api import strip_html


def _identity(value: Any) -> tuple[type, Any] | None:
    # Preserve JSON number/string identity; bool is not an integer identifier.
    if type(value) is int or (isinstance(value, str) and value):
        return (type(value), value)
    return None


def validate_discussion_selection(
    course_id: int | str, topic_id: int | str, unread_only: bool
) -> tuple[str, str]:
    if type(unread_only) is not bool:
        raise ValueError("unread_only must be a boolean")
    result = []
    for name, value in (("course_id", course_id), ("topic_id", topic_id)):
        if type(value) is int:
            valid = value > 0
            text = str(value)
        elif isinstance(value, str):
            valid = bool(value) and value.isascii() and value.isdigit() and any(char != "0" for char in value)
            text = value
        else:
            valid = False
            text = ""
        if not valid:
            raise ValueError(f"{name} must be a positive numeric Canvas ID")
        result.append(text)
    return result[0], result[1]


def _optional_list(view: dict[str, Any], name: str) -> list[Any] | None:
    value = view.get(name)
    if value is not None and not isinstance(value, list):
        raise ValueError(f"Canvas returned malformed discussion {name}")
    return value


def _marker_keys(view: dict[str, Any], name: str) -> set[tuple[type, Any]] | None:
    values = _optional_list(view, name)
    if values is None:
        return None
    keys = [_identity(value) for value in values]
    if any(key is None for key in keys):
        raise ValueError(f"Canvas returned malformed discussion {name} identifier")
    return set(keys)


def build_discussion_thread(
    topic: dict[str, Any], view: dict[str, Any], *, unread_only: bool = False
) -> dict[str, Any]:
    """Flatten the returned tree in source order and optionally retain unread paths.

    An unread selection contains known unread entries and the ancestors needed
    for their context. Unlocated read markers and unknown facts remain explicit.
    No request, entry merge, read marking or source-data mutation occurs here.
    """
    if type(unread_only) is not bool:
        raise ValueError("unread_only must be a boolean")
    if not isinstance(topic, dict) or not isinstance(view, dict):
        raise ValueError("Canvas returned a malformed discussion topic or view")
    roots = view.get("view")
    if not isinstance(roots, list):
        raise ValueError("Canvas returned a malformed discussion entry tree")
    participants = _optional_list(view, "participants")
    if participants is not None and any(not isinstance(p, dict) for p in participants):
        raise ValueError("Canvas returned malformed discussion participants")
    unread = _marker_keys(view, "unread_entries")
    forced = _marker_keys(view, "forced_entries")
    if unread_only and unread is None:
        raise ValueError("Unread selection is unavailable: Canvas did not supply unread_entries")

    # Iterative traversal also gives every occurrence its own structural address.
    # Repeated object references cannot occur in a JSON tree; refuse them rather
    # than looping on an aliased/cyclic object supplied to the pure Python helper.
    flattened: list[tuple[tuple[int, ...], dict[str, Any]]] = []
    stack = [((index,), entry) for index, entry in reversed(list(enumerate(roots)))]
    seen = set()
    while stack:
        path, entry = stack.pop()
        if not isinstance(entry, dict):
            raise ValueError("Canvas returned a malformed discussion entry")
        if id(entry) in seen:
            raise ValueError("Canvas returned an aliased or cyclic discussion entry tree")
        seen.add(id(entry))
        flattened.append((path, entry))
        replies = entry.get("replies", [])
        if not isinstance(replies, list):
            raise ValueError("Canvas returned malformed discussion replies")
        stack.extend(((*path, index), reply) for index, reply in reversed(list(enumerate(replies))))

    entry_counts = Counter(_identity(entry.get("id")) for _, entry in flattened)
    participant_counts = Counter(_identity(p.get("id")) for p in participants or [])
    participant_by_id = {
        _identity(p.get("id")): p
        for p in participants or []
        if _identity(p.get("id")) is not None and participant_counts[_identity(p.get("id"))] == 1
    }
    ambiguous_unread = {
        key for key in unread or set()
        if entry_counts[key] > 1
    }
    if unread_only and ambiguous_unread:
        raise ValueError("Unread selection is ambiguous: a returned entry ID is repeated")

    rows = []
    for path, entry in flattened:
        key = _identity(entry.get("id"))
        identifiable = key is not None and entry_counts[key] == 1
        state = "unknown"
        if identifiable and unread is not None:
            state = "unread" if key in unread else "read"
        body = entry.get("message")
        author = participant_by_id.get(_identity(entry.get("user_id")))
        rows.append({
            "path": list(path),
            "parent_path": list(path[:-1]) if len(path) > 1 else None,
            "entry": deepcopy({field: value for field, value in entry.items() if field != "replies"}),
            "replies_supplied": "replies" in entry,
            "reply_count": len(entry.get("replies", [])),
            "message_text": strip_html(body) if isinstance(body, str) and entry.get("deleted") is not True else None,
            "author": deepcopy(author) if entry.get("deleted") is not True else None,
            "read_state": state,
            "forced_read_state": key in forced if identifiable and forced is not None else None,
            "context_only": False,
        })
    selected = {tuple(row["path"]) for row in rows if row["read_state"] == "unread"}
    if unread_only:
        retained = {path[:size] for path in selected for size in range(1, len(path) + 1)}
        returned = [row for row in rows if tuple(row["path"]) in retained]
        for row in returned:
            row["context_only"] = tuple(row["path"]) not in selected
    else:
        returned = rows

    unmatched = [
        value for value in view.get("unread_entries") or []
        if entry_counts[_identity(value)] == 0
    ]
    warnings = []
    if unread is None:
        warnings.append("Canvas did not supply unread_entries; entry read states are unknown.")
    if any(row["read_state"] == "unknown" for row in rows):
        warnings.append("Some returned entries have an unknown read state; they are not inferred read or unread.")
    if unmatched:
        warnings.append("Some supplied unread identifiers are absent from this cached entry tree.")
    if any(key is not None and count > 1 for key, count in participant_counts.items()):
        warnings.append("Repeated participant identifiers are not used to attribute entries.")
    if any(key is not None and count > 1 for key, count in entry_counts.items()):
        warnings.append("Repeated entry identifiers do not establish a unique read-state association.")
    body = topic.get("message")
    return {
        "topic": deepcopy(topic),
        "topic_message_text": strip_html(body) if isinstance(body, str) else None,
        "source": {
            "kind": "canvas_cached_discussion_view",
            "eventually_consistent": True,
            "new_entries_requested": False,
        },
        "selection": "unread_with_ancestors" if unread_only else "all",
        "view_metadata": deepcopy({key: value for key, value in view.items() if key != "view"}),
        "entries": returned,
        "unmatched_unread_entries": deepcopy(unmatched),
        "counts": {
            "observed_entries": len(rows),
            "returned_entries": len(returned),
            "known_unread_entries": len(selected) if unread is not None else None,
            "unknown_read_state_entries": sum(row["read_state"] == "unknown" for row in rows),
        },
        "warnings": warnings,
    }
