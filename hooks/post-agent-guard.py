#!/usr/bin/env python3
"""PostToolUse(Task|Agent) — fires the instant a sub-agent returns, which is the
exact moment the orchestrator is tempted to narrate "here's what came back".
No hook can retract chat prose, but this injects a reminder at the danger point.
Fail-open, silent on any error."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

REMINDER = (
    "agent back. no chat. log 1 line -> $CLAUDE_JOB_DIR/tmp/pending.md. keep orchestrating.\n"
    "more agents running? wait all. no double-spew. ONE final summary after last agent.\n"
    "next code spawn: prompt CONTEXT(graphify map+file:line)/CHANGE/GOAL/VERIFY, no invented APIs, "
    "1 runnable check. guide: ~/awesome-harness/docs/CODING_AGENT_PROMPTING.md"
)


def main():
    try:
        sys.stdin.read()  # drain; content irrelevant, matcher already scopes to Task/Agent
    except Exception:
        pass
    # BEHAVIOR CHANGE 2026-07-12: hidden model-only inject, not raw stdout.
    _hookout.inject("PostToolUse", REMINDER)
    sys.exit(0)


if __name__ == "__main__":
    main()
