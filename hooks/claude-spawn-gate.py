#!/usr/bin/env python3
"""PreToolUse(Task|Agent) — block pure-Claude subagent types, CLI offload only.

CONTEXT 2026-08-09: 30d subagent spawns — general-purpose 886, codex 335,
Explore 127, codex-audit 122, codex:codex-rescue 121, opus 102. Cost-weighted,
subagents are 43.3% of all spend; claude-sonnet-5 alone is 13.7% (239.8M
weighted tokens), almost entirely spent inside these subagents. general-purpose
and Explore are pure Claude sidechains with no CLI offload at all — the two
highest-volume, highest-cost agent types with zero routing check on them.
hooks/spawn-necessity.py only advises WHETHER to spawn; hooks/coding-routing-guard.py
only fires when a spawn writes code AND is misrouted. Neither actually blocks a
Claude-only agent type. This hook is the first one that does.

Blocks subagent_type in {general-purpose, explore} (case-insensitive) with a
hard exit 2 naming the CLI replacement. Everything else — codex, codex-audit,
gemini, opus, map-refresh, plugin agents (name contains ':') — passes silently.
Fails OPEN (exit 0) on any exception so a broken hook never blocks a real spawn.
Kill switch: CLAUDE_SPAWN_GATE=off.
"""
import json
import sys

BLOCKED = {"general-purpose", "explore"}

MSG = (
    "BLOCKED: subagent_type={agent!r} is a pure-Claude sidechain with no CLI "
    "offload (30d: general-purpose 886 / Explore 127 spawns, 43.3% of all spend). "
    "Use `codex` for build/analysis or `codex-audit` for review instead."
)


def verdict(agent: str) -> bool:
    """True if this spawn should be BLOCKED."""
    a = (agent or "").strip().lower()
    if not a:
        return False
    if ":" in a:  # plugin agent, e.g. vercel:deployment-expert
        return False
    return a in BLOCKED


def main() -> int:
    import os

    if os.environ.get("CLAUDE_SPAWN_GATE", "").lower() == "off":
        return 0
    payload = json.load(sys.stdin) or {}
    ti = payload.get("tool_input") or {}
    agent = str(ti.get("subagent_type") or "")
    if not verdict(agent):
        return 0
    sys.stderr.write(MSG.format(agent=agent) + "\n")
    return 2


def _selftest() -> None:
    assert verdict("general-purpose") is True
    assert verdict("Explore") is True
    assert verdict("codex") is False
    assert verdict("codex-audit") is False
    assert verdict("opus") is False
    assert verdict("vercel:deployment-expert") is False
    assert verdict("") is False
    assert verdict("map-refresh") is False
    assert verdict("gemini") is False
    print("PASS")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
