import hashlib
import json
import os
import time

STATE_DIR = os.path.expanduser("~/.claude/hooks/state/once")


def inject(event, text):
    """Print model-only context, hidden from the user's transcript. Caller must exit 0."""
    if not text:
        return
    print(json.dumps({"suppressOutput": True, "hookSpecificOutput": {"hookEventName": event, "additionalContext": text[:10000]}}))


def once(key, session_id="", ttl=0):
    """True the FIRST time this (key, session) pair is seen; False forever after.

    The context-diet primitive (audit 13, 2026-08-02): hook text lands in the
    append-only transcript, so an injection repeated N times is paid N times AND
    re-sent on every later API call. Anything static must be said once per
    session, not once per fire. `ttl` (seconds) re-arms a key for slow-changing
    reminders. Fail-OPEN (returns True) so a broken sentinel never silences a
    guard that had something real to say.
    """
    try:
        sid = session_id or os.environ.get("CLAUDE_SESSION_ID") or "nosession"
        tag = hashlib.sha1(f"{key}\x00{sid}".encode()).hexdigest()[:20]
        os.makedirs(STATE_DIR, exist_ok=True)
        path = os.path.join(STATE_DIR, tag)
        if os.path.exists(path):
            if ttl and (time.time() - os.path.getmtime(path)) > ttl:
                os.utime(path, None)
                return True
            return False
        open(path, "w").close()
        _reap()
        return True
    except Exception:
        return True


def _reap(max_age=7 * 86400):
    """Keep the sentinel dir from growing forever. Best-effort."""
    try:
        cutoff = time.time() - max_age
        for n in os.listdir(STATE_DIR):
            p = os.path.join(STATE_DIR, n)
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
    except Exception:
        pass


def sid_of(payload):
    """Session id out of a hook stdin payload, '' if absent."""
    try:
        return str(payload.get("session_id") or payload.get("sessionId") or "")
    except Exception:
        return ""
