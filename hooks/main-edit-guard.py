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

LIMITATIONS (by design): this hook is registered on Write|Edit|MultiEdit ONLY.
Bash writes — `sed -i`, heredocs, `python3 -c 'open(...,"w")'`, `make`, `npm run
build`, `git apply` — bypass it entirely and always will. That is deliberate:
matching writes in a shell command line requires parsing an unparseable
language, and every false positive on a hard exit-2 gate wedges a real tool
call. Treat this as a BEHAVIORAL NUDGE, not a sandbox. The real backstop is
`builder-fence.postflight()`'s `git status --porcelain` diff review plus the
audit step. If true enforcement is ever wanted, the correct mechanism is a
`deny` permission rule or a git pre-commit hook — not a command-line regex.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

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
        # MAIN session: allow orientation files silently, BLOCK everything else
        # (code) so the main orchestrator can't write code directly.
        fp = str((data.get("tool_input", {}) or {}).get("file_path", "") or "")
        base = os.path.basename(fp)
        low = fp.replace("\\", "/")
        # Normalise so a RELATIVE payload (".scratch/discovery/x.md" or
        # "./.scratch/x.md") hits the same "/<dir>/" substring tests as an
        # absolute one. (Do NOT use lstrip("./") — it would eat the leading
        # dot of ".scratch".)
        if low.startswith("./"):
            low = low[2:]
        if not low.startswith("/"):
            low = "/" + low
        orientation = (
            base in (".northstar.md", ".northstar.done", "MEMORY.md", ".now.md",
                     "STATE", "STATE.md", "STATE-ARCHIVE.md")
            or "/memory/" in low
            or "/.scratch/" in low
            or "/.mulch/" in low
        )
        if orientation:
            return  # allow silently
        sys.stderr.write(
            f"MAIN-EDIT BLOCKED: {base} — main orchestrates, subagents write "
            f"code; delegate it. (allowed: orientation/.now/STATE/memory/"
            f".scratch/.mulch; "
            f"kill: MAIN_EDIT_GUARD=off)\n"
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
    # orientation allowlist (FIX 1): absolute AND relative payloads
    for fp, want_allowed in [
        ("/r/.scratch/discovery/foo.md", True),
        (".scratch/discovery/foo.md", True),
        ("./.scratch/discovery/foo.md", True),
        ("/r/.mulch/x.md", True),
        ("/r/.now.md", True), (".now.md", True),
        ("/r/STATE.md", True), ("/r/STATE", True),
        ("/r/.northstar.md", True), ("/r/memory/m.md", True),
        ("/r/src/runner.py", False), ("/r/scratch/foo.md", False),
    ]:
        base = os.path.basename(fp)
        low = fp.replace("\\", "/")
        if low.startswith("./"):
            low = low[2:]
        if not low.startswith("/"):
            low = "/" + low
        got = (base in (".northstar.md", ".northstar.done", "MEMORY.md", ".now.md",
                        "STATE", "STATE.md", "STATE-ARCHIVE.md")
               or "/memory/" in low or "/.scratch/" in low or "/.mulch/" in low)
        ok &= got == want_allowed
        print(f"  orientation({fp}) = {got} (want {want_allowed})")
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open
