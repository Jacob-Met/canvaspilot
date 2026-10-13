# Independent CanvasPilot export receiver; source bundle is supplied by the reviewer.
import json, sys
with open(sys.argv[1], encoding="utf-8") as bundle:
    PAYLOAD = json.load(bundle)
for variant in PAYLOAD["variants"]:
    variant["sources"] = {**PAYLOAD.get("shared", {}), **variant["sources"]}
import contextlib, copy, errno, hashlib, io, json, logging, os, platform, stat, sys, tempfile, types
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

checks = []
events = []
def require(name, value):
    if not value:
        raise AssertionError(name)
    checks.append(name)
def gitblob(text):
    payload = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()
class Frozen(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 10, 12, 23, 0, 0, tzinfo=UTC)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)
class ReceiverClient:
    def __init__(self, **kwargs):
        self.base_url = kwargs["base_url"]
        self.fixture = {}
        self.token = None
class ReceiverAPI:
    instances = []
    def __init__(self, client):
        self.client, self.calls, self.closed = client, [], False
        self.instances.append(self)
    def list_assignments(self, course, bucket=None):
        self.calls.append(("calendar", str(course), bucket))
        return [{"id": 41, "name": "Receiver Ω, export", "due_at": "2026-10-14T12:00:00Z",
                 "html_url": "https://receiver.invalid/courses/11/assignments/41"}]
    def grade_review(self, course):
        self.calls.append(("grade", str(course)))
        return {"course": {"id": 11, "name": "Receiver Ω <course>"},
                "assignment_groups": [], "totals_visibility": "reported_fields",
                "enrollments": [], "enrollments_state": "returned",
                "authenticated_user_id": 91, "grading_periods_state": "not_returned",
                "grading_periods": None, "warnings": ["Receiver fixture only"],
                "counts": {"groups_returned": 0, "assignments_returned": 0}}
    def module_progress(self, course, module_id=None):
        self.calls.append(("module", str(course), module_id))
        return {"course_id": 11, "module_id": None, "modules_returned": 1,
                "modules_included": 1, "module_state_counts": {"started": 1},
                "modules": [{"id": 71, "name": "Receiver Ω module", "state": "started",
                             "items": [], "item_coverage": {"collection_complete": False},
                             "requirement_counts": {}, "remaining_work": {},
                             "diagnostics": ["Receiver fixture only"]}]}
    def close(self):
        self.closed = True

def load_modules(sources, revision):
    for name in list(sys.modules):
        if name == "canvaspilot" or name.startswith("canvaspilot."):
            del sys.modules[name]
    package = types.ModuleType("canvaspilot")
    package.__path__ = []
    sys.modules["canvaspilot"] = package
    client = types.ModuleType("canvaspilot.client")
    client.CanvasClient = ReceiverClient
    client.CanvasAuthError = type("CanvasAuthError", (RuntimeError,), {})
    client.CanvasPaginationError = type("CanvasPaginationError", (RuntimeError,), {})
    client.default_base_url = lambda: "https://receiver.invalid"
    client.default_profile = lambda: Path("/unused-receiver-profile")
    def reject_broker():
        raise AssertionError("receiver must not consult a live broker")
    client.broker_health = reject_broker
    sys.modules[client.__name__] = client
    api = types.ModuleType("canvaspilot.api")
    api.CanvasAPI = ReceiverAPI
    sys.modules[api.__name__] = api
    httpx = types.ModuleType("httpx")
    httpx.HTTPError = type("HTTPError", (Exception,), {})
    sys.modules["httpx"] = httpx
    modules = {}
    for short in ("calendar_export", "grade_review_export", "module_progress_export", "cli"):
        item = sources[short]
        require(revision + ":" + short + ":exact-blob", gitblob(item["content"]) == item["sha"])
        name = "canvaspilot." + short
        mod = types.ModuleType(name)
        mod.__file__ = revision + "/src/canvaspilot/" + short + ".py"
        sys.modules[name] = mod
        exec(compile(item["content"], mod.__file__, "exec"), mod.__dict__)
        if hasattr(mod, "datetime"):
            mod.datetime = Frozen
        modules[short] = mod
    return modules

