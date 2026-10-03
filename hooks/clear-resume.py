#!/usr/bin/env python3
"""SessionStart(clear) hook — the /clear handoff (context-diet U4).

Flow: /compact-prep writes .planning/CONTINUE.md, then Ro types /clear. This
hook injects that file into the fresh session (<48 h old, <=1,500 B), so
nothing is pasted and no compact summary is paid for. No fresh CONTINUE.md ->
the first 5 lines of .now.md. Neither -> silence. Any other source -> silence.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hookout; _hookout.exit_if_product(); import json

CAP = 1500
MAX_AGE = 48 * 3600


def root(start):
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, ".git")) or os.path.isdir(os.path.join(d, ".planning")):
            return d
        up = os.path.dirname(d)
        if up == d:
            return os.path.abspath(start)
        d = up


def read(path, limit):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read(limit)


def block(base):
    cont = os.path.join(base, ".planning", "CONTINUE.md")
    if os.path.isfile(cont) and time.time() - os.path.getmtime(cont) < MAX_AGE:
        text = read(cont, CAP).strip()
        if text:
            return "Resumed after /clear. Handoff from .planning/CONTINUE.md:\n" + text
    now = os.path.join(base, ".now.md")
    if os.path.isfile(now):
        text = "".join(read(now, 4000).splitlines(True)[:5]).strip()
        if text:
            return "Resumed after /clear. No fresh CONTINUE.md; .now.md:\n" + text
    return ""


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    if payload.get("source") != "clear":
        return
    start = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        _hookout.inject("SessionStart", block(root(start)))
    except Exception:
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
