"""Verify the frozen six-file fence and preserve every unrelated source AST."""
import ast
import hashlib
import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parent
owner = pathlib.Path("/tmp/canvaspilot-inbox-713adaab")
base_commit = "ca2318fe7c56d2e4ec1b363ff8a945ab78bf4a0c"
candidate_commit = "db32bde55db5080ed7ee856faab5cf1a2b5c949a"
base = root / "baseline/src/canvaspilot"
candidate = root / "candidate-v2/src/canvaspilot"

def dump(tree):
    return ast.dump(tree, include_attributes=False)

def parsed(directory, name):
    return ast.parse((directory / name).read_text())

def without_inbox_api(tree):
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "CanvasAPI")
    cls.body = [node for node in cls.body
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                or node.name not in ("list_conversations", "get_conversation")]
    return tree

def without_inbox_metadata(tree):
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name in (
            "canvas_list_conversations", "canvas_get_conversation",
        ):
            node.decorator_list = []
    return tree

def added_parser(node):
    if isinstance(node, ast.Assign):
        return len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("inbox", "conversation")
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    call = node.value
    if isinstance(call.func, ast.Name) and call.func.id == "add_common":
        return len(call.args) == 1 and isinstance(call.args[0], ast.Name) and call.args[0].id in ("inbox", "conversation")
    return isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id in ("inbox", "conversation")

class RemoveInboxDispatch(ast.NodeTransformer):
    removed = 0
    def visit_If(self, node):
        self.generic_visit(node)
        test = node.test
        if (isinstance(test, ast.Compare)
            and dump(test.left) == dump(ast.parse("args.cmd", mode="eval").body)
            and len(test.ops) == 1 and isinstance(test.ops[0], ast.In)
            and len(test.comparators) == 1
            and dump(test.comparators[0]) == dump(ast.parse('("inbox", "conversation")', mode="eval").body)):
            self.removed += 1
            assert len(node.orelse) == 1
            return node.orelse[0]
        return node

before_cli = parsed(base, "cli.py")
after_cli = parsed(candidate, "cli.py")
main = next(node for node in after_cli.body if isinstance(node, ast.FunctionDef) and node.name == "main")
parser_nodes = [node for node in main.body if added_parser(node)]
assert len(parser_nodes) == 6
main.body = [node for node in main.body if not added_parser(node)]
strip_dispatch = RemoveInboxDispatch()
after_cli = strip_dispatch.visit(after_cli)
assert strip_dispatch.removed == 1
checks = {
    "unowned_api_AST_unchanged": dump(without_inbox_api(parsed(base, "api.py"))) == dump(without_inbox_api(parsed(candidate, "api.py"))),
    "MCP_functions_arguments_and_other_metadata_unchanged": dump(without_inbox_metadata(parsed(base, "mcp_server.py"))) == dump(without_inbox_metadata(parsed(candidate, "mcp_server.py"))),
    "CLI_unchanged_after_removing_only_six_parser_nodes_and_one_dispatch": dump(before_cli) == dump(after_cli),
    "all_other_runtime_bytes_unchanged": all(
        path.read_bytes() == (candidate / path.name).read_bytes()
        for path in base.glob("*.py") if path.name not in ("api.py", "cli.py", "mcp_server.py")
    ),
}
changed = subprocess.check_output(["git", "-C", str(owner), "diff", "--name-only", base_commit, candidate_commit], text=True).splitlines()
checks["exact_six_path_fence"] = sorted(changed) == sorted([
    "README.md", "docs/inbox-review.md", "src/canvaspilot/api.py", "src/canvaspilot/cli.py",
    "src/canvaspilot/mcp_server.py", "tests/test_inbox_review.py",
])
base_readme = subprocess.check_output(["git", "-C", str(owner), "show", base_commit + ":README.md"])
new_readme = subprocess.check_output(["git", "-C", str(owner), "show", candidate_commit + ":README.md"])
start, end = new_readme.index(b"## Review your inbox\n"), new_readme.index(b"## Auth modes\n")
checks["README_original_bytes_preserved_around_new_section"] = new_readme[:start] + new_readme[end:] == base_readme
assert all(checks.values()), checks
receipt = {"base": base_commit, "candidate": candidate_commit, "checks": checks, "changed_paths": changed,
           "runtime": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(candidate.glob("*.py"))},
           "reviewer": "chatgpt:/root/mac_execution", "method": "Independent source/AST preservation check; no owner mutation."}
out = root / "candidate-v2/source-preservation.json"
out.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"checks": checks, "receipt": str(out), "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}))
