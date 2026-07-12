#!/usr/bin/env python3
"""UserPromptSubmit + SessionStart hook — anti-drift.

Re-injects, every turn, two things so neither the agent nor Ro loses the thread:
  1. NORTH STAR (destination) from `.northstar.md`  — the fixed objective. Stable.
  2. NOW (position)        from `.now.md`           — the CURRENT step. Volatile.
Plus live git context (branch / last commits / dirty) as zero-maintenance ground
truth of what actually happened lately.

Why this shape (see global_orchestration_rules.md "cardinal rule"): a static
"don't drift" banner is advisory prose — the model skims it by turn 20. So
(a) NOW changes every turn → defeats banner-blindness, and (b) every DRIFT_EVERY
turns the banner escalates into a FORCED one-line alignment check, which breaks
autopilot without spending a per-turn model call.

Both files are opt-in per repo (absent → that section is silently skipped).
Keep each file tiny; only OBJECTIVE / NOW is strictly required.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

CAP = 800          # chars per block; a north star that needs more isn't one
DRIFT_EVERY = 5    # escalate the banner into a forced check every N turns
STATE = Path.home() / ".claude" / "hooks" / "state" / "northstar_counts.json"


def repo_root() -> Path:
    start = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    for d in [start, *start.parents]:
        if (d / ".northstar.md").exists() or (d / ".git").exists():
            return d
    return start


MANIFESTS = {"package.json", "pyproject.toml", "requirements.txt", "Cargo.toml",
             "go.mod", "pom.xml", "Gemfile", "composer.json", "Makefile"}
CODE_EXT = {"py", "js", "ts", "tsx", "jsx", "go", "rs", "rb", "java", "swift",
            "c", "cpp", "h", "sh"}


def _looks_like_project(root: Path) -> bool:
    """A dir worth having a north star: a git repo, a manifest, or >=3 code
    files. A brand-new empty/scratch dir stays quiet (nothing to drift on yet)."""
    if root == Path.home():
        return False
    if (root / ".git").exists():
        return True
    try:
        names = {p.name for p in root.iterdir() if p.is_file()}
    except OSError:
        return False
    if names & MANIFESTS:
        return True
    return sum(1 for n in names if n.rsplit(".", 1)[-1] in CODE_EXT) >= 3


def read_block(f: Path) -> str:
    try:
        t = f.read_text(errors="replace").strip()
    except OSError:
        return ""
    return (t[:CAP] + " …(truncated)") if len(t) > CAP else t


def git_context(root: Path) -> str:
    if not (root / ".git").exists():
        return ""

    def g(*a):  # ponytail: 3s timeout is the ceiling; slow `status` on a huge
        try:    # untracked tree just drops the dirty flag, branch/log survive.
            return subprocess.run(
                ["git", "-C", str(root), *a],
                capture_output=True, text=True, timeout=3,
            ).stdout.strip()
        except Exception:
            return ""

    branch = g("rev-parse", "--abbrev-ref", "HEAD")
    if not branch:
        return ""
    log = g("log", "-3", "--pretty=%s")
    dirty = "dirty" if g("status", "--porcelain") else "clean"
    commits = "\n".join("  - " + l for l in log.splitlines())
    return f"GIT: branch {branch} ({dirty}); recent commits:\n{commits}"


def bump(root: Path) -> int:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        d = json.loads(STATE.read_text()) if STATE.exists() else {}
    except Exception:
        d = {}
    n = int(d.get(str(root), 0)) + 1
    d[str(root)] = n
    try:
        STATE.write_text(json.dumps(d))
    except Exception:
        pass
    return n


def main() -> None:
    event = ""
    try:
        raw = sys.stdin.read()
        if raw.strip():
            event = (json.loads(raw) or {}).get("hook_event_name", "")
    except Exception:
        pass

    root = repo_root()
    star = read_block(root / ".northstar.md")
    if not star:
        # Three states, not two:
        #   retired  → .northstar.done present  → stay fully silent
        #   never-set on a REAL project (SessionStart) → NUDGE to establish one
        #             (this is the fix: new projects had no file, so every hook
        #              here was a silent no-op and no agent ever used it)
        #   scratch/empty → silent
        if (root / ".northstar.done").exists():
            return
        if event == "SessionStart" and _looks_like_project(root):
            print(
                "NO NORTH STAR SET for this project. Before any deep work, "
                "establish one WITH Ro: ask him for the one-sentence destination, "
                f"write it to {root}/.northstar.md, and the current step to "
                f"{root}/.now.md (NOW / LAST_VERIFIED / NEXT, <=5 lines). Until "
                "these exist, NOTHING here survives compaction and you WILL "
                "drift. Retire a finished project with `mv .northstar.md "
                ".northstar.done` so this stops firing."
            )
        return  # opt-in: no north star → nudge handled above, else silent

    # On SessionStart only, surface the full resume handoff (too big for every
    # turn). This is what closes the loop: the cold terminal reads it first.
    if event == "SessionStart":
        handoff = (root / ".handoff.md")
        if handoff.exists():
            try:
                h = handoff.read_text(errors="replace").strip()
                if h:
                    print("RESUME HANDOFF (from last compaction — read this "
                          "first; it's the recency-corrected state):\n" + h + "\n")
            except OSError:
                pass

    out = [
        "NORTH STAR — the fixed objective (if your next step doesn't serve this, "
        "STOP and tell Ro):",
        star,
    ]

    now = read_block(root / ".now.md")
    if now:
        out += [
            "",
            "NOW — where we actually are (keep .now.md current; if it's stale vs "
            "what you're doing, fix it before acting):",
            now,
        ]
    else:
        out += [
            "",
            "NOW — no .now.md yet. Create one at repo root (NOW / LAST_VERIFIED / "
            "NEXT, <=5 lines) so the current step survives compaction and Ro can "
            "see it at a glance.",
        ]

    git = git_context(root)
    if git:
        out += ["", git]

    if bump(root) % DRIFT_EVERY == 0:
        out += [
            "",
            f"DRIFT CHECK (fires every {DRIFT_EVERY} turns): in ONE line, state "
            "how your current action serves OBJECTIVE. If it doesn't — stop and "
            "flag it to Ro before doing anything else.",
        ]

    text = "\n".join(out)
    # SessionStart fires once/session and may exceed the 10k additionalContext
    # cap → keep it plain. UserPromptSubmit is the per-turn banner → hide from
    # the transcript, still reaches the model.
    if event == "SessionStart":
        print(text)
    else:
        _hookout.inject("UserPromptSubmit", text)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # never block a prompt over the north star
