#!/usr/bin/env python3
"""Select existing frozen MCP groups without modifying their code or product code."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
receiver = root / "receive_history.py"
expected = "158aa881f34a479a0ebcca0bf679f6cdff28ef8a8588d5d2a6a585e1983e84c3"
assert hashlib.sha256(receiver.read_bytes()).hexdigest() == expected
spec = importlib.util.spec_from_file_location("frozen_history_receiver", receiver)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
selected_names = (
    "G8 actual MCP schema and repeated fresh reads",
    "G9 actual MCP errors stay errors and do not poison the next call",
)
selected, skipped = [], []
original_dispatch = module.run_group


def dispatch(name, function):
    if name in selected_names:
        selected.append(name)
        return original_dispatch(name, function)
    skipped.append(name)


module.run_group = dispatch
status = module.main()
assert tuple(selected) == selected_names
assert len(skipped) == 7
output = Path(sys.argv[sys.argv.index("--out") + 1])
(output / "selection-proof.json").write_text(json.dumps({
    "receiver_sha256": expected,
    "selector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "selected": selected, "skipped": skipped,
    "scope": "Only receiver group dispatch is selected. Frozen case function bodies and production code are untouched.",
    "status": status,
}, indent=2) + "\n")
raise SystemExit(status)
