import hashlib
import json
import os
import sys
import time

STATE_DIR = os.path.expanduser("~/.claude/hooks/state/once")
TEMP_ROOTS = ("/private/var/folders/", "/var/folders/", "/private/tmp/", "/tmp/")


def is_product_call(env=None):
    """True for a headless `claude -p` fired by PRODUCT code (virality etc.), not Ro's work.

    Measured 2026-10-03 (docs/audits/2026-10-02/rule-value-audit.md §3): 8,233 of
    those sessions in 45d, every one CLAUDE_CODE_ENTRYPOINT=sdk-cli with cwd under a
    temp dir. Ro's sessions are `cli`; background jobs carry CLAUDE_JOB_DIR; harness
    `claude -p` auditors/builders run from a repo cwd -- all three keep the harness.
    HARNESS_HOOKS=on|off forces either way. Fails CLOSED to False (harness stays on).
    """
    e = os.environ if env is None else env
    try:
        force = e.get("HARNESS_HOOKS", "")
        if force in ("on", "off"):
            return force == "off"
        if not e.get("CLAUDE_CODE_ENTRYPOINT", "").startswith("sdk") or e.get("CLAUDE_JOB_DIR"):
            return False
        return (os.path.realpath(e.get("CLAUDE_PROJECT_DIR") or os.getcwd()) + "/").startswith(TEMP_ROOTS)
    except Exception:
        return False


def exit_if_product():
    """First statement of every registered hook: product calls get no harness at all."""
    if is_product_call():
        sys.exit(0)


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


if __name__ == "__main__":  # shell hooks: `python3 _hookout.py && exit 0`
    sys.exit(0 if is_product_call() else 1)
