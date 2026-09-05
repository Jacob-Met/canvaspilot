from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient


def test_strip_and_fixture_whoami():
    fixture = {
        "profile": {"id": 42, "name": "Test Student"},
        "routes": {
            "GET /api/v1/courses": [
                {"id": 1, "name": "CS101", "course_code": "CS101"},
            ],
            "GET /api/v1/courses/1/assignments": [
                {
                    "id": 9,
                    "name": "HW1",
                    "due_at": "2026-09-10T23:59:00Z",
                    "description": "<p>Do the <b>thing</b></p>",
                    "submission_types": ["online_upload"],
                }
            ],
            "GET /api/v1/courses/1/quizzes": [
                {"id": 3, "title": "Quiz 1", "question_count": 5, "points_possible": 10},
            ],
            "GET /api/v1/courses/1/pages": [
                {"url": "home", "title": "Home", "published": True},
            ],
        },
    }
    api = CanvasAPI(CanvasClient(fixture=fixture, base_url="https://example.test"))
    me = api.whoami()
    assert me["profile"]["name"] == "Test Student"
    assert me["mode"] == "fixture"
    courses = api.list_courses()
    assert courses[0]["id"] == 1
    brief = api.assignment_brief(1, 9)
    assert "thing" in brief["prompt"]
    assert "<" not in brief["prompt"]
    quizzes = api.list_quizzes(1)
    assert quizzes[0]["id"] == 3
    pages = api.list_pages(1)
    assert pages[0]["url"] == "home"
    api.close()
