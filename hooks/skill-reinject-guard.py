#!/usr/bin/env python3
"""PreToolUse(Skill) — stop paying for the same skill body twice.

CONTEXT DIET 2026-08-02 (audit 13 / audit 04 §5). The awesomeharness skill was
repeatedly injected in measured sessions. Every copy is byte-identical AND, because the transcript is
append-only, is then re-sent on every remaining API call. Re-loading a skill
whose body is already in the transcript buys nothing.

So: a session-scoped skill whose body is already in context gets DENIED on
re-invocation, with a ~25-token explanation instead of a ~13,000-token body.
The TTL re-arms it after 2h so a genuinely long session can reload the contract.

Only skills in BIG_SESSION_SKILLS are guarded — everything else passes through
untouched. Fail-open on any error: a broken guard must never block a skill.

Revert: remove the PreToolUse "Skill" block from ~/.claude/settings.json
(backup: ~/.claude/settings.json.bak-contextdiet-20260802).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hookout

# Skills whose body is large AND session-scoped (loading it twice changes nothing).
BIG_SESSION_SKILLS = {"awesomeharness"}
TTL = 2 * 3600


def main() -> None:
    try:
        payload = json.load(sys.stdin) or {}
    except Exception:
        return
    name = str((payload.get("tool_input") or {}).get("skill") or "").strip().lower()
    if name not in BIG_SESSION_SKILLS:
        return
    if _hookout.once(f"skill:{name}", _hookout.sid_of(payload), ttl=TTL):
        return  # first load this session — let it through, pay the body once
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"`{name}` is already loaded in this session — its body is still in your "
                "context above. Re-loading would append identical instructions. Scroll "
                "up to the active contract instead. (context-diet guard; re-arms after 2h)"
            ),
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
