#!/usr/bin/env python3
"""HARD compact-prep gate — Stop hook that enforces the every-turn ritual.

Ro asked three times: run compact-prep every message (update .now.md + STATE
resume point, sync memory/mulch) so nothing important lives only in chat. An
injected reminder doesn't make it happen. A Stop hook can: exit 2 blocks the
turn from ending and feeds the reason back, so the agent must do the ritual
before it can stop.

Wedge-proofing (this fires in EVERY session, including the 4 autonomous repos):
  * rate-limited to one block per RATE_SECS per repo — so a tight autonomous
    loop gets nudged at most once a minute, never spun. In an interactive
    session (turns minutes apart) that's effectively every turn = what Ro wants.
  * CONTENT-HASH aware: the gate passes only when `.now.md`'s current sha256
    DIFFERS from the hash recorded at the last block — i.e. real content changed
    since we last demanded an update. A bare `touch .now.md` (fresh mtime, same
    bytes) no longer satisfies the gate; only an actual edit does.
  * home dir / scratch dir with no project + no .now.md → silent (nothing to
    preserve there).
  * kill-switch env COMPACT_GATE=0 → no-op.  Fail-open on any error.

It intentionally does NOT commit/push (that would race the live autonomous
repos and spam their history — CUT-not-ADD). It enforces the JUDGMENT half
(orientation files current); the mechanical git half stays at real compaction.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RATE_SECS = 60          # max one block per repo per minute (loop guard)
STATE_DIR = Path.home() / ".claude" / "hooks" / "state" / "compact_gate"
MANIFESTS = {"package.json", "pyproject.toml", "requirements.txt", "Cargo.toml",
             "go.mod", "pom.xml", "Gemfile", "composer.json", "Makefile"}
CODE_EXT = {"py", "js", "ts", "tsx", "jsx", "go", "rs", "rb", "java", "swift",
            "c", "cpp", "h", "sh"}


def repo_root() -> Path:
    start = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    for d in [start, *start.parents]:
        if (d / ".northstar.md").exists() or (d / ".now.md").exists() or (d / ".git").exists():
            return d
    return start


def _is_worktree(root: Path) -> bool:
    """True if `root` is a linked git worktree (its `.git` is a FILE, or the
    common git-dir differs from the local git-dir). In that case the real
    orientation files live in the main checkout, so this gate must not fire."""
    if (root / ".git").is_file():
        return True

    def g(*a):
        return subprocess.run(["git", "-C", str(root), *a],
                              capture_output=True, text=True, timeout=3).stdout.strip()

    common = g("rev-parse", "--git-common-dir")
    gitdir = g("rev-parse", "--git-dir")
    if not common or not gitdir:
        return False
    return os.path.realpath(common) != os.path.realpath(gitdir)


def _is_project(root: Path) -> bool:
    if root == Path.home():
        return False
    if (root / ".git").exists() or (root / ".northstar.md").exists() or (root / ".now.md").exists():
        return True
    try:
        names = {p.name for p in root.iterdir() if p.is_file()}
    except OSError:
        return False
    if names & MANIFESTS:
        return True
    return sum(1 for n in names if n.rsplit(".", 1)[-1] in CODE_EXT) >= 3


def _state(root: Path) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(root))[-90:]
    return STATE_DIR / f"{safe or 'root'}.json"


def _last_state(p: Path):
    """Return (last_block_ts, last_block_hash). hash is None when unrecorded."""
    try:
        d = json.loads(p.read_text())
        return float(d.get("ts", 0)), d.get("hash")
    except Exception:
        return 0.0, None


def _now_hash(nowmd: Path) -> str:
    """sha256 of .now.md's bytes; empty-string hash when it doesn't exist."""
    try:
        return hashlib.sha256(nowmd.read_bytes()).hexdigest()
    except Exception:
        return hashlib.sha256(b"").hexdigest()


def _gate_should_block(root: Path, now: float) -> bool:
    """Core decision. True = deny the stop (records block ts+hash first).
    False = pass (rate-window re-stop, or .now.md content genuinely changed
    since the last block)."""
    st = _state(root)
    last_ts, last_hash = _last_state(st)
    # already nudged this repo within the rate window → don't spin
    if now - last_ts < RATE_SECS:
        return False
    cur_hash = _now_hash(root / ".now.md")
    # content really changed since we last demanded an update → satisfied
    if last_hash is not None and cur_hash != last_hash:
        return False
    # record the block time + current hash BEFORE denying, so a re-stop within
    # the window still passes and a touch-only (same hash) keeps blocking.
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        st.write_text(json.dumps({"ts": now, "hash": cur_hash}))
    except Exception:
        pass
    return True


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    if data.get("stop_hook_active"):
        return
    if os.environ.get("COMPACT_GATE") == "0":
        return
    now = time.time()
    root = repo_root()
    # BEHAVIOR CHANGE 2026-07-12: worktree false-positive fix. In a git worktree
    # the real .now.md lives in the MAIN checkout, so it never looks fresh here →
    # infinite re-fire loop. Detect a worktree and treat the gate as satisfied.
    try:
        if _is_worktree(root):
            return
    except Exception:
        pass  # fail-open: on error, continue as normal
    if not _is_project(root):
        return  # home / scratch → nothing to preserve

    if not _gate_should_block(root, now):
        return

    # BEHAVIOR CHANGE 2026-07-12: collapse the multi-line wall to ONE terse line.
    sys.stderr.write("COMPACT-PREP: delegate .now.md + STATE update to a cheap sub-agent before ending (kill: COMPACT_GATE=0)\n")
    sys.exit(2)


def _selftest() -> None:
    import tempfile
    d = Path(tempfile.mkdtemp())
    nowmd = d / ".now.md"
    nowmd.write_text("A")
    t = time.time()
    # first stop demands an update (no prior hash) → block
    assert _gate_should_block(d, t) is True, "first stop should block"
    # re-stop within the rate window → pass (loop guard preserved)
    assert _gate_should_block(d, t) is False, "re-stop within window should pass"
    # touch-only after the window (same bytes, fresh mtime) → still blocks
    assert _gate_should_block(d, t + 2 * RATE_SECS) is True, "touch-only should still block"
    # genuine content change after the window → passes
    nowmd.write_text("B — genuinely different content")
    assert _gate_should_block(d, t + 4 * RATE_SECS) is False, "content change should pass"
    print("PASS")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        try:
            _selftest()
        except AssertionError as e:
            print(f"FAIL: {e}")
            sys.exit(1)
    else:
        try:
            main()
        except Exception:
            sys.exit(0)  # fail-open: never wedge a session close over this gate
