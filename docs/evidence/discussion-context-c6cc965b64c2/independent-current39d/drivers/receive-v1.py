"""Independent Canvas discussion receiving; synthetic loopback only.
Target: current39d source export. No author source or tests are modified.
Each run owns one transient /dev namespace and exports its evidence before exit.
"""
from __future__ import annotations
import asyncio, copy, hashlib, importlib.metadata, io, json, logging, os, pathlib, platform
import subprocess, sys, tempfile, threading, time, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = pathlib.Path("/dev/shm/c6cc965b64c2-canvas-discussion/candidate-current39d")
PYTHON = "/workspace/scratch/20b27c2ea29e/workers/runtime-integration/product-discovery/canvaspilot/venv/bin/python"
PINS = json.loads("[{\"path\":\".github/workflows/ci.yml\",\"bytes\":708,\"sha256\":\"62f17b95af03d1ff8a172f168282b405fefcab3a5f1094c70e618b44920bd0ff\",\"git_blob\":\"ef7bbebe192c0db55dc4467e064ba44805c13446\"},{\"path\":\"README.md\",\"bytes\":20850,\"sha256\":\"0f22033f2c14c519e45fdb74c9a0894b306a90c0929f78730fca5f05f926bf30\",\"git_blob\":\"ad90e2ec17a3d2525f5f8ab89b7179a97d5cc493\"},{\"path\":\"docs/DISCUSSIONS.md\",\"bytes\":5645,\"sha256\":\"b1f82d30fd9c275fc73f2dc86298849f881eec7e1d4d510c1d5e80565483490e\",\"git_blob\":\"cbeab4607f322872351733639694890768a4521e\"},{\"path\":\"pyproject.toml\",\"bytes\":1353,\"sha256\":\"555ad3c7e338d38ae5feabc06c0c07503f22d9c732a9af153c7706c63d2b3c63\",\"git_blob\":\"76eba6d30696b4f2733539cd47df6e178bc0f585\"},{\"path\":\"scripts/inventory_pass.py\",\"bytes\":10515,\"sha256\":\"b2669747165f47b023f666bbb01657f47427d680ea8ff8cbf35203353ba05d06\",\"git_blob\":\"dda42bf3ac3679bc1936917ab1f981a8c6849811\"},{\"path\":\"scripts/readonly_sweep.py\",\"bytes\":5828,\"sha256\":\"30667032bc21a62db780d07bfbf0b48cc6c4aca63e9ea30a3953b78749603b06\",\"git_blob\":\"c273fdbcc495c5283422bcb7ee94664eb9a32230\"},{\"path\":\"src/canvaspilot/__init__.py\",\"bytes\":561,\"sha256\":\"377812a8bf90d26e31b2c8a159724e366642b90931ae761dec5d93abbfe852c5\",\"git_blob\":\"74a7a6087bf81fd7c75c15769b30408039618e0f\"},{\"path\":\"src/canvaspilot/api.py\",\"bytes\":28669,\"sha256\":\"1760e4ef1060dbf932e1d55d427e8ce57446e24cbebba0760df3fc4b4bf5b055\",\"git_blob\":\"55a9b7c9d4d01c8c6a2447ae952b79d8ceed7c0d\"},{\"path\":\"src/canvaspilot/assignment_submission.py\",\"bytes\":1296,\"sha256\":\"52fc732660b8844a2ee0801931a363f20db15b5309d148d01e3b618be487133d\",\"git_blob\":\"95b1f19927e4eecf99fc852325737c3cfe86cd0d\"},{\"path\":\"src/canvaspilot/bundle.py\",\"bytes\":2706,\"sha256\":\"43b5eb431f4d785e7e2561310a2f0ef5b8af15edfbd6594136182d54f53d753a\",\"git_blob\":\"cebeaa98440d745bb8f6bc3ae3ddf0d6cc1b83a8\"},{\"path\":\"src/canvaspilot/calendar_export.py\",\"bytes\":9950,\"sha256\":\"b92948c438063438bf9b8ef01b0b0c067802ddb06354f00e8ee18749f3c5e2fa\",\"git_blob\":\"ef74cfdf50fd894327dbe45a9a9d43042953bc31\"},{\"path\":\"src/canvaspilot/cli.py\",\"bytes\":15261,\"sha256\":\"1787673902c05df2dc826fe937efb956df9342d982f6f54bfaaa0f3144b5625f\",\"git_blob\":\"c4189865182af0d923a00166730cee575d541423\"},{\"path\":\"src/canvaspilot/client.py\",\"bytes\":18934,\"sha256\":\"d3473b7805908c15b276689abff9dd0dbd8d428e8691d557a26a5b2285444797\",\"git_blob\":\"1db4b1135305f7e410025ae7937f9a6cd349f020\"},{\"path\":\"src/canvaspilot/discussion_thread.py\",\"bytes\":8547,\"sha256\":\"11f955f827c29421143782518a1aaf1894d0892739c3b56c4d5e413da74555ff\",\"git_blob\":\"2ed658fcf5cee996a02115742935716f1d039e25\"},{\"path\":\"src/canvaspilot/feedback.py\",\"bytes\":3900,\"sha256\":\"55454598effea598474a21f67e36d5bc5bea84aaefeefc18e4d8c49804ab9869\",\"git_blob\":\"ec996f421a851d699a9ac7cb1f2a486f9ff7c4ea\"},{\"path\":\"src/canvaspilot/folder_browser.py\",\"bytes\":6293,\"sha256\":\"c6a67229b268c539e5edb581e3320b06229460adc3fbc01d72e4964e31c0348a\",\"git_blob\":\"4b3078ddb00a4a34015710e49fa7b7806adebd23\"},{\"path\":\"src/canvaspilot/mcp_server.py\",\"bytes\":14104,\"sha256\":\"69437b00220b81e0d933b5bd01e16800c0ad880799dff8104d407031d94b33d1\",\"git_blob\":\"51b203262db2d853e185385bb63c05bc484d60c5\"},{\"path\":\"src/canvaspilot/module_progress.py\",\"bytes\":9615,\"sha256\":\"974ee31925514a2e53b899888302a7fa357e280ab5f2461b754b814473653d99\",\"git_blob\":\"a9d3e4bbea22067f76110f03a5f31a5bc9d8de05\"},{\"path\":\"src/canvaspilot/offline_demo.py\",\"bytes\":4124,\"sha256\":\"2389f3ccc1b6db5995be0d90e014ea9345e3029aa5546a5b2dcf12c1197e6d4d\",\"git_blob\":\"9d2cfd260d8db052b8183e3ec4fc9626a5bb2b9a\"},{\"path\":\"src/canvaspilot/session_broker.py\",\"bytes\":13944,\"sha256\":\"a692cd2812cbc09536f1b60c84892bc8e87d2ae984c5a5aa25a13f6537ba6da2\",\"git_blob\":\"cc706d5860489ec37cb2cf7f0b1cb4eee33b664f\"},{\"path\":\"src/canvaspilot/submission_history.py\",\"bytes\":2853,\"sha256\":\"b007234b9861a68504e36f005ae463943b36b5cd50a3d157532c1cab09fcf9da\",\"git_blob\":\"9e71a0dc944bee71b0b5c61d7ff84cbb59119e1a\"},{\"path\":\"tests/fixtures/assignment_rubric.json\",\"bytes\":2057,\"sha256\":\"1c7eebf96e3a09b40b934fab219e9c8b7a6258fe881560f53a1c38a8e1b4bc4b\",\"git_blob\":\"8298dc92458b2f4c0f5c2b6845e32c52395d9d46\"},{\"path\":\"tests/fixtures/submission_feedback.json\",\"bytes\":2380,\"sha256\":\"435038bef1e6147eb60f60a2269de49df8bfa2fea31736694a7ada4cddfeb95a\",\"git_blob\":\"445d73ea1bf1db0b8bbbaeceaa3fb0b675f1ecdd\"},{\"path\":\"tests/folder_http_fixture.py\",\"bytes\":7440,\"sha256\":\"c7e29a633e66020b9440bbff54ee636889a022fc5a92d4ee2dae193314d72944\",\"git_blob\":\"454a761a6557daad73234b2f5801839a7db460a2\"},{\"path\":\"tests/module_progress_fixture.py\",\"bytes\":5185,\"sha256\":\"d7c724cd5147ff03321247728d99af19039e05d4a4d56d32feaa4303d68260b9\",\"git_blob\":\"cde6154c03f5987a31e30f3cefaeb97247fd0198\"},{\"path\":\"tests/test_announcements_pagination.py\",\"bytes\":7414,\"sha256\":\"da3393b733f4cc141bfe6ae1c3f3933398519b4ecd77f0ad44017b10a3b48064\",\"git_blob\":\"1765082a32c2ba35c25e68614a57aaeef4528c15\"},{\"path\":\"tests/test_assignment_brief_rubric.py\",\"bytes\":9514,\"sha256\":\"cc4bdb56034b32e08a63d4b1ae193e364bfc9b9b4b2a506cf2ef08f43000158c\",\"git_blob\":\"1881a19e593c4fb095d1a4dc97fce53a8c13f02e\"},{\"path\":\"tests/test_assignment_submission.py\",\"bytes\":9989,\"sha256\":\"ccf038f9e1fb0bd6c8658041d88bf90d11404ef32baeff3e937b2b514a44e4a5\",\"git_blob\":\"5a5b14e207a85b414e973508bcbc8c94558d2479\"},{\"path\":\"tests/test_assignment_submission_process.py\",\"bytes\":15931,\"sha256\":\"6cb60d1ffe02875999ef54ac8770984086b760afbc43ac10aa43fd3139820935\",\"git_blob\":\"41c5efc672cd1154c278609c773e5deff003ec08\"},{\"path\":\"tests/test_broker_encoding.py\",\"bytes\":7384,\"sha256\":\"1fd19dd35025c9201b2349f565c25932b7f3cd6cc0eff8259eddb0fdc2046b09\",\"git_blob\":\"511618760341a2e011c1334c3e49b1b7219ccff0\"},{\"path\":\"tests/test_broker_link_metadata_receiving.py\",\"bytes\":4080,\"sha256\":\"5b92def5254d9a00a73f6e268903b367664763d440bbfafd3861a570ce2c3ace\",\"git_blob\":\"c43c91f24adebfeafcc8f291427050aca20f8a88\"},{\"path\":\"tests/test_broker_links.py\",\"bytes\":11929,\"sha256\":\"a65ea84914e8afe13bdf2c88c9a6107fbc448ed46f00db50ae1d92f5de427028\",\"git_blob\":\"2485e980951cb76b39a43d0032631c28891bf0f8\"},{\"path\":\"tests/test_broker_loopback_bind.py\",\"bytes\":3327,\"sha256\":\"c889696ea86f73f0aa00b1b86f623855c92cd6eccef6b7764910e0df99b5c9e5\",\"git_blob\":\"fd8971cefe9da9bb8f7832d81c9a26c5725eda86\"},{\"path\":\"tests/test_broker_provider_routing.py\",\"bytes\":4087,\"sha256\":\"b3b896259c9c0c264988bfe532a66c3ffe4f36033e28597b25367fa76c5c865f\",\"git_blob\":\"7fc17ef832057d1090f742a0c3c85f0d67e80752\"},{\"path\":\"tests/test_broker_readonly.py\",\"bytes\":4746,\"sha256\":\"fd9baae5e8f176636eb5377fee753facd87c136416dcc2e3ec252090aad9d6c5\",\"git_blob\":\"fa609760903148b6d55623e6e3b79f6ffd3395b0\"},{\"path\":\"tests/test_browser_link_metadata.py\",\"bytes\":6870,\"sha256\":\"e7bb134adebdaaf9fda596f79b853d0c42bd42ff9aafb4958c1e07a6a0de90d3\",\"git_blob\":\"5f13caea0f3ad5a8d2e8b0aa7bae12c2ae59dec4\"},{\"path\":\"tests/test_bundle_api.py\",\"bytes\":1657,\"sha256\":\"a3c200027083582815bcdacf8b19f68a2a7f2b10597e4ae3270c819c54639615\",\"git_blob\":\"d42f4cca2f1f08203d831f098aa1d9f82d3d9f78\"},{\"path\":\"tests/test_calendar_export.py\",\"bytes\":11534,\"sha256\":\"0774869f562ab1bdff8d09df38216fab7cc44543ded02be620c2a4e5e3a9e17f\",\"git_blob\":\"b6e926ab14ef4320ceeb23d174fc62399e2356a7\"},{\"path\":\"tests/test_calendar_pagination_errors.py\",\"bytes\":2360,\"sha256\":\"f3738ecd6addd7cd877de90746c0a9e5c64845a2c3a7e8617ad0d3ca4bc4c8a6\",\"git_blob\":\"60df1b66987c0e1dc9027593d2d06710ee4a6b88\"},{\"path\":\"tests/test_calendar_session_identity.py\",\"bytes\":6647,\"sha256\":\"54571e3486e670669a19ac5fa1c10c46136435773487f5b566752bd5ef1e5605\",\"git_blob\":\"fcad9a69739aa859f399ed0c37712fa10bf3f7c6\"},{\"path\":\"tests/test_discussion_thread.py\",\"bytes\":13887,\"sha256\":\"22274853b6dfa5f377f9d42b7d9da9fabcf42ac2fdb1248285725148f7f84698\",\"git_blob\":\"47cc390773c5e1f8a9d8c0297fad1f43cbcc7b7b\"},{\"path\":\"tests/test_discussion_thread_native.py\",\"bytes\":13404,\"sha256\":\"2793e3f3a09c031e99aa735b487f324fb828671691320bca8481465fc7fccc5b\",\"git_blob\":\"8dd33f687ead0529d436be371d5d3c5ac446fca3\"},{\"path\":\"tests/test_fixture.py\",\"bytes\":1497,\"sha256\":\"3f53176abf7ee425b1ff8d62a0e4b7f84d2e47e0b0ff9f03adae152301bc23be\",\"git_blob\":\"fbee86133431fbe2b1eabaa598f8de094fc18b0c\"},{\"path\":\"tests/test_folder_browser.py\",\"bytes\":12027,\"sha256\":\"4068912fe7d32953c576b1278c28c47c3697592e6a194a230400be13b9cae95c\",\"git_blob\":\"f2aacab375da0976bcbbb3d50f0231a1db54eeb7\"},{\"path\":\"tests/test_legacy_metadata_policy.py\",\"bytes\":1223,\"sha256\":\"9e66b4a135ab4cb70123aad962bec5afb8a18bebe82b7063d39055521235ea93\",\"git_blob\":\"a46b5faa10c69dd4a3fa76543d95623cc05db779\"},{\"path\":\"tests/test_link_context_receiving.py\",\"bytes\":3901,\"sha256\":\"54c35e25c55e9c19b24f35680bcb2c4aa22e191f197b3894e26de1c730895d6f\",\"git_blob\":\"f0c2fbd048c182075f06fb92e2bb457673f4b8b4\"},{\"path\":\"tests/test_module_items.py\",\"bytes\":10342,\"sha256\":\"fd70a1a0f1e880c9c9075633ece8d83a710a47136e102ad675dce55bc844aad6\",\"git_blob\":\"8390e2d8cd6027ee0ba6d7f64d5163b455ae2e7d\"},{\"path\":\"tests/test_module_progress.py\",\"bytes\":9506,\"sha256\":\"bdbcf205666ede901fd012764cf009dd90611c1a18089c2e6ce13b242ed081c2\",\"git_blob\":\"97857eb7723ac9460cb38d791d883df9ddc4a449\"},{\"path\":\"tests/test_module_progress_process.py\",\"bytes\":12181,\"sha256\":\"21187c11a7bca557a8b37c0d61933e3532c8c69e628bd618fa62361e0f713826\",\"git_blob\":\"e80d30bbd87a16dc469c9bc3409eb2be24a24307\"},{\"path\":\"tests/test_offline_demo.py\",\"bytes\":2226,\"sha256\":\"ddc7a133e76f987decb5774b00e6d6c6b8973d5895d6c4a4ae5ea6d6e6bb1154\",\"git_blob\":\"96b0f352f9c8dfe4c268c32ddbf0027506a010e2\"},{\"path\":\"tests/test_strip_html.py\",\"bytes\":1493,\"sha256\":\"3445579d5d8e0863e3331fd8fe54de7a45bc88db5546186eb60dc70865dce915\",\"git_blob\":\"9cac253f89820d36375b364daec9b34bb2d78e25\"},{\"path\":\"tests/test_submission_feedback.py\",\"bytes\":6891,\"sha256\":\"d6669be101562d6d2c88e5e0a6a468f6c82d614960bee65cb294243ebf136be7\",\"git_blob\":\"0d747c4866ddc87e77ed84caad877414c7be329b\"},{\"path\":\"tests/test_submission_feedback_native.py\",\"bytes\":9410,\"sha256\":\"8ad68b80e63d2d448c2b1b9e8821bb6ebf47adc0b5e1ccc9379633bb9495d5fb\",\"git_blob\":\"bb5bce648386995732b08c098fb5d4249f6bc0c8\"},{\"path\":\"tests/test_submission_history.py\",\"bytes\":8309,\"sha256\":\"a21d440d0a2228972e3d7d6ba1ae85a8b102fdb61319f7b153e37c084cfaea46\",\"git_blob\":\"70cf93168d1f20519b241a4c3493ebdad501ffb3\"},{\"path\":\"tests/test_submission_history_process.py\",\"bytes\":10880,\"sha256\":\"256bd51e89832be07bab255aeb69fd0bda234fc078e0f89d049463da92950407\",\"git_blob\":\"9f05811f742ef7278b1db4216f05b85fe6240a60\"},{\"path\":\"tests/test_sync_summary.py\",\"bytes\":10415,\"sha256\":\"5e40e9207a53d423a139db7de9d43898cf95e26877f351baf15bdc129206a424\",\"git_blob\":\"f15e781cd0580324c668bec4181ed238b9cacb29\"},{\"path\":\"tests/test_terminal_page_shape_receiving.py\",\"bytes\":2146,\"sha256\":\"86d8d4e3556aa436b2eaf8021e67073bdfc44cac4c202791a1bb8608ff53280e\",\"git_blob\":\"f4b3ddae987eb1db7894a4d17e8aa00234628937\"},{\"path\":\"tests/test_token_collection_receiving.py\",\"bytes\":3154,\"sha256\":\"7ea5e0d80612a532cbe9829851e9c8c065a33f3b2d4a69a871142d46324faa3e\",\"git_blob\":\"b2f9066fe93269ae361e70f618507ce5990c122b\"},{\"path\":\"tests/test_token_pagination.py\",\"bytes\":8749,\"sha256\":\"7845205886f73ab3e8efdb783733a27be6e076c313089689117e5ed612e7923a\",\"git_blob\":\"5986acbe9315fce95c0dee02305c12d5090b83a1\"}]")
BASE = "39d835c8becb04d81b65c90d1491d2d3a2727ffe"
BIG = 9007199254741009
COURSE, TOPIC_ID = "017", "00019"
TOPIC_PATH = f"/api/v1/courses/{COURSE}/discussion_topics/{TOPIC_ID}"
VIEW_PATH = TOPIC_PATH + "/view"
FAKE_TOKEN = "fixture"
TOPIC = {
    "id": 19, "title": "Independent cached view boundary", "message": "<p>Boundary &amp; context</p>",
    "discussion_subentry_count": 904, "unread_count": 8, "locked": False,
    "opaque": {"empty": [], "flag": True, "large": BIG},
}
VIEW = {
    "participants": [
        {"id": 5, "display_name": "Numeric author", "opaque": {"tag": "n"}},
        {"id": "5", "display_name": "String author", "opaque": {"tag": "s"}},
        {"id": 6, "display_name": "Duplicate one"},
        {"id": 6, "display_name": "Duplicate two"},
        {"id": True, "display_name": "Boolean is not an ID"},
        {"display_name": "Missing ID"},
    ],
    "unread_entries": [BIG, "100", 404404, 404404],
    "forced_entries": [100, BIG, 201],
    "new_entries": [{"id": BIG, "parent_id": 100, "message": "A newer flat version; do not merge"}],
    "opaque_view": {"cached_generation": "independent-v1", "ratings": {"100": 4}},
    "view": [
        {"id": 100, "user_id": 5, "message": "<p>Root &amp; anchor</p>", "read_state": "unread",
         "parent_id": None, "opaque": {"unknown": [1, "2"]}, "replies": [
            {"id": 101, "deleted": True, "user_id": 6, "message": "Retain this raw deleted field", "replies": [
                {"id": BIG, "user_id": "5", "parent_id": 9999, "message": "<p>境界 &amp; résumé</p>", "replies": []},
                {"id": None, "user_id": 5, "message": {"media": "no invented text"}},
            ]},
            {"id": 102, "user_id": 5, "read_state": "unread", "message": "", "replies": []},
         ]},
        {"id": "100", "user_id": 6, "message": "Typed root"},
        {"id": 200, "forced_read_state": False, "message": "Duplicate children", "replies": [
            {"id": 201, "message": "First occurrence"},
            {"id": 201, "message": "Second occurrence"},
        ]},
        {"user_id": True, "attachment": {"url": "/synthetic/media", "size": 0}},
    ],
}
PATHS = [[0], [0,0], [0,0,0], [0,0,1], [0,1], [1], [2], [2,0], [2,1], [3]]
FOCUS_PATHS = [[0], [0,0], [0,0,0], [1]]

