"""Independent current-main source and ownership verification."""
import ast
import hashlib
import json
import pathlib
import subprocess

OWNER = pathlib.Path("/tmp/canvaspilot-inbox-713adaab")
OUT = pathlib.Path("/dev/shm/canvaspilot-inbox-composition-713adaab")
BASE = "0d1898544a90079e2dcc7ceb3fa4bc6bca88a2bc"
CANDIDATE = "6b94efe9ff1f117fe4c2f1dfca595003a283d988"

def git(*args):
    return subprocess.check_output(["git", "-C", str(OWNER), *args])
def read(commit, path):
    return git("show", commit + ":" + path)
def dump(node):
    return ast.dump(node, include_attributes=False)
def api_shape(data):
    tree = ast.parse(data)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "CanvasAPI")
    cls.body = [n for n in cls.body if not isinstance(n, ast.FunctionDef)
                or n.name not in ("list_conversations", "get_conversation")]
    return dump(tree)
def mcp_shape(data):
    tree = ast.parse(data)
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name in (
            "canvas_list_conversations", "canvas_get_conversation",
        ):
            node.decorator_list = []
    return dump(tree)
def parser_node(node):
    if isinstance(node, ast.Assign):
        return len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("inbox", "conversation")
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    call = node.value
    if isinstance(call.func, ast.Name) and call.func.id == "add_common":
        return len(call.args) == 1 and isinstance(call.args[0], ast.Name) and call.args[0].id in ("inbox", "conversation")
    return isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id in ("inbox", "conversation")
class RemoveDispatch(ast.NodeTransformer):
    count = 0
    def visit_If(self, node):
        self.generic_visit(node)
        expected = ast.parse('args.cmd in ("inbox", "conversation")', mode="eval").body
        if dump(node.test) == dump(expected):
            self.count += 1
            assert len(node.orelse) == 1
            return node.orelse[0]
        return node
def leaves(commit):
    result = {}
    for line in git("ls-tree", "-r", commit).decode().splitlines():
        meta, path = line.split("\t", 1)
        mode, kind, blob = meta.split()
        result[path] = {"mode": mode, "kind": kind, "blob": blob}
    return result

base_tree, candidate_tree = leaves(BASE), leaves(CANDIDATE)
runtime = sorted(path for path in base_tree if path.startswith("src/") and path.endswith(".py"))
assert len(runtime) == 13
checks = {
    "API_outside_two_owned_reader_bodies_unchanged": api_shape(read(BASE, "src/canvaspilot/api.py")) == api_shape(read(CANDIDATE, "src/canvaspilot/api.py")),
    "MCP_functions_arguments_and_unowned_metadata_unchanged": mcp_shape(read(BASE, "src/canvaspilot/mcp_server.py")) == mcp_shape(read(CANDIDATE, "src/canvaspilot/mcp_server.py")),
    "other_runtime_files_byte_identical": all(read(BASE, path) == read(CANDIDATE, path) for path in runtime if path not in ("src/canvaspilot/api.py", "src/canvaspilot/cli.py", "src/canvaspilot/mcp_server.py")),
}
cli_before = ast.parse(read(BASE, "src/canvaspilot/cli.py"))
cli_after = ast.parse(read(CANDIDATE, "src/canvaspilot/cli.py"))
main = next(n for n in cli_after.body if isinstance(n, ast.FunctionDef) and n.name == "main")
assert sum(parser_node(n) for n in main.body) == 6
main.body = [n for n in main.body if not parser_node(n)]
remove = RemoveDispatch()
cli_after = remove.visit(cli_after)
checks["CLI_preserves_current_main_after_only_owned_blocks_removed"] = remove.count == 1 and dump(cli_before) == dump(cli_after)
readme = read(CANDIDATE, "README.md")
start, end = readme.index(b"## Review your inbox\n"), readme.index(b"## Auth modes\n")
checks["README_preserves_incoming_assignment_submission_text"] = readme[:start] + readme[end:] == read(BASE, "README.md")
owned_existing = {"README.md", "src/canvaspilot/api.py", "src/canvaspilot/cli.py", "src/canvaspilot/mcp_server.py"}
checks["all_unrelated_current_main_leaves_and_modes_preserved"] = all(candidate_tree.get(path) == row for path, row in base_tree.items() if path not in owned_existing)
changes = sorted(path for path, row in candidate_tree.items() if base_tree.get(path) != row)
feature_changes = [path for path in changes if not path.startswith("docs/verification/inbox-review-713adaab/")]
checks["exact_six_feature_path_fence"] = set(feature_changes) == owned_existing | {"docs/inbox-review.md", "tests/test_inbox_review.py"}
assert all(checks.values()), checks
receipt = {
    "schema": "canvaspilot.inbox.current_main_peer_review.v1", "reviewer": "chatgpt:/root/mac_execution",
    "current_main": BASE, "reviewed_commit": CANDIDATE, "reviewed_tree": git("show", "-s", "--format=%T", CANDIDATE).decode().strip(),
    "checks": checks, "incoming_leaves": len(base_tree), "preserved_unrelated_leaves": len(base_tree) - len(owned_existing),
    "feature_paths": feature_changes, "evidence_files": len(changes) - len(feature_changes),
    "runtime_sha256": {path: hashlib.sha256(read(CANDIDATE, path)).hexdigest() for path in runtime},
    "limits": "Source/AST/tree review only; the separate receipt contains the actual 14-group replay and its authored provider boundary.",
}
path = OUT / "current-main-source-review.json"
path.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"checks": checks, "receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                  "incoming_leaves": len(base_tree), "preserved_unrelated_leaves": len(base_tree) - 4,
                  "evidence_files": len(changes) - len(feature_changes)}))
