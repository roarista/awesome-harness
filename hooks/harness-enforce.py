#!/usr/bin/env python3
"""UserPromptSubmit hook — anti-decay enforcement of the behavioral harness.

The problem Ro hit: he has to REMIND agents to use ponytail / graphify / mulch.
Why they decay: those three (plus caveman message-discipline) are injected ONCE
at SessionStart and then skimmed-away by turn ~20. The mechanisms that DON'T
decay — northstar, graphify-blindspot, token-discipline — each re-fire on their
own every turn / every action. So the fix isn't a bigger banner (the AGENTS.md
study says more static context HURTS); it's timed re-assertion: one short line
per turn, ROTATING through whichever mechanisms actually apply to this repo, so
each recurs every few turns without ever spamming all of them at once.

Applicability-gated (a mechanism only re-asserts where it's real):
  * ponytail / caveman → always (behavioral, every repo)
  * graphify           → only if `graphify-out/graph.json` exists up-tree
  * mulch              → only if `.mulch` exists up-tree

Add a mechanism = add one MECHS entry. Non-blocking (additionalContext),
fail-open on any error — never wedge a prompt over a reminder.
"""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

STATE = Path.home() / ".claude" / "hooks" / "state" / "enforce_counts.json"


def repo_root() -> Path:
    start = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    for d in [start, *start.parents]:
        if (d / ".git").exists() or (d / ".northstar.md").exists():
            return d
    return start


def _has_graphify(root: Path) -> bool:
    return any((d / "graphify-out" / "graph.json").exists()
               for d in [root, *root.parents])


def _has_mulch(root: Path) -> bool:
    return any((d / ".mulch").exists() for d in [root, *root.parents])


# Each: (key, applies?, one-line re-assertion). Keep every line short — this is
# reinforcement, not documentation. Order = rotation order.
MECHS = [
    ("ponytail", lambda r: True,
     "PONYTAIL: lazy senior dev. first rung that works (YAGNI->stdlib->native->1 line). "
     "delete>add. shortest diff. no speculative abstraction."),
    ("graphify", _has_graphify,
     "GRAPHIFY-FIRST: repo has code-map. `graphify query/explain/path` before cold-reading "
     "source. orient from map, don't browse blind."),
    ("mulch", _has_mulch,
     "MULCH: check `ml` for prior decisions/failures before deciding, log new ones with `ml`. "
     "no re-litigate, no repeat past fail."),
    ("caveman", lambda r: True,
     "MSG DISCIPLINE: zero mid-turn chat, tools silent. narrate urge? log 1 line -> "
     "$CLAUDE_JOB_DIR/tmp/pending.md not chat, expand into ONE final summary. end turn "
     "compaction-safe (update .now.md+STATE, sync memory/mulch). Ro reads final only."),
    ("routing", lambda r: True,
     "ROUTING: orchestrate, don't build. code writes -> codex 5.5 subagent, Opus-4.8-low audits. "
     "councils = Opus-4.8-low+Codex-5.5. edit only orientation files (.now/.northstar/"
     "STATE/memory) or tiny harness tweaks. Ro naming a model overrides."),
]


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
    root = repo_root()
    applicable = [m for m in MECHS if m[1](root)]
    if not applicable:
        return
    n = bump(root)
    caveman = next((m for m in applicable if m[0] == "caveman"), None)
    others = [m for m in applicable if m[0] != "caveman"]
    parts = []
    if caveman is not None:
        parts.append(f"[caveman] {caveman[2]}")
    if others:
        okey, _, oline = others[n % len(others)]
        parts.append(f"[{okey}] {oline}")
    if not parts:  # caveman not applicable and no others (shouldn't happen)
        okey, _, oline = applicable[n % len(applicable)]
        parts.append(f"[{okey}] {oline}")
    _hookout.inject("UserPromptSubmit", "HARNESS ENFORCE (obey now): " + "  ||  ".join(parts))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # never block a prompt over a reminder
