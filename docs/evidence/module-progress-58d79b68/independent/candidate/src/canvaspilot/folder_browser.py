"""Read one folder and bounded child-metadata pages within a Canvas course."""

from __future__ import annotations

import re
from typing import Any

from canvaspilot.client import CanvasClient

MAX_PAGE = 10_000
MAX_PER_PAGE = 100
_NUMERIC_ID = re.compile(r"[0-9]{1,32}\Z")
_FOLDER_FIELDS = (
    "id", "context_type", "context_id", "parent_folder_id", "name", "full_name",
    "position", "folders_count", "files_count", "created_at", "updated_at",
    "unlock_at", "lock_at", "locked", "hidden", "locked_for_user",
    "hidden_for_user", "for_submissions",
)
_FILE_FIELDS = (
    "id", "folder_id", "display_name", "filename", "size", "created_at",
    "updated_at", "modified_at", "unlock_at", "lock_at", "locked", "hidden",
    "locked_for_user", "hidden_for_user", "lock_explanation",
)


class FolderBrowseError(ValueError):
    """The server response cannot establish the requested folder scope."""


def _identifier(value: int | str, name: str, *, root: bool = False) -> str:
    if root and value == "root":
        return "root"
    if type(value) not in (int, str):
        raise ValueError(f"{name} must be a positive numeric Canvas ID")
    text = str(value)
    if not _NUMERIC_ID.fullmatch(text) or int(text) < 1:
        raise ValueError(f"{name} must be a positive numeric Canvas ID")
    return str(int(text))


def _bounded_integer(value: int, name: str, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be an integer from 1 to {maximum}")
    return value


def _response_id(value: Any, name: str) -> str:
    try:
        return _identifier(value, name)
    except ValueError as error:
        raise FolderBrowseError(f"Folder browser received an invalid {name}") from error


def _folder(
    value: Any,
    course_id: str,
    *,
    expected_id: str | None = None,
    parent_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FolderBrowseError("Folder browser expected a folder object")
    folder_id = _response_id(value.get("id"), "folder ID")
    if value.get("context_type") != "Course" or _response_id(
        value.get("context_id"), "course ID"
    ) != course_id:
        raise FolderBrowseError("Folder response belongs to another course")
    if expected_id is not None and folder_id != expected_id:
        raise FolderBrowseError("Folder response does not match the requested folder")
    if parent_id is not None and (
        folder_id == parent_id
        or _response_id(value.get("parent_folder_id"), "parent folder ID") != parent_id
    ):
        raise FolderBrowseError("Child folder response belongs to another parent")
    return {key: value[key] for key in _FOLDER_FIELDS if key in value}


def _file(value: Any, folder_id: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FolderBrowseError("Folder browser expected a file object")
    _response_id(value.get("id"), "file ID")
    if _response_id(value.get("folder_id"), "file folder ID") != folder_id:
        raise FolderBrowseError("File response belongs to another folder")
    result = {key: value[key] for key in _FILE_FIELDS if key in value}
    result["content_type"] = value.get("content-type") or value.get("content_type")
    return result


def _page(value: Any, page: int, per_page: int, project: Any) -> dict[str, Any]:
    if not isinstance(value, list):
        raise FolderBrowseError("Folder browser expected a metadata page array")
    if len(value) > per_page:
        raise FolderBrowseError("Folder browser received more items than the requested page bound")
    items = [project(item) for item in value]
    ids = [_response_id(item.get("id"), "item ID") for item in items]
    if len(ids) != len(set(ids)):
        raise FolderBrowseError("Folder browser received duplicate identities within a page")
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "returned_count": len(items),
        # CanvasClient.request and the broker return bodies without Link headers.
        # A short (or empty) page therefore does not establish global completeness.
        "has_more": None,
        "next_page_to_try": page + 1 if page < MAX_PAGE else None,
        "page_limit_reached": page == MAX_PAGE,
    }


def browse_course_folder(
    client: CanvasClient,
    course_id: int | str,
    folder_id: int | str = "root",
    *,
    folders_page: int = 1,
    files_page: int = 1,
    per_page: int = 50,
) -> dict[str, Any]:
    """Return one selected folder and direct child pages, without downloading files.

    All three requests are GETs. The course-scoped folder lookup must establish
    identity and membership before the two folder-ID list endpoints are called.
    Page numbers are explicit requests through the existing client; next-page
    probes are not a claim that another page exists or that a listing is complete.
    """
    course = _identifier(course_id, "course_id")
    requested = _identifier(folder_id, "folder_id", root=True)
    folders_page = _bounded_integer(folders_page, "folders_page", MAX_PAGE)
    files_page = _bounded_integer(files_page, "files_page", MAX_PAGE)
    per_page = _bounded_integer(per_page, "per_page", MAX_PER_PAGE)

    folder = _folder(
        client.request("GET", f"/api/v1/courses/{course}/folders/{requested}"),
        course,
        expected_id=None if requested == "root" else requested,
    )
    selected = _response_id(folder["id"], "folder ID")
    folders = _page(
        client.request(
            "GET", f"/api/v1/folders/{selected}/folders",
            params={"page": folders_page, "per_page": per_page},
        ),
        folders_page,
        per_page,
        lambda child: _folder(child, course, parent_id=selected),
    )
    files = _page(
        client.request(
            "GET", f"/api/v1/folders/{selected}/files",
            params={"page": files_page, "per_page": per_page},
        ),
        files_page,
        per_page,
        lambda child: _file(child, selected),
    )
    return {
        "course_id": course,
        "folder": folder,
        "folders": folders,
        "files": files,
        "scope": "direct_children",
        "pagination": "explicit_pages_without_next_link_metadata",
    }
