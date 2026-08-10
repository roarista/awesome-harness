#!/usr/bin/env python3
"""PreToolUse(Bash) — close the hole `main-edit-guard.py` documents but cannot
cover: the MAIN session writing source code through Bash.

MEASURED 2026-08-02: main wrote 90 of 763 source writes; 55 of those 90 (61%)
went through Bash (heredoc, `sed -i`, `cat >`, `python3 - <<PY`, `git apply`,
`tee`, `patch`, plain `>` redirection). main-edit-guard is registered on
Write|Edit|MultiEdit only and by design sees none of it.

Detection of MAIN vs SUB-AGENT is COPIED from main-edit-guard.py — a sub-agent's
hook payload carries `agent_id`; main's does not. Redirect writes are fenced for
both; only Codex tool invocations are exempt.

FALSE-POSITIVE DISCIPLINE (the `irreversible-pause.py` lesson): we do NOT
substring-match. Heredoc BODIES are stripped before the command line is scanned,
so `cat >> notes.md <<'EOF' ... foo.py ... EOF` cannot trigger on the word
"foo.py" in its text. Only WRITE-SHAPED constructs with an extractable target
are considered.

Modes via env BASH_WRITE_FENCE: enforce (default) | warn | off.
SILENT ON PASS: zero bytes, exit 0, for every non-write Bash call.
Fail-OPEN on any internal error.
"""
import json
import os
import re
import subprocess
import sys

BLOCK_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".sh", ".go", ".rs", ".rb",
             ".java", ".yaml", ".yml", ".json"}
# Path fragments that are ALWAYS allowed for main (orientation / memory / notes).
ALLOW_FRAG = ("/.planning/", "/docs/", "/.mulch/", "/memory/", "/.scratch/",
              "/tmp/", "/.claude/hooks/state/")
ALLOW_BASE = {".now.md", ".northstar.md", ".northstar.done", "MEMORY.md",
              "STATE", "STATE.md", "STATE-ARCHIVE.md"}
CODEX_TOOLS = ("codex-companion.mjs", "codex exec")

HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
INTERP = re.compile(r"\b(python3?|node|ruby|perl|php|bash|sh|zsh)\b")
# write-shaped constructs, each with a capturable target
REDIR = re.compile(r"(?:&>{1,2}|(?<![0-9&])>{1,2})\|?\s*([^\s;|&<>()]+)")
TEE = re.compile(r"\btee\s+(?:-a\s+)?([^\s;|&<>()]+)")
# `-i` capture stops at [^\s]* (attached backup suffix, e.g. -i.bak) then grabs
# the whole remaining statement tail; sed_i_targets() below tokenizes it because
# BSD `sed -i '' script file` puts the (possibly empty) backup suffix as its OWN
# arg — a single positional group can't tell suffix from script from file.
SED_I = re.compile(r"\bsed\s+(?:[^;|&]*?\s)?-i[^\s]*\s+([^;|&]*)")
SED_I_TOKEN = re.compile(r"'[^']*'|\"[^\"]*\"|\S+")
DD_OF = re.compile(r"\bdd\b[^;|&]*?\bof=([^\s;|&<>()]+)")
CPMV = re.compile(r"\b(?:cp|mv|install)\s+(?:-\S+\s+)*\S+\s+([^\s;|&<>()]+)")
PATCHY = re.compile(r"(?:^|[;&|]\s*)(?:git\s+apply|patch)\b")
PATCH_SAFE = re.compile(r"--(?:check|stat|numstat|summary|dry-run)\b")
# in-body writes for `python3 - <<PY` / `python3 -c '...'` / node equivalents
PY_OPEN = re.compile(r"\bopen\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"][wax]")
PY_WT = re.compile(r"['\"]([^'\"]+)['\"]\s*\)?\s*\.\s*write_(?:text|bytes)\(")
JS_WF = re.compile(r"\bwriteFileSync?\(\s*['\"]([^'\"]+)['\"]")
PERL_OPEN = re.compile(r"\bopen\(?\s*\w*\s*,\s*['\"]?>{1,2}([^'\",\s)]+)")
PERL_OPEN_3ARG = re.compile(
    r"\bopen\s*\(\s*\w+\s*,\s*['\"][<>!+-]{1,2}['\"]\s*,\s*['\"]([^'\"]+)['\"]"
)
PERL_OPEN_CONCAT = re.compile(
    r"\bopen\s*\(\s*\w+\s*,\s*['\"][<>!+-]{1,2}['\"]['\"]([^'\"]+)['\"]"
)
# inline-interpreter write: `python3 -c '...'`, `node -e "..."`, `perl -e '...'`
# — MATCH THE WRITE, not the language: any of python3/python/node/nodejs/perl
# followed (anywhere before the flag, flags/args in between are fine) by a
# -c or -e flag carrying a quoted script is scanned with the SAME write-shape
# regexes (PY_OPEN/PY_WT/JS_WF/PERL_OPEN) used for heredoc bodies below.
DASH_C = re.compile(
    r"\b(?:python3?|node|nodejs|perl)\b[^\n;|&]*?-[ce]\s+('([^']*)'|\"([^\"]*)\")"
)
QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")


