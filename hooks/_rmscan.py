#!/usr/bin/env python3
"""Recursive-force `rm` detector for irreversible-pause.py (split out for the
200-line cap). Flags count only directly after a command-position `rm`; targets
that are provably disposable (tmp, $CLAUDE_JOB_DIR, mktemp vars, worktrees, build
output) pass, after symlink resolution. Command position resets after separators
and shell keywords; prefix commands (sudo/env/timeout/...) are skipped WITH their
options; `sh -c`/`bash -lc`/`eval` strings are scanned recursively.
Audit: docs/audits/2026-10-03/hook-circumvention.md."""
import os
import re
import shlex

RM_FLAGS_LONG = {"--recursive": "r", "--force": "f"}
SAFE_PARTS = {"node_modules", "dist", "build", "out", "__pycache__", ".pytest_cache"}
SAFE_PREFIX = ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")
SAFE_VARS = ("CLAUDE_JOB_DIR", "TMPDIR")
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
PREFIX_CMDS = {"sudo", "doas", "command", "builtin", "xargs", "nice", "time", "env",
               "exec", "timeout", "gtimeout", "nohup", "stdbuf", "caffeinate", "ionice"}
RESET_WORDS = {"then", "do", "else", "elif", "if", "while", "until", "{", "!", "time"}
PUNCT = set(";&|()")


def _real(p: str) -> str:
    try:
        return os.path.realpath(p)
    except (OSError, ValueError):
        return os.path.normpath(p)


def _safe_target(t: str, tmpvars: set) -> bool:
    """True iff deleting `t` is disposable: scratch/tmp/job dirs or build output."""
    if ".." in t.split("/"):
        return False
    m = re.match(r"^\$\{?(\w+)\}?(/.*)?$", t)
    if m and m.group(1) in tmpvars:
        return True  # VAR=$(mktemp ...) made it in this same command
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


def _is_sep(t: str) -> bool:
    return bool(t) and set(t) <= PUNCT


def _skip_prefix(toks: list, i: int) -> int:
    """Index of the real command after a prefix command at toks[i], skipping its
    options, an option's argument, VAR=x assignments and bare numbers/durations."""
    j = i + 1
    while j < len(toks) and not _is_sep(toks[j]):
        t = toks[j]
        if t.startswith("-") and t != "-":
            nxt = toks[j + 1] if j + 1 < len(toks) else ""
            j += 1
            if (len(t) == 2 and nxt and not nxt.startswith("-") and not _is_sep(nxt)
                    and os.path.basename(nxt) not in {"rm"} | SHELLS | PREFIX_CMDS):
                j += 1  # option argument: `sudo -u ro`, `nice -n 5`
        elif re.match(r"^\w+=", t) or re.match(r"^[\d.]+[smhd]?$", t):
            j += 1
        else:
            break
    return j


def rm_is_recursive_force(cmd: str, depth: int = 0) -> bool:
    """True iff a command-position `rm` has -r AND -f in the flag tokens directly
    after it and any target is not provably disposable."""
    if depth > 4:
        return True  # absurd nesting: refuse to call it safe
    toks = _tokens(cmd)
    tmpvars = set(re.findall(r"(\w+)=\$\(\s*mktemp\b", cmd))
    at_cmd, i = True, 0
    while i < len(toks):
        t = toks[i]
        if _is_sep(t) or (at_cmd and t in RESET_WORDS):
            at_cmd, i = True, i + 1
            continue
        if not at_cmd:
            i += 1
            continue
        base = os.path.basename(t)
        if re.match(r"^\w+=", t):
            i += 1
            continue
        if base in PREFIX_CMDS:
            i = _skip_prefix(toks, i)
            continue
        if base == "eval":
            j = i + 1
            while j < len(toks) and not _is_sep(toks[j]):
                j += 1
            if rm_is_recursive_force(" ".join(toks[i + 1:j]), depth + 1):
                return True
            at_cmd, i = False, j
            continue
        if base in SHELLS:
            j, has_c = i + 1, False
            while j < len(toks) and toks[j].startswith("-") and toks[j] != "--":
                has_c = has_c or (not toks[j].startswith("--") and "c" in toks[j])
                j += 1
            if has_c and j < len(toks) and rm_is_recursive_force(toks[j], depth + 1):
                return True
            at_cmd, i = False, j
            continue
        if base == "rm":
            j, flags = i + 1, ""
            while j < len(toks) and toks[j].startswith("-") and toks[j] != "--":
                flags += RM_FLAGS_LONG.get(toks[j], "" if toks[j].startswith("--") else toks[j][1:])
                j += 1
            if j < len(toks) and toks[j] == "--":
                j += 1
            targets = []
            while j < len(toks) and not _is_sep(toks[j]):
                targets.append(toks[j])
                j += 1
            if ("r" in flags or "R" in flags) and "f" in flags:
                if not targets or not all(_safe_target(x, tmpvars) for x in targets):
                    return True
            i = j
            continue
        at_cmd, i = False, i + 1
    return False
