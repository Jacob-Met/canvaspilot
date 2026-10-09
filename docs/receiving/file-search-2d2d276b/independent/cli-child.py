"""Run the real native CLI with observed lifecycle and loopback-only sockets."""
import datetime, json, logging, os, pathlib, runpy, socket, sys, traceback
metadata = {"started": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "client_created": 0, "client_closed": 0, "connects": [], "blocked": []}
port = int(os.environ["RECEIVER_LOOPBACK_PORT"])
meta_path = pathlib.Path(os.environ["RECEIVER_META"])
original_connect = socket.socket.connect
original_getaddrinfo = socket.getaddrinfo
def guarded_connect(sock, address):
    if not isinstance(address, tuple) or address[0] != "127.0.0.1" or address[1] != port:
        metadata["blocked"].append({"kind":"connect", "address":repr(address)})
        raise RuntimeError("Independent receiver forbids a non-fixture connection")
    metadata["connects"].append([address[0],address[1]])
    return original_connect(sock,address)
def guarded_lookup(host, service, *args, **kwargs):
    if host not in ("127.0.0.1", b"127.0.0.1"):
        metadata["blocked"].append({"kind":"lookup", "host":repr(host)})
        raise RuntimeError("Independent receiver forbids a non-fixture lookup")
    return original_getaddrinfo(host,service,*args,**kwargs)
socket.socket.connect=guarded_connect
socket.getaddrinfo=guarded_lookup
from canvaspilot.client import CanvasClient
original_init=CanvasClient.__init__
original_close=CanvasClient.close
def observed_init(self,*args,**kwargs):
    metadata["client_created"]+=1
    return original_init(self,*args,**kwargs)
def observed_close(self,*args,**kwargs):
    metadata["client_closed"]+=1
    return original_close(self,*args,**kwargs)
CanvasClient.__init__=observed_init
CanvasClient.close=observed_close
logger=logging.getLogger("httpx")
logger.setLevel(int(os.environ.get("RECEIVER_LOG_LEVEL","17")))
metadata["logger_before"]=logger.level
code=0
try:
    sys.argv=["canvaspilot",*sys.argv[1:]]
    runpy.run_module("canvaspilot.cli",run_name="__main__",alter_sys=True)
except SystemExit as exc:
    code=exc.code if isinstance(exc.code,int) else (0 if exc.code is None else 1)
except BaseException as exc:
    code=1
    metadata["uncaught_exception"]=type(exc).__name__
    traceback.print_exc()
finally:
    metadata["source_modules"]={name:str(pathlib.Path(module.__file__).resolve())
        for name,module in sorted(sys.modules.items())
        if name.startswith("canvaspilot") and getattr(module,"__file__",None)}
    metadata["logger_after"]=logger.level
    metadata["exit"]=code
    metadata["finished"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with meta_path.open("x",encoding="utf-8") as handle:
        json.dump(metadata,handle,indent=2)
        handle.write("\n")
raise SystemExit(code)