def jbytes(x):
    return (json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
def digest(b):
    return hashlib.sha256(b).hexdigest()
def pin_source():
    observed = []
    for p in PINS:
        data = (ROOT / p["path"]).read_bytes()
        row = {"path": p["path"], "bytes": len(data), "sha256": digest(data),
               "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}
        assert row == p, ("source pin mismatch", p["path"], row)
        observed.append(row)
    files = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file()}
    assert files == {p["path"] for p in PINS}, ("unexpected source tree entries", files)
    return observed

temp = pathlib.Path(tempfile.mkdtemp(prefix="c6cc965b64c2-canvas-independent-", dir="/dev"))
stderr_parent = io.StringIO()
logging.basicConfig(stream=stderr_parent, level=logging.WARNING, force=True)
artifacts = {}
receipt = {"schema": "canvas-discussion-independent-current39d-v1",
           "base_commit": BASE, "source_root": str(ROOT), "runtime": PYTHON,
           "python_version": platform.python_version(),
           "dependencies": {x: importlib.metadata.version(x) for x in ["httpx", "mcp", "pydantic"]},
           "temporary_root": str(temp), "started_unix": time.time(), "groups": [],
           "scope": "Synthetic loopback consumer receiving; no live Canvas, browser, deployment or author-source writes."}
records = []
processes = []
active = {"group": "setup", "case": "setup"}
state = {"topic": copy.deepcopy(TOPIC), "view": copy.deepcopy(VIEW), "topic_spec": None,
         "view_spec": None, "broker_error": None, "health_status": 200}
source_before = pin_source()
receipt["source_before"] = source_before

def reset():
    state.update(topic=copy.deepcopy(TOPIC), view=copy.deepcopy(VIEW), topic_spec=None,
                 view_spec=None, broker_error=None, health_status=200)

def resource(path):
    p = urlsplit(path)
    assert parse_qs(p.query, keep_blank_values=True) == {"per_page": ["50"]}, ("unexpected query", path)
    if p.path == TOPIC_PATH:
        return "topic"
    if p.path == VIEW_PATH:
        return "view"
    raise AssertionError(("unexpected Canvas path", path))

def response_spec(path):
    key = resource(path)
    spec = state[key + "_spec"]
    if spec is None:
        return 200, "application/json", jbytes(state[key])
    return spec

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *args):
        pass
    def respond(self, status, ctype, data):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True
    def serve(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        row = {"index": len(records), "group": active["group"], "case": active["case"],
               "surface": self.server.surface, "wire_method": self.command,
               "path": self.path, "accept": self.headers.get("Accept"),
               "authorization": "fixture" if self.headers.get("Authorization") == "Bearer " + FAKE_TOKEN
                                else "absent" if not self.headers.get("Authorization") else "unexpected"}
        try:
            if self.server.surface == "token":
                assert self.command == "GET" and body == b"", "Canvas mutation attempted"
                assert row["authorization"] == "fixture", "wrong fixture authorization"
                status, ctype, data = response_spec(self.path)
                row["inner_canvas_method"] = "GET"
                row["inner_canvas_path"] = self.path
            elif self.command == "GET" and self.path == "/health":
                assert not body
                status, ctype = state["health_status"], "application/json"
                data = jbytes({"ok": status == 200, "base_url": token_url})
            elif self.command == "POST" and self.path == "/fetch":
                envelope = json.loads(body)
                row["envelope"] = envelope
                assert set(envelope) == {"op", "method", "path", "headers", "body"}
                assert envelope["op"] == "fetch" and envelope["method"] == "GET", "broker Canvas mutation attempted"
                assert envelope["body"] is None and envelope["headers"] == {"Accept": "application/json"}
                row["inner_canvas_method"] = envelope["method"]
                row["inner_canvas_path"] = envelope["path"]
                if state["broker_error"] is not None:
                    data = jbytes({"ok": False, "error": state["broker_error"]})
                else:
                    inner_status, inner_type, inner_data = response_spec(envelope["path"])
                    inner_json = json.loads(inner_data) if "json" in inner_type and inner_data else None
                    data = jbytes({"ok": True, "response": {"status": inner_status, "json": inner_json,
                                                          "text": inner_data.decode()}})
                status, ctype = 200, "application/json"
            else:
                raise AssertionError(("unexpected broker route", self.command, self.path))
            row.update(response_status=status, response_content_type=ctype,
                       response_bytes=len(data), response_sha256=digest(data))
        except BaseException as exc:
            row["receiver_error"] = repr(exc)
            status, ctype, data = 500, "application/json", jbytes({"receiver_error": repr(exc)})
        records.append(row)
        self.respond(status, ctype, data)
    do_GET = serve
    do_POST = serve
    do_PUT = serve
    do_DELETE = serve
    do_PATCH = serve
    do_HEAD = serve

token_server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
broker_server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
token_server.surface = "token"
broker_server.surface = "broker"
token_url = f"http://127.0.0.1:{token_server.server_port}"
for server in [token_server, broker_server]:
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
receipt["loopback"] = {"token": token_url, "broker_port": broker_server.server_port}
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["CANVAS_BASE_URL"] = token_url
os.environ["CANVAS_API_TOKEN"] = FAKE_TOKEN
os.environ["CANVAS_PROFILE"] = str(temp / "parent-profile-must-stay-absent")
os.environ["CANVAS_SESSION_PORT"] = str(broker_server.server_port)
os.environ["NO_PROXY"] = "127.0.0.1"
os.environ["no_proxy"] = "127.0.0.1"
sys.path.insert(0, str(ROOT / "src"))
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.discussion_thread import build_discussion_thread

def child_env(mode="token"):
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONPATH": str(ROOT / "src"),
            "PYTHONDONTWRITEBYTECODE": "1", "CANVAS_BASE_URL": token_url,
            "CANVAS_API_TOKEN": FAKE_TOKEN if mode == "token" else "",
            "CANVAS_PROFILE": str(temp / ("profile-" + mode + "-must-stay-absent")),
            "CANVAS_SESSION_PORT": str(broker_server.server_port),
            "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1",
            "HTTP_PROXY": "", "HTTPS_PROXY": "", "ALL_PROXY": "",
            "http_proxy": "", "https_proxy": "", "all_proxy": ""}

