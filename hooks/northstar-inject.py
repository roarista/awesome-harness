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
import re
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

CAP = 800          # chars per block; a north star that needs more isn't one
DRIFT_EVERY = 5    # escalate the banner into a forced check every N turns
STATE = Path.home() / ".claude" / "hooks" / "state" / "northstar_counts.json"
SLOT_HEADER = re.compile(r'^## \[(.+?)\]\s*$')


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


def slot_state_path(root: Path) -> Path:
    slug = str(root).strip("/").replace("/", "_") or "root"
    return Path.home() / ".claude" / "hooks" / "state" / "nowslots" / f"{slug}.json"


def load_slot_map(root: Path) -> dict:
    p = slot_state_path(root)
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def save_slot_map(root: Path, d: dict) -> None:
    p = slot_state_path(root)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d))
    except Exception:
        pass


def parse_now(text: str):
    """Split .now.md into (preamble, {label: body}, [labels in file order]).
    No `## [label]` headers at all -> ({}, {}, []) meaning "flat legacy file",
    caller must fall back to treating the whole text as one implicit block."""
    if "## [" not in text:
        return "", {}, []
    lines = text.splitlines()
    preamble_lines, slots, order = [], {}, []
    cur, cur_lines = None, []
    for ln in lines:
        m = SLOT_HEADER.match(ln)
        if m:
            if cur is not None:
                slots[cur] = "\n".join(cur_lines).strip()
            cur = m.group(1)
            order.append(cur)
            cur_lines = []
        elif cur is None:
            preamble_lines.append(ln)
        else:
            cur_lines.append(ln)
    if cur is not None:
        slots[cur] = "\n".join(cur_lines).strip()
    return "\n".join(preamble_lines).strip(), slots, order


def worktree_label(root: Path):
    """Default slot label = branch name, but only when root is a LINKED git
    worktree (its .git is a file pointing at the real gitdir), not the main repo."""
    gitpath = root / ".git"
    if not gitpath.is_file():
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        return out or None
    except Exception:
        return None


def resolve_slot(root: Path, session_id: str, slots: dict, order: list):
    """Returns (label_or_None, how) — how in claimed|worktree|unclaimed."""
    if session_id:
        smap = load_slot_map(root)
        claimed = smap.get(session_id)
        if claimed and claimed in slots:
            return claimed, "claimed"
    wl = worktree_label(root)
    if wl and wl in slots:
        return wl, "worktree"
    return None, "unclaimed"


def _cap_block(s: str) -> str:
    return (s[:CAP] + " …(truncated)") if len(s) > CAP else s


def now_section(root: Path, session_id: str) -> list:
    f = root / ".now.md"
    try:
        text = f.read_text(errors="replace").strip()
    except OSError:
        text = ""
    if not text:
        return ["", "NOW: no .now.md. create at repo root (NOW/LAST_VERIFIED/NEXT, "
                     "<=5 lines) so current step survives compaction."]
    preamble, slots, order = parse_now(text)
    if not slots:
        # legacy flat file — unchanged behavior
        return ["", "NOW:", _cap_block(text)]
    out = ["", "NOW:"]
    if preamble:
        out.append(_cap_block(preamble))
    label, how = resolve_slot(root, session_id, slots, order)
    if label is None:
        out.append(
            f"UNCLAIMED — no slot for this session. existing slots: {', '.join(order)}. "
            "claim: python3 ~/.claude/hooks/northstar-inject.py --claim <label>"
        )
        return out
    out.append(f"[{label}]")
    out.append(_cap_block(slots.get(label, "")))
    others = [l for l in order if l != label]
    if others:
        parts = []
        for l in others:
            b = " ".join(slots.get(l, "").split())
            parts.append(f"{l}: {b[:40]}")
        out.append("other slots: " + " | ".join(parts))
    return out


def cli_claim(label: str) -> None:
    root = repo_root()
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if not session_id:
        print("no CLAUDE_SESSION_ID env var set; can't claim. "
              "set CLAUDE_SESSION_ID=<id> and retry.")
        return
    smap = load_slot_map(root)
    smap[session_id] = label
    save_slot_map(root, smap)
    print(f"claimed slot '{label}' for session {session_id} in {root}")


