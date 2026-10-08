"""The actual calendar CLI refuses incomplete collections without an artifact."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pytest
from test_calendar_export import assignment, run_cli


@pytest.mark.parametrize("failure", ["metadata", "shape"])
def test_later_pagination_failure_has_structured_calendar_error(tmp_path, failure):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            requests.append(self.path)
            later = "cursor=" in self.path
            rows = {"error": "authored wrong collection shape"} if later and failure == "shape" else [
                assignment(2 if later else 1),
            ]
            payload = json.dumps(rows).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            if not later:
                self.send_header("Link", f'<{server.url}/api/v1/courses/42/assignments?cursor=next%2Fopaque>; rel="next"')
            elif failure == "metadata":
                self.send_header("Link", f'<{server.url}/api/v1/courses/42/assignments?cursor=invalid>')
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.url = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = run_cli(server, tmp_path)
        assert result.returncode == 1
        assert not result.stdout
        assert "Traceback" not in result.stderr
        error = json.loads(result.stderr.splitlines()[-1])
        assert error["ok"] is False
        assert error["error"] == "CanvasPaginationError"
        assert error["message"]
        assert len(requests) == 2
        assert [urlsplit(path).path for path in requests] == [
            "/api/v1/courses/42/assignments", "/api/v1/courses/42/assignments",
        ]
        assert urlsplit(requests[1]).query == "cursor=next%2Fopaque"
        assert not list(tmp_path.iterdir())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