def keep(name, value):
    artifacts[name] = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False) + "\n"

def expect_error(fn, part):
    try:
        fn()
    except ValueError as exc:
        assert part.lower() in str(exc).lower(), (part, str(exc))
        return {"type": type(exc).__name__, "message": str(exc)}
    raise AssertionError("Expected ValueError: " + part)

def assert_full(result):
    assert result["topic"] == TOPIC
    assert result["topic_message_text"] == "Boundary & context"
    assert result["source"] == {"kind": "canvas_cached_discussion_view", "eventually_consistent": True,
                                "new_entries_requested": False}
    assert result["selection"] == "all"
    assert result["view_metadata"] == {k: v for k, v in VIEW.items() if k != "view"}
    rows = result["entries"]
    assert [r["path"] for r in rows] == PATHS
    assert [r["parent_path"] for r in rows] == [None, [0], [0,0], [0,0], [0], None, None, [2], [2], None]
    assert [r["read_state"] for r in rows] == ["read", "read", "unread", "unknown", "read", "unread", "read", "unknown", "unknown", "unknown"]
    assert [r["forced_read_state"] for r in rows] == [True, False, True, None, False, False, False, None, None, None]
    assert result["counts"] == {"observed_entries": 10, "returned_entries": 10,
                                "known_unread_entries": 2, "unknown_read_state_entries": 4}
    assert result["unmatched_unread_entries"] == [404404, 404404]
    assert all(r["context_only"] is False for r in rows)
    assert rows[0]["author"]["display_name"] == "Numeric author"
    assert rows[2]["author"]["display_name"] == "String author"
    assert rows[5]["author"] is None and rows[9]["author"] is None
    assert rows[1]["entry"]["message"] == "Retain this raw deleted field"
    assert rows[1]["message_text"] is None and rows[1]["author"] is None
    assert rows[3]["message_text"] is None and rows[9]["message_text"] is None
    assert rows[2]["message_text"] == "境界 & résumé"
    assert type(rows[2]["entry"]["id"]) is int and rows[2]["entry"]["id"] == BIG
    assert rows[2]["entry"]["parent_id"] == 9999 and rows[2]["parent_path"] == [0,0]
    assert type(rows[0]["entry"]["id"]) is int and type(rows[5]["entry"]["id"]) is str
    # A consumer rebuilds the exact source forest, without using entry IDs or parent_id.
    by_path = {}
    rebuilt = []
    for row in rows:
        node = copy.deepcopy(row["entry"])
        if row["replies_supplied"]:
            node["replies"] = []
        path = tuple(row["path"])
        if row["parent_path"] is None:
            assert len(rebuilt) == path[-1]
            rebuilt.append(node)
        else:
            parent = by_path[tuple(row["parent_path"])]
            assert len(parent["replies"]) == path[-1]
            parent["replies"].append(node)
        by_path[path] = node
    assert rebuilt == VIEW["view"]
    assert [r["reply_count"] for r in rows] == [2,2,0,0,0,0,2,0,0,0]
    assert [r["replies_supplied"] for r in rows] == [True,True,True,False,True,False,True,False,False,False]
    assert len(result["warnings"]) == 4

