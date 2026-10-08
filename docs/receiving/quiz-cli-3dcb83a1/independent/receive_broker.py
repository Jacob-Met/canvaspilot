"""Independent current-source quiz CLI receiving through the real HTTP broker client."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ORIGIN = "https://canvas-receiving.invalid"
COURSE = "2189"
FIRST = "/api/v1/courses/2189/quizzes?per_page=50"
NEXT = ORIGIN + "/api/v1/courses/2189/quizzes?bookmark=q%2B2&per_page=2"
DETAIL_PATH = "/api/v1/courses/2189/quizzes/6407?per_page=50"
QUIZZES = [
    {"id": 6401, "title": "Warm-up – ratios", "due_at": "2026-10-20T23:30:00Z",
     "lock_at": None, "question_count": 7, "points_possible": 12.5, "published": True,
     "quiz_type": "practice_quiz", "html_url": ORIGIN + "/courses/2189/quizzes/6401",
     "description": "<p>Supplied description omitted by the existing list projection.</p>"},
    {"id": 6407, "title": "Revision – optional", "due_at": None,
     "lock_at": "2026-11-01T07:15:00Z", "question_count": 0, "points_possible": 0,
     "published": False, "quiz_type": "survey",
     "html_url": ORIGIN + "/courses/2189/quizzes/6407", "allowed_attempts": -1}
]
KEYS = ("id", "title", "due_at", "lock_at", "question_count", "points_possible",
        "published", "quiz_type", "html_url")
EXPECTED_LIST = [{key: item.get(key) for key in KEYS} for item in QUIZZES]
DETAIL = {**QUIZZES[1], "description": "<p>Review the supplied requirements.</p>",
          "time_limit": None, "shuffle_answers": False, "one_question_at_a_time": False,
          "cant_go_back": False, "unlock_at": "2026-10-08T09:00:00+09:00",
          "locked_for_user": True, "lock_info": {"unlock_at": "2026-10-08T00:00:00Z"},
          "all_dates": [{"due_at": None, "lock_at": "2026-11-01T07:15:00Z", "base": True}]}

class Broker(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def send(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.server.events.append({"transport": "GET", "path": self.path,
                                   "authorization_present": bool(self.headers.get("Authorization"))})
        if self.path != "/health":
            self.send({"ok": False, "error": "Unexpected broker route"}, 404)
            return
        self.send({"ok": True, "base_url": ORIGIN, "link_pagination": True})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if self.path != "/fetch" or not 0 < length <= 8192:
            self.send({"ok": False, "error": "Unexpected broker operation"}, 400)
            return
        payload = json.loads(self.rfile.read(length))
        self.server.events.append({"transport": "POST", "path": self.path,
                                   "authorization_present": bool(self.headers.get("Authorization")),
                                   "upstream": payload})
        if (payload.get("op") != "fetch" or payload.get("method") != "GET"
                or payload.get("body") is not None):
            self.send({"ok": False, "error": "Only read-only Canvas fetch is admitted"})
            return
        path = payload.get("path")
        status, link = 200, ""
        if path == FIRST:
            data, link = [QUIZZES[0]], '<' + NEXT + '>; rel="next"'
        elif path == NEXT:
            data = [QUIZZES[1]]
        elif path == DETAIL_PATH:
            if self.server.denied:
                data, status = {"errors": [{"message": "quiz metadata is unavailable"}]}, 403
            else:
                data = DETAIL
        else:
            data, status = {"errors": [{"message": "Unexpected Canvas path"}]}, 404
        self.send({"ok": True, "response": {"status": status, "headers": {"Link": link},
                                          "json": data, "text": None}})

def digest(data):
    return hashlib.sha256(data).hexdigest()

def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def snapshot(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            result[str(path.relative_to(root))] = {"bytes": len(data), "sha256": digest(data),
                                                  "git_blob": git_blob(data)}
    if len(result) > 100 or sum(x["bytes"] for x in result.values()) > 1048576:
        raise RuntimeError("Source snapshot exceeds the fixed receiving cap")
    return result

def method(source, name):
    text = (source / "src/canvaspilot/api.py").read_text()
    cls = next(x for x in ast.parse(text).body if isinstance(x, ast.ClassDef) and x.name == "CanvasAPI")
    node = next(x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == name)
    return ast.get_source_segment(text, node)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise RuntimeError("Receiving output already exists")
    free = shutil.disk_usage(args.out.parent).free
    available = int(next(x.split()[1] for x in Path("/proc/meminfo").read_text().splitlines()
                         if x.startswith("MemAvailable:"))) * 1024
    if free < 805306368 or available < 1610612736:
        raise RuntimeError("Unchanged 768 MiB disk / 1.5 GiB memory admission refused")
    sources = {"baseline": snapshot(args.baseline), "candidate": snapshot(args.candidate)}
    assert sources["baseline"]["src/canvaspilot/cli.py"]["git_blob"] == "545ec52f31b694a351e9a41a68e52a34c49db532"
    assert sources["candidate"]["src/canvaspilot/cli.py"]["sha256"] == "2c951207cf42ca0ddee33629c84eb561fab64ad1f62d552a059a6637b6c612fe"
    for name in ("baseline", "candidate"):
        assert sources[name]["src/canvaspilot/client.py"]["git_blob"] == "1db4b1135305f7e410025ae7937f9a6cd349f020"
        assert sources[name]["src/canvaspilot/api.py"]["git_blob"] == "73e47f1354fc5bab44e9f030c5bf5d29c12d065f"
    assert method(args.baseline, "list_quizzes") == method(args.candidate, "list_quizzes")
    assert method(args.baseline, "get_quiz") == method(args.candidate, "get_quiz")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Broker)
    server.daemon_threads = True
    server.events = []
    server.denied = False
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    checks, processes = [], []

    def check(name, condition):
        checks.append({"name": name, "pass": bool(condition)})

    def invoke(label, source, command):
        start = len(server.events)
        env = dict(os.environ)
        env.update({"PYTHONPATH": str(source / "src"), "PYTHONDONTWRITEBYTECODE": "1",
                    "CANVAS_API_TOKEN": "", "CANVAS_BASE_URL": ORIGIN,
                    "CANVAS_SESSION_PORT": str(server.server_port),
                    "CANVAS_PROFILE": str(args.out.parent / "unused-profile"),
                    "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9",
                    "ALL_PROXY": "http://127.0.0.1:9", "NO_PROXY": "[::1]"})
        argv = [args.python, "-B", "-m", "canvaspilot.cli", *command,
                "--base-url", ORIGIN, "--profile", str(args.out.parent / "unused-profile")]
        started = time.monotonic()
        completed = subprocess.run(argv, cwd=args.out.parent, env=env, text=True,
                                   capture_output=True, timeout=25, check=False)
        row = {"label": label, "argv": argv, "source": str(source), "returncode": completed.returncode,
               "stdout": completed.stdout, "stderr": completed.stderr,
               "seconds": round(time.monotonic() - started, 4), "events": server.events[start:]}
        processes.append(row)
        return row

    error = None
    try:
        for label, command in (("baseline-list", ["quizzes", COURSE]),
                               ("baseline-detail", ["quiz", COURSE, "6407"])):
            row = invoke(label, args.baseline, command)
            check(label + " refuses missing route before I/O",
                  row["returncode"] == 2 and not row["stdout"] and not row["events"]
                  and "invalid choice" in row["stderr"])
        listing = invoke("candidate-list", args.candidate, ["quizzes", COURSE])
        check("candidate list exits successfully", listing["returncode"] == 0)
        rows = json.loads(listing["stdout"]) if listing["returncode"] == 0 else []
        check("existing list projection preserves both pages exactly", rows == EXPECTED_LIST)
        paths = [e["upstream"]["path"] for e in listing["events"] if "upstream" in e]
        check("opaque absolute continuation is followed without extra filters", paths == [FIRST, NEXT])
        selected = next((x["id"] for x in rows if x.get("title") == QUIZZES[1]["title"]), None)
        check("detail selection comes from the actual list output", selected == 6407)
        detail = invoke("candidate-selected-detail", args.candidate,
                        ["quiz", COURSE, str(selected)])
        check("selected detail exits successfully", detail["returncode"] == 0)
        value = json.loads(detail["stdout"]) if detail["returncode"] == 0 else None
        check("all supplied timing attempt lock and null metadata remain exact", value == DETAIL)
        check("course and selected quiz route remain distinct",
              [e["upstream"]["path"] for e in detail["events"] if "upstream" in e] == [DETAIL_PATH])
        server.denied = True
        rejected = invoke("candidate-denied-detail", args.candidate, ["quiz", COURSE, "6407"])
        check("denied metadata exits one with no partial stdout",
              rejected["returncode"] == 1 and not rejected["stdout"])
        try:
            denial = json.loads(rejected["stderr"])
        except ValueError:
            denial = {}
        check("denied metadata returns the existing structured auth error",
              denial.get("ok") is False and denial.get("error") == "CanvasAuthError"
              and "403" in denial.get("message", "") and "Traceback" not in rejected["stderr"])
        server.denied = False
        retry = invoke("candidate-retry-detail", args.candidate, ["quiz", COURSE, "6407"])
        check("normal retry receives unchanged metadata",
              retry["returncode"] == 0 and json.loads(retry["stdout"]) == DETAIL)
        upstream = [e["upstream"] for e in server.events if "upstream" in e]
        check("all five Canvas fetches are GET metadata reads",
              len(upstream) == 5 and all(p["method"] == "GET" and p["body"] is None for p in upstream))
        check("no questions submissions or attempts route is called",
              all(p["path"] in (FIRST, NEXT, DETAIL_PATH) for p in upstream))
        check("broker transport carries no authorization header",
              all(not e["authorization_present"] for e in server.events))
        check("broker was used despite deliberately unusable proxy configuration",
              any(e["path"] == "/health" for e in server.events)
              and all(e["path"] in ("/health", "/fetch") for e in server.events))
        check("no browser profile is created", not (args.out.parent / "unused-profile").exists())
    except Exception as exc:
        error = {"class": type(exc).__name__, "message": str(exc)}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        unchanged = sources == {"baseline": snapshot(args.baseline), "candidate": snapshot(args.candidate)}
        check("both complete source snapshots are unchanged", unchanged)
        report = {"format": "hamon-canvas-quiz-broker-receiving/1", "reviewer": "estate-3dcb83a1/root",
                  "interpreter": args.python, "receiverRuntime": sys.version.split()[0],
                  "currentBase": "a5ce672e5b3580c1f52e13c49eefee830f11346c",
                  "currentTree": "0661a7005e577864cb87bc41e0e715409c92ee76",
                  "candidateCli": sources["candidate"]["src/canvaspilot/cli.py"],
                  "sourceSnapshots": sources, "fixtureSha256": digest(json.dumps(
                      {"origin": ORIGIN, "quizzes": QUIZZES, "detail": DETAIL}, sort_keys=True).encode()),
                  "admission": {"freeBytes": free, "availableMemoryBytes": available},
                  "checks": checks, "processes": processes, "error": error,
                  "accepted": error is None and all(x["pass"] for x in checks),
                  "scope": "Six actual CLI subprocesses through the existing HTTP session-broker client. Synthetic metadata; no live Canvas account, browser login or upstream write."}
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if len(text.encode()) > 131072:
            raise RuntimeError("Compact report exceeds its fixed bound")
        args.out.write_text(text, encoding="utf-8")
        print(json.dumps({"accepted": report["accepted"], "checks": len(checks),
                          "passed": sum(x["pass"] for x in checks),
                          "processes": len(processes), "error": error,
                          "report": str(args.out), "sha256": digest(text.encode()),
                          "bytes": len(text.encode())}))
    return 0 if report["accepted"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
