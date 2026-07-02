#!/usr/bin/env python3
"""PreToolUse hook — hard STOP on IRREVERSIBLE Bash ops (bypassPermissions guard).

This machine runs Claude Code in bypassPermissions mode: dangerous shell
commands execute with no confirmation. This gate converts a tight, denylist-only
set of irreversible operations into a forced reconsideration — the agent must
confirm with the user, then re-arm by re-running the command prefixed with the
override token.

Design principle: DENYLIST ONLY, tight, minimize false positives. A cry-wolf
gate gets ignored, so we cover exactly three families:
  1. Recursive force delete  (rm with combined -r + -f flags)
  2. Force push              (git push with --force / -f / --force-with-lease)
  3. Destructive SQL / DB reset (drop table / drop database / truncate table)

Override / re-arm: any command containing the literal substring
`CLAUDE_ALLOW_IRREVERSIBLE=1` is always allowed.

Deny protocol: exit 2 + reason on stderr → Claude Code blocks the call and
feeds the reason back to the model. Fail-open on any internal error (exit 0) —
this must never wedge the session.
"""
import json
import re
import sys

OVERRIDE = "CLAUDE_ALLOW_IRREVERSIBLE=1"

# 1. rm with BOTH recursive and force flags — handled by _rm_is_recursive_force
#    below (parses the clustered short flags; handles -rf, -fr, -r -f, -Rf, -rfv).

# 2. git push carrying a force flag.
GIT_FORCE_PUSH = re.compile(
    r"\bgit\b[^\n]*\bpush\b[^\n]*(?:--force-with-lease|--force|(?<![\w-])-f\b)",
)

# 3. Destructive SQL / DB reset (case-insensitive).
SQL_DESTRUCTIVE = re.compile(
    r"\b(?:drop\s+table|drop\s+database|truncate\s+table)\b",
    re.IGNORECASE,
)


def _rm_is_recursive_force(cmd: str) -> bool:
    """True iff a single `rm` invocation carries BOTH recursive AND force —
    via short-flag clusters (-rf, -fr, -Rf, -r -f), long flags
    (--recursive / --force), or any mix of the two."""
    for m in re.finditer(r"\brm\b([^\n;|&]*)", cmd):   # args up to a cmd separator
        args = m.group(1)
        short = "".join(re.findall(r"(?<!-)-([a-zA-Z]+)\b", args))  # clusters, not --long
        recursive = "r" in short or "R" in short or re.search(r"(?<!\S)--recursive\b", args)
        force = "f" in short or re.search(r"(?<!\S)--force\b", args)
        if recursive and force:
            return True
    return False


def matches_denylist(cmd: str) -> bool:
    if _rm_is_recursive_force(cmd):
        return True
    if GIT_FORCE_PUSH.search(cmd):
        return True
    if SQL_DESTRUCTIVE.search(cmd):
        return True
    return False


def deny() -> None:
    sys.stderr.write(
        "BLOCKED: this is an IRREVERSIBLE operation (recursive force-delete, "
        "force push, or destructive SQL/DB reset) and cannot be undone. "
        "STOP and confirm with the user before proceeding. After they approve, re-run "
        "the EXACT command prefixed with `" + OVERRIDE + " ` to re-arm and "
        "allow it through this guard."
    )
    sys.exit(2)


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    if data.get("tool_name", "") != "Bash":
        return
    cmd = str((data.get("tool_input", {}) or {}).get("command", ""))
    if OVERRIDE in cmd:
        return  # override / re-arm — always allow
    if matches_denylist(cmd):
        deny()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open: never wedge a tool call over this guard
