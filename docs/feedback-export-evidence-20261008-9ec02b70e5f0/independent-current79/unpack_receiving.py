"""Verify the complete current-parent capsule; optionally extract into a new directory."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile


def fingerprint(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capsule', type=Path, default=Path(__file__).with_name('receiving-capsule.tar.gz.base64'))
    parser.add_argument('--index', type=Path, default=Path(__file__).with_name('receiving-capsule-index.json'))
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    index = json.loads(args.index.read_text())
    encoded = args.capsule.read_bytes()
    if fingerprint(encoded) != index['archive']['encoded']:
        raise RuntimeError('encoded capsule pin mismatch')
    compressed = base64.b64decode(b''.join(encoded.split()), validate=True)
    if fingerprint(compressed) != index['archive']['compressed']:
        raise RuntimeError('compressed capsule pin mismatch')
    recovered = {}
    with tarfile.open(fileobj=io.BytesIO(compressed), mode='r:gz') as archive:
        for member in archive.getmembers():
            name = PurePosixPath(member.name)
            if not member.isfile() or name.is_absolute() or '..' in name.parts or member.name in recovered:
                raise RuntimeError('unexpected capsule member: ' + member.name)
            data = archive.extractfile(member).read()
            if fingerprint(data) != index['files'].get(member.name):
                raise RuntimeError('capsule member pin mismatch: ' + member.name)
            recovered[member.name] = data
    if set(recovered) != set(index['files']):
        raise RuntimeError('capsule file inventory mismatch')
    if args.destination is not None:
        args.destination.mkdir(parents=True, exist_ok=False)
        for name, data in recovered.items():
            destination = args.destination / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as handle:
                handle.write(data)
    print(json.dumps({'files': len(recovered), 'raw_bytes': sum(map(len, recovered.values())),
                      'all_members_exact': True,
                      'destination': str(args.destination) if args.destination is not None else None}))


if __name__ == '__main__':
    main()
