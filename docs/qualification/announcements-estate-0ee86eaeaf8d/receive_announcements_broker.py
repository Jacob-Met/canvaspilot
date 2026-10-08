#!/usr/bin/env python3
"""Independent announcement receiving through the real broker adapter.

Only the terminal HTTP boundary is substituted. No socket, account, browser,
or product mutation is used; this does not claim a real session-broker run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    sys.path.insert(0, str(source / "src"))
    from canvaspilot.api import CanvasAPI
    import canvaspilot.client as native

    def pins():
        return {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((source / "src").rglob("*.py"))}

    before = pins()
    results = []
    for name, count, detail, failed_page_status in [
        ("compact_61", 61, "compact", None),
        ("full_61", 61, "full", None),
        ("exact_page_multiple", 100, "full", None),
        ("later_auth_failure", 61, "compact", 403),
        ("later_server_failure", 61, "full", 500),
        ("single_page", 7, "compact", None),
        ("empty", 0, "full", None),
    ]:
        body = "Announcement & detail " + "x" * 450
        records = [{"id": i, "title": f"Topic {i}", "message": "<p>" + body.replace("&", "&amp;") + "</p>",
                    "posted_at": "2026-10-01T12:00:00Z", "context_code": "course_7",
                    "html_url": f"https://canvas.invalid/courses/7/discussion_topics/{i}"}
                   for i in range(1, count + 1)]
        records_before = json.dumps(records, sort_keys=True)
        courses = [7, "9"]
        seen = []

        def terminal_http(method, url, **kwargs):
            request = httpx.Request(method, url)
            if method == "GET" and url.endswith("/health"):
                return httpx.Response(200, json={"ok": True}, request=request)
            assert method == "POST" and url.endswith("/fetch"), (method, url)
            envelope = kwargs["json"]
            assert envelope["op"] == "fetch" and envelope["method"] == "GET"
            assert envelope["body"] is None
            target = httpx.URL("https://canvas.invalid" + envelope["path"])
            assert target.path == "/api/v1/announcements"
            query = target.params
            assert query.get_list("context_codes[]") == ["course_7", "course_9"]
            assert query["active_only"] == "true"
            assert query["start_date"] == "2026-10-01"
            assert query["per_page"] == "50"
            page = int(query.get("page", "1"))
            seen.append({"page": page, "path": envelope["path"]})
            status = failed_page_status if page == 2 and failed_page_status else 200
            payload = records[(page - 1) * 50:page * 50] if status == 200 else {"error": "synthetic refusal"}
            return httpx.Response(200, json={"ok": True, "response": {"status": status, "json": payload}}, request=request)

        returned = None
        failure = None
        with patch.object(native, "_broker_request", side_effect=terminal_http):
            with CanvasAPI(native.CanvasClient(base_url="https://canvas.invalid", token="", profile=Path("unused-profile"))) as api:
                try:
                    returned = api.list_announcements(courses, start_date="2026-10-01", detail=detail)
                except (native.CanvasAuthError, httpx.HTTPStatusError) as error:
                    failure = error
        if failed_page_status:
            expected_error = native.CanvasAuthError if failed_page_status == 403 else httpx.HTTPStatusError
            checks = {"whole_call_refused": isinstance(failure, expected_error),
                      "no_partial_return": returned is None,
                      "later_page_reached": [s["page"] for s in seen] == [1, 2]}
        else:
            expected_pages = list(range(1, count // 50 + 2))
            message = body if detail == "full" else body[:400] + "…"
            checks = {"no_error": failure is None,
                      "all_ids_in_order": returned is not None and [r["id"] for r in returned] == list(range(1, count + 1)),
                      "terminal_page_reached": [s["page"] for s in seen] == expected_pages,
                      "text_projection": returned is not None and all(r["message_text"] == message for r in returned)}
        checks["records_and_filters_unchanged"] = records_before == json.dumps(records, sort_keys=True) and courses == [7, "9"]
        results.append({"case": name, "passed": all(checks.values()), "checks": checks,
                        "requests": seen, "returned_rows": None if returned is None else len(returned),
                        "exception": None if failure is None else type(failure).__name__})

    preserved = before == pins()
    receipt = {"status": "pass" if preserved and all(r["passed"] for r in results) else "fail",
               "python": sys.version, "httpx": httpx.__version__, "source_sha256": before,
               "source_preserved": preserved, "cases": results,
               "scope": "Real curated API, pagination, health/fetch helpers and query encoding; synthetic terminal HTTP, no live broker."}
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "passed": sum(r["passed"] for r in results),
                      "failed": [r["case"] for r in results if not r["passed"]], "source_preserved": preserved}))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
