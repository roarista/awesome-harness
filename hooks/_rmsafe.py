#!/usr/bin/env python3
"""Target-safety rules for _rmscan.py (split out for the 200-line cap).

A delete target is disposable only if it is tmp, $CLAUDE_JOB_DIR/$TMPDIR under a
sub-path, a git worktree, build output, or a shell var whose LAST assignment in the
same command is `$(mktemp ...)` or an UNQUOTED LITERAL path that is itself
disposable (`M=/tmp/x; rm -rf $M`), with every assignment safe and none after a
use (see _tmpvars). A literal must be a whole standalone, unconditional
assignment — `M=/tmp/x rm -rf $M` expands the OLD $M and `false && M=...` may
never run, so neither counts. Reassignment to anything else re-arms the block.
U10 2026-10-03 (.artifacts/agent-reports/hook-impact-2026-10-03.md row 11).
"""
import os
import re

SAFE_PARTS = {"node_modules", "dist", "build", "out", "__pycache__", ".pytest_cache"}
SAFE_PREFIX = ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")
SAFE_VARS = ("CLAUDE_JOB_DIR", "TMPDIR")
ASSIGN = re.compile(r"(?<![\w$-])(\w+)=(\$\(\s*mktemp\b)?|\b(?:for|read(?:\s+-\w+)*)\s+(\w+)")
# literal value: no expansion/quote/glob chars, then only blanks up to a separator
LITVAL = re.compile(r"([^\s;&|$`'\"()<>\\*?\[\]{}]+)(?=[ \t]*(?:[;&|\n]|$))")
QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"|\'[^\']*\'')


def _real(p: str) -> str:
    try:
        return os.path.realpath(p)
    except (OSError, ValueError):
        return os.path.normpath(p)


def _real_assign(blanked: str, m) -> bool:
    """Unquoted and unconditional: at command start, or after ; / newline / export."""
    if blanked[m.start(1)] == " ":
        return False  # inside quotes: data, not an assignment
    pre = re.sub(r"(?:\bexport\s+)?$", "", blanked[:m.start(1)]).rstrip(" \t")
    return pre == "" or pre[-1] in ";\n"


def _assign_safe(blanked: str, m) -> bool:
    if not _real_assign(blanked, m):
        return False
    if m.group(2):
        return True  # $(mktemp ...)
    v = LITVAL.match(blanked, m.end())
    return bool(v) and _safe_target(v.group(1), set())


def _tmpvars(cmd: str, outer: frozenset = frozenset()) -> set:
    """Vars that hold scratch at EVERY use: each assignment in `cmd` is a real
    mktemp/literal-scratch one and no `$VAR` reference precedes the first of them
    (or the var was already scratch in the outer scope). Stricter than "last
    assignment before the rm": a later unsafe reassignment also blocks."""
    blanked = QUOTED.sub(lambda q: " " * len(q.group()), cmd)
    events = {}
    for m in ASSIGN.finditer(cmd):
        if m.group(1):
            events.setdefault(m.group(1), []).append((m.start(), _assign_safe(blanked, m)))
        else:
            events.setdefault(m.group(3), []).append((m.start(), False))
    out = set()
    for var in set(outer) | set(events):
        ev = events.get(var, [])
        if not all(ok for _, ok in ev):
            continue
        if var not in outer:
            ref = re.search(r"\$\{?" + re.escape(var) + r"\b", cmd)
            if ref and ref.start() < ev[0][0]:
                continue  # used before it is assigned: inherited value
        out.add(var)
    return out


def _safe_target(t: str, tmpvars: set) -> bool:
    """True iff deleting `t` is disposable: scratch/tmp/job dirs or build output."""
    if ".." in t.split("/"):
        return False
    m = re.match(r"^\$\{?(\w+)\}?(/.*)?$", t)
    if m and m.group(1) in tmpvars:
        return True
    if m and m.group(1) in SAFE_VARS:
        sub = (m.group(2) or "").strip("/")
        val = os.environ.get(m.group(1), "").rstrip("/")
        if not sub:
            return False
        if not val:
            return True  # unset here; strictly under the job/tmp dir by name
        t = val + "/" + sub
    if "$" in t or "`" in t or t.startswith("~"):
        return False  # unresolvable expansion, or $HOME: not provably scratch
    real = _real(t.rstrip("/") or "/")
    for var in SAFE_VARS:
        val = os.environ.get(var, "").rstrip("/")
        if val and real.startswith(_real(val) + "/"):
            return True
    if real.startswith(SAFE_PREFIX) or re.search(r"/\.claude/worktrees/[^/]", real):
        return True
    return bool(SAFE_PARTS & set(real.split("/")))
