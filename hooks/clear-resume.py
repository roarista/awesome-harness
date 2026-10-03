#!/usr/bin/env python3
"""SessionStart(clear) hook — the /clear handoff (context-diet U4).

Flow: /compact-prep writes .planning/CONTINUE.md, then Ro types /clear. This
hook injects that file into the fresh session (<48 h old, whole injection
<=1,500 UTF-8 bytes), so nothing is pasted and no compact summary is paid for.
CONTINUE.md missing, stale or unreadable -> silence. NOW lines are not
repeated here: northstar-inject.py already injects .now.md on SessionStart.
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hookout; _hookout.exit_if_product(); import json

CAP = 1500  # bytes, header included
MAX_AGE = 48 * 3600
HEADER = "Resumed after /clear. Handoff from .planning/CONTINUE.md:\n"


def root(start):
    """Repo top-level (linked worktrees included) via git; else start itself."""
    try:
        r = subprocess.run(["git", "-C", start, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return start


def block(base):
    path = os.path.join(base, ".planning", "CONTINUE.md")
    try:
        if time.time() - os.path.getmtime(path) >= MAX_AGE:
            return ""
        with open(path, "rb") as f:
            raw = f.read(CAP)
    except OSError:
        return ""
    budget = CAP - len(HEADER.encode())
    text = raw[:budget].decode("utf-8", errors="ignore").strip()
    return HEADER + text if text else ""


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return
    if not isinstance(payload, dict) or payload.get("source") != "clear":
        return
    start = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        _hookout.inject("SessionStart", block(root(str(start))))
    except Exception:
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
