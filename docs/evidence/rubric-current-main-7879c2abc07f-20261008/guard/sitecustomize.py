"""Receiving-only startup guard; outside all published source directories."""
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

sys.dont_write_bytecode = True
_ROOT = Path("/dev/shm/canvaspilot-rubric-receiving-7879c2abc07f")
_GUARD = str(_ROOT / "guard")
_SOURCE = os.environ.get("RECEIVING_SOURCE_ROOT")
_LOG = _ROOT / "evidence" / "runtime-guard.jsonl"

def _record(event, **fields):
    row = {"time": time.time(), "pid": os.getpid(), "event": event, "source": _SOURCE, **fields}
    fd = os.open(_LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, (json.dumps(row, sort_keys=True) + "\n").encode())
    finally:
        os.close(fd)

def _loopback(host):
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="strict")
    if host is None:
        return True
    if str(host).lower().rstrip(".") == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False

_native_getaddrinfo = socket.getaddrinfo
def _getaddrinfo(host, port, *args, **kwargs):
    if not _loopback(host):
        _record("denied_resolution", host=str(host), port=port)
        raise PermissionError("Receiving permits synthetic loopback addresses only")
    return _native_getaddrinfo(host, port, *args, **kwargs)
socket.getaddrinfo = _getaddrinfo

def _check(address):
    if isinstance(address, tuple):
        host, port = address[:2]
        if not _loopback(host) or port == 18765:
            _record("denied_connect", host=str(host), port=port)
            raise PermissionError("Receiving forbids external or default Canvas broker connections")
        _record("loopback_connect", host=str(host), port=port)

_native_connect = socket.socket.connect
_native_connect_ex = socket.socket.connect_ex
def _connect(self, address):
    _check(address)
    return _native_connect(self, address)
def _connect_ex(self, address):
    _check(address)
    return _native_connect_ex(self, address)
socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex

_native_popen = subprocess.Popen
class ReceivingPopen(_native_popen):
    def __init__(self, *args, **kwargs):
        positional = list(args)
        supplied = positional[10] if len(positional) > 10 else kwargs.get("env")
        child_env = dict(os.environ if supplied is None else supplied)
        prior = child_env.get("PYTHONPATH", "")
        parts = [p for p in prior.split(os.pathsep) if p and p != _GUARD]
        child_env["PYTHONPATH"] = os.pathsep.join([_GUARD, *parts])
        child_env["PYTHONDONTWRITEBYTECODE"] = "1"
        child_env["PYTHONNOUSERSITE"] = "1"
        if _SOURCE:
            child_env["RECEIVING_SOURCE_ROOT"] = _SOURCE
        child_env.setdefault("CANVAS_PROFILE", str(_ROOT / "tmp" / "unused-profile"))
        if len(positional) > 10:
            positional[10] = child_env
        else:
            kwargs["env"] = child_env
        super().__init__(*positional, **kwargs)
subprocess.Popen = ReceivingPopen

if not _SOURCE:
    _record("missing_source_binding")
    os._exit(72)
_spec = importlib.util.find_spec("canvaspilot")
_expected = Path(_SOURCE) / "src" / "canvaspilot" / "__init__.py"
if _spec is None or _spec.origin is None or Path(_spec.origin).resolve() != _expected.resolve():
    _record("wrong_package_origin", actual=None if _spec is None else _spec.origin, expected=str(_expected))
    os._exit(72)
_record("startup", interpreter=sys.executable, package_origin=_spec.origin, bytecode_disabled=sys.dont_write_bytecode)
