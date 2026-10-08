"""Constrain this authored receiving child to the explicitly supplied loopback fixture."""
import atexit
import hashlib
import json
import os
from pathlib import Path
import sys

port = int(os.environ["GRADE_REVIEW_LOOPBACK_PORT"])
root = Path(os.environ["GRADE_REVIEW_SOURCE"]).resolve()
receipt = Path(os.environ["GRADE_REVIEW_CHILD_RECEIPT"])
events = []
blocked = []
def check(event, args):
    if event == "socket.connect":
        address = args[1]
        allowed = isinstance(address, tuple) and address[0] == "127.0.0.1" and address[1] == port
        if not allowed:
            blocked.append(repr(address))
            raise RuntimeError("Only the authored loopback Canvas fixture is allowed")
        events.append({"host": address[0], "port": address[1]})
sys.addaudithook(check)
def finish():
    sources = {}
    for name, module in tuple(sys.modules.items()):
        value = getattr(module, "__file__", None)
        if value:
            path = Path(value).resolve()
            if path.is_relative_to(root) and path.is_file():
                sources[name] = {"path": str(path.relative_to(root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    receipt.write_text(json.dumps({
        "guard_active": True, "allowed_connections": events, "blocked_connections": blocked,
        "source_origins": sources,
        "guard_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }, indent=2) + "\n")
atexit.register(finish)