def assert_focus(result):
    assert result["selection"] == "unread_with_ancestors"
    assert [r["path"] for r in result["entries"]] == FOCUS_PATHS
    assert [r["context_only"] for r in result["entries"]] == [True, True, False, False]
    assert [r["read_state"] for r in result["entries"]] == ["read", "read", "unread", "unread"]
    assert result["counts"] == {"observed_entries": 10, "returned_entries": 4,
                                "known_unread_entries": 2, "unknown_read_state_entries": 4}
    assert result["topic"]["discussion_subentry_count"] == 904
    assert result["view_metadata"]["new_entries"] == VIEW["new_entries"]
    assert result["entries"][1]["entry"]["deleted"] is True
    assert result["entries"][1]["message_text"] is None
    assert result["unmatched_unread_entries"] == [404404, 404404]

def request_window(start, mode, expected):
    segment = records[start:]
    assert not any("receiver_error" in x for x in segment), segment
    if mode == "token":
        assert all(r["surface"] == "token" and r["wire_method"] == "GET" for r in segment)
        actual = [r["inner_canvas_path"] for r in segment]
        assert all(r["authorization"] == "fixture" for r in segment)
    else:
        assert all(r["surface"] == "broker" for r in segment), ("fallback escaped broker", segment)
        inner = [r for r in segment if r["path"] == "/fetch"]
        actual = [r["inner_canvas_path"] for r in inner]
        assert all(r["wire_method"] == "POST" and r["inner_canvas_method"] == "GET" for r in inner)
        assert all(r["authorization"] == "absent" for r in segment)
        assert [r["path"] for r in segment] == [p for _ in expected for p in ["/health", "/fetch"]], segment
    assert actual == [p + "?per_page=50" for p in expected], (actual, expected)
    return segment

