#!/usr/bin/env python3
"""PostToolUse(Task|Agent) — fires the instant a sub-agent returns, which is the
exact moment the orchestrator is tempted to narrate "here's what came back".
No hook can retract chat prose, but this injects a reminder at the danger point.
Fail-open, silent on any error."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

REMINDER = (
    "AGENT BACK: no chat. ONE caveman line -> $CLAUDE_JOB_DIR/tmp/pending.md; summary ONLY when last agent in wave is back.\n"
    "next code spawn: prompt CONTEXT(graphify map+file:line)/CHANGE/GOAL/VERIFY, no invented APIs, "
    "1 runnable check. guide: /Users/rodrigoarista/Downloads/awesome-harness/docs/CODING_AGENT_PROMPTING.md"
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
