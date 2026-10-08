from __future__ import annotations
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(r"D:\Hamon\worktrees\canvaspilot-history-0378a7b6")
PROOF = Path(r"D:\Hamon\worktrees\canvaspilot-history-0378a7b6-proof")
SOURCE = ROOT / "src/canvaspilot/submission_history_export.py"
HTML = PROOF / "candidate/submission-history.html"
EXPECTED = PROOF / "candidate/expected-normalized-report.json"
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
expected_source = sys.argv[1]
assert sha(SOURCE) == expected_source, "Source pin changed before receiving"
expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
# Establish the independent receiving fixture's important distinctions first.
assert expected["current_submission"]["attempt"] == 4
assert expected["current_submission"]["grade_matches_current_submission"] is False
records = expected["history"]["records"]
assert [r.get("attempt") for r in records] == [2, 1, 2, None]
assert records[0]["score"] == 0 and records[1]["score"] is None
assert "score" not in records[2] and records[3] == {}
assert len(expected["submission_comments"]) == 2

class Element:
    def __init__(self, tag, attrs):
        self.tag, self.attrs, self.children = tag, dict(attrs), []
    def text(self):
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)
    def descendants(self):
        for c in self.children:
            if isinstance(c, Element):
                yield c
                yield from c.descendants()

class Document(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("document", [])
        self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        self.stack[-1].children.append(element)
        if tag not in self.VOID:
            self.stack.append(element)
    def handle_endtag(self, tag):
        assert self.stack[-1].tag == tag, ("Unexpected HTML nesting", tag, self.stack[-1].tag)
        self.stack.pop()
    def handle_data(self, data):
        self.stack[-1].children.append(data)

doc = Document()
html_bytes = HTML.read_bytes()
doc.feed(html_bytes.decode("utf-8"))
doc.close()
assert len(doc.stack) == 1
elements = list(doc.root.descendants())
ids = [e.attrs["id"] for e in elements if "id" in e.attrs]
assert len(ids) == len(set(ids)), "Duplicate report id"
by_id = {e.attrs["id"]: e for e in elements if "id" in e.attrs}
download = by_id["download-history"]
prefix = "data:application/json;base64,"
assert download.tag == "a" and download.attrs["download"] == "submission-history.json"
assert download.attrs["href"].startswith(prefix)
payload = base64.b64decode(download.attrs["href"][len(prefix):], validate=True)
assert json.loads(payload) == expected
assert by_id["json-sha256"].text() == hashlib.sha256(payload).hexdigest()
assert "does not match the latest submission" in by_id["current-grade-context"].text()

def visible_fields(identifier, wanted):
    parent = by_id[identifier]
    fields = [e for e in parent.descendants() if e.tag == "div" and "field" in e.attrs.get("class", "").split()]
    found = {}
    keys = []
    for field in fields:
        dt = [e for e in field.children if isinstance(e, Element) and e.tag == "dt"]
        dd = [e for e in field.children if isinstance(e, Element) and e.tag == "dd"]
        assert len(dt) == len(dd) == 1
        key = json.loads(dt[0].text())
        assert key not in found
        found[key] = json.loads(dd[0].text())
        keys.append(key)
    assert keys == list(wanted), (identifier, "field order", keys, list(wanted))
    assert found == wanted, (identifier, "field values")
    return len(fields)

field_count = visible_fields("assignment-record", expected["assignment"])
field_count += visible_fields("current-record", expected["current_submission"])
for index, record in enumerate(records, start=1):
    field_count += visible_fields(f"history-record-{index}", record)
for index, comment in enumerate(expected["submission_comments"], start=1):
    field_count += visible_fields(f"top-comment-{index}", comment)
assert len([e for e in elements if "history-record" in e.attrs.get("class", "").split()]) == 4
assert len([e for e in elements if "top-comment" in e.attrs.get("class", "").split()]) == 2
active = {"script", "img", "iframe", "object", "embed", "form", "audio", "video", "link", "base", "input", "button", "source"}
assert not [e.tag for e in elements if e.tag in active]
for element in elements:
    assert not any(k.startswith("on") for k in element.attrs)
    assert "src" not in element.attrs
    if "href" in element.attrs:
        href = element.attrs["href"]
        assert href.startswith("#") or element is download
for style in [e for e in elements if e.tag == "style"]:
    assert "url(" not in style.text().lower() and "@import" not in style.text().lower()
assert sha(SOURCE) == expected_source, "Source pin changed during receiving"

receipt = {
    "status": "pass", "recorded_at": datetime.now(timezone.utc).isoformat(),
    "reviewer": "chatgpt-0378a7b6b7c2/root", "python": sys.version,
    "source_sha256": expected_source, "html_sha256": hashlib.sha256(html_bytes).hexdigest(),
    "expected_normalized_report_sha256": sha(EXPECTED),
    "downloaded_json_sha256": hashlib.sha256(payload).hexdigest(),
    "visible_fields_read_back": field_count, "history_records_in_returned_order": 4,
    "top_level_comments": 2, "current_attempt": 4,
    "checks": [
        "Embedded downloadable JSON equals the complete independent normalized reader fixture",
        "Digest matches the exact decoded JSON bytes",
        "Every visible assignment, current, history and top-level comment field re-admits to its original JSON value in order",
        "Duplicate attempt 2, out-of-order attempt 1, absent attempt, zero, null, missing score and empty record remain distinct",
        "Literal HTML, URLs, control characters and Unicode remain data",
        "Current mismatched-grade context makes no historical-attempt assignment",
        "No active HTML, network resource or event handler is present"
    ],
    "scope": "Independent bounded readback of the actual CLI-produced artifact; native browser and complete project gates are recorded separately by its implementation worker."
}
out = PROOF / ("root-independent-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
out.mkdir(exist_ok=False)
(out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"receipt": str(out / "receipt.json"), **receipt}, indent=2))
