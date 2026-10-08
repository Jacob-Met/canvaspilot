"""Launch the real module with source binding and a loopback-only socket guard."""
import os
import runpy
import socket
import sys
from pathlib import Path

port = int(sys.argv[1])
source = Path(sys.argv[2]).resolve()
assert source.is_dir()
profile = Path(os.environ["CANVAS_PROFILE"]).resolve()
receiver = Path("/tmp/canvaspilot-inbox-independent-713adaab")
assert profile.is_relative_to(receiver) and not profile.exists()
connect = socket.socket.connect
connect_ex = socket.socket.connect_ex

def admitted(address):
    if not isinstance(address, tuple) or address[:2] != ("127.0.0.1", port):
        raise RuntimeError("independent receiver refused a non-fixture connection")

def guarded_connect(self, address):
    admitted(address)
    return connect(self, address)

def guarded_connect_ex(self, address):
    admitted(address)
    return connect_ex(self, address)

socket.socket.connect = guarded_connect
socket.socket.connect_ex = guarded_connect_ex
sys.path.insert(0, str(source))
sys.argv = ["canvaspilot", *sys.argv[3:]]
runpy.run_module("canvaspilot.cli", run_name="__main__")
