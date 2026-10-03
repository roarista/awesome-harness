#!/usr/bin/env python3
"""PostToolUse Write|Edit|MultiEdit — one-line nudge when a source file is over 200 lines.

The git pre-commit ratchet (tools/git-hooks/ratchet.py) only speaks at commit
time; this says it while the file is still being written. Never blocks: emits
additionalContext "<path> is N lines (cap 200): split into a new module before
continuing." and is silent at <=200, on non-source files, and on product calls.
Extension / skip lists mirror ratchet.py (tests/test_size_nudge.py checks that).
Fail-open on any error. U10 2026-10-03.
"""
import _hookout; _hookout.exit_if_product(); import json
import os
import _hookout as hookout  # inject(); separate import survives the guard-strip test
import sys

CAP = 200
SRC_EXT = {".py", ".sh", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb",
           ".swift", ".java", ".c", ".h", ".cpp", ".sql"}
SKIP_DIRS = {"test", "tests", "__tests__", "node_modules", "dist", "build",
             ".venv", "venv", "vendor", "migrations"}
TOOLS = {"Write", "Edit", "MultiEdit"}


def is_source(path: str) -> bool:
    name = os.path.basename(path)
    dot = name.rfind(".")
    ext = name[dot:].lower() if dot > 0 else ""
    if ext not in SRC_EXT or name.endswith(".min.js"):
        return False
    return not (SKIP_DIRS & set(path.replace("\\", "/").split("/")[:-1]))


def message(path: str) -> str:
    """The nudge line, or '' when the hook should stay silent."""
    if not path or not is_source(path) or not os.path.isfile(path):
        return ""
    with open(path, "rb") as f:
        n = len(f.read().splitlines())
    if n <= CAP:
        return ""
    return f"{path} is {n} lines (cap {CAP}): split into a new module before continuing."


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    if data.get("tool_name", "") not in TOOLS:
        return
    path = str((data.get("tool_input") or {}).get("file_path", ""))
    if path and not os.path.isabs(path) and data.get("cwd"):
        path = os.path.join(data["cwd"], path)
    hookout.inject("PostToolUse", message(path))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
