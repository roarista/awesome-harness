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
     "PONYTAIL: lazy senior dev. Stop at the first rung that works (YAGNI → "
     "stdlib → native → 1 line). Delete > add. Shortest diff wins. No "
     "speculative abstraction."),
    ("graphify", _has_graphify,
     "GRAPHIFY-FIRST: this repo has a code-map. Run `graphify query/explain/"
     "path` BEFORE cold-reading source — orient from the map, don't browse "
     "blind or re-read files you can query."),
    ("mulch", _has_mulch,
     "MULCH: check `ml` for prior decisions/conventions/failures before "
     "deciding, and log new decisions with `ml` — don't re-litigate or repeat "
     "a past failure."),
    ("caveman", lambda r: True,
     "MESSAGE DISCIPLINE: ZERO intermediate chat text (call tools silently — no "
     "prose until the end). ONE thorough standalone FINAL summary per turn, and end "
     "every turn compaction-safe (update .now.md + STATE resume point, sync memory/"
     "mulch, state what was saved). Ro reads only the final message."),
    ("routing", lambda r: True,
     "ROUTING: you ORCHESTRATE, you don't build. Delegate code writes/edits to a "
     "codex 5.5 subagent (builder = billing), have glm 5.2 audit it; LLM councils = "
     "Opus-4.8-low + Codex-5.5 + GLM-5.2. Only edit orientation files (.now/.northstar/"
     "STATE/memory) or tiny harness tweaks directly. Ro naming a model overrides this."),
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
    key, _, line = applicable[n % len(applicable)]
    print(f"HARNESS ENFORCE ({key}, active — obey it now): {line}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # never block a prompt over a reminder
