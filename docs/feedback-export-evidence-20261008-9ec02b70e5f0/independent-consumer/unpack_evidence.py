"""Verify all indexed archive members before optional extraction to a new path."""
from pathlib import Path, PurePosixPath
import argparse
import base64
import hashlib
import io
import json
import tarfile

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path)
args = parser.parse_args()
index = json.loads((HERE / 'raw-evidence-index.json').read_text())
encoded = (HERE / 'raw-evidence.tar.gz.base64').read_bytes()
if hashlib.sha256(encoded).hexdigest() != index['encoded_sha256']:
    raise ValueError('encoded archive mismatch')
raw = base64.b64decode(b''.join(encoded.split()), validate=True)
if len(raw) != index['compressed_bytes'] or hashlib.sha256(raw).hexdigest() != index['compressed_sha256']:
    raise ValueError('compressed archive mismatch')
verified = {}
with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
    for member in archive:
        path = PurePosixPath(member.name)
        if not member.isfile() or path.is_absolute() or '..' in path.parts or member.name in verified:
            raise ValueError('unexpected archive member')
        expected = index['files'].get(member.name)
        if expected is None:
            raise ValueError('unindexed archive member')
        content = archive.extractfile(member).read()
        if len(content) != expected['bytes'] or hashlib.sha256(content).hexdigest() != expected['sha256']:
            raise ValueError('member bytes differ: ' + member.name)
        verified[member.name] = content
if set(verified) != set(index['files']):
    raise ValueError('archive member set differs')
if args.output is not None:
    args.output.mkdir(parents=True, exist_ok=False)
    for name, content in verified.items():
        path = args.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(content)
print(json.dumps({'verified_files': len(verified), 'bytes': sum(map(len, verified.values())),
                  'extracted_to': str(args.output) if args.output else None}))