def cli(case, *, mode="token", args=None, success=True, error=None, expected=None):
    active["case"] = case
    start = len(records)
    command = [PYTHON, "-B", "-m", "canvaspilot.cli", "discussion", COURSE, TOPIC_ID] + (args or [])
    cp = subprocess.run(command, cwd=temp, env=child_env(mode), capture_output=True, text=True, timeout=25)
    processes.append({"kind": "cli", "case": case, "mode": mode, "returncode": cp.returncode})
    keep("processes/" + case + ".json", {"command": command, "mode": mode, "returncode": cp.returncode,
        "stdout": cp.stdout, "stderr": cp.stderr, "http_start": start, "http_end": len(records)})
    if expected is not None:
        request_window(start, mode, expected)
    if success:
        assert cp.returncode == 0, (case, cp.returncode, cp.stderr)
        return json.loads(cp.stdout)
    assert cp.returncode == 1 and cp.stdout == "", (case, cp.returncode, cp.stdout, cp.stderr)
    lines = cp.stderr.strip().splitlines()
    body = json.loads(lines[-1])
    assert body["ok"] is False and body["error"] == error, (case, body)
    return body

def run_group(name, fn):
    active.update(group=name, case=name)
    start = len(records)
    began = time.monotonic()
    try:
        details = fn()
        group = {"name": name, "status": "passed", "details": details}
    except BaseException as exc:
        group = {"name": name, "status": "failed", "error": repr(exc), "traceback": traceback.format_exc()}
    group.update(http_start=start, http_end=len(records), seconds=round(time.monotonic()-began, 4))
    receipt["groups"].append(group)
    return group

