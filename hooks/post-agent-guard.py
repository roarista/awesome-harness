#!/usr/bin/env python3
"""PostToolUse(Task|Agent) — fires the instant a sub-agent returns, which is the
exact moment the orchestrator is tempted to narrate "here's what came back".
No hook can retract chat prose, but this injects a reminder at the danger point.
Fail-open, silent on any error."""
import os
import re
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

# A FORWARDER returns a receipt, not code. Measured 2026-08-02: codex:codex-rescue
# had 84 transcripts and ZERO source writes; 48% of its receipts never resolved.
# A build that returns a receipt with no working-tree change is NOT done.
RECEIPT = re.compile(
    r"\b(?:task[ _-]?id|conversation[ _-]?id|session[ _-]?id)\b\s*[:=]"
    r"|\b(?:handed off|running in the background|will report back|kicked off|"
    r"follow[- ]up rescue|check back)\b", re.IGNORECASE)
NOT_DONE = ("FORWARDER RECEIPT, NOT A BUILD: the agent returned a task/receipt and "
            "`git status --porcelain` is EMPTY — zero files changed. This unit is NOT "
            "done. Re-run it through the `codex` agent (synchronous `codex exec`), "
            "not `codex:codex-rescue`, and require a real diffstat before accepting.")


def _receipt_with_no_diff(payload):
    """True iff the sub-agent's return looks like a receipt AND nothing changed.

    Cheap by construction: the regex runs first and the git call only happens on
    a receipt-shaped return, which is rare. Fail-open (False) on any error.
    """
    try:
        resp = payload.get("tool_response")
        text = resp if isinstance(resp, str) else str(resp)
        if not text or not RECEIPT.search(text[:4000]):
            return False
        cwd = payload.get("cwd") or os.getcwd()
        out = subprocess.run(["git", "status", "--porcelain"], cwd=cwd, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=3, check=False).stdout
        return not out.strip()
    except Exception:
        return False


REMINDER = (
    "AGENT BACK: no chat. ONE caveman line -> $CLAUDE_JOB_DIR/tmp/pending.md; summary ONLY when last agent in wave is back.\n"
    "next code spawn: prompt CONTEXT(graphify map+file:line)/CHANGE/GOAL/VERIFY, no invented APIs, "
    "1 runnable check. guide: /Users/rodrigoarista/Downloads/awesome-harness/docs/CODING_AGENT_PROMPTING.md"
)


def main():
    payload = {}
    try:
        raw = sys.stdin.read()  # matcher already scopes to Task/Agent; we only need session_id
        if raw.strip():
            import json
            payload = json.loads(raw) or {}
    except Exception:
        pass
    # BEHAVIOR CHANGE 2026-07-12: hidden model-only inject, not raw stdout.
    # CONTEXT DIET 2026-08-02 (audit 13): this fired 186x in 5 sessions at ~85
    # tok = 15.7 K tokens of byte-identical text, all of it re-sent on every
    # later API call, with 35.7% measured caveman compliance. The reminder is
    # static, so saying it 186 times cannot beat saying it once. Once per
    # session now; silence afterwards costs 0 tokens.
    # Not once-per-session: this is a per-unit correctness fact, not static prose.
    if _receipt_with_no_diff(payload):
        _hookout.inject("PostToolUse", NOT_DONE)
        sys.exit(0)
    if not _hookout.once("post-agent", _hookout.sid_of(payload)):
        sys.exit(0)
    _hookout.inject("PostToolUse", REMINDER)
    sys.exit(0)


if __name__ == "__main__":
    main()
