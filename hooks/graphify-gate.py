#!/usr/bin/env python3
"""HARD graphify-first gate — the enforcement upgrade over graphify-blindspot.

The blind-spot hook only ADVISES ("maybe run graphify"), and advisories get
skimmed away — measured: graphify was invoked in ~16% of sessions. Ro's ask:
make it USED every time, without reminding. Advisory → DENY.

Contract (two jobs, branch on event):
  * PostToolUse Bash  → if the command ran `graphify query|explain|path|update`,
    mark this session as "graphified" (gate lifts for the rest of the session).
  * PreToolUse Read/Grep → in a repo that HAS `graphify-out/graph.json`, if the
    session has NOT run graphify yet AND the target is source CODE, DENY (exit 2)
    with the exact command to run. First cold code-read is blocked; the moment
    ANY graphify command runs, the gate never fires again this session.

Deliberately narrow so it enforces without wedging:
  * no graphify-out up-tree            → instant no-op (almost every repo / home)
  * already ran graphify this session  → no-op
  * target is .md/.json/.txt/config/a test/graphify-out itself → allowed (you
    must be able to read docs + the map + run the tool)
  * kill-switch env GRAPHIFY_GATE=0    → no-op
  * any internal error                 → fail-open (exit 0), never wedge
"""
import json
import os
import sys
from pathlib import Path

STATE_DIR = Path.home() / ".claude" / "hooks" / "state" / "graphify_ran"
CODE_EXT = {"py", "js", "ts", "tsx", "jsx", "go", "rs", "rb", "java", "swift",
            "c", "cc", "cpp", "h", "hpp", "sh", "vue", "svelte", "php", "scala",
            "kt", "m", "mm"}


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


def _deny(target_desc: str) -> None:
    sys.stderr.write(
        f"GRAPHIFY-FIRST GATE — this repo has a code map, and you haven't queried "
        f"it yet this session. Before cold-reading source ({target_desc}), orient "
        f"from the map:\n"
        f"  graphify query \"<what you're looking for>\"   (scoped subgraph)\n"
        f"  graphify explain \"<file-or-concept>\"          (focused)\n"
        f"  graphify path \"<A>\" \"<B>\"                     (how two things relate)\n"
        f"The moment you run any graphify command this gate lifts for the whole "
        f"session. Reading a specific file you already located via the map is fine "
        f"— run the query first. (kill-switch: GRAPHIFY_GATE=0)"
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

    # --- job 2: PreToolUse Read/Grep → gate cold source browsing ---
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


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open: never wedge a tool call over the gate
