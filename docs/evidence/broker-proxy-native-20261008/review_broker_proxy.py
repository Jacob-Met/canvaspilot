"""Independent public-client/CLI and actual native Handler receiving for PR26.

Runs twelve product invariants; unchanged main is expected to violate seven.
Every service, proxy, profile path, person and response is a disposable fixture.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
args.source = args.source.resolve()
here = Path(__file__).resolve().parent
results = []
proxy_keys = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


@contextmanager
def environment(values):
    original = dict(os.environ)
    for key in proxy_keys:
        os.environ.pop(key, None)
    os.environ.update(values)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


def probe(name, function):
    try:
        details = function() or {}
        results.append({"name": name, "passed": True, "details": details})
    except Exception as error:
        results.append({"name": name, "passed": False, "error_type": type(error).__name__, "error": str(error)})


class LocalHTTP:
    def __init__(self, role):
        self.role, self.calls = role, []
        instance = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def answer(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length) if length else b""
                instance.calls.append({"method": self.command, "path": self.path, "body_bytes": len(body),
                                       "authorization_present": bool(self.headers.get("Authorization"))})
                value = json.dumps({"via": role, "path": self.path}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(value)))
                self.end_headers()
                self.wfile.write(value)

            do_GET = answer
            do_POST = answer

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_port)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


with tempfile.TemporaryDirectory(prefix="canvaspilot-native-receiving-") as temporary:
    temporary = Path(temporary)
    os.environ.pop("CANVAS_API_TOKEN", None)
    os.environ["CANVAS_BASE_URL"] = "https://canvas.fixture.invalid"
    os.environ["CANVAS_PROFILE"] = str(temporary / "unused-profile")
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONPATH"] = str(args.source / "src")
    journal = temporary / "native-requests.jsonl"
    native = subprocess.Popen([sys.executable, str(here / "native_broker_fixture.py"),
                               "--source", str(args.source), "--journal", str(journal)],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, env=dict(os.environ))
    startup = native.stdout.readline()
    if not startup:
        _, startup_error = native.communicate(timeout=10)
        raise RuntimeError("native fixture failed to start: " + startup_error)
    initial = json.loads(startup)
    check(initial["native_handler"] and not initial["browser_started"], "wrong receiving boundary")
    os.environ["CANVAS_SESSION_PORT"] = str(initial["port"])
    sys.path.insert(0, str(args.source / "src"))
    from canvaspilot.client import CanvasAuthError, CanvasClient, broker_fetch, broker_health

    proxy, direct = LocalHTTP("authored-proxy"), LocalHTTP("direct-fixture")
    hostile = {"HTTP_PROXY": proxy.url, "HTTPS_PROXY": proxy.url, "ALL_PROXY": proxy.url, "NO_PROXY": "[::1]"}
    ordinary_proxy = {"HTTP_PROXY": proxy.url, "HTTPS_PROXY": proxy.url, "ALL_PROXY": proxy.url, "NO_PROXY": ""}

    def cli(*arguments, extra_environment=None):
        env = dict(os.environ)
        env.update(extra_environment or {})
        return subprocess.run([sys.executable, "-m", "canvaspilot.cli", *arguments], env=env,
                              capture_output=True, text=True, timeout=15)

    def characterization():
        check(httpx.__version__ == "0.28.1", "qualification requires exact httpx 0.28.1")
        with environment(hostile):
            try:
                with httpx.Client(trust_env=True):
                    pass
            except httpx.InvalidURL as error:
                return {"exception": type(error).__name__, "message": str(error)}
        raise AssertionError("malformed NO_PROXY did not reproduce the dependency behavior")

    def native_neutral():
        with environment({}):
            health = broker_health()
            check(health and health["ready"] is True, "native healthy broker unavailable without proxy environment")
            value = broker_fetch("GET", "/api/v1/courses")
            check(value["path"] == "/api/v1/courses", "native queue reply changed")

    def native_health_hostile():
        before = len(proxy.calls)
        with environment(hostile):
            health = broker_health()
            check(health and health["ready"] is True, "native healthy broker unavailable with malformed NO_PROXY")
        check(len(proxy.calls) == before, "loopback health reached proxy")

    def native_fetch_hostile():
        before = len(proxy.calls)
        with environment(hostile):
            value = broker_fetch("GET", "/api/v1/courses?existing=yes", params=[("include[]", "a"), ("include[]", "b"), ("name", "雪 &")])
        check(value["method"] == "GET" and value["body"] is None, "native fetch method/body changed")
        check(parse_qs(urlsplit(value["path"]).query) == {"existing": ["yes"], "include[]": ["a", "b"], "name": ["雪 &"]}, "native query fields changed")
        check(len(proxy.calls) == before, "loopback fetch reached proxy")

    def cli_whoami_hostile():
        with environment(hostile):
            result = cli("whoami")
        check(result.returncode == 0, result.stderr)
        check(json.loads(result.stdout) == {
            "mode": "session_broker", "base_url": "https://canvas.fixture.invalid",
            "profile": {"id": 4242, "name": "Authored fixture person"},
        }, "public CLI did not return native authored person and session mode")

    def cli_status_hostile():
        with environment(hostile):
            result = cli("session", "status")
        check(result.returncode == 0, result.stderr)
        value = json.loads(result.stdout)
        check(value["health"]["ready"] is True and value["status"]["fixture_status"] == "ready", "public CLI status did not reach native handler")

    def ignores_proxy():
        before = len(proxy.calls)
        with environment(ordinary_proxy):
            value = broker_health()
            check(value and value.get("ready") is True, "loopback broker health was replaced by proxy response")
            check(broker_fetch("GET", "/api/v1/courses")["path"] == "/api/v1/courses", "proxy replaced fetch response")
        check(len(proxy.calls) == before, "broker HTTP request reached fixture proxy")

    def readonly_refusal():
        with environment({}):
            try:
                broker_fetch("POST", "/api/v1/courses/1", json_body={"name": "must not dispatch"})
            except CanvasAuthError as error:
                check("read-only" in str(error), "wrong native refusal")
                return {"error": "CanvasAuthError", "read_only": True}
        raise AssertionError("native read-only gate accepted a write")

    def upstream_auth_refusal():
        with environment({}):
            try:
                broker_fetch("GET", "/api/v1/auth-denied")
            except CanvasAuthError as error:
                check("401" in str(error), "upstream auth status lost")
                return {"error": "CanvasAuthError", "status": 401}
        raise AssertionError("authored upstream refusal became success")

    def unavailable_health():
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            closed_port = reservation.getsockname()[1]
        with environment(hostile):
            env = dict(os.environ)
            env["CANVAS_SESSION_PORT"] = str(closed_port)
            result = subprocess.run([sys.executable, "-c", "import json; from canvaspilot.client import broker_health; print(json.dumps(broker_health()))"],
                                    env=env, capture_output=True, text=True, timeout=10)
        check(result.returncode == 0, result.stderr)
        check(json.loads(result.stdout) is None, "closed broker reported healthy")

    def direct_canvas_proxy():
        before_proxy, before_direct = len(proxy.calls), len(direct.calls)
        with environment(ordinary_proxy):
            with CanvasClient(base_url=direct.url, token="authored-fixture-value", profile=temporary / "unused-profile") as client:
                value = client.request("GET", "/api/v1/courses")
        check(value.get("via") == "authored-proxy", "direct Canvas mode lost existing proxy support")
        check(len(proxy.calls) == before_proxy + 1 and len(direct.calls) == before_direct, "direct networking used unexpected path")
        check(proxy.calls[-1]["authorization_present"], "direct authenticated request lost authorization header")

    def native_stop_hostile():
        with environment(hostile):
            result = cli("session", "stop")
        check(result.returncode == 0, result.stderr)
        value = json.loads(result.stdout)
        check(value.get("ok") is True and value.get("fixture_shutdown") is True, result.stdout)
        check(native.wait(timeout=5) == 0, "genuine native shutdown did not stop its disposable fixture child")

    try:
        for name, function in [
            ("dependency_invalid_url_characterization", characterization),
            ("native_health_and_fetch_without_proxy", native_neutral),
            ("native_health_with_malformed_no_proxy", native_health_hostile),
            ("native_fetch_with_malformed_no_proxy", native_fetch_hostile),
            ("public_cli_whoami_with_malformed_no_proxy", cli_whoami_hostile),
            ("public_cli_status_with_malformed_no_proxy", cli_status_hostile),
            ("broker_bypasses_valid_proxy_configuration", ignores_proxy),
            ("native_read_only_refusal_preserved", readonly_refusal),
            ("upstream_auth_failure_preserved", upstream_auth_refusal),
            ("unavailable_broker_health_is_clean", unavailable_health),
            ("direct_canvas_proxy_behavior_preserved", direct_canvas_proxy),
            ("native_cli_stop_with_malformed_no_proxy", native_stop_hostile),
        ]:
            probe(name, function)
    finally:
        if native.poll() is None:
            stdout, stderr = native.communicate("finish\n", timeout=10)
        else:
            stdout, stderr = native.communicate(timeout=10)
        proxy.close()
        direct.close()
        records = [json.loads(line) for line in journal.read_text().splitlines()]
        source_hashes = {str(file.relative_to(args.source)): hashlib.sha256(file.read_bytes()).hexdigest()
                         for file in sorted((args.source / "src/canvaspilot").glob("*.py"))}
        receipt = {"schema": "canvaspilot.broker-proxy-native-receiving.v1", "source": str(args.source),
                   "python": sys.version, "platform": platform.platform(),
                   "dependencies": {name: importlib.metadata.version(name) for name in ("httpx", "httpcore", "anyio", "certifi", "pytest", "mcp", "pydantic")},
                   "source_sha256": source_hashes, "results": results,
                   "passed": sum(result["passed"] for result in results), "failed": sum(not result["passed"] for result in results),
                   "native_fixture_exit": native.returncode, "native_fixture_stderr": stderr,
                   "native_http_requests": [record for record in records if record["event"] == "http"],
                   "native_jobs": [record["job"] for record in records if record["event"] == "job"],
                   "proxy_requests": proxy.calls, "direct_requests": direct.calls,
                   "boundary": "Unchanged native Handler, public client and CLI; authored queue worker and loopback services only. No real Canvas, browser, account, provider or installed broker is used."}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps({"passed": receipt["passed"], "failed": receipt["failed"], "results": [{"name": result["name"], "passed": result["passed"], **({"error_type": result["error_type"]} if not result["passed"] else {})} for result in results]}, indent=2))

raise SystemExit(0 if all(result["passed"] for result in results) and not stderr else 1)
