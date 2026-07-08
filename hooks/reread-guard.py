#!/usr/bin/env python3
"""Read hook — kill the redundant full re-read (the runner.py×65 pathology).

Measured waste: one 66k-token file read 65× in a single session ≈ 4.2M tokens
for zero new information. Nothing tells the agent it already has the file, so it
reads again. This closes that: when you go to Read a large file you ALREADY read
in full this session-stretch, AND it hasn't changed on disk, the full content is
already above in your context — so we block the re-read and tell you how to get a
slice instead. graphify prevents reading source in the first place; this dedups
the reads you did do.

Three jobs, one file (branch on event):
  * PostToolUse Read  → record {abspath: [mtime, size]} for FULL reads of large
    files (no offset/limit). Partial reads are NOT recorded (you don't have the
    whole thing, so a later full read is legit).
  * PreToolUse  Read  → deny iff: same abspath recorded, THIS call is also a full
    read (no offset/limit), file is unchanged (mtime+size match), size >= MIN.
  * SessionStart      → clear this session's record. This is the compaction-safety
    valve: after a compact the earlier read is gone from context and re-reading is
    legitimate, so we must not block it.

Safety: DENY only on the unchanged-full-reread case (tight, like irreversible-
pause). Changed file → allow+refresh. Partial read → allow. Small file → allow.
Kill-switch: env REREAD_GUARD=0 → no-op (so a live pipeline can never be wedged).
Fail-open on ANY error. Deny protocol matches the repo: exit 2 + reason on stderr.
"""
import json
import os
import sys
import time
from pathlib import Path

MIN_BYTES = 8000          # ~2k tokens; below this a re-read isn't worth friction
STATE_DIR = Path.home() / ".claude" / "hooks" / "state" / "reread_readset"
TTL = 2 * 86400           # prune stale session files


def _path(session: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session)[:80]
    return STATE_DIR / f"{safe or 'nosession'}.json"


def _load(session: str) -> dict:
    try:
        return json.loads(_path(session).read_text())
    except Exception:
        return {}


def _save(session: str, d: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        _path(session).write_text(json.dumps(d))
    except Exception:
        pass


def _prune() -> None:
    now = time.time()
    try:
        for f in STATE_DIR.glob("*.json"):
            if now - f.stat().st_mtime > TTL:
                f.unlink()
    except OSError:
        pass


def _abspath(fp: str) -> str:
    return fp if os.path.isabs(fp) else os.path.join(os.getcwd(), fp)


def _full_read(ti: dict) -> bool:
    """A read with neither offset nor limit — i.e. the whole file."""
    return not ti.get("offset") and not ti.get("limit")


def main() -> None:
    if os.environ.get("REREAD_GUARD") == "0":
        return  # live-session kill-switch
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    event = data.get("hook_event_name", "")
    session = str(data.get("session_id", "") or "")

    if event == "SessionStart":
        try:
            _path(session).unlink()
        except OSError:
            pass
        _prune()
        return

    if data.get("tool_name", "") != "Read":
        return
    ti = data.get("tool_input", {}) or {}
    fp = str(ti.get("file_path", "") or "")
    if not fp:
        return
    ap = _abspath(fp)
    try:
        st = os.stat(ap)
    except OSError:
        return  # can't stat → let the real tool report the error
    if st.st_size < MIN_BYTES or not _full_read(ti):
        return  # small, or a partial read → never interfere

    rec = _load(session)

    if event == "PostToolUse":
        rec[ap] = [int(st.st_mtime), st.st_size]
        _save(session, rec)
        return

    # PreToolUse: block only an unchanged full re-read.
    prev = rec.get(ap)
    if not prev:
        return
    prev_mtime, prev_size = prev
    if st.st_size == prev_size and int(st.st_mtime) <= prev_mtime:
        approx = st.st_size // 4
        rel = os.path.relpath(ap, os.getcwd()) if ap.startswith(os.getcwd()) else ap
        sys.stderr.write(
            f"BLOCKED re-read: {rel} — you already read this file IN FULL this "
            f"session and it is UNCHANGED on disk, so its whole content is already "
            f"above in your context. Re-reading spends ~{approx:,} tokens for zero "
            f"new information. If you need a specific part, re-issue Read with "
            f"offset/limit for just that span. If you mean to change it, use "
            f"Edit/Write directly. (After a /compact this resets — legit re-reads "
            f"pass.)"
        )
        sys.exit(2)
    # changed on disk → allow; refresh happens on the PostToolUse pass.


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open: never wedge a tool call over this guard