def pure_forest():
    result = build_discussion_thread(copy.deepcopy(TOPIC), copy.deepcopy(VIEW))
    assert_full(result)
    keep("oracle/source-topic.json", TOPIC); keep("oracle/source-view.json", VIEW)
    keep("oracle/full-result.json", result)
    return {"reconstructed_source_exactly": True, "rows": 10, "large_id": BIG,
            "typed_ids_distinct": True, "separate_new_entries_preserved": True}
def pure_focus():
    result = build_discussion_thread(copy.deepcopy(TOPIC), copy.deepcopy(VIEW), unread_only=True)
    assert_focus(result); keep("oracle/focus-result.json", result)
    return {"paths": FOCUS_PATHS, "context_only": [True, True, False, False], "deleted_ancestor_retained": True}
def missing_and_ambiguous():
    result = []
    for shape in ["missing", "null", "empty", "unmatched", "ambiguous"]:
        view = copy.deepcopy(VIEW)
        if shape == "missing":
            view.pop("unread_entries")
        elif shape == "null":
            view["unread_entries"] = None
        elif shape == "empty":
            view["unread_entries"] = []
        elif shape == "unmatched":
            view["unread_entries"] = [404404, 404404]
        else:
            view["unread_entries"] = [201]
        full = build_discussion_thread(TOPIC, view)
        if shape in ["missing", "null"]:
            assert full["counts"]["known_unread_entries"] is None
            assert full["counts"]["unknown_read_state_entries"] == 10
            err = expect_error(lambda: build_discussion_thread(TOPIC, view, unread_only=True), "unavailable")
            result.append({"shape": shape, "refusal": err})
        elif shape == "ambiguous":
            assert [r["read_state"] for r in full["entries"] if r["entry"].get("id") == 201] == ["unknown", "unknown"]
            err = expect_error(lambda: build_discussion_thread(TOPIC, view, unread_only=True), "ambiguous")
            result.append({"shape": shape, "refusal": err})
        else:
            focus = build_discussion_thread(TOPIC, view, unread_only=True)
            assert focus["entries"] == [] and focus["counts"]["observed_entries"] == 10
            assert focus["unmatched_unread_entries"] == ([] if shape == "empty" else [404404,404404])
            result.append({"shape": shape, "focus": focus})
    topic, view = copy.deepcopy(TOPIC), copy.deepcopy(VIEW)
    before = copy.deepcopy((topic, view))
    report = build_discussion_thread(topic, view)
    report["topic"]["opaque"]["empty"].append("output mutation")
    report["view_metadata"]["participants"][0]["opaque"]["tag"] = "output"
    report["entries"][0]["entry"]["opaque"]["unknown"].append("output")
    report["entries"][0]["author"]["opaque"]["tag"] = "output"
    assert (topic, view) == before
    report2 = build_discussion_thread(topic, view)
    view["participants"][0]["opaque"]["tag"] = "input"
    view["view"][0]["opaque"]["unknown"].append("input")
    assert report2["entries"][0]["author"]["opaque"]["tag"] == "n"
    assert report2["entries"][0]["entry"]["opaque"]["unknown"] == [1,"2"]
    keep("oracle/unknown-and-ambiguity.json", result)
    return {"shape_cases": 5, "independent_input_output_mutability": True}
