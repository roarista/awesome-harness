#!/usr/bin/env python3
"""HARD graphify-first gate — the enforcement upgrade over graphify-blindspot.

The blind-spot hook only ADVISES ("maybe run graphify"), and advisories get
skimmed away — measured: graphify was invoked in ~16% of sessions. Ro's ask:
make it USED every time, without reminding. Advisory → DENY.

Contract (four jobs, branch on event):
  * SessionStart      → CLEAR this session's "graphified" marker, so graphify is
    re-required at the start of every session AND after every /compact (Ro
    compacts a lot; post-compaction the map orientation is gone from context, so
    the agent must re-query before cold-reading source again).
  * PostToolUse Bash  → if the command ran `graphify query|explain|path|update`,
    mark this session as "graphified" (gate lifts until the next SessionStart).
  * PreToolUse Read/Grep → in a repo that HAS `graphify-out/graph.json`, if the
    session has NOT run graphify yet AND the target is source CODE, DENY (exit 2)
    with the exact command to run.
  * PreToolUse Bash   → same gate for the shell-read ESCAPE: reading a code file
    via cat/less/more/head/tail/bat/sed/awk/rg/grep bypassed the Read/Grep gate.
    If the shell command unambiguously reads a source-code file, DENY too.

Deliberately narrow so it enforces without wedging:
  * no graphify-out up-tree            → instant no-op (almost every repo / home)
  * already ran graphify this session  → no-op
  * target is .md/.json/.txt/config/a test/graphify-out itself → allowed (you
    must be able to read docs + the map + run the tool)
  * shell read we can't confidently resolve to a code FILE → allowed (fail-open)
  * kill-switch env GRAPHIFY_GATE=0    → no-op
  * any internal error                 → fail-open (exit 0), never wedge
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

STATE_DIR = Path.home() / ".claude" / "hooks" / "state" / "graphify_ran"
CODE_EXT = {"py", "js", "ts", "tsx", "jsx", "go", "rs", "rb", "java", "swift",
            "c", "cc", "cpp", "h", "hpp", "sh", "vue", "svelte", "php", "scala",
            "kt", "m", "mm"}
# shell tools that read a file's contents (the Read/Grep-gate escape hatch)
READERS = {"cat", "less", "more", "head", "tail", "bat", "sed", "awk", "rg", "grep"}


def _marker(session: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session)[:80]
    return STATE_DIR / f"{safe or 'nosession'}.json"


def _has_graph(start: Path) -> bool:
    for d in [start, *start.parents]:
        if (d / "graphify-out" / "graph.json").exists():
            return True
    return False


def _is_code(fp: str) -> bool:
    ext = fp.rsplit(".", 1)[-1].lower() if "." in os.path.basename(fp) else ""
    if ext not in CODE_EXT:
        return False
    low = fp.replace("\\", "/").lower()
    # docs / the map / obvious test files are always readable
    if "graphify-out/" in low or "/test" in low or low.endswith((".test.ts", ".test.js", ".spec.ts", ".spec.js")):
        return False
    return True


def _bash_code_target(cmd: str):
    """Return the abspath of a code FILE that `cmd` unambiguously reads via a
    known reader tool, else None. Conservative: only trips on an existing code
    file passed to a reader in its own pipeline segment; anything ambiguous
    (globs, patterns with spaces, non-existent paths) → None (allow)."""
    try:
        segments = re.split(r"&&|\|\||;|\||\n", cmd)
    except Exception:
        return None
    for seg in segments:
        try:
            toks = shlex.split(seg)
        except Exception:
            continue
        if not toks or os.path.basename(toks[0]) not in READERS:
            continue
        for tok in toks[1:]:
            if tok.startswith("-"):
                continue
            if any(ch in tok for ch in " \t*?"):
                continue  # a pattern / glob, not a single filename → ambiguous
            if not _is_code(tok):
                continue
            ap = tok if os.path.isabs(tok) else os.path.join(os.getcwd(), tok)
            if os.path.isfile(ap):
                return ap
    return None


def _deny(target_desc: str) -> None:
    sys.stderr.write(
        f"GRAPHIFY-FIRST GATE — repo has code map, not queried this session. "
        f"before cold-reading source ({target_desc}), orient from map:\n"
        f"  graphify query \"<target>\"     (scoped subgraph)\n"
        f"  graphify explain \"<file>\"      (focused)\n"
        f"  graphify path \"<A>\" \"<B>\"      (relation)\n"
        f"any graphify command lifts the gate for the session. run the query first. "
        f"(kill-switch: GRAPHIFY_GATE=0)"
    )
    sys.exit(2)


def main() -> None:
    if os.environ.get("GRAPHIFY_GATE") == "0":
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    event = data.get("hook_event_name", "")
    tool = data.get("tool_name", "")
    session = str(data.get("session_id", "") or "")
    ti = data.get("tool_input", {}) or {}

    # --- job 0: SessionStart → re-arm the gate (new session OR post-compact) ---
    if event == "SessionStart":
        try:
            _marker(session).unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass
        return

    # --- job 1: PostToolUse Bash → record that graphify was used ---
    if event == "PostToolUse" and tool == "Bash":
        cmd = str(ti.get("command", ""))
        if "graphify" in cmd and any(f"graphify {v}" in cmd or f"graphify\t{v}" in cmd
                                     for v in ("query", "explain", "path", "update", "map")):
            try:
                STATE_DIR.mkdir(parents=True, exist_ok=True)
                _marker(session).write_text("1")
            except Exception:
                pass
        return

    # --- job 2: PreToolUse Bash → close the shell-read escape hatch ---
    if event == "PreToolUse" and tool == "Bash":
        if _marker(session).exists():
            return  # graphify already used this session → free
        target = _bash_code_target(str(ti.get("command", "")))
        if target and _has_graph(Path(target).parent):
            _deny(f"shell read {os.path.basename(target)}")
        return

    # --- job 3: PreToolUse Read/Grep → gate cold source browsing ---
    if event != "PreToolUse" or tool not in ("Read", "Grep"):
        return
    if _marker(session).exists():
        return  # graphify already used this session → free

    # locate the target + whether it's inside a graphify repo
    if tool == "Read":
        fp = str(ti.get("file_path", "") or "")
        if not fp:
            return
        abspath = fp if os.path.isabs(fp) else os.path.join(os.getcwd(), fp)
        if not _has_graph(Path(abspath).parent):
            return
        if not _is_code(abspath):
            return
        _deny(os.path.basename(abspath))
    else:  # Grep
        path = str(ti.get("path", "") or os.getcwd())
        base = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
        if not _has_graph(Path(base)):
            return
        # a grep scoped to a code glob / whole tree is exactly "cold browsing"
        _deny(f"grep {ti.get('pattern', '')!r}")


def _selftest() -> None:
    import tempfile
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "graphify-out"))
    with open(os.path.join(d, "graphify-out", "graph.json"), "w") as f:
        f.write("{}")
    with open(os.path.join(d, "foo.py"), "w") as f:
        f.write("x = 1\n")
    with open(os.path.join(d, "README.md"), "w") as f:
        f.write("# hi\n")
    script = os.path.abspath(__file__)

    def run(cmd, session):
        ev = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
              "session_id": session, "tool_input": {"command": cmd}}
        return subprocess.run([sys.executable, script], input=json.dumps(ev),
                              text=True, capture_output=True, cwd=d)

    import subprocess
    # (a) cat foo.py in graphify repo w/o marker → block (exit 2)
    r = run("cat foo.py", "selftest-nomark-a")
    assert r.returncode == 2, f"a: cat foo.py should block, got {r.returncode}"
    # (b) cat README.md (non-code) → allow (exit 0)
    r = run("cat README.md", "selftest-nomark-b")
    assert r.returncode == 0, f"b: cat README.md should allow, got {r.returncode}"
    # (c) marker present → allow even for foo.py
    sess = "selftest-marked-c"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _marker(sess).write_text("1")
    try:
        r = run("cat foo.py", sess)
        assert r.returncode == 0, f"c: marked session should allow, got {r.returncode}"
    finally:
        try:
            _marker(sess).unlink()
        except FileNotFoundError:
            pass
    # (d) pattern-only grep (no code file) → allow
    r = run("grep -n 'import os' foo_notafile", "selftest-nomark-d")
    assert r.returncode == 0, f"d: no resolvable code file should allow, got {r.returncode}"
    print("PASS")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        import subprocess
        try:
            _selftest()
        except AssertionError as e:
            print(f"FAIL: {e}")
            sys.exit(1)
    else:
        try:
            main()
        except Exception:
            sys.exit(0)  # fail-open: never wedge a tool call over the gate
