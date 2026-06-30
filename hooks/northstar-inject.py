#!/usr/bin/env python3
"""UserPromptSubmit hook — re-injects a repo's NORTH STAR every turn so agents
stop drifting off the main objective. Dormant unless the repo opts in by adding a
`.northstar.md` at its root. Stdout becomes context. CPU: one small file read.

.northstar.md format (keep it <= ~6 lines; only OBJECTIVE is required):
    OBJECTIVE: <the one big thing this work is for>
    DONE_WHEN: <the verifiable end-state>
    NOT_NOW:   <explicitly out of scope — what NOT to wander into>
    UPDATED:   <date>
"""
import os
import sys
from pathlib import Path

CAP = 800  # chars; a north star that needs more than this isn't a north star


def repo_root() -> Path:
    # honor Claude Code's project dir, else cwd; walk up to a git root if present
    start = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    for d in [start, *start.parents]:
        if (d / ".northstar.md").exists() or (d / ".git").exists():
            return d
    return start


def main() -> None:
    f = repo_root() / ".northstar.md"
    if not f.exists():
        return  # opt-in: no file → silent no-op
    text = f.read_text(errors="replace").strip()
    if not text:
        return
    if len(text) > CAP:
        text = text[:CAP] + " …(truncated)"
    print("NORTH STAR (current objective — do not drift; if a task isn't serving "
          "this, stop and flag it):\n" + text)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # never block a prompt over the north star
