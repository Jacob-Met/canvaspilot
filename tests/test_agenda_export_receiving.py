"""Independent native receiving for the complete selected-course agenda view."""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import canvaspilot

FIXTURE = json.loads("{\n  \"courses\": [\n    901,\n    \"00044\",\n    7\n  ],\n  \"start\": \"2026-10-09\",\n  \"end\": \"2026-10-11\",\n  \"event\": [\n    {\n      \"id\": 0,\n      \"context_code\": \"course_901\",\n      \"all_day\": false,\n      \"start_at\": \"2026-10-10T00:15:00+14:00\",\n      \"title\": \"<script id=\\\"peer-injection\\\">no</script> & zero\",\n      \"description\": \"<img src=\\\"https://invalid.example/pixel\\\" onerror=\\\"alert(1)\\\">\",\n      \"location_name\": \"\",\n      \"hidden\": false,\n      \"audit\": {\n        \"n\": 0,\n        \"null\": null,\n        \"empty\": []\n      }\n    },\n    {\n      \"id\": \"same\",\n      \"context_code\": \"course_44\",\n      \"all_day\": false,\n      \"start_at\": \"2026-10-10T23:59:60Z\",\n      \"title\": \"Unresolved leap-second source\"\n    },\n    {\n      \"id\": -2,\n      \"context_code\": \"course_7\",\n      \"all_day\": false,\n      \"start_at\": \"2026-10-10T01:00:00-00:00\",\n      \"title\": \"Unknown-local-offset marker retained\"\n    },\n    {\n      \"id\": \"all-day-event\",\n      \"context_code\": \"course_44\",\n      \"all_day\": true,\n      \"all_day_date\": \"2026-10-09\",\n      \"start_at\": null,\n      \"title\": \"Source-date all-day marker\"\n    }\n  ],\n  \"assignment\": [\n    {\n      \"id\": \"0\",\n      \"context_code\": \"course_44\",\n      \"all_day\": false,\n      \"start_at\": \"2026-10-09T23:59:59.0000000000000000009-10:00\",\n      \"title\": \"String zero at exact fractional instant\",\n      \"assignment\": {\n        \"id\": 0,\n        \"course_id\": \"00044\",\n        \"due_at\": null,\n        \"overrides\": []\n      }\n    },\n    {\n      \"id\": \"same\",\n      \"context_code\": \"course_section_18\",\n      \"effective_context_code\": \"course_901\",\n      \"all_day\": null,\n      \"start_at\": \"2026-10-10T01:00:00Z\",\n      \"title\": \"No all-day declaration; retain timing unavailable\",\n      \"assignment\": null\n    },\n    {\n      \"id\": \"assignment-day\",\n      \"context_code\": \"course_7\",\n      \"all_day\": true,\n      \"all_day_date\": \"2026-10-11\",\n      \"start_at\": \"different retained source\",\n      \"title\": \"Declared day is not a timestamp\",\n      \"assignment\": {\n        \"course_id\": 7,\n        \"due_at\": \"not interpreted\"\n      },\n      \"overrides\": [\n        {\n          \"student_ids\": [],\n          \"due_at\": null\n        }\n      ]\n    }\n  ]\n}\n")
GROUPS = ("timed", "all_day", "timing_unavailable")
SOURCE = Path(canvaspilot.__file__).resolve().parents[2]
EVIDENCE = os.environ.get("CANVAS_AGENDA_PEER_EVIDENCE")


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(SOURCE)): digest(path.read_bytes())
        for path in sorted((SOURCE / "src").rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


@contextmanager
def calendar(late_bad: bool = False):
    requests = []

    class Calendar(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            target = urlsplit(self.path)
            query = parse_qs(target.query)
            requests.append({"method": "GET", "path": target.path, "query": query})
            next_url = None
            if target.path != "/api/v1/calendar_events":
                self.send_error(404)
                return
            if query == {"opaque_cursor": ["peer-tail"]}:
                rows = copy.deepcopy(FIXTURE["assignment"][1:])
                if late_bad:
                    rows[0]["context_code"] = "course_999"
                    rows[0].pop("effective_context_code")
            elif query.get("type") == ["event"]:
                rows = FIXTURE["event"]
            elif query.get("type") == ["assignment"]:
                rows = FIXTURE["assignment"][:1]
                next_url = (
                    f"http://127.0.0.1:{self.server.server_port}"
                    "/api/v1/calendar_events?opaque_cursor=peer-tail"
                )
            else:
                self.send_error(400)
                return
            content = json.dumps(rows).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            if next_url:
                self.send_header("Link", f'<{next_url}>; rel="next"')
            self.end_headers()
            self.wfile.write(content)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Calendar)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


class SavedHtml(HTMLParser):
    def __init__(self, content: bytes):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.articles = []
        self.active = None
        self.pre = None
        self.download = None
        self.text = []
        self.feed(content.decode("utf-8"))
        self.close()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.tags.append((tag, attributes))
        if tag == "article" and "agenda-entry" in attributes.get("class", "").split():
            self.active = {"attributes": attributes, "entries": []}
        if tag == "pre" and self.active is not None:
            self.pre = []
        if tag == "a" and attributes.get("id") == "download-native":
            self.download = attributes

    def handle_data(self, data):
        self.text.append(data)
        if self.pre is not None:
            self.pre.append(data)

    def handle_endtag(self, tag):
        if tag == "pre" and self.pre is not None:
            self.active["entries"].append(json.loads("".join(self.pre)))
            self.pre = None
        if tag == "article" and self.active is not None:
            self.articles.append(self.active)
            self.active = None


class AgendaViewIndependentReceiving(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_before = source_hashes()
        cls.fixture_before = json.dumps(FIXTURE, sort_keys=True)
        cls.native, cls.native_trace = cls.cli("original-agenda", "agenda")
        cls.report = json.loads(cls.native.stdout)
        if EVIDENCE:
            Path(EVIDENCE).mkdir(parents=True, exist_ok=True)
            (Path(EVIDENCE) / "source-before.json").write_text(
                json.dumps(cls.source_before, indent=2) + "\n", encoding="utf-8"
            )

    @classmethod
    def tearDownClass(cls):
        after = source_hashes()
        if EVIDENCE:
            (Path(EVIDENCE) / "source-after.json").write_text(
                json.dumps(after, indent=2) + "\n", encoding="utf-8"
            )
        if after != cls.source_before:
            raise AssertionError("Native source changed during receiving")
        if json.dumps(FIXTURE, sort_keys=True) != cls.fixture_before:
            raise AssertionError("Authored input records changed during receiving")

    @classmethod
    def cli(cls, label, command, *, output=None, late_bad=False):
        with tempfile.TemporaryDirectory(prefix="canvas-agenda-peer-client-") as folder:
            profile = Path(folder) / "unused-profile"
            with calendar(late_bad) as (base, requests):
                arguments = [
                    sys.executable, "-B", "-m", "canvaspilot.cli", command,
                    *map(str, FIXTURE["courses"]),
                    "--start", FIXTURE["start"], "--end", FIXTURE["end"],
                    "--base-url", base, "--token", "authored-peer-calendar-token",
                    "--profile", str(profile),
                ]
                if output is not None:
                    arguments += ["--out", str(output)]
                # Only this explicit loopback child omits ambient proxy variables.
                env = {
                    key: value for key, value in os.environ.items()
                    if not key.lower().endswith("_proxy")
                }
                env["PYTHONDONTWRITEBYTECODE"] = "1"
                env["PYTHONPATH"] = str(SOURCE / "src") + os.pathsep + env.get("PYTHONPATH", "")
                result = subprocess.run(
                    arguments, cwd=SOURCE, env=env, capture_output=True, timeout=25, check=False
                )
                trace = copy.deepcopy(requests)
            if profile.exists():
                raise AssertionError("Explicit-token CLI unexpectedly created a profile")
        if EVIDENCE:
            destination = Path(EVIDENCE) / label
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "stdout").write_bytes(result.stdout)
            (destination / "stderr").write_bytes(result.stderr)
            (destination / "process.json").write_text(
                json.dumps({
                    "exit": result.returncode,
                    "requests": trace,
                    "stdout_sha256": digest(result.stdout),
                    "stderr_sha256": digest(result.stderr),
                    "output_created": output is not None and output.exists(),
                }, indent=2) + "\n", encoding="utf-8"
            )
            if output is not None and output.exists():
                (destination / "agenda.html").write_bytes(output.read_bytes())
        return result, trace

    def renderer(self):
        name = "canvaspilot.agenda_export"
        self.assertIsNotNone(importlib.util.find_spec(name), "New agenda view module is absent")
        return importlib.import_module(name)

    def assert_trace(self, trace):
        self.assertEqual(len(trace), 3)
        self.assertTrue(all(row["method"] == "GET" for row in trace))
        self.assertTrue(all(row["path"] == "/api/v1/calendar_events" for row in trace))
        self.assertEqual(
            [row["query"].get("type") for row in trace], [["event"], ["assignment"], None]
        )
        for row in trace[:2]:
            self.assertEqual(row["query"]["context_codes[]"], ["course_901", "course_44", "course_7"])
            self.assertEqual(row["query"]["start_date"], [FIXTURE["start"]])
            self.assertEqual(row["query"]["end_date"], [FIXTURE["end"]])
        self.assertEqual(trace[2]["query"], {"opaque_cursor": ["peer-tail"]})

    def assert_html(self, content):
        parsed = SavedHtml(content)
        self.assertTrue(content.startswith(b"<!doctype html>"))
        expected = [entry for group in GROUPS for entry in self.report[group]]
        self.assertEqual(len(parsed.articles), 7)
        self.assertEqual([row["entries"] for row in parsed.articles], [[entry] for entry in expected])
        self.assertEqual(
            [row["attributes"]["data-course"] for row in parsed.articles],
            [entry["course_id"] for entry in expected],
        )
        self.assertEqual(
            [row["attributes"]["data-group"] for row in parsed.articles],
            ["timed"] * 3 + ["all_day"] * 2 + ["timing_unavailable"] * 2,
        )
        # These are authored source dates, deliberately different from UTC dates.
        self.assertEqual(
            [row["attributes"]["data-date"] for row in parsed.articles],
            ["2026-10-10", "2026-10-10", "2026-10-09", "2026-10-09", "2026-10-11", "", ""],
        )
        self.assertIsNotNone(parsed.download)
        encoded = parsed.download["href"]
        self.assertTrue(encoded.startswith("data:application/json;base64,"))
        raw = base64.b64decode(encoded.split(",", 1)[1], validate=True)
        self.assertEqual(raw, self.native.stdout)
        self.assertEqual(parsed.download["data-sha256"], digest(raw))
        self.assertEqual(parsed.download["download"], "course-agenda.json")
        self.assertIn(FIXTURE["event"][0]["title"], "".join(parsed.text))
        self.assertFalse(any(attrs.get("id") == "peer-injection" for _, attrs in parsed.tags))
        self.assertFalse(any(tag in {"img", "iframe", "object", "embed"} for tag, _ in parsed.tags))
        self.assertFalse(any(tag == "script" and "src" in attrs for tag, attrs in parsed.tags))
        self.assertFalse(any(tag == "link" for tag, _ in parsed.tags))
        if EVIDENCE:
            (Path(EVIDENCE) / "rendered.html").write_bytes(content)
        return parsed

    def test_original_native_paginated_source_control(self):
        self.assertEqual(self.native.returncode, 0, self.native.stderr)
        self.assertEqual(self.native.stderr, b"")
        self.assert_trace(self.native_trace)
        self.assertEqual(self.report["selection"]["course_ids"], ["901", "44", "7"])
        self.assertEqual(self.report["collection_counts"], {"event": 4, "assignment": 3})
        self.assertEqual(
            self.report["counts"], {"total": 7, "timed": 3, "all_day": 2, "timing_unavailable": 2}
        )
        self.assertEqual(
            [[(row["kind"], row["source"]["index"]) for row in self.report[group]] for group in GROUPS],
            [[("event", 0), ("event", 2), ("assignment", 0)],
             [("event", 3), ("assignment", 2)], [("event", 1), ("assignment", 1)]],
        )
        for group in GROUPS:
            for entry in self.report[group]:
                self.assertEqual(entry["record"], FIXTURE[entry["kind"]][entry["source"]["index"]])
        identities = [row["record"]["id"] for row in self.report["timed"]]
        self.assertEqual(identities, [0, -2, "0"])
        self.assertEqual([type(value) for value in identities], [int, int, str])
        self.assertEqual(self.native.stdout, (json.dumps(self.report, indent=2) + "\n").encode())

    def test_complete_typed_source_and_human_render(self):
        render = self.renderer().render_agenda_html
        before = copy.deepcopy(self.report)
        content = render(self.report)
        self.assertIsInstance(content, bytes)
        self.assertEqual(content, render(self.report))
        self.assert_html(content)
        self.assertEqual(self.report, before)

    def test_source_binding_refusals(self):
        render = self.renderer().render_agenda_html
        before = copy.deepcopy(self.report)
        bad_reports = [copy.deepcopy(self.report) for _ in range(5)]
        bad_reports[0]["counts"]["total"] += 1
        bad_reports[1]["collection_counts"]["event"] += 1
        bad_reports[2]["timed"][1]["source"] = copy.deepcopy(bad_reports[2]["timed"][0]["source"])
        bad_reports[3]["timed"][0]["course_id"] = "999"
        bad_reports[4]["timed"][0]["record"]["context_code"] = "course_999"
        for malformed in bad_reports:
            original_bad = copy.deepcopy(malformed)
            with self.assertRaises((TypeError, ValueError)):
                render(malformed)
            self.assertEqual(malformed, original_bad)
        self.assertEqual(self.report, before)

    def test_actual_cli_paginated_export_and_exclusive_writer(self):
        with tempfile.TemporaryDirectory(prefix="canvas-agenda-peer-output-") as folder:
            output = Path(folder) / "Agenda – ñ 7.html"
            result, trace = self.cli("export-complete", "export-agenda", output=output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, b"")
            self.assert_trace(trace)
            content = output.read_bytes()
            self.assert_html(content)
            self.assertEqual(content, self.renderer().render_agenda_html(self.report))
            self.assertEqual(json.loads(result.stdout), {
                "ok": True, "output": str(output), "counts": self.report["counts"],
                "native_report_sha256": digest(self.native.stdout), "html_sha256": digest(content),
            })
            self.assertEqual(list(Path(folder).iterdir()), [output])
            refused, repeated = self.cli("export-existing", "export-agenda", output=output)
            self.assertEqual(refused.returncode, 1)
            self.assertEqual(refused.stdout, b"")
            self.assertEqual(repeated, [])
            error = json.loads(refused.stderr)
            self.assertIs(error["ok"], False)
            self.assertEqual(error["error"], "FileExistsError")
            self.assertIn("already exists", error["message"])
            self.assertEqual(output.read_bytes(), content)
            self.assertEqual(list(Path(folder).iterdir()), [output])

    def test_late_source_refusal_no_partial_publication(self):
        with tempfile.TemporaryDirectory(prefix="canvas-agenda-peer-refusal-") as folder:
            output = Path(folder) / "not-published.html"
            result, trace = self.cli(
                "export-late-source-refusal", "export-agenda", output=output, late_bad=True
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(result.stdout, b"")
            self.assert_trace(trace)
            error = json.loads(result.stderr)
            self.assertIs(error["ok"], False)
            self.assertEqual(error["error"], "ValueError")
            self.assertIn("assignment[1]", error["message"])
            self.assertIn("outside the selected courses", error["message"])
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

