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
  * if `.now.md` was modified within RATE_SECS, the ritual clearly just ran →
    pass. So the agent clears the gate simply BY doing the update — no loop.
  * home dir / scratch dir with no project + no .now.md → silent (nothing to
    preserve there).
  * kill-switch env COMPACT_GATE=0 → no-op.  Fail-open on any error.

It intentionally does NOT commit/push (that would race the live autonomous
repos and spam their history — CUT-not-ADD). It enforces the JUDGMENT half
(orientation files current); the mechanical git half stays at real compaction.
"""
import json
import os
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


def _last_block(p: Path) -> float:
    try:
        return float(json.loads(p.read_text()).get("ts", 0))
    except Exception:
        return 0.0


def main() -> None:
    if os.environ.get("COMPACT_GATE") == "0":
        return
    now = time.time()
    root = repo_root()
    if not _is_project(root):
        return  # home / scratch → nothing to preserve

    st = _state(root)
    # already nudged this repo within the rate window → don't spin
    if now - _last_block(st) < RATE_SECS:
        return

    nowmd = root / ".now.md"
    # ritual clearly just ran (or is being run) → pass
    try:
        if nowmd.exists() and now - nowmd.stat().st_mtime < RATE_SECS:
            return
    except OSError:
        pass

    # record the block time BEFORE denying so a re-stop within the window passes
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        st.write_text(json.dumps({"ts": now}))
    except Exception:
        pass

    where = ".now.md is missing" if not nowmd.exists() else ".now.md is stale"
    sys.stderr.write(
        f"COMPACT-PREP GATE — before you end this turn, run the compact-prep "
        f"ritual so nothing lives only in chat ({where} at {root}):\n"
        f"  1. update {root}/.now.md  (NOW / LAST_VERIFIED / NEXT, <=5 lines)\n"
        f"  2. update the STATE / resume point for what you just did\n"
        f"  3. sync durable memory / mulch if a decision or fact changed\n"
        f"  4. then your FINAL message states what was saved + the exact resume "
        f"point.\nDo it now, then stop. (kill-switch: COMPACT_GATE=0)"
    )
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open: never wedge a session close over this gate
