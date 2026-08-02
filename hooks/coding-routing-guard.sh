#!/bin/sh
# PreToolUse(Task) — thin wrapper; settings.json invokes this path.
# Real logic (and the rationale for the 2026-08-02 context diet) lives in
# coding-routing-guard.py. A heredoc'd `python3 -` cannot be used here: the
# heredoc occupies stdin, so the hook payload would be unreadable.
# Revert: hooks/.bak-contextdiet/coding-routing-guard.sh
exec python3 "$(dirname "$0")/coding-routing-guard.py"
