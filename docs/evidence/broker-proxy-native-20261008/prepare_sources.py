"""Reconstruct the two pinned source trees from an existing authorized git repo."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repo", required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent


def git(*arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(args.repo), *arguments], timeout=30)


for kind in ("head", "base"):
    manifest = json.loads((root / (kind + "-source-manifest.json")).read_text())
    commit = manifest.get("commit") or manifest["head"]
    paths = git("ls-tree", "-r", "--name-only", "-z", commit).decode().split("\0")[:-1]
    if sorted(paths) != sorted(item["path"] for item in manifest["files"]):
        raise RuntimeError("Pinned tree paths differ from manifest: " + kind)
    for item in manifest["files"]:
        content = git("show", commit + ":" + item["path"])
        actual = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        if actual != item["sha"]:
            raise RuntimeError("Git blob mismatch: " + kind + "/" + item["path"])
        destination = root / kind / item["path"]
        if destination.exists() and destination.read_bytes() != content:
            raise RuntimeError("Refusing to replace different existing source: " + str(destination))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    print(kind + ": verified " + str(len(paths)) + " files at " + commit)
