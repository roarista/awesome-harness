#!/usr/bin/env python3
"""PreToolUse(Task) — routing guard. Silent unless THIS spawn violates routing.

CONTEXT DIET 2026-08-02 (audit 13). The previous shell version `cat`-ed a
421-token routing policy on EVERY Task spawn: ~48 fires/session ≈ 20 K tokens,
byte-identical every time and, because the transcript is append-only, re-sent on
every later API call. Measured in the awesome-harness corpus: 198 fires x 433 tok
= 85.8 K tokens over 5 sessions = 63% of all hook tokens there.

The policy it repeated is ALREADY in the static preamble (~/.claude/CLAUDE.md,
"Delegation default"), so every fire was pure duplication — and audit 07 found
186 advisory fires with no demonstrated behavior change.

New contract: emit NOTHING unless the spawn actually writes code AND is routed to
something other than the builder; then one short line, once per session. A hook
that prints nothing still records a hook_success attachment, but with EMPTY
content — measured 0 tokens.

Revert: hooks/.bak-contextdiet/coding-routing-guard.sh
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hookout

# Builder / auditor / second-opinion / read-only agents: nothing to correct.
OK_AGENTS = ("codex", "opus", "glm", "gemini", "explore", "plan", "statusline")

WRITES_CODE = re.compile(
    r"\b(implement|refactor|write the code|add (?:a |the )?(?:function|endpoint|module|feature|test)"
    r"|fix the bug|apply the (?:diff|fix|change)|create (?:a |the )?(?:file|module|script|component))\b",
    re.I,
)
TOUCHES_SOURCE = re.compile(r"\.(py|js|ts|tsx|jsx|go|rs|rb|java|swift|c|cpp|h|sh)\b")

MSG = (
    "ROUTING: this spawn writes code but is not routed to the builder "
    "(subagent_type={agent}). Build with `codex:codex-rescue`, audit with `opus` (low). "
    "Prompt shape CONTEXT(file:line map)/CHANGE/GOAL/VERIFY, no invented APIs. "
    "Full guide: docs/CODING_AGENT_PROMPTING.md. (said once per session)"
)


def verdict(agent: str, prompt: str) -> bool:
    """True if this spawn is a routing violation worth one line of context."""
    if any(a in agent for a in OK_AGENTS):
        return False
    return bool(WRITES_CODE.search(prompt) and TOUCHES_SOURCE.search(prompt))


def main() -> None:
    payload = json.load(sys.stdin) or {}
    ti = payload.get("tool_input") or {}
    agent = str(ti.get("subagent_type") or "").lower()
    prompt = str(ti.get("prompt") or "")
    if not verdict(agent, prompt):
        return
    if not _hookout.once("routing-violation", _hookout.sid_of(payload)):
        return
    _hookout.inject("PreToolUse", MSG.format(agent=agent or "default"))


def _selftest() -> None:
    assert not verdict("general-purpose", "find where auth lives")
    assert verdict("general-purpose", "implement the retry function in src/api.py and add a test")
    assert not verdict("codex:codex-rescue", "implement the retry function in src/api.py")
    assert not verdict("general-purpose", "implement a new marketing plan")  # no source file
    print("PASS")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
