"""Compact facts from the requesting user's included Canvas submission."""

from __future__ import annotations

from typing import Any

_FIELDS = (
    ("workflow_state", str, "string"),
    ("submission_type", str, "string"),
    ("submitted_at", str, "string"),
    ("late_policy_status", str, "string"),
    ("attempt", int, "nonnegative integer"),
    ("late", bool, "boolean"),
    ("missing", bool, "boolean"),
    ("excused", bool, "boolean"),
)


def project_assignment_submission(value: Any) -> tuple[dict[str, Any] | None, list[str]]:
    """Keep supplied facts without deriving submission or deadline policy."""
    if value is None:
        return None, []
    if not isinstance(value, dict):
        return None, ["submission: expected an object or null"]

    result: dict[str, Any] = {}
    warnings: list[str] = []
    for name, expected_type, description in _FIELDS:
        if name not in value:
            continue
        supplied = value[name]
        valid = supplied is None or (
            type(supplied) is expected_type
            and (expected_type is not int or supplied >= 0)
        )
        if valid:
            result[name] = supplied
        else:
            warnings.append(f"submission.{name}: expected {description} or null")
    return result, warnings
