#!/usr/bin/env python3
"""Ornith scaffold-ledger v1 (software analog, no GPUs).

A "scaffold" = the verified APPROACH for a task-category (how to decompose/route/
retry it), not the code. We capture it only when the work actually PASSED the
deterministic verifier (check-all), and we keep the CHEAPEST one — promote-on-beat
means a new approach replaces the old only if it passed in fewer iterations.

Scaffolds live as markdown in ~/.claude/scaffolds/ so memgraph indexes them and
`recall` re-injects them next time the same category comes up. That's the loop:
  verify -> capture -> recall -> beat -> replace.

The verifier must stay OUTSIDE the builder's control: this script is meant to be
called by the orchestrator / check-all gate AFTER a real PASS, never by the coder
subagent mid-task. Rotating-auditor signoff is the human-side guard.

Usage:
  scaffold-record.py <category> <iterations_to_pass> [--auditor MODEL] < approach.md
  echo "APPROACH ..." | scaffold-record.py db-migration 2 --auditor sonnet-4.6

Exit 0 = recorded or kept-existing (better wins); always non-fatal.
"""
import sys
import re
from pathlib import Path

SCAFFOLD_DIR = Path.home() / ".claude" / "scaffolds"


def parse_iters(text: str):
    m = re.search(r"^iterations_to_pass:\s*(\d+)", text, re.M)
    return int(m.group(1)) if m else None


def main() -> int:
    args = [a for a in sys.argv[1:]]
    auditor = "unspecified"
    if "--auditor" in args:
        i = args.index("--auditor")
        auditor = args[i + 1] if i + 1 < len(args) else auditor
        del args[i:i + 2]
    if len(args) < 2:
        print("usage: scaffold-record.py <category> <iterations> [--auditor M] < approach.md", file=sys.stderr)
        return 0
    category = re.sub(r"[^a-z0-9-]", "-", args[0].lower()).strip("-")
    try:
        iters = int(args[1])
    except ValueError:
        print("iterations must be an integer", file=sys.stderr)
        return 0
    approach = sys.stdin.read().strip()
    if not approach:
        print("no approach on stdin — nothing recorded", file=sys.stderr)
        return 0

    SCAFFOLD_DIR.mkdir(parents=True, exist_ok=True)
    f = SCAFFOLD_DIR / f"scaffold-{category}.md"

    if f.exists():
        old = f.read_text(errors="replace")
        old_iters = parse_iters(old)
        if old_iters is not None and iters >= old_iters:
            print(f"kept existing scaffold for '{category}' "
                  f"(existing {old_iters} <= new {iters} iters — not beaten)")
            return 0

    body = (
        "---\n"
        f"name: scaffold-{category}\n"
        f"description: Verified approach for {category} tasks (passed check-all in {iters} iter(s))\n"
        "metadata:\n"
        "  type: reference\n"
        "  scaffold: true\n"
        f"iterations_to_pass: {iters}\n"
        f"auditor: {auditor}\n"
        "---\n\n"
        f"# Scaffold — {category}\n\n"
        f"**Verified approach** (check-all PASS in {iters} iteration(s); auditor: {auditor}).\n"
        "Re-use this decomposition/routing before improvising a new one. "
        "Beat it (fewer iterations) to replace it.\n\n"
        f"{approach}\n"
    )
    f.write_text(body)
    print(f"recorded scaffold '{category}' @ {iters} iter(s) -> {f}")
    return 0


def _demo():
    # self-check: promote-on-beat logic
    assert parse_iters("iterations_to_pass: 3\nfoo") == 3
    assert parse_iters("no field here") is None
    print("demo ok")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--demo":
        _demo()
    else:
        sys.exit(main())
