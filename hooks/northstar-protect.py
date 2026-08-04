#!/usr/bin/env python3
"""PreToolUse hook — protect the north star from goal-erosion.

The one fixed point of the anti-drift system is `.northstar.md`. A drifting
agent (which believes it's on-task) can silence its own alarms by softening or
erasing the goal. This hook is the mechanical gate that forbids that.

Covers BOTH attack surfaces:
  1. Write / Edit / MultiEdit whose target IS `.northstar.md`.
  2. The Bash bypass: `echo >`, `sed -i`, `tee`, `chmod`, `mv/cp/rm/truncate`
     targeting `.northstar.md`. (chmod 444 alone is not a gate — the agent can
     `chmod +w` then write; this hook is the real gate.)

GRANT PROTOCOL (Ro, 2026-08-04) — the agent may now edit it, but only after
asking out loud and being told yes:

    agent:  python3 ~/.claude/hooks/northstar-protect.py --request "WHAT: … | WHY: …"
    Ro:     python3 ~/.claude/hooks/northstar-protect.py --grant
    agent:  writes ONCE. The grant is consumed, and expires after 60 min.

Two invariants survive the grant: the request is on record (no silent edit),
and the new content still contains OBJECTIVE / DONE_WHEN / NOT_NOW (no erasing
the goal by "rewriting" it).

Deny protocol: exit 2 + reason on stderr → Claude Code blocks the call and
feeds the reason back to the model. Reads are never blocked. Fail-open on any
internal error (exit 0) — this must never wedge the session.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

TARGET = ".northstar.md"
TTL = 3600  # a grant is good for one hour, one write
REQUIRED_HEADINGS = ("OBJECTIVE", "DONE_WHEN", "NOT_NOW")
STATE = Path(os.path.expanduser("~/.claude/hooks/state/northstar-grant"))

# Bash tokens that MUTATE a file. A command that merely names .northstar.md in a
# read (cat/grep/less) must NOT match — that's the cry-wolf failure we avoid.
# ponytail: denylist of write-verbs; add a pattern if a new bypass shows up.
BASH_MUTATORS = [
    r">>?\s*[^\s|;&<>]*\.northstar\.md",  # > path / >> path (redirect target is ONE token)
    r"\btee\b[^\n]*\.northstar\.md",
    r"\bsed\b[^\n]*-i[^\n]*\.northstar\.md",
    r"\b(?:mv|cp|rm|truncate|dd|install|ln)\b[^\n]*\.northstar\.md",
    r"\bchmod\b[^\n]*\.northstar\.md",
    r"\bchflags\b[^\n]*\.northstar\.md",
]


def _slug(cwd: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", str(cwd)).strip("-") or "root"


def _f(cwd: str) -> Path:
    return STATE / (_slug(cwd) + ".json")


def _read(cwd: str) -> dict:
    try:
        return json.loads(_f(cwd).read_text())
    except Exception:
        return {}


def _save(cwd: str, d: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    _f(cwd).write_text(json.dumps(d))


def deny(reason: str) -> None:
    sys.stderr.write(reason)
    sys.exit(2)


def ask_text(cwd: str) -> str:
    req = _read(cwd).get("request", "(none on record)")
    return (
        f"BLOCKED: {TARGET} is the protected north star.\n"
        "Editable ONLY with Ro's explicit permission, asked for out loud.\n\n"
        "1. Say in chat WHAT you want to change and WHY, then record it:\n"
        '   python3 ~/.claude/hooks/northstar-protect.py --request "WHAT: … | WHY: …"\n'
        "2. Ro grants:  python3 ~/.claude/hooks/northstar-protect.py --grant\n"
        "3. Retry the write ONCE. Keep the OBJECTIVE / DONE_WHEN / NOT_NOW\n"
        "   structure — a rewrite that drops a heading is refused.\n\n"
        f"request on record: {req}"
    )


def check_grant(cwd: str, content) -> None:
    """Allow the write iff a fresh unconsumed grant exists. Consumes it."""
    r = _read(cwd)
    ts = r.get("granted_at", 0)
    if not ts or r.get("consumed") or (time.time() - ts) > TTL:
        deny(ask_text(cwd))
    if content is not None:
        missing = [h for h in REQUIRED_HEADINGS if h not in content]
        if missing:
            deny(
                f"BLOCKED: permission is granted, but this rewrite drops "
                f"{', '.join(missing)} from {TARGET}. The north star keeps its "
                "structure — edit the lines, do not delete the headings."
            )
    r["consumed"] = True
    r["consumed_at"] = time.time()
    _save(cwd, r)


def _try(fn, *a) -> int:
    try:
        fn(*a)
        return 0
    except SystemExit as e:
        return int(e.code or 0)


def _selftest() -> None:
    import tempfile
    global STATE
    ok = True
    with tempfile.TemporaryDirectory() as d:
        STATE = Path(d)
        c, good = "/tmp/x", "OBJECTIVE DONE_WHEN NOT_NOW"
        got = _try(check_grant, c, good)
        ok &= got == 2
        print(("PASS " if got == 2 else "FAIL ") + "no grant denies")
        _save(c, {"request": "r", "granted_at": time.time()})
        for label, want in [("grant allows", 0), ("grant is one-shot", 2)]:
            got = _try(check_grant, c, good)
            ok &= got == want
            print(("PASS " if got == want else "FAIL ") + label)
        _save(c, {"request": "r", "granted_at": time.time()})
        got = _try(check_grant, c, "OBJECTIVE only")
        ok &= got == 2
        print(("PASS " if got == 2 else "FAIL ") + "missing heading denied")
    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


def cli() -> bool:
    """--request / --grant / --status / --selftest. True if handled."""
    if len(sys.argv) < 2 or not sys.argv[1].startswith("--"):
        return False
    cmd, cwd = sys.argv[1], os.getcwd()
    if cmd == "--request":
        text = " ".join(sys.argv[2:]).strip()
        if not text:
            print('usage: --request "WHAT: … | WHY: …"')
            sys.exit(1)
        _save(cwd, {"request": text, "requested_at": time.time()})
        print("REQUEST RECORDED for", cwd)
        print(" ", text)
        print("Ro grants with: python3 ~/.claude/hooks/northstar-protect.py --grant")
    elif cmd == "--grant":
        r = _read(cwd)
        if not r.get("request"):
            print("no request on record for", cwd, "— the agent must --request first")
            sys.exit(1)
        r.update(granted_at=time.time(), consumed=False)
        _save(cwd, r)
        print("GRANTED (one write, 60 min):", r["request"])
    elif cmd == "--status":
        print(json.dumps(_read(cwd), indent=2, default=str))
    elif cmd == "--selftest":
        _selftest()
    else:
        return False
    return True


def main() -> None:
    if cli():
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}
    cwd = data.get("cwd") or os.getcwd()

    if tool in ("Write", "Edit", "MultiEdit"):
        path = str(ti.get("file_path", ""))
        if path.endswith(TARGET) or path.endswith("/" + TARGET):
            # Write carries the whole new file; Edit only a fragment, where a
            # structure check would false-positive, so it is skipped there.
            check_grant(cwd, ti.get("content") if tool == "Write" else None)

    elif tool == "Bash":
        cmd = str(ti.get("command", ""))
        if TARGET in cmd and any(re.search(p, cmd) for p in BASH_MUTATORS):
            check_grant(cwd, None)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)  # fail-open: never wedge a tool call over this guard
