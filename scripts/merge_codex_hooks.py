#!/usr/bin/env python3
"""Merge awesome-harness's narrow Codex PreToolUse entries without clobbering a repo.

Only the two entries owned by this installer are managed.  The old, repository
relative ``exec_command`` entry is migrated only when it is an exact known
awesome-harness command; arbitrary user hooks are left untouched.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

MANAGED_MATCHERS = ("^Bash$", "^apply_patch$")
# This was the first local adapter location used during the Codex migration.
LEGACY_COMMANDS = {
    'python3 "$(git rev-parse --show-toplevel)/.codex/awesome-harness/pre_tool_use.py"',
}


def managed_command(adapter: str) -> str:
    return f'python3 "{adapter}"'


def load(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.stat().st_size:
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"refusing to merge malformed JSON at {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"refusing to merge {path}: top-level JSON must be an object")
    return value


def hook(command: str) -> dict[str, Any]:
    return {"type": "command", "command": command, "timeout": 10}


def is_exact_legacy(entry: Any) -> bool:
    if not isinstance(entry, dict) or entry.get("matcher") != "exec_command":
        return False
    hooks = entry.get("hooks")
    return (
        isinstance(hooks, list)
        and len(hooks) == 1
        and isinstance(hooks[0], dict)
        and hooks[0].get("type") == "command"
        and hooks[0].get("command") in LEGACY_COMMANDS
    )


def merge(settings: dict[str, Any], adapter: str) -> tuple[dict[str, Any], list[str]]:
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("refusing to merge: hooks must be an object")
    pre = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre, list):
        raise ValueError("refusing to merge: hooks.PreToolUse must be an array")

    actions: list[str] = []
    legacy = [entry for entry in pre if is_exact_legacy(entry)]
    if legacy:
        pre[:] = [entry for entry in pre if not is_exact_legacy(entry)]
        actions.append("migrate exact legacy exec_command harness entry")

    command = managed_command(adapter)
    for matcher in MANAGED_MATCHERS:
        matches = [entry for entry in pre if isinstance(entry, dict) and entry.get("matcher") == matcher]
        if not matches:
            pre.append({"matcher": matcher, "hooks": [hook(command)]})
            actions.append(f"add PreToolUse {matcher}")
            continue
        entry = matches[0]
        nested = entry.get("hooks")
        if not isinstance(nested, list):
            raise ValueError(f"refusing to merge: PreToolUse {matcher} hooks must be an array")
        if not any(isinstance(item, dict) and item.get("command") == command for item in nested):
            nested.append(hook(command))
            actions.append(f"add harness command to PreToolUse {matcher}")

    return settings, actions


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp = Path(handle.name)
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    parser.add_argument("hooks_json", type=Path)
    parser.add_argument("adapter", type=Path)
    args = parser.parse_args()
    adapter = args.adapter.expanduser().resolve()
    if not adapter.is_file():
        parser.error(f"installed adapter does not exist: {adapter}")
    try:
        settings = load(args.hooks_json)
        merged, actions = merge(settings, str(adapter))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    content = json.dumps(merged, indent=2, sort_keys=True) + "\n"
    original = args.hooks_json.read_text(encoding="utf-8") if args.hooks_json.exists() else None
    if original == content:
        print(f"unchanged: {args.hooks_json}")
        return 0
    if args.dry_run:
        print(f"DRY: would merge {args.hooks_json}: {', '.join(actions) or 'format JSON'}")
        return 0
    if args.hooks_json.exists():
        backup = args.hooks_json.with_name(args.hooks_json.name + f".bak.{time.time_ns()}")
        shutil.copy2(args.hooks_json, backup)
        print(f"backup: {backup}")
    write_atomic(args.hooks_json, content)
    print(f"merged: {args.hooks_json}: {', '.join(actions) or 'format JSON'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
