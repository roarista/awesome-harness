#!/usr/bin/env python3
"""Recursive-force `rm` detector for irreversible-pause.py (split out for the
200-line cap). Flags count only directly after a command-position `rm`; targets
that are provably disposable (tmp, $CLAUDE_JOB_DIR, mktemp vars, worktrees, build
output) pass. Audit: docs/audits/2026-10-03/hook-circumvention.md."""
import os
import re
import shlex

RM_FLAGS_LONG = {"--recursive": "r", "--force": "f"}
SAFE_PARTS = {"node_modules", "dist", "build", "out", "__pycache__", ".pytest_cache"}
SAFE_PREFIX = ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")
SAFE_VARS = ("CLAUDE_JOB_DIR", "TMPDIR")
SHELLS = {"bash", "sh", "zsh", "dash"}
PREFIX_CMDS = {"sudo", "command", "xargs", "nice", "time", "env", "exec"}


def _safe_target(t: str, tmpvars: set) -> bool:
    """True iff deleting `t` is disposable: scratch/tmp/job dirs or build output."""
    if ".." in t.split("/"):
        return False
    m = re.match(r"^\$\{?(\w+)\}?(/.*)?$", t)
    if m and m.group(1) in tmpvars:
        return True  # VAR=$(mktemp ...) made it in this same command
    if m and m.group(1) in SAFE_VARS and (m.group(2) or "/").strip("/"):
        return True  # strictly under $CLAUDE_JOB_DIR / $TMPDIR
    if "$" in t or "`" in t or t.startswith("~"):
        return False  # unresolvable expansion, or $HOME: not provably scratch
    for var in SAFE_VARS:
        val = os.environ.get(var, "").rstrip("/")
        if val and (t + "/").startswith(val + "/") and t.rstrip("/") != val:
            return True
    norm = os.path.normpath(t)
    if norm.startswith(SAFE_PREFIX) or re.search(r"(^|/)\.claude/worktrees/[^/]", norm):
        return True
    return bool(SAFE_PARTS & set(norm.split("/")))


def _lex(text: str, comments: bool) -> list:
    lx = shlex.shlex(text, posix=True, punctuation_chars=";&|()")
    lx.whitespace_split = True
    lx.commenters = "#" if comments else ""
    return list(lx)


def _tokens(cmd: str) -> list:
    """Shell tokens with ";" between lines. Per-line so `#` comments end at EOL;
    a quote spanning lines falls back to one whole-command pass."""
    try:
        out = []
        for line in cmd.split("\n"):
            out += _lex(line, True) + [";"]
        return out
    except ValueError:
        try:
            return _lex(cmd.replace("\n", " ; "), False)
        except ValueError:
            return cmd.split()


def rm_is_recursive_force(cmd: str) -> bool:
    """True iff a command-position `rm` has -r AND -f in the flag tokens directly
    after it (never `-Rodrigo` inside a filename) and any target is not provably
    disposable. Quoted heredoc text and quoted arguments are single shlex tokens,
    so `echo "rm -rf /"` is never at command position."""
    toks = _tokens(cmd)
    tmpvars = set(re.findall(r"(\w+)=\$\(\s*mktemp\b", cmd))
    at_cmd, i = True, 0
    while i < len(toks):
        t = toks[i]
        if t and set(t) <= set(";&|()"):
            at_cmd, i = True, i + 1
            continue
        if at_cmd and (t in PREFIX_CMDS or re.match(r"^\w+=", t)):
            i += 1
            continue
        if at_cmd and os.path.basename(t) in SHELLS and toks[i + 1:i + 2] == ["-c"]:
            if i + 2 < len(toks) and rm_is_recursive_force(toks[i + 2]):
                return True
        if at_cmd and os.path.basename(t) == "rm":
            j, flags = i + 1, ""
            while j < len(toks) and toks[j].startswith("-") and toks[j] != "--":
                flags += RM_FLAGS_LONG.get(toks[j], toks[j].lstrip("-") if not toks[j].startswith("--") else "")
                j += 1
            if j < len(toks) and toks[j] == "--":
                j += 1
            targets = []
            while j < len(toks) and not set(toks[j]) <= set(";&|()"):
                targets.append(toks[j])
                j += 1
            if ("r" in flags or "R" in flags) and "f" in flags:
                if not targets or not all(_safe_target(x, tmpvars) for x in targets):
                    return True
            i = j
            continue
        at_cmd, i = False, i + 1
    return False
