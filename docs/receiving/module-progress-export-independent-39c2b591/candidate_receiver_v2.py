from pathlib import Path
from html.parser import HTMLParser
import argparse, base64, hashlib, json, traceback
from producer_receiver_v1 import WireFixture, command, assert_complete_wire
from independent_fixture_v1 import EXPECTED, expected_selected

class SavedHTML(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.scripts = []
        self.source_attributes = []
        self.handlers = []
        self.text = []
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and "download" in values:
            self.links.append(values)
        if tag in {"script", "iframe", "form"}:
            self.scripts.append(tag)
        if "src" in values or tag == "link" and values.get("rel") == "stylesheet":
            self.source_attributes.append((tag, values))
        self.handlers.extend((tag, name) for name, _ in attrs if name.lower().startswith("on"))
    def handle_data(self, value):
        self.text.append(value)

def normalized_from_html(path, expected):
    content = path.read_bytes()
    doc = SavedHTML(content.decode("utf-8"))
    assert not doc.scripts and not doc.source_attributes and not doc.handlers
    links = [a for a in doc.links if a.get("href", "").startswith("data:application/json")]
    assert len(links) == 1, {"normalized_download_links": len(links)}
    prefix, encoded = links[0]["href"].split(";base64,", 1)
    decoded = base64.b64decode(encoded, validate=True)
    observed = json.loads(decoded)
    assert observed == expected, {"expected": expected, "actual": observed}
    rendered_text = "".join(doc.text)
    previous = -1
    for module in expected["modules"]:
        position = rendered_text.index(module["name"])
        assert position > previous
        previous = position
        for item in module["items"]:
            assert item["title"] in rendered_text, item["id"]
    return {"path": str(path), "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            "json_bytes": len(decoded), "json_sha256": hashlib.sha256(decoded).hexdigest(),
            "download_name": links[0]["download"], "included_modules": [m["id"] for m in observed["modules"]]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--chrome", required=True)
    parser.add_argument("--original-cli-stdout", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir()
    report = {"source": str(args.source), "groups": [], "artifacts": {}, "children": 0}
    def group(name, run):
        try:
            result = run()
            report["groups"].append({"name": name, "pass": True, "result": result})
        except Exception as error:
            report["groups"].append({"name": name, "pass": False, "error": str(error), "traceback": traceback.format_exc()})
    with WireFixture() as server:
        def export(label, target, expected, selection=None):
            args_list = ["export-module-progress", "00731", "--out", str(target)]
            if selection is not None:
                args_list.extend(["--module-id", selection])
            result, receipt = command(args.source, args.out, server, label, args_list)
            report["children"] += 1
            assert result.returncode == 0, result.stderr.decode()
            assert_complete_wire(receipt)
            artifact = normalized_from_html(target, expected)
            if selection is None:
                assert artifact["json_sha256"] == hashlib.sha256(args.original_cli_stdout.read_bytes()).hexdigest(), "The complete embedded JSON differs from the actual original CLI bytes"
            report["artifacts"][label] = artifact
            return artifact
        all_path, selected_path = args.out / "all.html", args.out / "selected.html"
        group("Actual all-module CLI/client report preserves complete original normalized observation",
              lambda: export("all", all_path, EXPECTED))
        group("Actual selected-module CLI/client report retains all-returned selection counts",
              lambda: export("selected", selected_path, expected_selected(), "009101"))
        refused_path = args.out / "recoverable.html"
        def refusal():
            server.phase = "later-read-failure"
            result, receipt = command(args.source, args.out, server, "later-read-failure",
                ["export-module-progress", "731", "--out", str(refused_path)])
            report["children"] += 1
            assert result.returncode == 1
            assert not refused_path.exists()
            assert not list(args.out.glob(".recoverable.html.*"))
            assert [row["status"] for row in receipt["wire"]] == [200, 503]
            assert all(row["method"] == "GET" and row["synthetic_token_matches"] for row in receipt["wire"])
            assert b"Traceback" not in result.stderr
            assert b"503" in result.stderr
            return {"exit": result.returncode, "partial_html_published": False, "get_statuses": [200, 503]}
        group("Later real HTTP read failure refuses a partial report", refusal)
        server.phase = "complete"
        group("The same refused destination succeeds after the source read recovers",
              lambda: export("recovered", refused_path, EXPECTED))
        report["wire_requests"] = len(server.records)
        report["canvas_methods"] = sorted(set(row["method"] for row in server.records))
    # Mutate only our saved artifact to exercise the same extraction and oracle.
    # This is a receiver negative control; the candidate source stays exact.
    def sensitivity():
        original = all_path.read_text()
        doc = SavedHTML(original)
        original_link = next(a for a in doc.links if a["href"].startswith("data:application/json"))
        wrong = json.loads(json.dumps(EXPECTED))
        wrong["collection_complete"] = True
        replacement = "data:application/json;base64," + base64.b64encode(json.dumps(wrong).encode()).decode()
        corrupted = args.out / "control-invented-completeness.html"
        corrupted.write_text(original.replace(original_link["href"], replacement, 1))
        try:
            normalized_from_html(corrupted, EXPECTED)
        except AssertionError:
            return {"incorrect_whole_course_completion_claim_detected": True,
                    "changed_own_artifact": str(corrupted), "product_source_mutated": False}
        raise AssertionError("The receiver accepted an invented collection-complete claim")
    group("Negative control detects an invented completeness claim in normalized data", sensitivity)
    report["pass"] = all(row["pass"] for row in report["groups"])
    if report["pass"]:
        (args.out / "expected-all.json").write_text(json.dumps(EXPECTED, ensure_ascii=False, indent=2) + "\n")
        (args.out / "expected-selected.json").write_text(json.dumps(expected_selected(), ensure_ascii=False, indent=2) + "\n")
        config = {"all_html": str(all_path), "selected_html": str(selected_path),
                  "expected_all": str(args.out / "expected-all.json"),
                  "expected_selected": str(args.out / "expected-selected.json"),
                  "chrome": args.chrome, "original_cli_stdout": str(args.original_cli_stdout),
                  "out": str(args.out.parent / "browser-v1")}
        (args.out / "browser-config.json").write_text(json.dumps(config, indent=2) + "\n")
    (args.out / "RECEIPT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"pass": report["pass"], "groups": len(report["groups"]), "children": report["children"],
                      "requests": report["wire_requests"], "out": str(args.out)}, indent=2))
    raise SystemExit(0 if report["pass"] else 1)

if __name__ == "__main__":
    main()
