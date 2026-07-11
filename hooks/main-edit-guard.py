#!/usr/bin/env python3
"""PreToolUse(Write|Edit|MultiEdit) — force the MAIN session to delegate all
file writes to sub-agents. Sub-agents' own edits are still allowed (else nothing
could ever write). Ro's rule: the main orchestrator edits NOTHING; a sub-agent
does every write, incl. .now.md / STATE / settings / memory.

The crux is telling MAIN from a SUB-AGENT. The real discriminator: a SUB-AGENT
tool call's hook payload carries `agent_id` (and `agent_type`); a MAIN-session
tool call does NOT. subagent iff `agent_id` is present. The old `/tasks/`
transcript_path heuristic NEVER fired because transcript_path (and session_id)
are IDENTICAL for main and its subagents — verified empirically 2026-07-11 via a
full-stdin dump.

Modes via env MAIN_EDIT_GUARD:
  off / unset -> no-op (DEFAULT — safe; does nothing until enabled)
  log         -> append role+path to state/main-edit-guard.log, ALLOW (observe)
  enforce     -> SUB allowed; MAIN denied (exit 2) with a delegate-it message
Kill-switch: write `off` to state/main-edit-guard.mode (overrides env, live,
no restart), or MAIN_EDIT_GUARD=off. Fail-open on any error.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG = Path.home() / ".claude" / "hooks" / "state" / "main-edit-guard.log"


def is_subagent(data: dict) -> bool:
    # A subagent's hook payload carries agent_id/agent_type; main's does not.
    # transcript_path is identical for both (same session_id) so the old
    # /tasks/ heuristic never fired — verified empirically 2026-07-11 via
    # full-stdin dump.
    return bool(data.get("agent_id"))


def _mode() -> str:
    # Control file overrides env so the mode can flip LIVE, mid-session, across
    # every running session without a restart (hooks spawn per tool call → fresh read).
    f = Path.home() / ".claude" / "hooks" / "state" / "main-edit-guard.mode"
    try:
        v = f.read_text().strip().lower()
        if v in ("off", "log", "enforce"):
            return v
    except Exception:
        pass
    return os.environ.get("MAIN_EDIT_GUARD", "off").lower()


def main() -> None:
    mode = _mode()
    if mode in ("", "off"):
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    sub = is_subagent(data)
    role = "SUB" if sub else "MAIN"

    if mode == "log":
        try:
            LOG.parent.mkdir(parents=True, exist_ok=True)
            fp = (data.get("tool_input", {}) or {}).get("file_path", "")
            with LOG.open("a") as f:
                f.write(f"{datetime.now().isoformat()}\trole={role}\t"
                        f"tp={data.get('transcript_path','')}\t"
                        f"tool={data.get('tool_name','')}\tfile={fp}\n")
        except Exception:
            pass
        return  # observe only

    if mode == "enforce" and not sub:
        fp = (data.get("tool_input", {}) or {}).get("file_path", "")
        sys.stderr.write(
            "MAIN-EDIT GUARD — the main orchestrator must not edit files "
            "directly; delegate this write to a sub-agent (see "
            "~/.claude/CLAUDE.md delegation default). "
            f"file: {os.path.basename(str(fp))}. (kill-switch: write `off` to "
            "state/main-edit-guard.mode (overrides env, live, no restart), or "
            "MAIN_EDIT_GUARD=off)\n"
        )
        sys.exit(2)
    # enforce + subagent, or any other mode -> allow


def _selftest() -> None:
    cases = [
        ({"agent_id": "a1b2", "agent_type": "general-purpose"}, True),
        ({}, False),
        ({"transcript_path": "/x/tasks/a.jsonl"}, False),  # no agent_id = main
    ]
    ok = True
    for d, want in cases:
        got = is_subagent(d)
        ok &= got == want
        print(f"  is_subagent(agent_id={d.get('agent_id','-')}) = {got} (want {want})")
    # unset env AND isolate from the live control file (point HOME at a temp
    # dir so _mode() finds no .mode file) -> falls back to unset env -> no-op.
    os.environ.pop("MAIN_EDIT_GUARD", None)
    import tempfile
    _home = os.environ.get("HOME")
    os.environ["HOME"] = tempfile.mkdtemp()
    try:
        assert main() is None
    finally:
        if _home is not None:
            os.environ["HOME"] = _home
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open
