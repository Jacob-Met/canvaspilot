"""Actual offline direct-file children; this is not a package-import substitute."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_agenda_changes import raw, saved

CLI = Path(__file__).resolve().parents[1] / "src/canvaspilot/agenda_changes_cli.py"


class AgendaChangesCLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="agenda-changes-")
        self.root = Path(self.temporary.name)
        self.before = self.root / "before café.json"
        self.after = self.root / "after file.json"
        self.before.write_bytes(raw(saved([{"id": 1, "title": "before"}])))
        self.after.write_bytes(raw(saved([{"id": 1, "title": "after"}])))

    def tearDown(self):
        self.temporary.cleanup()

    def run_cli(self, *extra, before=None, after=None):
        files = [self.before, self.after, CLI, CLI.with_name("agenda_changes.py")]
        pins = {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in files}
        cmd = [sys.executable, "-B", str(CLI), "--before", str(before or self.before),
               "--after", str(after or self.after), *extra]
        result = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, timeout=10, check=False,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(pins, {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in files})
        return result

    def test_actual_json_and_default_text_delivery(self):
        result = self.run_cli("--format", "json")
        self.assertEqual((result.returncode, result.stderr), (0, b""))
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed["counts"]["changed"], 1)
        self.assertEqual(parsed["groups"][0]["field_changes"][0]["field"], "title")
        readable = self.run_cli()
        self.assertEqual((readable.returncode, readable.stderr), (0, b""))
        self.assertIn(b'"value": "before"', readable.stdout)
        self.assertIn(b'"value": "after"', readable.stdout)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["after file.json", "before café.json"])

    def test_late_malformed_input_has_no_success_stdout(self):
        self.after.write_bytes(b'{"schema":')
        result = self.run_cli("--format", "json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertIsInstance(json.loads(result.stderr)["error"], str)

    def test_missing_directory_and_fifo_inputs_refuse(self):
        paths = [self.root / "missing", self.root]
        if hasattr(os, "mkfifo"):
            fifo = self.root / "saved.fifo"
            os.mkfifo(fifo)
            paths.append(fifo)
        for path in paths:
            with self.subTest(path=path):
                result = self.run_cli(after=path)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b"")
                self.assertIn("error", json.loads(result.stderr))

    def test_symlink_regular_input_is_read_only(self):
        link = self.root / "chosen report.json"
        link.symlink_to(self.after)
        result = self.run_cli("--format", "json", after=link)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(link.is_symlink())
        self.assertEqual(json.loads(result.stdout)["inputs"]["after"]["bytes"], self.after.stat().st_size)

    def test_usage_and_repeated_flags_refuse_before_read(self):
        result = self.run_cli("--before", "never-read")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"only once", result.stderr)
        result = self.run_cli("--format", "html", before=self.root / "missing")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")

    def test_strict_invalid_bytes_and_source_counts_refuse(self):
        for data in (b"\xff", b'{"duplicate":1,"duplicate":2}', raw(saved()).replace(b'"total": 0', b'"total": false')):
            with self.subTest(data=data):
                self.after.write_bytes(data)
                result = self.run_cli()
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b"")
                self.assertIn("error", json.loads(result.stderr))


if __name__ == "__main__":
    unittest.main()
