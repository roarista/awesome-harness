#!/usr/bin/env python3
"""Target-safety rules for _rmscan.py (split out for the 200-line cap).

A delete target is disposable only if it is tmp, $CLAUDE_JOB_DIR/$TMPDIR under a
sub-path, a git worktree, build output, or a shell var whose LAST assignment in the
same command is `$(mktemp ...)` or an UNQUOTED LITERAL path that is itself
disposable (`M=/tmp/x; rm -rf $M`). A literal must be a whole standalone
assignment (followed by ; & | newline or end) — `M=/tmp/x rm -rf $M` expands the
OLD $M, so it does not count. Reassignment to anything else re-arms the block.
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


def _literal_safe(cmd: str, blanked: str, m) -> bool:
    """True iff ASSIGN match `m` is an unquoted standalone literal scratch path."""
    if m.group(2) or not m.group(1) or blanked[m.start(1)] == " ":
        return False  # mktemp handled elsewhere; `for`/`read`; or inside quotes
    v = LITVAL.match(blanked, m.end())
    return bool(v) and _safe_target(v.group(1), set())


def _tmpvars(cmd: str, outer: frozenset = frozenset()) -> set:
    """Vars whose LAST assignment (outer scope first, then `cmd`) is mktemp or a
    literal disposable path."""
    last = dict.fromkeys(outer, True)
    blanked = QUOTED.sub(lambda q: " " * len(q.group()), cmd)
    for m in ASSIGN.finditer(cmd):
        if m.group(1):
            last[m.group(1)] = bool(m.group(2)) or _literal_safe(cmd, blanked, m)
        else:
            last[m.group(3)] = False
    return {k for k, v in last.items() if v}


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
