"""Focused stdlib tests; run directly without importing CanvasPilot's initializer."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "src/canvaspilot/syllabus_source_compare.py"
SPEC = importlib.util.spec_from_file_location("syllabus_source_compare", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourceComparisonTests(unittest.TestCase):
    def test_exact_tokens_occurrences_and_context(self):
        before = b"same\r\nx\ry\nz"
        after = b"same\nx\ry\nz\n"
        value = MODULE.compare_sources(before, after)
        self.assertEqual(value["status"], "different")
        self.assertEqual(value["before"]["endings"], {"LF": 1, "CRLF": 1, "CR": 1, "NONE": 1})
        self.assertEqual(value["hunks"][0]["before_end"], 4)
        self.assertEqual([op["tag"] for op in value["hunks"][0]["operations"]], ["replace", "equal", "replace"])
        self.assertEqual(MODULE.compare_sources(b"", b"")["before"]["lines"], 0)
        self.assertEqual(MODULE.compare_sources(b"\n", b"\n")["before"]["lines"], 1)
        embedded = "\ufeffA\u0085B\u2028C\u2029D".encode()
        self.assertEqual(MODULE.compare_sources(embedded, embedded)["before"]["lines"], 1)

    def test_admission_boundaries_and_repetitive_work(self):
        exact = (b"a" * 127 + b"\n") * 4096
        self.assertEqual(len(exact), 512 * 1024)
        self.assertEqual(MODULE.compare_sources(exact, exact)["before"]["lines"], 4096)
        for bad in (exact + b"x", b"x\n" * 4097, b"\xff", b"\xed\xa0\x80"):
            with self.subTest(size=len(bad)), self.assertRaises(ValueError):
                MODULE.compare_sources(bad, b"")
        for bad in ("", bytearray(), None, 0):
            with self.subTest(kind=type(bad).__name__), self.assertRaises(TypeError):
                MODULE.compare_sources(bad, b"")
        start = time.perf_counter()
        repetitive = MODULE.compare_sources(b"a\n" * 4096, b"a\n" * 4095 + b"b\n")
        elapsed = time.perf_counter() - start
        self.assertEqual(repetitive["status"], "different")
        self.assertEqual(repetitive["hunks"][-1]["before_end"], 4096)
        print(json.dumps({"observation": "4096-line repetitive changed input", "seconds": elapsed,
                          "latency_guarantee": False}), flush=True)

    def test_reversible_display_and_report_limit(self):
        literal = '\ufeffé"\\\x00\x1b\x7f\u0085\u2028\u2029\U000e0001\U000e007f'
        quoted = MODULE.quote_display(literal)
        self.assertEqual(json.loads(quoted), literal)
        self.assertIn("\\udb40\\udc01", quoted)
        self.assertIn("\\udb40\\udc7f", quoted)
        self.assertIn("é", quoted)
        self.assertFalse(any(ord(c) < 32 or 0x7f <= ord(c) <= 0x9f for c in quoted))
        result = MODULE.compare_sources(b"x\r", b"x\n")
        rendered = MODULE.render_report(result, "a\x1b", "b").decode()
        self.assertIn('- B1 "x" ending=CR', rendered)
        self.assertIn('+ A1 "x" ending=LF', rendered)
        self.assertIn('"a\\u001b"', rendered)
        with patch.object(MODULE, "MAX_REPORT_BYTES", 10), self.assertRaises(ValueError):
            MODULE.render_report(result, "a", "b")

    def test_regular_file_selection_and_observed_change(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source"
            source.write_bytes(b"x")
            self.assertEqual(MODULE.read_source(str(source), "before"), b"x")
            link = Path(root) / "link"
            link.symlink_to(source)
            with self.assertRaises(ValueError):
                MODULE.read_source(str(link), "before")
            if hasattr(os, "mkfifo"):
                fifo = Path(root) / "fifo"
                os.mkfifo(fifo)
                with self.assertRaises(ValueError):
                    MODULE.read_source(str(fifo), "before")
            original_lstat = MODULE.os.lstat
            calls = 0

            def changed(path):
                nonlocal calls
                calls += 1
                if calls == 2:
                    source.write_bytes(b"changed")
                return original_lstat(path)

            with patch.object(MODULE.os, "lstat", side_effect=changed), self.assertRaises(ValueError):
                MODULE.read_source(str(source), "before")

    def test_publication_existing_race_and_long_basename(self):
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / ("a" * 240 + ".txt")
            self.assertEqual(MODULE.publish_report(str(destination), b"new"), [])
            self.assertEqual(destination.read_bytes(), b"new")
            with self.assertRaises(FileExistsError):
                MODULE.publish_report(str(destination), b"replace")
            for name, make in (("directory", lambda p: p.mkdir()),
                               ("broken", lambda p: p.symlink_to(Path(root) / "absent"))):
                path = Path(root) / name
                make(path)
                with self.assertRaises(FileExistsError):
                    MODULE.publish_report(str(path), b"replace")
            raced = Path(root) / "raced"

            def race(*args):
                raced.write_bytes(b"other writer")
                raise FileExistsError("raced")

            with patch.object(MODULE.os, "link", side_effect=race), self.assertRaises(FileExistsError):
                MODULE.publish_report(str(raced), b"ours")
            self.assertEqual(raced.read_bytes(), b"other writer")
            self.assertEqual(list(Path(root).glob(".cp-sc-*")), [])

    def test_staging_write_failure_and_cleanup_warning(self):
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "out"
            real_fdopen = MODULE.os.fdopen

            class BrokenWriter:
                def __init__(self, descriptor):
                    self.file = real_fdopen(descriptor, "wb")

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    self.file.close()

                def write(self, data):
                    self.file.write(data[:1])
                    raise OSError("injected write failure")

            with patch.object(MODULE.os, "fdopen", side_effect=lambda fd, mode: BrokenWriter(fd)):
                with self.assertRaises(OSError):
                    MODULE.publish_report(str(destination), b"complete")
            self.assertFalse(destination.exists())
            self.assertEqual(list(Path(root).glob(".cp-sc-*")), [])
            with patch.object(MODULE.os, "unlink", side_effect=OSError("injected cleanup failure")):
                warnings = MODULE.publish_report(str(destination), b"complete")
            self.assertEqual(destination.read_bytes(), b"complete")
            self.assertEqual(len(warnings), 1)
            self.assertIn("report published", warnings[0])
            for staging in Path(root).glob(".cp-sc-*"):
                staging.unlink()

    def test_receipt_write_and_flush_failure_preserves_report(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "input"
            source.write_bytes(b"unchanged")
            for stage in ("write", "flush"):
                class BrokenReceipt(io.StringIO):
                    def write(self, text):
                        if stage == "write":
                            super().write(text[:9])
                            raise BrokenPipeError("injected receipt write")
                        return super().write(text)

                    def flush(self):
                        if stage == "flush":
                            raise OSError("injected receipt flush")

                sink, errors = BrokenReceipt(), io.StringIO()
                output = Path(root) / stage
                with patch.object(MODULE.sys, "stdout", sink), patch.object(MODULE.sys, "stderr", errors), \
                        patch.object(MODULE, "_silence_failed_stream"):
                    code = MODULE.main([str(source), str(source), "--out", str(output)])
                self.assertEqual(code, 1)
                self.assertTrue(output.is_file())
                self.assertTrue(sink.getvalue())
                error = json.loads(errors.getvalue())
                self.assertEqual(error["error"]["kind"], "output")
                self.assertIn("report published; receipt undelivered", error["error"]["message"])
                self.assertEqual(source.read_bytes(), b"unchanged")

    def test_cli_direct_file_optimized_and_refusal(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            source = directory / "Café-雪.txt"
            source.write_bytes("\ufeffé\r\n".encode())
            output = directory / "report.txt"
            command = [sys.executable, "-B", "-E", "-S", str(SOURCE), str(source), str(source), "--out", str(output)]
            normal = subprocess.run(command, cwd=root, capture_output=True)
            self.assertEqual(normal.returncode, 0, normal.stderr)
            self.assertEqual(normal.stderr, b"")
            self.assertTrue(normal.stdout.isascii())
            report = output.read_bytes()
            output.unlink()
            optimized = subprocess.run(command[:1] + ["-O"] + command[1:], cwd=root, capture_output=True)
            self.assertEqual(optimized.returncode, 0, optimized.stderr)
            self.assertEqual(normal.stdout, optimized.stdout)
            self.assertEqual(report, output.read_bytes())
            refusal = subprocess.run(command, cwd=root, capture_output=True)
            self.assertEqual(refusal.returncode, 1)
            self.assertEqual(refusal.stdout, b"")
            self.assertEqual(json.loads(refusal.stderr)["error"]["kind"], "output")
            self.assertEqual(report, output.read_bytes())

    def test_before_publication_failure_envelopes(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "input"
            source.write_bytes(b"\xff")
            output = Path(root) / "report"
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = MODULE.main([str(source), str(source), "--out", str(output)])
            self.assertEqual(code, 1)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(json.loads(err.getvalue())["error"]["kind"], "input")
            self.assertFalse(output.exists())
            source.write_bytes(b"valid")
            with patch.object(MODULE, "MAX_REPORT_BYTES", 10), contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(MODULE.main([str(source), str(source), "--out", str(output)]), 1)
            self.assertEqual(json.loads(err.getvalue())["error"]["kind"], "comparison")
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(root).glob(".cp-sc-*")), [])


if __name__ == "__main__":
    unittest.main()
