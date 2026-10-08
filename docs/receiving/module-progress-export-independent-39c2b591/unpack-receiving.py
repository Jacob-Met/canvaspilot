from pathlib import Path
import base64,gzip,hashlib,json,sys

base=Path(__file__).resolve().parent
target=Path(sys.argv[1])
manifest=json.loads((base/"RAW_MANIFEST.json").read_text())
encoded=b""
for part in manifest["parts"]:
    value=(base/part["path"]).read_bytes()
    assert len(value)==part["bytes"] and hashlib.sha256(value).hexdigest()==part["sha256"]
    encoded+=value
assert hashlib.sha256(encoded).hexdigest()==manifest["encoded_sha256"]
compressed=base64.b64decode(encoded,validate=True)
assert len(compressed)==manifest["gzip_bytes"]
assert hashlib.sha256(compressed).hexdigest()==manifest["gzip_sha256"]
raw=gzip.decompress(compressed)
assert len(raw)==manifest["container_bytes"]
assert hashlib.sha256(raw).hexdigest()==manifest["container_sha256"]
container=json.loads(raw)
assert len(container["files"])==len(manifest["files"])
material=[]
for file,expected in zip(container["files"],manifest["files"]):
    assert {key:file[key] for key in ("path","bytes","sha256")}==expected
    relative=Path(file["path"])
    assert not relative.is_absolute() and ".." not in relative.parts
    data=base64.b64decode(file["base64"],validate=True)
    assert len(data)==file["bytes"] and hashlib.sha256(data).hexdigest()==file["sha256"]
    material.append((relative,data))
target.mkdir(parents=True,exist_ok=False)
for relative,data in material:
    destination=target/relative
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("xb") as handle:handle.write(data)
print(json.dumps({"files":len(material),"bytes":sum(len(data) for _,data in material),"output":str(target)}))
