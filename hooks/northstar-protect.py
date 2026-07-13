#!/usr/bin/env python3
"""PreToolUse hook — protect the north star from goal-erosion.

The one fixed point of the anti-drift system is `.northstar.md`. A drifting
agent (which believes it's on-task) can silence its own alarms by softening or
erasing the goal. This hook is the mechanical gate that forbids that — the
agent may READ the north star but never mutate it. Only Ro edits it, by hand.

Covers BOTH attack surfaces:
  1. Write / Edit / MultiEdit whose target IS `.northstar.md`.
  2. The Bash bypass: `echo >`, `sed -i`, `tee`, `chmod`, `mv/cp/rm/truncate`
     targeting `.northstar.md`. (chmod 444 alone is not a gate — the agent can
     `chmod +w` then write; this hook is the real gate.)

Deny protocol: exit 2 + reason on stderr → Claude Code blocks the call and
feeds the reason back to the model. Reads are never blocked. Fail-open on any
internal error (exit 0) — this must never wedge the session.
"""
import json
import re
import sys

TARGET = ".northstar.md"

# Bash tokens that MUTATE a file. A command that merely names .northstar.md in a
# read (cat/grep/less) must NOT match — that's the cry-wolf failure we avoid.
# ponytail: denylist of write-verbs; add a pattern if a new bypass shows up.
BASH_MUTATORS = [
    r">>?\s*[^\s|;&<>]*\.northstar\.md",  # > path / >> path (redirect target is ONE token)
    r"\btee\b[^\n]*\.northstar\.md",
    r"\bsed\b[^\n]*-i[^\n]*\.northstar\.md",
    r"\b(?:mv|cp|rm|truncate|dd|install|ln)\b[^\n]*\.northstar\.md",
    r"\bchmod\b[^\n]*\.northstar\.md",
    r"\bchflags\b[^\n]*\.northstar\.md",
]


def deny(reason: str) -> None:
    sys.stderr.write(reason)
    sys.exit(2)


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}

    if tool in ("Write", "Edit", "MultiEdit"):
        path = str(ti.get("file_path", ""))
        if path.endswith(TARGET) or path.endswith("/" + TARGET):
            deny(
                f"BLOCKED: {TARGET} is the protected north star — the agent may "
                "not edit it (goal-erosion guard). If the objective genuinely "
                "changed, tell Ro; only he edits it by hand."
            )

    elif tool == "Bash":
        cmd = str(ti.get("command", ""))
        if TARGET in cmd and any(re.search(p, cmd) for p in BASH_MUTATORS):
            deny(
                f"BLOCKED: this command would mutate {TARGET} (the protected "
                "north star). Reads are fine; writes are not. If the objective "
                "genuinely changed, tell Ro — only he edits it by hand."
            )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open: never wedge a tool call over this guard
