#!/usr/bin/env python3
"""Recursive-force `rm` detector for irreversible-pause.py (split out for the
200-line cap). ROBUST RULE: any `rm` token ANYWHERE in the token stream with
-r/-R and -f (any spelling) blocks unless every target is provably disposable
(tmp, $CLAUDE_JOB_DIR, a var whose LAST assignment is mktemp, worktrees, build
output; symlinks resolved). So prefixes (sudo/ssh/watch/parallel/...) and
keywords cannot hide it. Strings that become code are scanned recursively:
$(...) and backtick bodies, `sh -c` / `bash -lc`, eval, here-strings fed to a
shell, and arguments piped into a shell (`echo "..." | sh`).
Audit: docs/audits/2026-10-03/hook-circumvention.md."""
import os
import re
import shlex

RM_FLAGS_LONG = {"--recursive": "r", "--force": "f"}
SAFE_PARTS = {"node_modules", "dist", "build", "out", "__pycache__", ".pytest_cache"}
SAFE_PREFIX = ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")
SAFE_VARS = ("CLAUDE_JOB_DIR", "TMPDIR")
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
SUBST = re.compile(r"`([^`]*)`|\$\(((?:[^()]|\([^()]*\))*)\)")
ASSIGN = re.compile(r"(?<![\w$-])(\w+)=(\$\(\s*mktemp\b)?|\b(?:for|read(?:\s+-\w+)*)\s+(\w+)")
REDIR = re.compile(r"^(?:\d*|&)(?:>>?|<)&?")


def _real(p: str) -> str:
    try:
        return os.path.realpath(p)
    except (OSError, ValueError):
        return os.path.normpath(p)


def _tmpvars(cmd: str) -> set:
    """Vars whose LAST assignment in `cmd` is `$(mktemp ...)`."""
    last = {}
    for m in ASSIGN.finditer(cmd):
        if m.group(1):
            last[m.group(1)] = bool(m.group(2))
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


def _lex(text: str, comments: bool) -> list:
    lx = shlex.shlex(text, posix=True, punctuation_chars=";&|()")
    lx.whitespace_split = True
    lx.commenters = "#" if comments else ""
    return list(lx)


def _tokens(cmd: str) -> list:
    """Shell tokens with ";" between lines (per-line so `#` comments end at EOL)."""
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


def _segments(toks: list) -> list:
    """[(separator_before, [words])] for each simple command."""
    segs, cur, sep = [], [], ";"
    for t in toks:
        if t and set(t) <= set(";&|()"):
            segs.append((sep, cur))
            cur, sep = [], t
        else:
            cur.append(t)
    segs.append((sep, cur))
    return [s for s in segs if s[1]]


def _rm_hit(seg: list, k: int, tmpvars: set) -> bool:
    j, flags = k + 1, ""
    while j < len(seg) and seg[j].startswith("-") and seg[j] != "--":
        flags += RM_FLAGS_LONG.get(seg[j], "" if seg[j].startswith("--") else seg[j][1:])
        j += 1
    if not (("r" in flags or "R" in flags) and "f" in flags):
        return False
    targets, skip = [], False
    for t in seg[j:]:
        if skip or t == "--":
            skip = False
            continue
        if REDIR.match(t):
            skip = bool(REDIR.fullmatch(t))  # bare `>` / `2>`: next token is the file
            continue
        targets.append(t)
    return not targets or not all(_safe_target(x, tmpvars) for x in targets)


def rm_is_recursive_force(cmd: str, depth: int = 0) -> bool:
    if depth > 6:
        return True  # absurd nesting: refuse to call it safe
    again = lambda s: bool(s) and rm_is_recursive_force(s, depth + 1)  # noqa: E731
    if any(again(m.group(1) if m.group(1) is not None else m.group(2))
           for m in SUBST.finditer(cmd)):
        return True
    tmpvars, segs = _tmpvars(cmd), _segments(_tokens(cmd))
    for n, (sep, seg) in enumerate(segs):
        bases = [os.path.basename(w) for w in seg]
        has_shell = bool(SHELLS & set(bases))
        for k, w in enumerate(seg):
            if bases[k] == "rm" and _rm_hit(seg, k, tmpvars):
                return True
            if bases[k] in SHELLS:
                j, has_c = k + 1, False
                while j < len(seg) and seg[j].startswith("-") and seg[j] != "--":
                    has_c = has_c or (not seg[j].startswith("--") and "c" in seg[j])
                    j += 1
                if has_c and j < len(seg) and again(seg[j]):
                    return True
            if w == "eval" and again(" ".join(seg[k + 1:])):
                return True
            if w.startswith("<<<") and has_shell:
                if again(w[3:] or (seg[k + 1] if k + 1 < len(seg) else "")):
                    return True
        if sep == "|" and has_shell and n > 0 and again(" ".join(segs[n - 1][1][1:])):
            return True
    return False
