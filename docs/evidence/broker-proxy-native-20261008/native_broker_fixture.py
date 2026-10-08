"""Disposable real native Handler with authored queue results, never a browser.

The genuine /shutdown route exits this isolated child process. Only this child
binds the fixture port; no existing broker or account is contacted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import queue
import sys
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True, type=Path)
parser.add_argument("--journal", required=True, type=Path)
args = parser.parse_args()
sys.path.insert(0, str(args.source / "src"))
from canvaspilot.session_broker import Handler, STATE

lock = threading.Lock()


def record(value):
    with lock, args.journal.open("a", encoding="utf-8") as output:
        output.write(json.dumps(value, ensure_ascii=False) + "\n")


class ObservedHandler(Handler):
    def do_GET(self):
        record({"event": "http", "method": "GET", "path": self.path})
        return super().do_GET()

    def do_POST(self):
        record({"event": "http", "method": "POST", "path": self.path})
        return super().do_POST()


STATE.ready.set()
STATE.error = None
STATE.read_only = True
STATE.page_url = "https://canvas.fixture.invalid/courses"
STATE.page_title = "Authored receiving fixture"
stopping = threading.Event()


def respond():
    while not stopping.is_set():
        try:
            job, reply = STATE.jobs.get(timeout=0.1)
        except queue.Empty:
            continue
        record({"event": "job", "job": job})
        operation = job.get("op")
        if operation == "status":
            reply.put({"ok": True, "fixture_status": "ready"})
        elif operation == "shutdown":
            reply.put({"ok": True, "fixture_shutdown": True})
        elif operation == "fetch":
            target = urlsplit(job.get("path") or "").path
            status = 401 if target.endswith("/auth-denied") else 200
            payload = ({"id": 4242, "name": "Authored fixture person"}
                       if target.endswith("/users/self/profile") else
                       {"method": job.get("method"), "path": job.get("path"),
                        "headers": job.get("headers"), "body": job.get("body")})
            reply.put({"ok": True, "response": {"status": status, "json": payload, "text": None}})
        else:
            reply.put({"ok": False, "error": "unexpected authored fixture operation"})


worker = threading.Thread(target=respond, daemon=True)
worker.start()
server = ThreadingHTTPServer(("127.0.0.1", 0), ObservedHandler)
server.daemon_threads = True
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
print(json.dumps({"port": server.server_port, "native_handler": True, "browser_started": False}), flush=True)
try:
    if sys.stdin.readline().strip() != "finish":
        raise RuntimeError("fixture shutdown command missing")
finally:
    server.shutdown()
    server.server_close()
    stopping.set()
    worker.join(timeout=2)
    thread.join(timeout=2)
