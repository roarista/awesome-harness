#!/usr/bin/env python3
"""PostToolUse — soft session checkpoint. Fires only when a session is already
abnormal, and NEVER blocks: it injects a nudge to re-scope via the ritual the
operator already runs (compact-prep → /compact → resume from the CONTINUE block).

Triggers (each fires at most once per band, so it's not a per-call nag):
  * call count crosses a multiple of CALLS      (150, 300, …) → "deep session"
  * error count crosses a multiple of ERRORS    (25, 50, …)   → "lots of errors"
  * the SAME command runs STREAK times in a row (3)           → "looping"

The streak trigger is the sharp one — you don't run the identical command three
times back-to-back unless it's failing/looping — and it needs no fragile
error-detection. Fail-open; state is per-session and self-prunes.
"""
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

CALLS = 150
ERRORS = 25
STREAK = 3
STATE_DIR = Path.home() / ".claude" / "hooks" / "state" / "checkpoint"
TTL = 2 * 86400


def _emit(reason: str) -> None:
    _hookout.inject("PostToolUse", (
        f"CHECKPOINT ({reason}). This session looks abnormal — stop and "
        "re-scope before continuing: run the compact-prep skill, then "
        "/compact with no message, then resume from the CONTINUE block. "
        "If you're mid-loop, state in one line what you're actually trying "
        "to achieve and whether the current approach can get there."))


def _is_error(resp) -> bool:
    if isinstance(resp, dict):
        if resp.get("is_error") or resp.get("error"):
            return True
        c = resp.get("content")
        if isinstance(c, str) and c.lstrip().lower().startswith(("error", "traceback")):
            return True
    if isinstance(resp, str) and resp.lstrip().lower().startswith(("error", "traceback")):
        return True
    return False


def _path(session: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session)[:80]
    return STATE_DIR / f"{safe or 'nosession'}.json"


def _prune() -> None:
    now = time.time()
    try:
        for f in STATE_DIR.glob("*.json"):
            if now - f.stat().st_mtime > TTL:
                f.unlink()
    except OSError:
        pass


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    session = str(data.get("session_id", "") or "")
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}
    resp = data.get("tool_response", data.get("tool_result", {}))

    p = _path(session)
    try:
        st = json.loads(p.read_text())
    except Exception:
        st = {"calls": 0, "errors": 0, "last_cmd": "", "streak": 0, "fired": []}
    fired = set(st.get("fired", []))

    st["calls"] += 1
    if _is_error(resp):
        st["errors"] += 1

    # repeated identical command (Bash) — the loop signal
    reason = None
    if tool == "Bash":
        cmd = str(ti.get("command", ""))
        if cmd and cmd == st.get("last_cmd"):
            st["streak"] = st.get("streak", 0) + 1
        else:
            st["streak"] = 1
            fired.discard("loop")           # re-arm for the next distinct loop
        st["last_cmd"] = cmd
        if st["streak"] >= STREAK and "loop" not in fired:
            reason = f"same command run {st['streak']}× in a row"
            fired.add("loop")

    if reason is None:
        band = (st["calls"] // CALLS) * CALLS
        if band and f"calls:{band}" not in fired:
            reason = f"{st['calls']} tool calls"
            fired.add(f"calls:{band}")
    if reason is None:
        band = (st["errors"] // ERRORS) * ERRORS
        if band and f"errors:{band}" not in fired:
            reason = f"{st['errors']} errors"
            fired.add(f"errors:{band}")

    st["fired"] = sorted(fired)
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(st))
    except Exception:
        pass

    if reason:
        _emit(reason)
        _prune()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # never wedge a tool call over a checkpoint nudge