def api_validation_and_raw():
    reset()
    client = CanvasClient(base_url=token_url, token=FAKE_TOKEN, profile=temp/"api-profile", timeout=5)
    api = CanvasAPI(client)
    try:
        errors = []
        for course, topic, flag in [(True,19,False),(17,19,0),("017","19/../../",False),
                                   ("１７","19",False),(0,19,False),("17","0",False),(" 17","19",False)]:
            start = len(records)
            errors.append(expect_error(lambda: api.discussion_thread(course,topic,unread_only=flag), "must"))
            assert len(records) == start
        start = len(records)
        raw = api.get_discussion(COURSE, TOPIC_ID)
        assert raw == {"topic": TOPIC, "view": VIEW}
        request_window(start, "token", [TOPIC_PATH, VIEW_PATH])
        start = len(records)
        result = api.discussion_thread(COURSE, TOPIC_ID)
        assert_full(result)
        request_window(start, "token", [TOPIC_PATH, VIEW_PATH])
        keep("api/raw.json", raw)
        return {"local_invalid_inputs": len(errors), "no_invalid_input_http": True,
                "raw_api_exact": True, "leading_zero_paths_preserved": True}
    finally:
        api.close()
def api_recovery():
    reset()
    api = CanvasAPI(CanvasClient(base_url=token_url,token=FAKE_TOKEN,profile=temp/"api-recovery-profile",timeout=5))
    try:
        state["view"]["unread_entries"] = [201]
        start = len(records)
        failure = expect_error(lambda:api.discussion_thread(COURSE,TOPIC_ID,unread_only=True),"ambiguous")
        request_window(start,"token",[TOPIC_PATH,VIEW_PATH])
        reset()
        state["view"]["unread_entries"] = [102]
        start = len(records)
        result = api.discussion_thread(COURSE,TOPIC_ID,unread_only=True)
        assert [r["path"] for r in result["entries"]] == [[0],[0,1]]
        assert [r["context_only"] for r in result["entries"]] == [True,False]
        request_window(start,"token",[TOPIC_PATH,VIEW_PATH])
        keep("api/recovery.json",{"refusal":failure,"next_explicit_result":result})
        return {"same_api_client_recovered":True,"fresh_selected_paths":[[0],[0,1]],"implicit_retries":0}
    finally:
        api.close()
def cli_read():
    reset()
    all_result = cli("cli-full",expected=[TOPIC_PATH,VIEW_PATH]);assert_full(all_result)
    focus = cli("cli-focus",args=["--unread-only"],expected=[TOPIC_PATH,VIEW_PATH]);assert_focus(focus)
    return {"actual_cli_processes":2,"success_stdout_json":True,"read_and_forced_facts_separate":True}
def cli_first_refusal():
    results=[]
    for status in [401,403]:
        reset()
        state["topic_spec"] = (status,"application/json",jbytes({"error":"require_initial_post" if status==403 else "synthetic unauthorized"}))
        err=cli("cli-topic-"+str(status),success=False,error="CanvasAuthError",expected=[TOPIC_PATH])
        results.append({"status":status,"error":err})
    return {"topic_failures":results,"view_requests_after_refusal":0,"implicit_post_or_retry":0}
def cli_malformed_recovery():
    reset();state["topic_spec"]=(204,"application/json",b"")
    cli("cli-topic-empty204",success=False,error="ValueError",expected=[TOPIC_PATH,VIEW_PATH])
    reset();state["view_spec"]=(200,"text/html",b"<p>not a cached view</p>")
    cli("cli-view-html",success=False,error="ValueError",expected=[TOPIC_PATH,VIEW_PATH])
    reset();state["view_spec"]=(200,"application/json",b'{"view":')
    cli("cli-view-truncated-json",success=False,error="JSONDecodeError",expected=[TOPIC_PATH,VIEW_PATH])
    reset();result=cli("cli-after-malformed",args=["--unread-only"],expected=[TOPIC_PATH,VIEW_PATH]);assert_focus(result)
    return {"malformed_cases":3,"later_explicit_process_recovers":True,
            "raw_reader_fetches_both_before_shape_validation":True}
def broker_cli_read():
    reset()
    result=cli("broker-cli-full",mode="broker",expected=[TOPIC_PATH,VIEW_PATH]);assert_full(result)
    result=cli("broker-cli-focus",mode="broker",args=["--unread-only"],expected=[TOPIC_PATH,VIEW_PATH]);assert_focus(result)
    return {"outer_loopback_fetch":"POST","inner_canvas_operations":["GET","GET"],
            "token_endpoint_contacted":False,"profile_created":False}
def broker_errors_recovery():
    reset();state["broker_error"]="synthetic broker requires authentication"
    cli("broker-auth-refusal",mode="broker",success=False,error="CanvasAuthError",expected=[TOPIC_PATH])
    reset();state["view_spec"]=(503,"application/json",jbytes({"error":"synthetic unavailable cache"}))
    cli("broker-cache-503",mode="broker",success=False,error="HTTPStatusError",expected=[TOPIC_PATH,VIEW_PATH])
    reset();result=cli("broker-after-error",mode="broker",args=["--unread-only"],expected=[TOPIC_PATH,VIEW_PATH]);assert_focus(result)
    return {"broker_auth_and_native503_visible":True,"no_direct_http_fallback":True,"explicit_recovery":True}
def broker_health_unavailable():
    reset();state["health_status"]=503
    start=len(records)
    cli("broker-health-unavailable",mode="broker",success=False,error="CanvasAuthError")
    segment=records[start:]
    assert len(segment)==1 and segment[0]["surface"]=="broker" and segment[0]["path"]=="/health",segment
    assert not any(p.name.startswith("profile-") for p in temp.iterdir())
    return {"unavailable_health_requests":1,"canvas_requests":0,"browser_or_profile_start":False}

