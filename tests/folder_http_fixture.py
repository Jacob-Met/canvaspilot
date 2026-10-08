"""Authored course metadata over disposable loopback HTTP; never real Canvas."""

from __future__ import annotations

import copy
import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


def folder(identity, parent, name, *, course=42, folders=0, files=0):
    return {
        "id": identity, "context_type": "Course", "context_id": course,
        "parent_folder_id": parent, "name": name, "full_name": "course files/" + name,
        "folders_count": folders, "files_count": files, "locked_for_user": False,
        "folders_url": "https://must-not-follow.invalid/folders",
        "files_url": "https://must-not-follow.invalid/files",
    }


def file(identity, parent, name):
    return {
        "id": identity, "folder_id": parent, "display_name": name, "filename": name,
        "size": 123, "content-type": "application/pdf", "hidden_for_user": False,
        "url": "https://must-not-download.invalid/file?verifier=authored-fixture",
        "preview_url": "https://must-not-preview.invalid/file",
        "body": "This authored body must never be returned as file metadata.",
    }


class FolderHTTPFixture:
    def __init__(self):
        self.requests = []
        self.overrides = {}
        self.folders = {
            100: folder(100, None, "course files", folders=3, files=1),
            110: folder(110, 100, "Unit 1 — 雪", folders=1, files=3),
            111: folder(111, 110, "Lab <notes>", files=1),
            120: folder(120, 100, "Empty"),
            130: folder(130, 100, "Restricted"),
        }
        self.child_folders = {100: [110, 120, 130], 110: [111]}
        self.files = {
            100: [file(1001, 100, "Syllabus.pdf")],
            110: [file(2001, 110, "A.pdf"), file(2002, 110, "B 雪.pdf"), file(2003, 110, "C.pdf")],
            111: [file(3001, 111, "Lab <notes>.pdf")],
        }
        instance = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_arguments):
                pass

            def do_GET(self):
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)
                instance.requests.append({"method": "GET", "path": parsed.path, "query": query})
                status, body = instance.route(parsed.path, query)
                encoded = json.dumps(body, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                # Deliberately opaque: the product must not invent Link availability.
                self.send_header("Link", '<https://must-not-follow.invalid/opaque>; rel="next"')
                self.end_headers()
                self.wfile.write(encoded)

            def do_POST(self):
                instance.requests.append({"method": "POST", "path": self.path})
                self.send_error(405)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True,
        )
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_port)

    def route(self, path, query):
        if path in self.overrides:
            return copy.deepcopy(self.overrides[path])
        parts = path.strip("/").split("/")
        if len(parts) == 6 and parts[:4] == ["api", "v1", "courses", "42"] and parts[4] == "folders":
            selected = parts[5]
            if selected == "900":
                return 403, {"error": "authored foreign-course refusal"}
            if selected == "901":
                return 200, folder(901, None, "Foreign private name", course=77)
            if selected == "902":
                return 200, self.folders[110]
            identity = 100 if selected == "root" else int(selected)
            if identity not in self.folders:
                return 404, {"error": "authored missing folder"}
            return 200, self.folders[identity]
        if len(parts) == 5 and parts[:3] == ["api", "v1", "folders"]:
            identity = int(parts[3])
            kind = parts[4]
            if identity == 130 and kind == "files":
                return 403, {"error": "authored files permission refusal"}
            if kind == "folders":
                values = [self.folders[item] for item in self.child_folders.get(identity, [])]
            elif kind == "files":
                values = self.files.get(identity, [])
            else:
                return 404, {"error": "unexpected authored fixture route"}
            page, limit = int(query.get("page", ["1"])[0]), int(query.get("per_page", ["50"])[0])
            return 200, values[(page - 1) * limit:page * limit]
        return 404, {"error": "unexpected authored fixture route"}

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


class FolderBrokerFixture:
    """Actual broker Handler with authored GET results at its browser queue seam."""

    def __init__(self, metadata):
        from canvaspilot.session_broker import STATE, Handler

        self.state = STATE
        self.saved = {
            name: getattr(STATE, name) for name in (
                "base_url", "profile", "headless", "read_only", "jobs", "page_url",
                "page_title", "error",
            )
        }
        self.was_ready = STATE.ready.is_set()
        STATE.base_url = "https://canvas.fixture.invalid"
        STATE.page_url = "https://canvas.fixture.invalid/courses"
        STATE.page_title = "Authored folder receiving"
        STATE.headless = False
        STATE.read_only = True
        STATE.error = None
        STATE.jobs = queue.Queue()
        STATE.ready.set()
        self.jobs = []
        self.stopping = threading.Event()

        def respond():
            while not self.stopping.is_set():
                try:
                    job, reply = STATE.jobs.get(timeout=0.05)
                except queue.Empty:
                    continue
                self.jobs.append(copy.deepcopy(job))
                if job.get("op") != "fetch" or job.get("method") != "GET":
                    reply.put({"ok": False, "error": "unexpected fixture operation"})
                    continue
                parsed = urlsplit(job["path"])
                status, body = metadata.route(parsed.path, parse_qs(parsed.query))
                reply.put({"ok": True, "response": {"status": status, "json": body, "text": None}})

        self.worker = threading.Thread(target=respond, daemon=True)
        self.worker.start()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True,
        )
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.stopping.set()
        self.worker.join(timeout=3)
        self.thread.join(timeout=3)
        for name, value in self.saved.items():
            setattr(self.state, name, value)
        if not self.was_ready:
            self.state.ready.clear()