def mask_quotes(s):
    """Blank out the INTERIOR of quoted args (keep the quote chars + length) so
    redirect-shaped text inside a quoted string (e.g. grep 'cat > x.py') cannot
    be mistaken for an actual shell write."""
    def _mask(m):
        q = m.group(0)
        return q[0] + ("x" * (len(q) - 2)) + q[0]
    return QUOTED.sub(_mask, s)


def is_subagent(data):
    """COPIED from main-edit-guard.py — subagent iff agent_id is present."""
    return bool(data.get("agent_id"))


def split_heredocs(cmd):
    """-> (code_text_without_heredoc_bodies, [(opener_line, body), ...])."""
    lines = cmd.split("\n")
    code, docs, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        code.append(line)
        delims = [m.group(2) for m in HEREDOC.finditer(line)]
        i += 1
        for delim in delims:
            body = []
            while i < len(lines) and lines[i].strip() != delim:
                body.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            docs.append((line, "\n".join(body)))
    return "\n".join(code), docs


def sed_i_target(tail):
    """Pick the FILE arg out of a `sed -i<suffix> ...` tail. BSD sed puts a
    (possibly empty) backup suffix as its OWN token when written `-i ''`, so a
    positional guess is wrong; prefer a token that looks like a path."""
    tokens = [t.strip("'\"") for t in SED_I_TOKEN.findall(tail)]
    i = 0
    while i < len(tokens) and tokens[i] == "-e":
        i += 2
    tokens = tokens[i:]
    path_like = [t for t in tokens if t and ("/" in t or os.path.splitext(t)[1] in BLOCK_EXT
                                              or t.lower().endswith(".md"))]
    if path_like:
        return path_like[-1]
    last = tokens[-1] if tokens else ""
    return last or None


def targets(cmd):
    """Every write-shaped target in `cmd`. Heredoc bodies never contribute text."""
    code, docs = split_heredocs(cmd)
    unquoted = mask_quotes(code)
    out = []
    for rx in (REDIR, TEE, DD_OF, CPMV):
        out += [m.group(1) for m in rx.finditer(unquoted)]
    for m in SED_I.finditer(code):
        t = sed_i_target(m.group(1))
        if t:
            out.append(t)
    for opener, body in docs:
        if INTERP.search(opener):
            for rx in (PY_OPEN, PY_WT, JS_WF, REDIR, TEE):
                out += [m.group(1) for m in rx.finditer(body)]
    for m in DASH_C.finditer(code):
        inner = m.group(2) or m.group(3) or ""
        for rx in (PY_OPEN, PY_WT, JS_WF, PERL_OPEN, PERL_OPEN_3ARG,
                   PERL_OPEN_CONCAT):
            out += [x.group(1) for x in rx.finditer(inner)]
    return [t.strip("'\"") for t in out
            if t and not t.startswith("&") and not t.startswith("/dev/")]