def exercise(modules, label, repaired, root):
    writer = modules["calendar_export"].write_calendar
    cli = modules["cli"].main
    content = "BEGIN:VCALENDAR\r\nSUMMARY:Receiver Ω export\r\nEND:VCALENDAR\r\n".encode()
    original_link, original_unlink = os.link, Path.unlink
    def new(name):
        directory = root / (label + "-" + name)
        directory.mkdir()
        return directory, directory / "out.ics"
    def invoke_write(path, data=content):
        try:
            return writer(path, data), None
        except BaseException as exc:
            return None, exc
    def tempnames(directory, path):
        return [entry for entry in directory.iterdir() if entry != path and entry.name.startswith(".") and entry.suffix == ".tmp"]
    def cleanup_fault(directory, marker):
        def fail(path, *args, **kwargs):
            if path.parent == directory and path.name.endswith(".tmp"):
                raise marker
            return original_unlink(path, *args, **kwargs)
        return fail

    directory, path = new("normal")
    warning, error = invoke_write(path)
    require(label + ":normal-return", error is None and warning is None)
    require(label + ":normal-complete-bytes", path.read_bytes() == content)
    require(label + ":normal-no-alias", not tempnames(directory, path))
    require(label + ":normal-private-permission", stat.S_IMODE(path.stat().st_mode) == 0o600)

    directory, path = new("empty")
    warning, error = invoke_write(path, b"")
    require(label + ":empty-complete", error is None and warning is None and path.read_bytes() == b"")

    for kind in ("file", "symlink", "dangling", "directory"):
        directory, path = new("existing-" + kind)
        sentinel = b"independent existing output\n"
        target = directory / "target"
        if kind == "file":
            path.write_bytes(sentinel)
        elif kind == "symlink":
            target.write_bytes(sentinel)
            path.symlink_to(target)
        elif kind == "dangling":
            path.symlink_to(target)
        else:
            path.mkdir()
            (path / "sentinel").write_bytes(sentinel)
        identity = path.lstat().st_ino
        warning, error = invoke_write(path)
        require(label + ":" + kind + ":refused", isinstance(error, FileExistsError))
        require(label + ":" + kind + ":same-entry", path.lstat().st_ino == identity)
        require(label + ":" + kind + ":no-alias", not tempnames(directory, path))
        if kind in ("file", "symlink"):
            require(label + ":" + kind + ":same-bytes", path.read_bytes() == sentinel)
        elif kind == "dangling":
            require(label + ":" + kind + ":target-absent", not target.exists() and path.is_symlink())
        else:
            require(label + ":" + kind + ":child-preserved", (path / "sentinel").read_bytes() == sentinel)

    directory, path = new("cleanup-only")
    cleanup = PermissionError(errno.EACCES, "receiver temporary cleanup denied")
    with patch.object(Path, "unlink", cleanup_fault(directory, cleanup)):
        warning, error = invoke_write(path)
    aliases = tempnames(directory, path)
    require(label + ":cleanup-complete-output", path.read_bytes() == content)
    require(label + ":cleanup-retained-alias", len(aliases) == 1 and aliases[0].read_bytes() == content)
    if repaired:
        require(label + ":cleanup-successful-return", error is None)
        require(label + ":cleanup-warning", isinstance(warning, str) and bool(warning))
        require(label + ":cleanup-warning-identifies-alias", aliases[0].name in warning)
    else:
        require(label + ":before-reproduces-false-failure", error is cleanup)
    events.append({"case": label + ":cleanup-only", "published": True,
                   "raised": type(error).__name__ if error else None, "warning": bool(warning)})

    for stage in ("link", "fsync", "write", "cancel"):
        directory, path = new("primary-" + stage)
        cleanup = PermissionError(errno.EACCES, "receiver secondary cleanup denied")
        primary = KeyboardInterrupt("receiver primary cancellation") if stage == "cancel" else OSError(errno.ENOSPC, "receiver primary " + stage + " denied")
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(Path, "unlink", cleanup_fault(directory, cleanup)))
            if stage in ("link", "cancel"):
                stack.enter_context(patch.object(os, "link", side_effect=primary))
            elif stage == "fsync":
                stack.enter_context(patch.object(os, "fsync", side_effect=primary))
            warning, error = invoke_write(path, object() if stage == "write" else content)
        require(label + ":" + stage + ":no-output", not os.path.lexists(path))
        require(label + ":" + stage + ":retained-alias", len(tempnames(directory, path)) == 1)
        if repaired:
            require(label + ":" + stage + ":primary-preserved",
                    isinstance(error, TypeError) if stage == "write" else error is primary)
        else:
            require(label + ":" + stage + ":before-masks-primary", error is cleanup)
        events.append({"case": label + ":primary-" + stage,
                       "raised": type(error).__name__ if error else None, "published": False})

    for failure_mode in ("close-primary", "write-before-close"):
        directory, path = new(failure_mode)
        cleanup = PermissionError(errno.EACCES, "receiver unlink secondary")
        primary = OSError(errno.ENOSPC, "receiver primary " + failure_mode)
        secondary_close = OSError(errno.EIO, "receiver close secondary")
        original_temporary = tempfile.NamedTemporaryFile
        close_calls = []
        class HandleBoundary:
            def __init__(self, handle):
                self.inner, self.name = handle, handle.name
            def write(self, data):
                if failure_mode == "write-before-close":
                    raise primary
                return self.inner.write(data)
            def flush(self):
                return self.inner.flush()
            def fileno(self):
                return self.inner.fileno()
            def close(self):
                close_calls.append(True)
                self.inner.close()
                raise primary if failure_mode == "close-primary" else secondary_close
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.close()
        def wrapped_temporary(*args, **kwargs):
            return HandleBoundary(original_temporary(*args, **kwargs))
        with patch.object(tempfile, "NamedTemporaryFile", wrapped_temporary), patch.object(Path, "unlink", cleanup_fault(directory, cleanup)):
            warning, error = invoke_write(path)
        require(label + ":" + failure_mode + ":no-output", not os.path.lexists(path))
        require(label + ":" + failure_mode + ":real-close-attempted", bool(close_calls))
        require(label + ":" + failure_mode + ":correct-primary", error is (primary if repaired else cleanup))
        events.append({"case": label + ":" + failure_mode,
                       "raised": type(error).__name__ if error else None,
                       "original_primary_preserved": error is primary})

    directory, path = new("allocation-failure")
    primary = PermissionError(errno.EACCES, "receiver allocation denied")
    with patch.object(tempfile, "NamedTemporaryFile", side_effect=primary):
        warning, error = invoke_write(path)
    require(label + ":allocation-original-error", error is primary)
    require(label + ":allocation-no-output", not list(directory.iterdir()))

    directory, path = new("alias-already-removed")
    def link_then_remove(source, destination):
        original_link(source, destination)
        original_unlink(Path(source))
    with patch.object(os, "link", link_then_remove):
        warning, error = invoke_write(path)
    require(label + ":removed-alias-complete", path.read_bytes() == content)
    require(label + ":removed-alias-absent", not tempnames(directory, path))
    if repaired:
        require(label + ":removed-alias-no-false-failure", error is None)
    else:
        require(label + ":before-missing-alias-false-failure", isinstance(error, FileNotFoundError))

    normal_bytes = {}
    commands = (("export-calendar", "output", "calendar"),
                ("export-grade-review", "path", "grade"),
                ("export-module-progress", "output", "module"))
    for command, pathkey, apimethod in commands:
        for scenario in ("normal", "cleanup", "link-failure", "existing", "dangling", "race", "race-cleanup"):
            directory, path = new(command + "-" + scenario)
            if command != "export-calendar":
                path = path.with_suffix(".html")
            sentinel = b"independent competitor output\n"
            target = directory / "missing-target"
            if scenario == "existing":
                path.write_bytes(sentinel)
            elif scenario == "dangling":
                path.symlink_to(target)
            cleanup = PermissionError(errno.EACCES, "receiver CLI cleanup denied")
            def competitor(source, destination):
                Path(destination).write_bytes(sentinel)
                return original_link(source, destination)
            stdout, stderr = io.StringIO(), io.StringIO()
            logger = logging.getLogger("httpx")
            old_level = logger.level
            logger.setLevel(logging.INFO)
            before = len(ReceiverAPI.instances)
            code = 0
            try:
                with contextlib.ExitStack() as stack:
                    stack.enter_context(contextlib.redirect_stdout(stdout))
                    stack.enter_context(contextlib.redirect_stderr(stderr))
                    if scenario in ("cleanup", "race-cleanup"):
                        stack.enter_context(patch.object(Path, "unlink", cleanup_fault(directory, cleanup)))
                    if scenario == "link-failure":
                        stack.enter_context(patch.object(os, "link", side_effect=PermissionError(errno.EACCES, "receiver CLI publication denied")))
                    elif scenario in ("race", "race-cleanup"):
                        stack.enter_context(patch.object(os, "link", competitor))
                    try:
                        cli([command, "11", "--out", str(path), "--base-url", "https://receiver.invalid"])
                    except SystemExit as exc:
                        code = exc.code
                require(label + ":" + command + ":" + scenario + ":logger-restored", logger.level == logging.INFO)
            finally:
                logger.setLevel(old_level)
            require(label + ":" + command + ":" + scenario + ":one-client", len(ReceiverAPI.instances) == before + 1)
            api = ReceiverAPI.instances[-1]
            require(label + ":" + command + ":" + scenario + ":closed", api.closed)
            require(label + ":" + command + ":" + scenario + ":reads",
                    len(api.calls) == (0 if scenario in ("existing", "dangling") else 1))
            if api.calls:
                require(label + ":" + command + ":" + scenario + ":correct-reader", api.calls[0][0] == apimethod)
            success = scenario == "normal" or (scenario == "cleanup" and repaired)
            if success:
                require(label + ":" + command + ":" + scenario + ":exit-success", code == 0)
                require(label + ":" + command + ":" + scenario + ":stderr-empty", stderr.getvalue() == "")
                report = json.loads(stdout.getvalue())
                require(label + ":" + command + ":" + scenario + ":ok", report["ok"] is True)
                require(label + ":" + command + ":" + scenario + ":existing-path-key", report[pathkey] == str(path))
                payload = path.read_bytes()
                require(label + ":" + command + ":" + scenario + ":digest", report["sha256"] == hashlib.sha256(payload).hexdigest())
                if command == "export-calendar":
                    require(label + ":" + command + ":" + scenario + ":calendar-bytes", payload.startswith(b"BEGIN:VCALENDAR\r\n") and payload.endswith(b"END:VCALENDAR\r\n"))
                    require(label + ":" + command + ":" + scenario + ":calendar-count", report["events_exported"] == 1)
                else:
                    require(label + ":" + command + ":" + scenario + ":html-bytes", payload.startswith(b"<!doctype html>") and report["html_bytes"] == len(payload))
                    require(label + ":" + command + ":" + scenario + ":json-digest-present", len(report["json_sha256"]) == 64)
                if scenario == "normal":
                    require(label + ":" + command + ":normal-no-warning", "cleanup_warning" not in report)
                    require(label + ":" + command + ":normal-alias-cleaned", not tempnames(directory, path))
                    normal_bytes[command] = payload
                else:
                    require(label + ":" + command + ":warning-exposed", bool(report.get("cleanup_warning")))
                    require(label + ":" + command + ":warning-byte-equality", payload == normal_bytes[command])
                    aliases = tempnames(directory, path)
                    require(label + ":" + command + ":warning-alias", len(aliases) == 1 and aliases[0].read_bytes() == payload)
            else:
                require(label + ":" + command + ":" + scenario + ":exit-failure", code == 1)
                require(label + ":" + command + ":" + scenario + ":stdout-empty", stdout.getvalue() == "")
                report = json.loads(stderr.getvalue())
                require(label + ":" + command + ":" + scenario + ":ok-false", report["ok"] is False)
                expected_error = "FileExistsError" if scenario in ("existing", "dangling", "race") or (scenario == "race-cleanup" and repaired) else "PermissionError"
                require(label + ":" + command + ":" + scenario + ":original-error-type", report["error"] == expected_error)
                if scenario in ("existing", "race", "race-cleanup"):
                    require(label + ":" + command + ":" + scenario + ":competitor-preserved", path.read_bytes() == sentinel)
                elif scenario == "dangling":
                    require(label + ":" + command + ":" + scenario + ":symlink-preserved", path.is_symlink() and not target.exists())
                elif scenario == "cleanup":
                    require(label + ":" + command + ":before-cli-false-failure-has-output", path.read_bytes() == normal_bytes[command])
                else:
                    require(label + ":" + command + ":" + scenario + ":no-output", not os.path.lexists(path))
            events.append({"case": label + ":" + command + ":" + scenario,
                           "exit": code, "ok": report["ok"], "output_entry_exists": os.path.lexists(path),
                           "export_published": scenario in ("normal", "cleanup"),
                           "warning": bool(report.get("cleanup_warning"))})
    return normal_bytes

with tempfile.TemporaryDirectory(prefix="canvaspilot-consumer-receiver-") as directory:
    snapshots = []
    for variant in PAYLOAD["variants"]:
        modules = load_modules(variant["sources"], variant["revision"])
        snapshots.append(exercise(modules, variant["label"], variant["repaired"], Path(directory)))
    if len(snapshots) == 2:
        for command in snapshots[0]:
            require("before-after:" + command + ":normal-bytes-identical", snapshots[0][command] == snapshots[1][command])
print(json.dumps({"receiver": "independent_canvaspilot_export_cleanup_v1", "checks_passed": len(checks),
                  "revisions": [v["revision"] for v in PAYLOAD["variants"]],
                  "environment": {"host": platform.node(), "uid": os.getuid(),
                                  "python": sys.version.split()[0], "platform": platform.platform()},
                  "events": events,
                  "scope": "Exact helper, CLI and real renderers; transport fixture only; no live Canvas or installed app mutation"},
                 indent=2))
