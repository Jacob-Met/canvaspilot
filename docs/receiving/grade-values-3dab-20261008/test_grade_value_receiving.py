"""Independent grade-value matrix through actual API, CLI and registered MCP."""
from __future__ import annotations
import asyncio
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(sys.argv[1]).resolve()
MANIFEST_PATH = Path(sys.argv[2]).resolve()
OUT = Path(sys.argv[3]).resolve()
if OUT.exists():
    raise RuntimeError("Use a fresh receiving output directory")
OUT.mkdir()
MANIFEST = json.loads(MANIFEST_PATH.read_text())
EXPECTED_SOURCES = {row["path"]: row for row in MANIFEST["files"]}
def source_guard():
    current = {}
    for name, row in EXPECTED_SOURCES.items():
        raw = (ROOT / name).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if sha != row["sha256"] or blob != row["git_blob"]:
            raise RuntimeError("Pinned source changed: " + name)
        current[name] = {"sha256": sha, "git_blob": blob}
    return current
SOURCE_BEFORE = source_guard()
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
for name in list(os.environ):
    if name.lower().endswith("_proxy"):
        os.environ.pop(name)
os.environ["CANVAS_PROFILE"] = str(OUT / "unused-parent-profile")
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from grade_review_fixture import GradeReviewHTTPFixture

def value_data():
    def assignment(aid, group, name, points, submission_marker="absent"):
        row = {"id": aid, "course_id": 42, "assignment_group_id": group,
               "name": name, "points_possible": points, "due_at": "2000-01-01T00:00:00Z"}
        if submission_marker != "absent":
            row["submission"] = submission_marker
        return row
    def submission(aid, **values):
        return {"assignment_id": aid, "user_id": 7, **values}
    rows = [
        assignment(301, 3, "Bonus with zero possible points", 0, submission(
            301, score=7.5, grade="7.5", entered_score=7.5, entered_grade="7.50",
            points_deducted=0, posted_at="2026-10-08T09:00:00Z", assignment_visible=True,
            missing=False, late=False, excused=False)),
        assignment(302, 3, "A real zero from an earlier attempt", 10, submission(
            302, score=0, grade="0", posted_at="2026-10-08T09:00:00Z",
            attempt=2, grade_matches_current_submission=False, missing=False)),
        assignment(303, 3, "Explicit null grades", None, submission(
            303, score=None, grade=None, entered_score=None, entered_grade=None,
            points_deducted=None, posted_at="2026-10-08T09:00:00Z",
            assignment_visible=None, missing=None, late=None, excused=None)),
        assignment(304, 3, "No supplied grade or posting metadata", 10, submission(
            304, workflow_state="unsubmitted", assignment_visible=None)),
    ]
    other = [
        assignment(401, 4, "Withheld despite neighboring values", 100, submission(
            401, score=99, grade="A", entered_score=100, entered_grade="A+",
            points_deducted=1, posted_at=None, missing=True, late=True, excused=True)),
        assignment(402, 4, "Invisible despite a supplied zero", 10, submission(
            402, score=0, grade="0", entered_score=0, entered_grade="0",
            points_deducted=0, posted_at="2026-10-08T09:00:00Z",
            assignment_visible=False, missing=False)),
        assignment(403, 4, "No returned submission is not missing work", 10),
        assignment(404, 4, "Null submission is not missing work", 10, None),
    ]
    return {
        "profile": {"id": 7, "name": "Authored receiver learner"},
        "course": {
            "id": 42, "name": "Authored grade-value matrix", "hide_final_grades": False,
            "apply_assignment_group_weights": False,
            "enrollments": [
                {"type": "teacher", "role": "TeacherEnrollment", "user_id": 7,
                 "enrollment_state": "active", "computed_final_score": None},
                {"type": "student", "role": "StudentEnrollment", "user_id": 7,
                 "enrollment_state": "active", "computed_current_score": 0,
                 "computed_final_score": 105.25, "computed_current_grade": "0",
                 "computed_final_grade": "A+", "computed_current_letter_grade": "",
                 "current_grading_period_id": 5, "current_grading_period_title": "Autumn",
                 "current_period_computed_current_score": 0,
                 "current_period_computed_final_score": None,
                 "current_period_computed_current_grade": None,
                 "current_period_computed_final_grade": "A",
                 "unposted_current_score": 999, "override_score": 888},
                {"type": "student", "role": "StudentEnrollment", "user_id": "7",
                 "enrollment_state": "completed", "computed_current_score": None,
                 "computed_final_score": 99.5, "computed_current_grade": "",
                 "computed_final_grade": "Pass", "unposted_final_score": 777},
            ],
            "grading_periods": [{"id": 5, "title": "Autumn", "weight": 0}],
        },
        "groups": [
            {"id": 3, "name": "Zero weight", "group_weight": 0,
             "rules": {"drop_lowest": 0, "drop_highest": 0, "never_drop": [302]},
             "assignments": rows},
            {"id": 4, "name": "Weight above one hundred", "group_weight": 150,
             "rules": None, "assignments": other},
        ],
    }

