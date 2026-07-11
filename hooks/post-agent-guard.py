#!/usr/bin/env python3
"""PostToolUse(Task|Agent) — fires the instant a sub-agent returns, which is the
exact moment the orchestrator is tempted to narrate "here's what came back".
No hook can retract chat prose, but this injects a reminder at the danger point.
Fail-open, silent on any error."""
import sys

REMINDER = (
    "⏸ SUB-AGENT RETURNED — DO NOT narrate this to chat. Append ONE caveman "
    "line to $CLAUDE_JOB_DIR/tmp/pending.md (e.g. '- codexA: built X, tests pass'), "
    "stay silent, keep orchestrating. Expand ALL pending lines into the SINGLE final "
    "message at turn end. Ro reads only that final message; mid-turn prose is banned.\n"
    "If MORE agents are still running, WAIT for them too — do NOT summarize now and "
    "again later (that double-spews the same info). ONE consolidated summary after "
    "the LAST agent lands.\n"
    "Next spawn that WRITES code: prompt the coder with CONTEXT (graphify map + "
    "file:line anchors) / CHANGE / GOAL / VERIFY, forbid invented APIs, demand one "
    "runnable check. Full guide: ~/awesome-harness/docs/CODING_AGENT_PROMPTING.md"
)


def main():
    try:
        sys.stdin.read()  # drain; content irrelevant, matcher already scopes to Task/Agent
    except Exception:
        pass
    print(REMINDER)
    sys.exit(0)


if __name__ == "__main__":
    main()
