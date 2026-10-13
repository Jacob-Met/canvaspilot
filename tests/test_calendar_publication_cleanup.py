"""Publication and cleanup regressions using real temporary files, without a provider."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canvaspilot import calendar_export


class _FaultedFile:
    """Keep real disk writes and descriptors while injecting one operation failure."""

    def __init__(self, handle, *, write_error=None, close_error=None):
        self.handle = handle
        self.name = handle.name
        self.write_error = write_error
        self.close_error = close_error

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def write(self, content):
        if self.write_error is not None:
            raise self.write_error
        return self.handle.write(content)

    def flush(self):
        return self.handle.flush()

    def fileno(self):
        return self.handle.fileno()

    def close(self):
        self.handle.close()
        if self.close_error is not None:
            raise self.close_error


class CalendarPublicationCleanupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.output = self.root / "report.ics"
        self.content = b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
        self.original_unlink = Path.unlink
        self.original_temporary_file = tempfile.NamedTemporaryFile

    def deny_staging_cleanup(self, path, *args, **kwargs):
        if path.parent == self.root and path.name.startswith(".report.ics."):
            raise PermissionError("synthetic staging cleanup denial")
        return self.original_unlink(path, *args, **kwargs)

    def assert_only_staging_remains(self):
        entries = list(self.root.iterdir())
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0].name.startswith(".report.ics."))
        self.assertTrue(entries[0].name.endswith(".tmp"))

    def test_success_returns_no_warning_and_cleans_staging(self):
        self.assertIsNone(calendar_export.write_calendar(self.output, self.content))
        self.assertEqual(self.output.read_bytes(), self.content)
        self.assertEqual(list(self.root.iterdir()), [self.output])

    def test_existing_file_and_dangling_symlink_are_preserved(self):
        self.output.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            calendar_export.write_calendar(self.output, self.content)
        self.assertEqual(self.output.read_bytes(), b"existing")
        self.output.unlink()
        absent = self.root / "absent.ics"
        self.output.symlink_to(absent)
        with self.assertRaises(FileExistsError):
            calendar_export.write_calendar(self.output, self.content)
        self.assertTrue(self.output.is_symlink())
        self.assertFalse(absent.exists())
        self.assertEqual(list(self.root.iterdir()), [self.output])

    def test_successful_publication_with_cleanup_failure_returns_warning(self):
        with patch.object(Path, "unlink", autospec=True, side_effect=self.deny_staging_cleanup):
            warning = calendar_export.write_calendar(self.output, self.content)
        self.assertIsInstance(warning, str)
        self.assertTrue(warning)
        self.assertEqual(self.output.read_bytes(), self.content)
        staged = [path for path in self.root.iterdir() if path != self.output]
        self.assertEqual(len(staged), 1)
        self.assertIn(staged[0].name, warning)
        self.assertEqual(staged[0].read_bytes(), self.content)

    def test_link_failure_remains_primary_when_staging_cleanup_also_fails(self):
        primary = PermissionError("synthetic link denial")
        with patch.object(calendar_export.os, "link", side_effect=primary), \
                patch.object(Path, "unlink", autospec=True, side_effect=self.deny_staging_cleanup):
            with self.assertRaises(PermissionError) as result:
                calendar_export.write_calendar(self.output, self.content)
        self.assertIs(result.exception, primary)
        self.assertFalse(self.output.exists())
        self.assert_only_staging_remains()

    def test_fsync_failure_prevents_publication_and_cleans_staging(self):
        primary = OSError("synthetic fsync failure")
        with patch.object(calendar_export.os, "fsync", side_effect=primary), \
                patch.object(calendar_export.os, "link") as publish:
            with self.assertRaises(OSError) as result:
                calendar_export.write_calendar(self.output, self.content)
        self.assertIs(result.exception, primary)
        publish.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_close_failure_remains_primary_and_prevents_publication(self):
        primary = OSError("synthetic close failure")

        def factory(*args, **kwargs):
            return _FaultedFile(self.original_temporary_file(*args, **kwargs), close_error=primary)

        with patch.object(tempfile, "NamedTemporaryFile", side_effect=factory), \
                patch.object(Path, "unlink", autospec=True, side_effect=self.deny_staging_cleanup), \
                patch.object(calendar_export.os, "link") as publish:
            with self.assertRaises(OSError) as result:
                calendar_export.write_calendar(self.output, self.content)
        self.assertIs(result.exception, primary)
        publish.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assert_only_staging_remains()

    def test_write_failure_or_interruption_survives_failed_close_and_unlink(self):
        for primary in (OSError("synthetic write failure"), KeyboardInterrupt("synthetic cancellation")):
            with self.subTest(error=type(primary).__name__):
                def factory(*args, **kwargs):
                    return _FaultedFile(
                        self.original_temporary_file(*args, **kwargs),
                        write_error=primary, close_error=OSError("secondary close failure"),
                    )

                with patch.object(tempfile, "NamedTemporaryFile", side_effect=factory), \
                        patch.object(Path, "unlink", autospec=True, side_effect=self.deny_staging_cleanup), \
                        patch.object(calendar_export.os, "link") as publish:
                    with self.assertRaises(type(primary)) as result:
                        calendar_export.write_calendar(self.output, self.content)
                self.assertIs(result.exception, primary)
                publish.assert_not_called()
                self.assertFalse(self.output.exists())
                self.assert_only_staging_remains()
                for path in self.root.iterdir():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