async def mcp_receive(mode):
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    reset()
    log_path=temp/("mcp-"+mode+"-stderr.log")
    params=StdioServerParameters(command=PYTHON,args=["-B","-m","canvaspilot.cli","mcp"],
                                env=child_env(mode),cwd=str(temp))
    calls=[]
    with log_path.open("w+",encoding="utf-8") as errlog:
        async with stdio_client(params,errlog=errlog) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                inventory=await session.list_tools()
                selected={t.name:t.model_dump(by_alias=True) for t in inventory.tools
                          if t.name in ["canvas_discussion_thread","canvas_get_discussion","canvas_post_discussion_reply"]}
                tool=selected["canvas_discussion_thread"]
                assert tool["annotations"]["readOnlyHint"] is True
                assert tool["annotations"]["destructiveHint"] is False
                assert tool["inputSchema"]["properties"]["unread_only"]["type"]=="boolean"
                assert tool["inputSchema"]["properties"]["course_id"]["type"]=="string"
                assert set(selected)=={"canvas_discussion_thread","canvas_get_discussion","canvas_post_discussion_reply"}
                keep("mcp/"+mode+"-inventory.json",{"tool_count":len(inventory.tools),"selected":selected})
                async def invoke(case,args,*,name="canvas_discussion_thread",failed=False,expected=None):
                    active["case"]=case;start=len(records)
                    response=await session.call_tool(name,args)
                    raw=response.model_dump(by_alias=True)
                    calls.append({"case":case,"tool":name,"arguments":args,"response":raw,
                                  "http_start":start,"http_end":len(records)})
                    if expected is not None:request_window(start,mode,expected)
                    if failed:
                        assert raw["isError"] is True,(case,raw)
                        return raw
                    assert raw["isError"] is False,(case,raw)
                    assert len(raw["content"])==1 and raw["content"][0]["type"]=="text",(case,raw)
                    return json.loads(raw["content"][0]["text"])
                args={"course_id":COURSE,"topic_id":TOPIC_ID}
                if mode=="token":
                    for i,bad in enumerate([
                        {"course_id":17,"topic_id":TOPIC_ID},
                        {"course_id":COURSE,"topic_id":19},
                        {**args,"unread_only":"false"},
                        {**args,"unread_only":None},
                        {"course_id":"17/other","topic_id":TOPIC_ID},
                    ]):
                        start=len(records)
                        await invoke("mcp-invalid-"+str(i),bad,failed=True,expected=[])
                        assert len(records)==start
                    result=await invoke("mcp-full",args,expected=[TOPIC_PATH,VIEW_PATH]);assert_full(result)
                    raw=await invoke("mcp-raw",args,name="canvas_get_discussion",expected=[TOPIC_PATH,VIEW_PATH])
                    assert raw=={"topic":TOPIC,"view":VIEW}
                    state["view"]["unread_entries"]=[201]
                    await invoke("mcp-ambiguous",{**args,"unread_only":True},failed=True,expected=[TOPIC_PATH,VIEW_PATH])
                    reset()
                    result=await invoke("mcp-after-ambiguity",{**args,"unread_only":True},expected=[TOPIC_PATH,VIEW_PATH]);assert_focus(result)
                else:
                    result=await invoke("mcp-broker-full",args,expected=[TOPIC_PATH,VIEW_PATH]);assert_full(result)
                    state["view_spec"]=(503,"application/json",jbytes({"error":"synthetic native cache unavailable"}))
                    await invoke("mcp-broker-cache503",args,failed=True,expected=[TOPIC_PATH,VIEW_PATH])
                    reset();state["view"].pop("unread_entries")
                    await invoke("mcp-broker-missing-unread",{**args,"unread_only":True},failed=True,expected=[TOPIC_PATH,VIEW_PATH])
                    reset()
                    result=await invoke("mcp-broker-recovered",{**args,"unread_only":True},expected=[TOPIC_PATH,VIEW_PATH]);assert_focus(result)
        errlog.flush();errlog.seek(0);logs=errlog.read()
    keep("mcp/"+mode+"-calls.json",calls)
    keep("mcp/"+mode+"-stderr.log",logs)
    processes.append({"kind":"mcp","mode":mode,"calls":len(calls),"stdio_closed":True})
    return {"actual_mcp_process":1,"calls":len(calls),"persistent_process_recovery":True,
            "schema_strict_boolean":True,"read_only_tool_annotation":True,"same_raw_tool_available":True}

def final_boundaries():
    assert not any("receiver_error" in r for r in records),[r for r in records if "receiver_error" in r]
    assert all(r.get("inner_canvas_method","GET")=="GET" for r in records)
    assert all(r["authorization"]!="unexpected" for r in records)
    assert not any(p.name.startswith("profile-") or p.name.endswith("-profile") for p in temp.iterdir())
    after=pin_source()
    assert after==source_before
    receipt["source_after"]=after
    return {"source_files_unchanged":len(after),"all_inner_canvas_requests_get":True,
            "no_profile_created":True,"no_unexpected_http_path":True}

try:
    for name,fn in [
        ("01_exact_consumer_reconstruction",pure_forest),
        ("02_unread_structural_context",pure_focus),
        ("03_unknown_empty_ambiguous_and_mutability",missing_and_ambiguous),
        ("04_python_validation_and_raw_compatibility",api_validation_and_raw),
        ("05_persistent_python_error_recovery",api_recovery),
        ("06_cli_full_and_focus",cli_read),
        ("07_topic_refusal_short_circuit",cli_first_refusal),
        ("08_cli_malformed_response_and_recovery",cli_malformed_recovery),
        ("09_broker_cli_transport",broker_cli_read),
        ("10_broker_refusals_and_recovery",broker_errors_recovery),
        ("11_broker_unavailable_no_fallback",broker_health_unavailable),
        ("12_mcp_token_consumer_and_recovery",lambda:asyncio.run(mcp_receive("token"))),
        ("13_mcp_broker_consumer_and_recovery",lambda:asyncio.run(mcp_receive("broker"))),
        ("14_final_readonly_and_source_boundaries",final_boundaries),
    ]:
        run_group(name,fn)
finally:
    for server in [token_server,broker_server]:
        server.shutdown();server.server_close()
    receipt["finished_unix"]=time.time()
    receipt["passed"]=sum(g["status"]=="passed" for g in receipt["groups"])
    receipt["failed"]=sum(g["status"]=="failed" for g in receipt["groups"])
    receipt["processes"]=processes
    receipt["http_requests"]=len(records)
    receipt["inner_canvas_gets"]=sum(r.get("inner_canvas_method")=="GET" for r in records)
    receipt["outer_broker_posts"]=sum(r["surface"]=="broker" and r["wire_method"]=="POST" for r in records)
    receipt["temporary_files"]=[p.relative_to(temp).as_posix() for p in temp.rglob("*") if p.is_file()]
    keep("http/requests.json",records)
    keep("runtime/parent-stderr.log",stderr_parent.getvalue())
    keep("receipt.json",receipt)
    packet={"schema":"canvas-independent-receiving-packet-v1","files":[
        {"path":name,"content":content,"bytes":len(content.encode()),"sha256":digest(content.encode())}
        for name,content in sorted(artifacts.items())]}
    print("CANVAS_RECEIVING_PACKET="+json.dumps(packet,ensure_ascii=False,separators=(",",":")))
