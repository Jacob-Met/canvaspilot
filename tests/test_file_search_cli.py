import contextlib
import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from canvaspilot.cli import main
from canvaspilot.client import CanvasClient as NativeClient


class FileSearchCLITests(unittest.TestCase):
    def run_cli(self, handler, argv=None, stdout=None):
        calls, clients = [], []
        def handle(request):
            calls.append((request.method, str(request.url)))
            return handler(request)
        def factory(**kwargs):
            client = NativeClient(**kwargs)
            client._http = httpx.Client(base_url=kwargs["base_url"],
                                       transport=httpx.MockTransport(handle))
            clients.append(client)
            return client
        output = stdout if stdout is not None else io.StringIO()
        error = io.StringIO()
        logger = logging.getLogger("httpx")
        previous = logger.level
        logger.setLevel(logging.DEBUG)
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / "never-created"
            args = ["find-files", *(argv or ["42", "--text", "notes"]),
                    "--base-url", "https://synthetic.invalid", "--token", "synthetic",
                    "--profile", str(profile)]
            with patch("canvaspilot.client.CanvasClient", factory), contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                try:
                    main(args)
                    status = 0
                except SystemExit as exc:
                    status = exc.code
            self.assertFalse(profile.exists())
        self.assertEqual(logger.level, logging.DEBUG)
        logger.setLevel(previous)
        self.assertTrue(all(client._http is None for client in clients))
        return status, output.getvalue(), error.getvalue(), calls, clients

    def test_real_client_complete_pagination_and_normalized_observation(self):
        def handler(q):
            if "cursor" in q.url.params:
                return httpx.Response(200, json=[
                    {"id": 8, "display_name": None, "filename": "NOTES.txt", "size": 2**60},
                    {"id": 8, "display_name": None, "filename": "other"}], request=q)
            return httpx.Response(200, json=[
                {"id": 8, "display_name": "notes.pdf", "filename": "", "size": 0,
                 "url": "https://do-not-follow.invalid/document"}, None],
                headers={"Link": '<https://synthetic.invalid/api/v1/courses/42/files?cursor=opaque%2B2>; rel="next"'}, request=q)
        status, stdout, stderr, calls, clients = self.run_cli(handler)
        self.assertEqual(status, 0, stderr)
        self.assertEqual(stderr, "")
        result = json.loads(stdout)
        self.assertEqual(result["counts"], {"returned": 3, "matched": 2, "nonmatching": 0, "unknown": 1})
        self.assertEqual([x["source"]["id"] for x in result["courses"][0]["observations"]], [8, 8, 8])
        self.assertEqual(result["courses"][0]["observations"][1]["source"]["size"], 2**60)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(method == "GET" and "/courses/42/files?" in url for method, url in calls))
        self.assertIn("cursor=opaque%2B2", calls[1][1])
        self.assertEqual(len(clients), 1)

    def test_all_courses_in_explicit_order_and_empty_observation(self):
        status, stdout, stderr, calls, _ = self.run_cli(
            lambda q: httpx.Response(200, json=[], request=q), ["0077", "42", "--text", "notes"])
        self.assertEqual(status, 0, stderr)
        self.assertEqual(json.loads(stdout)["course_ids"], ["77", "42"])
        self.assertIn("/courses/77/files?", calls[0][1])
        self.assertIn("/courses/42/files?", calls[1][1])

    def test_late_course_error_has_no_successful_stdout(self):
        def handler(q):
            if "/42/" in q.url.path:
                return httpx.Response(200, json=[{"display_name": "notes", "filename": ""}], request=q)
            return httpx.Response(503, text="synthetic unavailable", request=q)
        status, stdout, stderr, calls, _ = self.run_cli(handler, ["42", "77", "--text", "notes"])
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertFalse(json.loads(stderr)["ok"])
        self.assertEqual(len(calls), 2)

    def test_late_page_error_has_no_successful_stdout(self):
        def handler(q):
            if "cursor" in q.url.params:
                return httpx.Response(500, text="synthetic late page", request=q)
            return httpx.Response(200, json=[{"display_name": "notes", "filename": ""}],
                headers={"Link": '<https://synthetic.invalid/api/v1/courses/42/files?cursor=next>; rel="next"'}, request=q)
        status, stdout, stderr, calls, _ = self.run_cli(handler)
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertFalse(json.loads(stderr)["ok"])
        self.assertEqual(len(calls), 2)

    def test_invalid_input_before_client_or_profile_setup(self):
        for argv in (["0", "--text", "x"], ["1", "01", "--text", "x"],
                     ["1", "--text", "  "], ["1", "--text", "é" * 257]):
            with self.subTest(argv=repr(argv)), patch("canvaspilot.client.CanvasClient") as client, patch("canvaspilot.client.default_profile") as profile, contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as caught:
                    main(["find-files", *argv])
                self.assertEqual(caught.exception.code, 1)
                self.assertEqual(out.getvalue(), "")
                self.assertFalse(json.loads(err.getvalue())["ok"])
                client.assert_not_called()
                profile.assert_not_called()

    def test_malformed_name_refuses_and_closes_client(self):
        status, stdout, stderr, calls, _ = self.run_cli(
            lambda q: httpx.Response(200, json=[{"display_name": False, "filename": "notes"}], request=q))
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("display_name", json.loads(stderr)["message"])
        self.assertEqual(len(calls), 1)

    def test_auth_failure_is_not_empty_success(self):
        status, stdout, stderr, calls, _ = self.run_cli(
            lambda q: httpx.Response(401, json={"errors": []}, request=q))
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"], "CanvasAuthError")
        self.assertEqual(len(calls), 1)

    def test_broken_stdout_is_an_error_after_client_close(self):
        class Broken(io.StringIO):
            def write(self, value):
                raise BrokenPipeError("synthetic closed consumer")
        status, stdout, stderr, calls, clients = self.run_cli(
            lambda q: httpx.Response(200, json=[], request=q), stdout=Broken())
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"], "BrokenPipeError")
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(clients), 1)
