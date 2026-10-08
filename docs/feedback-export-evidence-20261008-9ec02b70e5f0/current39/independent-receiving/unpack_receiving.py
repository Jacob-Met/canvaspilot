#!/usr/bin/env python3
"""Verify a lossless receiving capsule, optionally display or extract it."""
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile


def digest(body):
    return hashlib.sha256(body).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--cat", metavar="MEMBER")
    target.add_argument("--output", type=Path)
    args = parser.parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    name = index["archive"]
    if Path(name).name != name:
        raise ValueError("Archive must be beside its index.")
    raw = args.index.with_name(name).read_bytes()
    if len(raw) != index["bytes"] or digest(raw) != index["sha256"]:
        raise ValueError("Encoded archive byte/hash mismatch.")
    compressed = base64.b64decode(raw.strip(), validate=True)
    if len(compressed) != index["compressed_bytes"] or digest(compressed) != index["compressed_sha256"]:
        raise ValueError("Compressed archive byte/hash mismatch.")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(compressed)), mode="r:") as archive:
        members = archive.getmembers()
        if len(members) != index["member_count"]:
            raise ValueError("Member count mismatch.")
        for member in members:
            path = PurePosixPath(member.name)
            if not member.isfile() or path.is_absolute() or ".." in path.parts or "\\" in member.name:
                raise ValueError("Nonordinary archive member.")
            if member.name in files:
                raise ValueError("Duplicate member.")
            body = archive.extractfile(member).read()
            expected = index["members"].get(member.name)
            if expected != {"bytes": len(body), "sha256": digest(body)}:
                raise ValueError("Member byte/hash mismatch: " + member.name)
            files[member.name] = body
    if set(files) != set(index["members"]):
        raise ValueError("Member allowlist mismatch.")
    if sum(map(len, files.values())) != index["uncompressed_member_bytes"]:
        raise ValueError("Total member bytes mismatch.")
    if args.cat is not None:
        sys.stdout.buffer.write(files[args.cat])
    elif args.output is not None:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, body in files.items():
            path = args.output.joinpath(*PurePosixPath(name).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(body)
        print(json.dumps({"verified": len(files), "extracted_to": str(args.output)}))
    else:
        print(json.dumps({"verified": len(files), "bytes": sum(map(len, files.values())),
                          "archive_sha256": digest(raw)}))


if __name__ == "__main__":
    main()