def cli_slots() -> None:
    root = repo_root()
    f = root / ".now.md"
    try:
        text = f.read_text(errors="replace") if f.exists() else ""
    except OSError:
        text = ""
    _, _, order = parse_now(text)
    if not order:
        print("no slots (flat/legacy .now.md, or file missing)")
        return
    for l in order:
        print(l)


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
    dirty = "dirty" if g("status", "--porcelain") else "clean"
    return f"GIT: branch {branch} ({dirty})"


def git_context_with_commits(root: Path) -> str:
    """SessionStart-only variant: keep commits, but only if the whole block stays <400B."""
    base = git_context(root)
    if not base:
        return base
    if not (root / ".git").exists():
        return base

    def g(*a):
        try:
            return subprocess.run(
                ["git", "-C", str(root), *a],
                capture_output=True, text=True, timeout=3,
            ).stdout.strip()
        except Exception:
            return ""

    log = g("log", "-3", "--pretty=%s")
    commits = "\n".join("  - " + l for l in log.splitlines())
    full = base + "; recent commits:\n" + commits
    return full if len(full) < 400 else base


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


def state_trim_nudge(root: Path) -> str:
    """SessionStart only: if STATE.md bloated past ~40 non-empty lines, nudge the
    incoming agent to trim it to current scope before deep work (archive rest to
    STATE-ARCHIVE.md — never delete). Judgment trim = the `state-trim` skill; the
    deterministic split is tools/state-distiller.py. Fail-open, advisory."""
    for rel in ("STATE.md", ".planning/STATE.md"):
        f = root / rel
        try:
            if not f.exists():
                continue
            n = sum(1 for ln in f.read_text(errors="replace").splitlines() if ln.strip())
        except OSError:
            continue
        if n > 40:
            return (f"STATE ({rel}) is {n} lines — trim to CURRENT scope before deep work: "
                    "keep canonical model + resume point, move the rest to STATE-ARCHIVE.md "
                    "(never delete). run the `state-trim` skill.\n\n")
    return ""


def main() -> None:
    event = ""
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    try:
        raw = sys.stdin.read()
        if raw.strip():
            data = json.loads(raw) or {}
            event = data.get("hook_event_name", "")
            session_id = data.get("session_id") or session_id
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
            # BEHAVIOR CHANGE 2026-07-12: hidden model-only inject, not raw stdout.
            _hookout.inject(
                "SessionStart",
                "NO NORTH STAR set. before deep work, ask Ro the one-sentence destination, "
                f"write it -> {root}/.northstar.md, current step -> {root}/.now.md "
                "(NOW/LAST_VERIFIED/NEXT, <=5 lines). without these nothing survives compaction, "
                "you drift. retire done project: `mv .northstar.md .northstar.done`."
            )
        return  # opt-in: no north star → nudge handled above, else silent

    # On SessionStart only, surface the full resume handoff (too big for every
    # turn). This is what closes the loop: the cold terminal reads it first.
    session_prefix = ""
    if event == "SessionStart":
        for rel in (".planning/COMPACT_HANDOFF.md", ".handoff.md"):
            handoff = root / rel
            if handoff.exists():
                session_prefix = f"RESUME HANDOFF: {rel} (read it if resuming)\n\n"
                break
        session_prefix += state_trim_nudge(root)

    out = [
        "NORTH STAR:",
        star,
    ]

    out += now_section(root, session_id)

    git = git_context_with_commits(root) if event == "SessionStart" else git_context(root)
    if git:
        out += ["", git]

    if bump(root) % DRIFT_EVERY == 0:
        out += [
            "",
            f"DRIFT CHECK (every {DRIFT_EVERY} turns): 1 line, how current action serves "
            "OBJECTIVE. doesn't? stop, flag Ro first.",
        ]

    text = "\n".join(out)
    # BEHAVIOR CHANGE 2026-07-12: SessionStart output now goes through the hidden
    # inject path too (model-only, off the terminal) instead of raw stdout, so
    # nothing dumps into Ro's terminal. UserPromptSubmit was already hidden.
    if event == "SessionStart":
        _hookout.inject("SessionStart", session_prefix + text)
    else:
        _hookout.inject("UserPromptSubmit", text)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--claim":
        cli_claim(sys.argv[2])
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--slots":
        cli_slots()
        sys.exit(0)
    try:
        main()
    except Exception:
        sys.exit(0)  # never block a prompt over the north star
