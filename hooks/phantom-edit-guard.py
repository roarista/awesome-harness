#!/usr/bin/env python3
"""PostToolUse(Write|Edit|MultiEdit) — phantom-edit guard, LOG MODE ONLY.

Pattern lifted from `mumei`: record which files are ACTUALLY edited vs what a
task DECLARED it would touch, so "phantom edits" (writes outside the declared
set) can eventually be caught. We don't yet have a reliable declared-file-set
wired in, so this starts PURELY OBSERVATIONAL — it logs every edit and allows.

Logged per edit: file path, tool, and subagent-vs-main role (subagent iff the
hook payload carries `agent_id`, same signal as main-edit-guard.py; main's
payload has no agent_id) -> state/phantom-edit.jsonl.

Modes via env PHANTOM_EDIT_GUARD:
  off / unset -> no-op (DEFAULT — safe; does nothing)
  log         -> append edit record, ALLOW (observe; current wired mode)
  enforce     -> RESERVED. For now behaves EXACTLY like `log` (no blocking).
                 See the TODO block in main() for where divergence-blocking goes.
NEVER blocks today. Fail-open on any error (exit 0 always). stdlib only.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG = Path.home() / ".claude" / "hooks" / "state" / "phantom-edit.jsonl"


def is_subagent(data: dict) -> bool:
    # A subagent's hook payload carries agent_id/agent_type; main's does not.
    # transcript_path is identical for both (same session_id) so the old
    # /tasks/ heuristic never fired — verified empirically 2026-07-11.
    return bool(data.get("agent_id"))


def edited_paths(data: dict):
    """Extract file path(s) from Write/Edit/MultiEdit tool_input."""
    ti = data.get("tool_input") or {}
    fp = ti.get("file_path")
    if fp:
        return [str(fp)]
    # MultiEdit variants sometimes nest edits; best-effort
    edits = ti.get("edits")
    if isinstance(edits, list):
        return [str(e.get("file_path")) for e in edits if isinstance(e, dict) and e.get("file_path")]
    return [""]


def _mode() -> str:
    # Control file overrides env so the mode can flip LIVE, mid-session, across
    # every running session without a restart (hooks spawn per tool call → fresh read).
    f = Path.home() / ".claude" / "hooks" / "state" / "phantom-edit-guard.mode"
    try:
        v = f.read_text().strip().lower()
        if v in ("off", "log", "enforce"):
            return v
    except Exception:
        pass
    return os.environ.get("PHANTOM_EDIT_GUARD", "off").lower()


def main() -> None:
    mode = _mode()
    if mode in ("", "off"):
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    role = "SUB" if is_subagent(data) else "MAIN"

    # log (and, for now, enforce) both just observe + allow.
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            for fp in edited_paths(data):
                f.write(json.dumps({
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "role": role,
                    "tool": data.get("tool_name", ""),
                    "file": fp,
                    "tp": data.get("transcript_path", ""),
                }, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # ------------------------------------------------------------------ #
    # TODO(enforce): divergence-blocking, NOT YET IMPLEMENTED.
    #   When a reliable "declared file set" for the active task exists
    #   (e.g. written by a planning step to state/declared-files/<sid>.json),
    #   load it here and compare against edited_paths(data):
    #       declared = load_declared(session_id)
    #       if mode == "enforce" and fp not in declared and not bypass():
    #           sys.stderr.write("PHANTOM-EDIT GUARD — <fp> not in declared "
    #                            "set for this task. (bypass: BYPASS=1)\n")
    #           sys.exit(2)   # block
    #   BYPASS escape sketch:
    #       def bypass(): return os.environ.get("BYPASS") == "1"
    #   Until then, `enforce` deliberately falls through to ALLOW below.
    # ------------------------------------------------------------------ #
    return  # observe only


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
    p1 = edited_paths({"tool_input": {"file_path": "/a/b.py"}})
    p2 = edited_paths({"tool_input": {"edits": [{"file_path": "/a/c.py"}, {"file_path": "/a/d.py"}]}})
    ok &= p1 == ["/a/b.py"] and p2 == ["/a/c.py", "/a/d.py"]
    print(f"  edited_paths(single) = {p1}")
    print(f"  edited_paths(multi)  = {p2}")
    os.environ.pop("PHANTOM_EDIT_GUARD", None)  # unset -> no-op
    assert main() is None
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open
