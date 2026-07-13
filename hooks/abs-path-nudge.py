#!/usr/bin/env python3
"""abs-path-nudge — passive Stop hook: next-turn reminder to include ABSOLUTE
clickable paths for files created/edited this turn.

Why a Stop hook (and its honest limit): Ro repeatedly asks that the MAIN
session's FINAL message list full absolute clickable paths of every file it
created/edited. A Stop hook fires AFTER that message is already sent, so it
CANNOT rewrite it. Its only realistic value is a *next-turn* reminder that
surfaces the next time the model speaks. So this is a nudge, not a fix.

Low-noise: only fires when the turn actually touched files. It reuses the
phantom-edit log (state/phantom-edit.jsonl), which logs every Write/Edit with
the transcript path (== session id) + ts. If this session has a recent
(<=10 min) Write/Edit entry, emit one short reminder; otherwise stay silent.

Passive & fail-open: never blocks the stop (never exit 2 / decision=block).
Prints the reminder to stderr and exits 0. Any error → exit 0 silent.

Mode: state/abs-path-nudge.mode — "off" disables; missing/anything-else = on.
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

HOOK_DIR = Path.home() / ".claude" / "hooks"
LOG = HOOK_DIR / "state" / "phantom-edit.jsonl"
MODE = HOOK_DIR / "state" / "abs-path-nudge.mode"
WINDOW_SECS = 600  # 10 min
EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

MSG = ("final msg: list FULL absolute path for every file created/edited this turn (e.g. /Users/...).")


def _enabled() -> bool:
    try:
        return MODE.read_text().strip().lower() != "off"
    except OSError:
        return True  # default ON


def _recent_edit(session_id: str, tpath: str) -> bool:
    """True if this session has a Write/Edit logged within WINDOW_SECS."""
    now = time.time()
    try:
        lines = LOG.read_text().splitlines()
    except OSError:
        return False
    for ln in reversed(lines[-400:]):  # tail only; newest last
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        tp = e.get("tp", "")
        # Match this session: transcript path equal, or session_id embedded in it.
        if tp and tp != tpath and (not session_id or session_id not in tp):
            continue
        if e.get("tool") not in EDIT_TOOLS or not e.get("file"):
            continue
        ts = e.get("ts", "")
        try:
            age = now - datetime.fromisoformat(ts).timestamp()
        except ValueError:
            continue
        if 0 <= age <= WINDOW_SECS:
            return True
    return False


def main() -> int:
    if not _enabled():
        return 0
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if data.get("stop_hook_active"):
        return 0
    session_id = data.get("session_id", "") or ""
    tpath = data.get("transcript_path", "") or ""
    try:
        if _recent_edit(session_id, tpath):
            _hookout.inject("Stop", MSG)
    except Exception:
        return 0
    return 0


def _selftest() -> int:
    import os
    import tempfile

    global LOG, MODE
    d = Path(tempfile.mkdtemp())
    LOG = d / "phantom-edit.jsonl"
    MODE = d / "abs-path-nudge.mode"
    ok = True

    # Case 1: recent edit for our session -> reminder expected.
    sid = "test-session-abc"
    tp = f"/x/projects/{sid}.jsonl"
    now_iso = datetime.now().isoformat(timespec="seconds")
    LOG.write_text(
        json.dumps({"ts": now_iso, "role": "MAIN", "tool": "Edit",
                    "file": "/Users/x/foo.py", "tp": tp}) + "\n"
    )
    got = _recent_edit(sid, tp)
    print(f"case1 recent-edit -> {got} (want True)")
    ok &= got is True

    # Case 2: no entries for this session -> silence.
    got = _recent_edit("other-session", "/x/projects/other.jsonl")
    print(f"case2 no-entry -> {got} (want False)")
    ok &= got is False

    # Case 3: entry too old -> silence.
    old_iso = datetime.fromtimestamp(time.time() - WINDOW_SECS - 60).isoformat(timespec="seconds")
    LOG.write_text(
        json.dumps({"ts": old_iso, "role": "MAIN", "tool": "Write",
                    "file": "/Users/x/bar.py", "tp": tp}) + "\n"
    )
    got = _recent_edit(sid, tp)
    print(f"case3 stale-edit -> {got} (want False)")
    ok &= got is False

    # Case 4: mode off -> disabled.
    MODE.write_text("off")
    print(f"case4 mode-off enabled -> {_enabled()} (want False)")
    ok &= _enabled() is False

    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    sys.exit(main())
