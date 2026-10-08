"""Execute exact planner CLI source over unchanged native API/client fixtures.

The namespace bootstrap and import/exception-only HTTPX adapter are explicit.
This receives CLI dispatch, output, cleanup and error propagation, not installed
entry points, real HTTPX pagination, MCP bootstrap or live Canvas authentication.
The full product CLI source is compiled unchanged in each actual child.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

CHILD = r'''
import json, logging, os, sys, types
from pathlib import Path
payload = json.loads(sys.argv[1])
receipt_fd = int(sys.argv[2])
source = Path(payload["native_source"])
package = types.ModuleType("canvaspilot")
package.__path__ = [str(source / "src/canvaspilot")]
sys.modules["canvaspilot"] = package
effects = []
httpx = types.ModuleType("httpx")
class HTTPError(Exception):
    pass
httpx.HTTPError = HTTPError
def forbidden_httpx(name):
    effects.append("HTTPX behavior: " + name)
    raise AssertionError("Real HTTPX is outside this fixture receiver: " + name)
httpx.__getattr__ = forbidden_httpx
sys.modules["httpx"] = httpx
def guard(event, args):
    if event.startswith("socket.") or event in ("subprocess.Popen", "os.system"):
        effects.append(event)
        raise AssertionError("Forbidden external effect: " + event)
    if event == "import" and str(args[0]).split(".")[0] in (
        "mcp", "playwright", "selenium", "tkinter", "cv2", "matplotlib",
    ):
        effects.append("import " + str(args[0]))
        raise AssertionError("Forbidden runtime import: " + str(args[0]))
    if event == "open":
        mode, flags = args[1:3]
        if (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        ):
            effects.append("file write")
            raise AssertionError("Forbidden product file write")
sys.addaudithook(guard)
from canvaspilot import client as client_module
if payload.get("api_source") is not None:
    api_module = types.ModuleType("canvaspilot.api")
    api_module.__file__ = payload["api_label"]
    api_module.__package__ = "canvaspilot"
    sys.modules["canvaspilot.api"] = api_module
    exec(compile(payload["api_source"], payload["api_label"], "exec"), api_module.__dict__)
from canvaspilot.api import CanvasAPI
NativeClient = client_module.CanvasClient
constructed, calls, attempts, closed = [], [], [], []
http_log = logging.getLogger("httpx")
http_log.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("synthetic-httpx-info: %(message)s"))
http_log.addHandler(handler)
error_types = {
    "auth": client_module.CanvasAuthError,
    "pagination": client_module.CanvasPaginationError,
    "http": HTTPError,
    "value": ValueError,
}
class RecordedClient(NativeClient):
    def get_paginated(self, path, **kwargs):
        attempts.append({"path": path, **kwargs})
        http_log.info("fixture planner read")
        fault = payload.get("fault")
        if fault in error_types:
            raise error_types[fault]("Synthetic " + fault + " refusal after native read admission")
        return super().get_paginated(path, **kwargs)
    def request(self, method, path, **kwargs):
        calls.append({"method": method, "path": path, **kwargs})
        if method != "GET":
            effects.append("non-GET fixture")
            raise AssertionError("Read-only fixture admits GET only")
        return super().request(method, path, **kwargs)
    def close(self):
        closed.append(True)
        return super().close()
def factory(**kwargs):
    constructed.append({key: str(value) if isinstance(value, Path) else value
                        for key, value in kwargs.items()})
    return RecordedClient(**kwargs, fixture={
        "routes": {
            "GET /api/v1/planner/items": payload["rows"],
            "GET /api/v1/users/self/profile": {"id": 123, "name": "Synthetic planner reader"},
        },
    })
client_module.CanvasClient = factory
sys.argv = [payload["cli_label"], *payload["arguments"]]
status = 0
try:
    exec(compile(payload["cli_source"], payload["cli_label"], "exec"),
         {"__name__": "__main__", "__file__": payload["cli_label"]})
except SystemExit as error:
    status = error.code
finally:
    metadata = {
        "constructed": constructed, "calls": calls, "attempts": attempts,
        "closed": len(closed), "httpx_logger_after": http_log.level, "effects": effects,
        "api_class": CanvasAPI.__module__ + "." + CanvasAPI.__name__,
        "native_api_file": sys.modules["canvaspilot.api"].__file__,
        "native_client_file": client_module.__file__,
        "bootstrap": "namespace package and import/exception-only HTTPX adapter",
    }
    raw = json.dumps(metadata, ensure_ascii=True, allow_nan=False).encode("utf-8")
    if len(raw) > 16000:
        raise AssertionError("Fixture metadata exceeds bounded pipe receipt")
    os.write(receipt_fd, raw)
    os.close(receipt_fd)
raise SystemExit(status)
'''

def pin(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-source", required=True, type=Path)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--cli", type=Path)
    source_group.add_argument("--cli-source")
    api_group = parser.add_mutually_exclusive_group()
    api_group.add_argument("--api", type=Path)
    api_group.add_argument("--api-source")
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--only-case", help="Run one named receiving family")
    args = parser.parse_args()
    source = args.native_source.resolve()
    cli_bytes = args.cli.read_bytes() if args.cli else args.cli_source.encode("utf-8")
    cli_source = cli_bytes.decode("utf-8")
    label = str(args.cli.resolve()) if args.cli else "<exact-candidate-cli-source>"
    api_bytes = args.api.read_bytes() if args.api else (args.api_source.encode("utf-8") if args.api_source is not None else None)
    api_source = api_bytes.decode("utf-8") if api_bytes is not None else None
    api_label = str(args.api.resolve()) if args.api else "<exact-current-native-api-source>"
    fixture_bytes = args.fixture.read_bytes()
    fixture = json.loads(fixture_bytes)
    support_paths = [
        "src/canvaspilot/api.py", "src/canvaspilot/client.py",
        "src/canvaspilot/assignment_submission.py", "src/canvaspilot/feedback.py",
        "src/canvaspilot/__init__.py", "src/canvaspilot/bundle.py",
    ]
    before = {p: pin((source / p).read_bytes()) for p in support_paths}
    common = ["--base-url", "https://canvas.synthetic.example", "--token", "synthetic-fixture-token",
              "--profile", str(source / "unused-planner-profile")]
    cases = [
        ("dated", ["planner", "--start-date", fixture["start"], "--end-date", fixture["end"]],
         fixture["rows"], None, fixture["rows"]),
        ("empty-defaults", ["planner"], [], None, []),
        ("native-terminal-object", ["planner"], {"future_shape": [0, False, None]},
         None, [{"future_shape": [0, False, None]}]),
        *[(fault, ["planner"], fixture["rows"], fault, None)
          for fault in ("auth", "pagination", "http", "value")],
        ("missing-date", ["planner", "--start-date"], fixture["rows"], None, None),
        ("unchanged-whoami", ["whoami"], fixture["rows"], None,
         {"mode": "fixture", "base_url": "https://canvas.synthetic.example",
          "profile": {"id": 123, "name": "Synthetic planner reader"}}),
    ]
    if args.only_case:
        cases = [case for case in cases if case[0] == args.only_case]
        if not cases:
            parser.error("unknown receiving case")
    conditions = []
    observations = {}
    def check(name, passed):
        conditions.append({"name": name, "pass": bool(passed)})
    for name, arguments, rows, fault, expected in cases:
        payload = {
            "native_source": str(source), "cli_source": cli_source, "cli_label": label,
            "arguments": arguments + common, "rows": rows, "fault": fault,
            "api_source": api_source, "api_label": api_label,
        }
        read_fd, write_fd = os.pipe()
        try:
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-S", "-c", CHILD,
                 json.dumps(payload, ensure_ascii=True), str(write_fd)],
                pass_fds=(write_fd,), cwd=source,
                env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1",
                     "PYTHONHASHSEED": "0", "LANG": "C.UTF-8"},
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
            )
        finally:
            os.close(write_fd)
        with os.fdopen(read_fd, "rb") as stream:
            metadata_bytes = stream.read(16001)
        metadata = json.loads(metadata_bytes)
        observations[name] = {
            "returncode": result.returncode, "arguments": arguments + common,
            "stdout": result.stdout.decode("utf-8"), "stdout_pin": pin(result.stdout),
            "stderr": result.stderr.decode("utf-8"), "stderr_pin": pin(result.stderr),
            "metadata": metadata, "metadata_pin": pin(metadata_bytes),
        }
        check(name + ": no forbidden effects", metadata["effects"] == [])
        check(name + ": caller logger restored", metadata["httpx_logger_after"] == 10)
        if name == "missing-date":
            check(name + ": native parser refusal", result.returncode == 2 and
                  result.stdout == b"" and b"expected one argument" in result.stderr)
            check(name + ": no client, read or close", metadata["constructed"] == [] and
                  metadata["calls"] == [] and metadata["attempts"] == [] and metadata["closed"] == 0)
            continue
        check(name + ": common client inputs retained", metadata["constructed"] == [{
            "base_url": common[1], "token": common[3], "profile": common[5],
        }])
        check(name + ": native client closed once", metadata["closed"] == 1)
        if fault:
            expected_error = {"auth": "CanvasAuthError", "pagination": "CanvasPaginationError",
                              "http": "HTTPError", "value": "ValueError"}[fault]
            error = json.loads(result.stderr) if result.stderr else {}
            check(name + ": complete error document and no partial list",
                  result.returncode == 1 and result.stdout == b"" and
                  error.get("ok") is False and error.get("error") == expected_error and
                  isinstance(error.get("message"), str))
            check(name + ": one native collection admission", len(metadata["attempts"]) == 1 and
                  metadata["calls"] == [])
        else:
            value = json.loads(result.stdout) if result.stdout else None
            check(name + ": complete native result", result.returncode == 0 and value == expected)
            check(name + ": clean error stream", result.stderr == b"")
            route = "/api/v1/users/self/profile" if name == "unchanged-whoami" else "/api/v1/planner/items"
            params = {"start_date": fixture["start"], "end_date": fixture["end"]} if name == "dated" else {}
            expected_call = {"method": "GET", "path": route}
            if name != "unchanged-whoami":
                expected_call["params"] = params
            check(name + ": native read and raw date values", metadata["calls"] == [expected_call])
    after = {p: pin((source / p).read_bytes()) for p in support_paths}
    check("all native source/support files unchanged", before == after)
    check("retained baseline fixture bytes unchanged", args.fixture.read_bytes() == fixture_bytes)
    check("no native profile directory created", not (source / "unused-planner-profile").exists())
    receipt = {
        "format": "canvas-planner-cli-native-fixture-receiving-v1",
        "python": sys.version, "cli_source": pin(cli_bytes), "native_support": before,
        "compiled_api_source": pin(api_bytes) if api_bytes is not None else None,
        "retained_fixture": pin(fixture_bytes), "actual_cli_children": len(cases),
        "conditions": conditions, "passed": sum(c["pass"] for c in conditions),
        "failed": sum(not c["pass"] for c in conditions), "observations": observations,
        "limits": [
            "Full exact CLI source is compiled in each actual Python -I -B -S child; actual_cli_children reports the selected count.",
            "When compiled_api_source is present, that full exact API source is compiled before CLI execution; native_support records the retained on-disk files and unchanged client/helpers. Otherwise the API is imported from those files.",
            "Package __init__/bundle/MCP and installed entry points are not executed.",
            "HTTPX is only an import/exception adapter with every other attribute forbidden.",
            "Error propagation uses explicit native exception injection; real HTTP, token/session transport and Link pagination are separate tests.",
            "No network, GUI, provider, file mutation or live Canvas effect was admitted.",
        ],
    }
    print(json.dumps(receipt, ensure_ascii=True, indent=2))
    return bool(receipt["failed"])

if __name__ == "__main__":
    raise SystemExit(main())
