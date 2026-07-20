#!/usr/bin/env python3
"""Fence external codex/glm builder calls at the Bash boundary; fail-open."""
import ast
import json
import os
import re
import subprocess
import sys

BUILDER = re.compile(r"^\s*(?:\S*/)?(codex|glm)\b")
BUILD_EDIT = re.compile(r"\bexec\b|--edit\b|\bgit apply\b|<<")
BRIEF = re.compile(r"\b(?:CONTEXT|CHANGE|GOAL|VERIFY)\b", re.IGNORECASE)


def _is_builder(command):
    # Identity check: a builder CALL is codex/glm invoked command-initial (optionally
    # via an absolute path). Edit-intent (BUILD_EDIT) is tested separately so a bare
    # `codex apply` still counts as a builder call, while `grep -w codex` does not.
    return bool(BUILDER.search(command))


def _context(event_name, message):
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": event_name, "additionalContext": message,
    }})


def preflight(event):
    """Return (additional-context JSON, blocked)."""
    if event.get("hook_event_name") != "PreToolUse" or event.get("tool_name") != "Bash":
        return "", False
    command = str((event.get("tool_input") or {}).get("command", ""))
    if not _is_builder(command):
        return "", False
    edit_intent = bool(BUILD_EDIT.search(command))
    # Block the north star only on an actual EDIT - a builder READ of it is fine.
    if ".northstar.md" in command and edit_intent:
        return "builder must never edit the north star.", True
    if edit_intent and not BRIEF.search(command):
        msg = "builder call missing CONTEXT/CHANGE/GOAL/VERIFY — decompose first (code-decompose)."
        return _context("PreToolUse", msg), os.environ.get("BUILDER_FENCE") == "enforce"
    return "", False


def _run(args, cwd):
    return subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, timeout=3, check=False).stdout


def _path_from_status(line):
    path = line[3:]
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[1]
    if path.startswith('"'):
        try:
            path = ast.literal_eval(path)
        except Exception:
            pass
    return path


def postflight(event):
    if event.get("hook_event_name") != "PostToolUse" or event.get("tool_name") != "Bash":
        return ""
    command = str((event.get("tool_input") or {}).get("command", ""))
    if not _is_builder(command):
        return ""
    cwd = str(event.get("cwd") or os.getcwd())
    status = _run(["git", "-C", cwd, "status", "--porcelain"], cwd)
    _run(["git", "-C", cwd, "diff", "--stat"], cwd)
    paths = [_path_from_status(line) for line in status.splitlines() if len(line) >= 4]
    notes = []
    if any(os.path.basename(path) == ".northstar.md" for path in paths):
        notes.append("LOUD: builder touched north star — revert")
    if any(os.path.basename(path) == ".now.md" or os.path.basename(path) == "STATE" for path in paths):
        notes.append("builder changed .now.md/STATE")
    for path in paths:
        full_path = path if os.path.isabs(path) else os.path.join(cwd, path)
        try:
            if not os.path.isfile(full_path):
                continue
            size = os.path.getsize(full_path)
            with open(full_path, "rb") as f:
                lines = sum(1 for _ in f)
            if size > 64000 or lines > 800:
                notes.append(f"large changed file: {path} ({size} bytes, {lines} lines)")
        except Exception:
            continue
    notes.append(f"Builder diff ready ({len(paths)} files). Route to Opus 4.8 audit before commit.")
    return _context("PostToolUse", "; ".join(notes))


def _selftest():
    event = {"hook_event_name": "PreToolUse", "tool_name": "Bash"}
    event["tool_input"] = {"command": 'codex exec "CHANGE: x"'}
    assert preflight(event) == ("", False)
    event["tool_input"] = {"command": 'codex exec "just do it"'}
    assert "decompose" in preflight(event)[0]
    event["tool_input"] = {"command": 'codex exec --edit .northstar.md'}
    assert preflight(event)[1]
    event["tool_input"] = {"command": "ls -la"}
    assert preflight(event) == ("", False)
    event["tool_input"] = {"command": "grep -w codex file"}
    assert preflight(event) == ("", False)
    event["tool_input"] = {"command": "kubectl apply -f codex.yaml"}
    assert preflight(event) == ("", False)
    event["tool_input"] = {"command": "cat .northstar.md"}
    assert preflight(event) == ("", False)
    assert _is_builder("/usr/local/bin/codex apply")
    assert not _is_builder("grep -w codex file")
    assert not _is_builder('echo "use codex"')
    print("selftest passed")


def main():
    if "--selftest" in sys.argv:
        _selftest()
        return
    raw = sys.stdin.read()
    event = json.loads(raw) if raw.strip() else {}
    if event.get("hook_event_name") == "PreToolUse":
        output, blocked = preflight(event)
        if blocked:
            sys.stderr.write(output)
            sys.exit(2)
        if output:
            print(output)
    elif event.get("hook_event_name") == "PostToolUse":
        output = postflight(event)
        if output:
            print(output)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