def scenarios():
    values = value_data()
    hidden = deepcopy(values)
    hidden["course"]["hide_final_grades"] = True
    result = {"values": values, "hidden": hidden}
    for state in ("absent", "null", "empty"):
        data = value_data()
        for key in ("enrollments", "grading_periods"):
            if state == "absent":
                data["course"].pop(key)
            else:
                data["course"][key] = None if state == "null" else []
        data["groups"] = (
            [{"id": 3}, {"id": 4, "assignments": None}, {"id": 5, "assignments": []}]
            if state == "absent" else []
        )
        result["containers_" + state] = data
    return result

CASES = scenarios()
OBSERVATIONS = []
PARENT_CONNECTIONS = []
PARENT_BLOCKED = []
PROFILE_PATHS = []

class GradeValueReceiving(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = GradeReviewHTTPFixture()
        cls.port = cls.fixture.server.server_port
        def audit(event, args):
            if event == "socket.connect":
                address = args[1]
                allowed = isinstance(address, tuple) and address[0] == "127.0.0.1" and address[1] == cls.port
                if not allowed:
                    PARENT_BLOCKED.append(repr(address))
                    raise RuntimeError("Only the authored loopback fixture is allowed")
                PARENT_CONNECTIONS.append({"host": address[0], "port": address[1]})
        sys.addaudithook(audit)
        (OUT / "authored-cases.json").write_text(json.dumps(CASES, indent=2, allow_nan=False) + "\n")

    @classmethod
    def tearDownClass(cls):
        cls.fixture.close()

    def child_env(self, label):
        env = {name: os.environ[name] for name in ("PATH", "SYSTEMROOT", "LANG") if name in os.environ}
        profile = OUT / ("unused-profile-" + label)
        PROFILE_PATHS.append(profile)
        env.update({
            "PYTHONPATH": os.pathsep.join([str(Path(__file__).parent / "guard"), str(ROOT / "src")]),
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(OUT),
            "CANVAS_BASE_URL": self.fixture.base_url,
            "CANVAS_API_TOKEN": "grade-review-synthetic-token",
            "CANVAS_PROFILE": str(profile),
            "NO_PROXY": "127.0.0.1,localhost",
            "GRADE_REVIEW_LOOPBACK_PORT": str(self.port),
            "GRADE_REVIEW_SOURCE": str(ROOT),
            "GRADE_REVIEW_CHILD_RECEIPT": str(OUT / (label + "-guard.json")),
        })
        return env

    def record(self, route, case, result, start, raw=None):
        requests = deepcopy(self.fixture.requests[start:])
        self.assertEqual([row["method"] for row in requests], ["GET"] * 4)
        self.assertEqual([row["path"] for row in requests], [
            "/api/v1/users/self/profile", "/api/v1/courses/42",
            "/api/v1/courses/42/assignment_groups", "/api/v1/courses/42/assignment_groups"])
        self.assertEqual(requests[1]["query"]["include[]"],
                         ["total_scores", "current_grading_period_scores", "grading_periods"])
        self.assertEqual(requests[2]["query"]["include[]"], ["assignments", "submission"])
        self.assertEqual(requests[3]["query"], {"cursor": ["last-page"]})
        self.assertEqual(self.fixture.data, CASES[case])
        self.check_report(case, result)
        OBSERVATIONS.append({"route": route, "case": case, "report": result,
                             "requests": requests, "raw": raw})

    def check_report(self, case, report):
        self.assertEqual(report["authenticated_user_id"], 7)
        self.assertIsNone(report["collection_complete"])
        self.assertEqual(report["upstream_response_shape"], "not_observed")
        self.assertEqual(report["reader_source"], "CanvasClient.get_paginated")
        self.assertEqual(report["warnings"], [])
        if case.startswith("containers_"):
            state = case.removeprefix("containers_")
            for key in ("enrollments", "grading_periods"):
                self.assertEqual(report[key + "_state"],
                                 {"absent": "not_returned", "null": "null", "empty": "returned"}[state])
                self.assertEqual(report[key], [] if state == "empty" else None)
            counts = {key: 0 for key in report["counts"]}
            if state == "absent":
                self.assertEqual([row["assignments_state"] for row in report["assignment_groups"]],
                                 ["not_returned", "null", "returned"])
                self.assertEqual([row["assignments"] for row in report["assignment_groups"]],
                                 [None, None, []])
                counts["groups_returned"] = 3
                counts["groups_without_assignment_list"] = 2
            else:
                self.assertEqual(report["assignment_groups"], [])
            self.assertEqual(report["counts"], counts)
            return

        rows = report["enrollments"]
        self.assertEqual(len(rows), 3)
        self.assertEqual([row["context"]["type"] for row in rows], ["teacher", "student", "student"])
        self.assertEqual([row["context"]["role"] for row in rows],
                         ["TeacherEnrollment", "StudentEnrollment", "StudentEnrollment"])
        self.assertEqual([row["context"]["enrollment_state"] for row in rows],
                         ["active", "active", "completed"])
        self.assertEqual([row["context"]["user_id"] for row in rows], [7, 7, "7"])
        if case == "hidden":
            self.assertEqual(report["totals_visibility"], "hidden_by_course")
            self.assertEqual([row["reported_totals"] for row in rows], [{}, {}, {}])
        else:
            self.assertEqual(report["totals_visibility"], "reported_fields_only")
            self.assertEqual(rows[0]["reported_totals"], {"computed_final_score": None})
            self.assertEqual(rows[1]["reported_totals"], {
                "computed_current_score": 0, "computed_final_score": 105.25,
                "computed_current_grade": "0", "computed_final_grade": "A+",
                "computed_current_letter_grade": "",
                "current_period_computed_current_score": 0,
                "current_period_computed_final_score": None,
                "current_period_computed_current_grade": None,
                "current_period_computed_final_grade": "A",
            })
            self.assertIs(type(rows[1]["reported_totals"]["computed_current_score"]), int)
            self.assertEqual(rows[2]["reported_totals"], {
                "computed_current_score": None, "computed_final_score": 99.5,
                "computed_current_grade": "", "computed_final_grade": "Pass"})
        self.assertEqual(rows[1]["context"]["current_grading_period_id"], 5)
        self.assertEqual(rows[1]["context"]["current_grading_period_title"], "Autumn")
        self.assertEqual(report["grading_periods"], [{"id": 5, "title": "Autumn", "weight": 0}])
        self.assertFalse(report["course"]["apply_assignment_group_weights"])
        groups = report["assignment_groups"]
        self.assertEqual([row["group_weight"] for row in groups], [0, 150])
        self.assertEqual(groups[0]["rules"], {"drop_lowest": 0, "drop_highest": 0, "never_drop": [302]})
        self.assertIsNone(groups[1]["rules"])
        assignments = {row["fields"]["id"]: row for group in groups for row in group["assignments"]}
        bonus = assignments[301]
        self.assertEqual(bonus["fields"]["points_possible"], 0)
        self.assertEqual(bonus["submission"]["fields"]["score"], 7.5)
        self.assertEqual(bonus["submission"]["fields"]["entered_grade"], "7.50")
        self.assertEqual(bonus["submission"]["fields"]["points_deducted"], 0)
        zero = assignments[302]["submission"]["fields"]
        self.assertEqual(zero["score"], 0)
        self.assertIs(type(zero["score"]), int)
        self.assertEqual(zero["grade"], "0")
        self.assertIs(type(zero["grade"]), str)
        self.assertFalse(zero["grade_matches_current_submission"])
        self.assertEqual(zero["attempt"], 2)
        null = assignments[303]["submission"]
        self.assertEqual(null["grade_visibility"], "reported_fields")
        for key in ("score", "grade", "entered_score", "entered_grade", "points_deducted"):
            self.assertIn(key, null["fields"])
            self.assertIsNone(null["fields"][key])
        absent = assignments[304]["submission"]
        self.assertEqual(absent["grade_visibility"], "reported_fields")
        for key in ("score", "grade", "posted_at", "missing"):
            self.assertNotIn(key, absent["fields"])
        for aid, expected in ((401, "not_posted"), (402, "assignment_not_visible")):
            hidden = assignments[aid]["submission"]
            self.assertEqual(hidden["grade_visibility"], expected)
            for key in ("score", "grade", "entered_score", "entered_grade", "points_deducted"):
                self.assertNotIn(key, hidden["fields"])
        self.assertTrue(assignments[401]["submission"]["fields"]["excused"])
        self.assertEqual(assignments[403]["submission_state"], "not_returned")
        self.assertEqual(assignments[404]["submission_state"], "null")
        self.assertIsNone(assignments[403]["submission"])
        self.assertIsNone(assignments[404]["submission"])
        self.assertEqual(report["counts"], {
            "groups_returned": 2, "assignments_returned": 8, "groups_without_assignment_list": 0,
            "submissions_not_returned": 1, "submissions_null": 1,
            "explicitly_not_posted": 1, "explicitly_not_visible": 1,
            "excused_true": 1, "missing_true": 1, "late_true": 1,
            "grade_matches_current_submission_false": 1})

    def check_child(self, label):
        receipt = json.loads((OUT / (label + "-guard.json")).read_text())
        self.assertTrue(receipt["guard_active"])
        self.assertEqual(receipt["blocked_connections"], [])
        self.assertTrue(receipt["allowed_connections"])
        self.assertEqual(receipt["guard_sha256"],
                         hashlib.sha256((Path(__file__).parent / "guard/sitecustomize.py").read_bytes()).hexdigest())
        self.assertIn("canvaspilot.grade_review", receipt["source_origins"])
        for item in receipt["source_origins"].values():
            self.assertEqual(item["sha256"], EXPECTED_SOURCES[item["path"]]["sha256"])

    def test_api_values_and_unknown_containers(self):
        with CanvasAPI(CanvasClient(base_url=self.fixture.base_url,
                                   token="grade-review-synthetic-token",
                                   profile=OUT / "unused-api-profile")) as api:
            for name, data in CASES.items():
                with self.subTest(case=name):
                    self.fixture.data = deepcopy(data)
                    start = len(self.fixture.requests)
                    result = api.grade_review(42)
                    self.record("API", name, result, start)

    def test_cli_values_and_unknown_containers(self):
        for name, data in CASES.items():
            with self.subTest(case=name):
                self.fixture.data = deepcopy(data)
                start = len(self.fixture.requests)
                label = "cli-" + name
                flags = ["-B"] + (["-O"] if sys.flags.optimize else [])
                process = subprocess.run(
                    [sys.executable, *flags, "-m", "canvaspilot.cli", "grade-review", "42"],
                    env=self.child_env(label), capture_output=True, text=True, timeout=15)
                self.assertEqual(process.returncode, 0, process.stderr)
                result = json.loads(process.stdout)
                self.record("CLI", name, result, start,
                            {"exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr})
                self.check_child(label)

    def test_registered_mcp_values_and_unknown_containers(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def run():
            flags = ["-B"] + (["-O"] if sys.flags.optimize else [])
            params = StdioServerParameters(command=sys.executable,
                args=[*flags, "-m", "canvaspilot.cli", "mcp"], env=self.child_env("mcp"))
            with (OUT / "mcp.stderr").open("w") as stderr:
                async with (stdio_client(params, errlog=stderr) as (read, write),
                            ClientSession(read, write, read_timeout_seconds=10) as session):
                    await session.initialize()
                    for name, data in CASES.items():
                        with self.subTest(case=name):
                            self.fixture.data = deepcopy(data)
                            start = len(self.fixture.requests)
                            response = await session.call_tool("canvas_grade_review", {"course_id": "42"})
                            wire = response.model_dump(by_alias=True)
                            self.assertFalse(wire.get("isError", False), wire)
                            result = json.loads(wire["content"][0]["text"])
                            self.record("MCP", name, result, start, wire)
        asyncio.run(run())
        self.check_child("mcp")

if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(GradeValueReceiving))
    after = source_guard()
    for p in PROFILE_PATHS + [OUT / "unused-parent-profile", OUT / "unused-api-profile"]:
        if p.exists():
            raise RuntimeError("Unexpected profile materialization: " + str(p))
    payload = {
        "source_manifest_sha256": hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "guard_sha256": hashlib.sha256((Path(__file__).parent / "guard/sitecustomize.py").read_bytes()).hexdigest(),
        "head": MANIFEST["head"], "tree": MANIFEST["tree"],
        "python": sys.version, "optimize": sys.flags.optimize,
        "packages": {name: importlib.metadata.version(name) for name in ("httpx", "mcp", "pydantic")},
        "methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "expected_value_scenarios": list(CASES),
        "observations": OBSERVATIONS, "parent_connections": PARENT_CONNECTIONS,
        "blocked_connections": PARENT_BLOCKED, "profile_paths_created": [],
        "source_before": SOURCE_BEFORE, "source_after": after,
    }
    (OUT / "receipt.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    ok = result.wasSuccessful() and SOURCE_BEFORE == after and not PARENT_BLOCKED and len(OBSERVATIONS) == 15
    print(json.dumps({"ok": ok, "methods": result.testsRun, "observations": len(OBSERVATIONS),
                      "receipt": str(OUT / "receipt.json")}))
    raise SystemExit(0 if ok else 1)