def norm(path, cwd):
    p = path.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    if p.startswith("~"):
        p = os.path.expanduser(p)
    if not p.startswith("/"):
        p = os.path.join(cwd or "/", p)
    return os.path.normpath(p)


def blocked(path, cwd):
    """True iff writing `path` through fenced Bash should be denied."""
    p = norm(path, cwd)
    low = p.lower()
    if os.path.basename(p) in ALLOW_BASE or low.endswith(".md"):
        return False
    if any(f in low for f in ALLOW_FRAG):
        return False
    job = os.environ.get("CLAUDE_JOB_DIR")
    if job and p.startswith(os.path.normpath(job) + "/"):
        return False
    if os.path.splitext(low)[1] not in BLOCK_EXT:
        return False
    # scoped to the repo (per spec); code outside the working tree is not ours
    root = os.path.normpath(cwd) if cwd else None
    return bool(root and (p == root or p.startswith(root + "/")))


def main():
    mode = os.environ.get("BASH_WRITE_FENCE", "enforce").lower()
    if mode == "off" or os.environ.get("CLAUDE_BASH_WRITE_FENCE", "").lower() == "off":
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    cmd = str((data.get("tool_input") or {}).get("command", "") or "")
    if not cmd:
        return
    if any(tool in mask_quotes(cmd) for tool in CODEX_TOOLS):
        return
    cwd = str(data.get("cwd") or os.getcwd())
    hits = [t for t in targets(cmd) if blocked(t, cwd)]
    if not hits:
        code, _ = split_heredocs(cmd)
        if PATCHY.search(code) and not PATCH_SAFE.search(code):
            hits = ["<git apply/patch>"]
    if not hits:
        return  # SILENT: zero bytes, exit 0
    role = "subagent" if is_subagent(data) else "main"
    msg = (f"BASH-WRITE BLOCKED: {role} tried to write source via Bash -> "
           f"{', '.join(sorted(set(hits))[:3])}. Use codex-companion/codex exec "
           f"for code writes. Allowed here: *.md, .planning/, docs/, "
           f".mulch/, memory/, /tmp. Kill: BASH_WRITE_FENCE=off\n")
    sys.stderr.write(msg)
    sys.exit(0 if mode == "warn" else 2)


def _selftest():
    def run(command, subagent=False):
        payload = {"cwd": "/repo", "tool_input": {"command": command}}
        if subagent:
            payload["agent_id"] = "test-subagent"
        env = os.environ.copy()
        env.pop("BASH_WRITE_FENCE", None)
        env.pop("CLAUDE_BASH_WRITE_FENCE", None)
        return subprocess.run(
            [sys.executable, __file__], input=json.dumps(payload), text=True,
            capture_output=True, env=env, check=False,
        ).returncode

    cases = [
        ("perl three-argument open", 'perl -e \'open(F,">>","evil.py")\'', False, 2),
        ("perl concatenated open", 'perl -e \'open(F,">""evil.py")\'', False, 2),
        ("quoted allowlist is not executable", "echo 'codex exec' > evil.py", False, 2),
        ("python inline write", 'python3 -c "open(\'evil.py\',\'w\').write(\'x\')"', False, 2),
        ("bsd sed in-place", "sed -i '' s/a/b/ hooks/x.py", False, 2),
        ("cat redirect", "cat > evil.py", False, 2),
        ("quoted grep example", "command grep -n 'cat > x.py' hooks/bash-write-fence.py", False, 0),
        ("quoted echo example", "echo 'we used cat > foo.py earlier'", False, 0),
        ("python inline read-only", 'python3 -c "print(1)"', False, 0),
        ("markdown heredoc body",
         "cat > notes.md <<'EOF'\ncat > a.py\nEOF", False, 0),
        ("companion allowlist",
         'node /path/to/codex-companion.mjs dispatch "prompt text with > in it"', True, 0),
    ]
    for name, command, subagent, expected in cases:
        actual = run(command, subagent)
        assert actual == expected, f"{name}: rc={actual}, want {expected}"
    print("selftest passed")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open
