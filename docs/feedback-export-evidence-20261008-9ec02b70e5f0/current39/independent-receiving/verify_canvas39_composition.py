"""Bounded independent receiving of the current39 feedback-export composition."""
import argparse
import ast
import base64
from difflib import SequenceMatcher
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import time
import traceback


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def pretty(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def exact_method_bodies(raw):
    text = raw.decode()
    cls = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == "CanvasAPI")
    return {n.name: ast.get_source_segment(text, n).encode()
            for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def independent_insertions(before, current, expected):
    a, b = before.splitlines(keepends=True), current.splitlines(keepends=True)
    operations = SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    changes = [item for item in operations if item[0] != "equal"]
    check(len(changes) == expected and all(item[0] == "insert" for item in changes),
          "Unexpected nonadditive or extra source change")
    recovered = b"".join(b[k:l] for tag, i, j, k, l in operations if tag == "equal")
    check(recovered == before, "Dropping only the independently located insertions must recover all native bytes")
    return [{"before_line": i + 1, "candidate_line": k + 1, "body": b"".join(b[k:l]).decode(),
             "pin": pin(b"".join(b[k:l]))} for tag, i, j, k, l in changes]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["source", "pins", "published", "before-source", "support", "prior-receiving", "prior-json", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {"schema": "independent-canvas39-export-composition.v1", "status": "running",
              "parent": "39d835c8becb04d81b65c90d1491d2d3a2727ffe",
              "tree": "53b67d3f06b4c780e508325ec42b2b435ec57e97",
              "mode": "optimized" if sys.flags.optimize else "normal",
              "source_root": str(args.source), "python": sys.version,
              "probe": pin(Path(__file__).read_bytes()), "source_before": {}, "source_after": {},
              "commands": [], "browser_allocations": 0, "github_writes": 0, "live_accounts": 0}
    pins = json.loads(args.pins.read_bytes())
    def source_pins():
        found = {}
        for row in pins["files"]:
            value = pin((args.source / row["path"]).read_bytes())
            check(value == {key: row[key] for key in ["bytes", "sha256", "git_blob"]},
                  "Candidate input changed: " + row["path"])
            found[row["path"]] = value
        check(len(found) == 30, "Expected exact 30-input receiving composition")
        return found
    try:
        check(pin(args.pins.read_bytes())["sha256"] == "560196c2439531be7d988b10b7a9f5a41a2e3d207b3336649410f810c50d659b",
              "Frozen current39 source manifest changed")
        result["source_before"] = source_pins()
        proof = {"insertions": {}, "unchanged_current_owner_files": {}, "before_source_pins": {}}
        for name, count in [("src/canvaspilot/cli.py", 2), ("README.md", 1)]:
            before = (args.published / name).read_bytes()
            current = (args.source / name).read_bytes()
            old_qualified = (args.before_source / name).read_bytes()
            insertions = independent_insertions(before, current, count)
            for entry in insertions:
                check(old_qualified.count(entry["body"].encode()) == 1,
                      "Insertion differs from the already qualified export contribution")
            proof["insertions"][name] = {"complete_native_before": pin(before),
                "candidate": pin(current), "inverse_exact": True, "blocks": insertions}
            proof["before_source_pins"][name] = pin(old_qualified)
        for name in ["api.py", "bundle.py", "mcp_server.py", "submission_history.py"]:
            relative = "src/canvaspilot/" + name
            before = (args.published / relative).read_bytes()
            check((args.source / relative).read_bytes() == before,
                  "Incoming owner file changed: " + relative)
            proof["unchanged_current_owner_files"][relative] = pin(before)
        old_api = (args.before_source / "src/canvaspilot/api.py").read_bytes()
        new_api = (args.source / "src/canvaspilot/api.py").read_bytes()
        prior_methods, current_methods = exact_method_bodies(old_api), exact_method_bodies(new_api)
        check(len(prior_methods) == 40 and len(current_methods) == 41,
              "Unexpected API method set")
        check(set(current_methods) - set(prior_methods) == {"submission_history"},
              "Unexpected newly imported API entry")
        check(all(current_methods.get(name) == body for name, body in prior_methods.items()),
              "An existing API method body changed")
        api_insertions = independent_insertions(old_api, new_api, 1)
        check("from canvaspilot.submission_history import read_submission_history" in api_insertions[0]["body"],
              "Submission history no longer uses the native lazy import")
        proof["api_before"] = pin(old_api)
        proof["api_method_bodies_unchanged"] = {name: pin(body) for name, body in prior_methods.items()}
        proof["api_added_body"] = pin(current_methods["submission_history"])
        proof["api_only_insertion"] = api_insertions
        check(result["source_before"]["src/canvaspilot/feedback_export.py"]["sha256"] ==
              "a0db41dca9cce28c9fb7594c88ea6dc103b0f3104d5ba4d061bd93aaed92a714",
              "Formatter changed")
        result["preservation"] = proof
        (args.output / "source-preservation.json").write_bytes(pretty(proof))

        support_file = args.support / "receiving_support.py"
        support_pin = pin(support_file.read_bytes())
        check(support_pin["sha256"] == "27b2851617939bdce42549cb5a0de2e663f66b7ceea6ee53e6ff24b88ec6089b",
              "Existing native transport/HTML consumer changed")
        spec = importlib.util.spec_from_file_location("receiving_support", support_file)
        support = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = support
        spec.loader.exec_module(support)
        result["support"] = support_pin
        prior_index_path = args.prior_receiving / "receiving-capsule-index.json"
        prior_index = json.loads(prior_index_path.read_bytes())
        prior_encoded = (args.prior_receiving / "receiving-capsule.tar.gz.base64").read_bytes()
        check(pin(prior_encoded) == prior_index["archive"]["encoded"], "Prior receiving capsule changed")
        compressed = base64.b64decode(prior_encoded)
        check(pin(compressed) == prior_index["archive"]["compressed"], "Prior compressed capsule changed")
        with tarfile.open(fileobj=io.BytesIO(gzip.decompress(compressed)), mode="r:") as archive:
            previous_html = archive.extractfile("normal/feedback.html").read()
        check(pin(previous_html) == prior_index["files"]["normal/feedback.html"],
              "Retained actual0d HTML differs from its verified member")
        check(pin(previous_html)["sha256"] == "cde044dccf276552199e12c332c00b4c78b501ef876f948e72ec7627fd2b743d",
              "Unexpected previous HTML")
        prior_json_raw = args.prior_json.read_bytes()
        check(pin(prior_json_raw)["sha256"] == "dea6f42dc3260a05bb634453adfb8904ed2349a893a579f81233e656a4e8f323",
              "Retained feedback JSON control changed")
        expected_json = json.loads(prior_json_raw)["stdout"]
        (args.output / "prior-actual0d-export.html").write_bytes(previous_html)
        (args.output / "prior-feedback-stdout.json").write_bytes(expected_json.encode())
        result["previous_html"] = pin(previous_html)
        result["previous_json_receipt"] = pin(prior_json_raw)
        result["previous_capsule"] = pin(prior_encoded)
        assignment, submission = support.authored_feedback()
        export_path = args.output / "feedback.html"
        with support.LocalCanvas(assignment, submission, args.output / "wire") as local:
            current_json = local.cli(args.source, "feedback")
            exported = local.cli(args.source, "export-feedback", out=export_path)
        result["commands"] = local.commands
        result["requests"] = local.requests
        check(len(local.commands) == 2 and all(c["returncode"] == 0 for c in local.commands),
              "An actual current CLI command failed")
        check(len(local.requests) == 4 and
              [r["path"] for r in local.requests] == [support.ASSIGNMENT_PATH, support.SUBMISSION_PATH] * 2,
              "Expected two existing GET routes per command")
        check(all(r["method"] == "GET" and r["synthetic_authorization_matches"] for r in local.requests),
              "Unexpected method or fixture authentication")
        check(current_json["stdout"] == expected_json, "Existing feedback JSON output changed byte-for-byte")
        received_json = json.loads(current_json["stdout"])
        check(received_json["submission"]["score"] == 0 and received_json["submission"]["missing"] is None,
              "Zero and absent feedback values changed")
        raw = export_path.read_bytes()
        receipt = json.loads(exported["stdout"])
        check(receipt["ok"] is True and receipt["sha256"] == pin(raw)["sha256"],
              "Actual exported-file receipt does not match its bytes")
        old_doc, new_doc = support.OfflineDocument(previous_html), support.OfflineDocument(raw)
        old_fields, new_fields = old_doc.fields(), new_doc.fields()
        old_stamp, new_stamp = old_fields.pop("captured_at"), new_fields.pop("captured_at")
        check(old_fields == new_fields, "Existing feedback semantic fields changed")
        check(old_doc.text().count(old_stamp) == new_doc.text().count(new_stamp) == 1,
              "Ambiguous capture-time normalization")
        check(previous_html.count(old_stamp.encode()) == raw.count(new_stamp.encode()) == 1,
              "Capture time must occupy one exact native HTML field")
        check(previous_html.replace(old_stamp.encode(), b"[capture-time]") ==
              raw.replace(new_stamp.encode(), b"[capture-time]"),
              "HTML bytes changed outside their actual capture-time field")
        check(old_doc.tables() == new_doc.tables(), "Ordered rubric/comment tables changed")
        check(not new_doc.elements("script"), "Literal comment text became a script element")
        check(new_fields["submission.score"] == "0" and new_fields["submission.missing"] == "Not returned",
              "Export zero/unknown presentation changed")
        result.update(status="passed", actual_cli_processes=2, actual_loopback_GETs=4, actual_html_files=1,
                      feedback_json_byte_identical=True, html_byte_identical_except_unique_capture_time=True,
                      actual_export=pin(raw), imported_history_behavior_tested=False)
    except Exception:
        result["status"] = "failed"
        result["error"] = traceback.format_exc()
    finally:
        try:
            result["source_after"] = source_pins()
            check(result["source_before"] == result["source_after"], "Native source changed during receiving")
        except Exception:
            result["status"] = "failed"
            result["source_error"] = traceback.format_exc()
        result["elapsed_seconds"] = time.monotonic() - started
        (args.output / "result.json").write_bytes(pretty(result))
        print(json.dumps({key: result.get(key) for key in ["status", "mode", "actual_cli_processes",
            "actual_loopback_GETs", "actual_html_files", "feedback_json_byte_identical",
            "html_byte_identical_except_unique_capture_time", "elapsed_seconds", "error", "source_error"]}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
