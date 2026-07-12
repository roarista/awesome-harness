#!/usr/bin/env python3
"""Graphify blind-spot advisory — objective "map before you edit" nudge.

The problem: an agent can't self-diagnose "I don't understand this pipeline."
A file it's been editing for 20 turns *feels* familiar even if it never looked
at what calls it. So instead of asking the agent to judge familiarity, we let
the CODE-MAP judge it: if you're about to edit a file that other files depend
on, and you have NOT opened any of those dependents this session, that's an
objective blind spot — a change here can silently break callers you've never
seen. Only then do we surface the map.

Two jobs, one file (branch on event/tool):
  * PostToolUse on Read   → record the file into this session's read-set.
  * PreToolUse  on Edit/Write/MultiEdit → if the target has >= MIN_UNREAD
    dependents NOT in the read-set, inject a non-blocking advisory naming them
    and pointing at `graphify explain`.

Self-scoping by construction:
  * No `graphify-out/graph.json` up-tree  → instant no-op (almost every repo).
  * File with no / few callers            → never fires (leaf scripts are safe).
  * Dependents already read this session   → never fires (you did the homework).

Never blocks (advisory via additionalContext). Fail-open on any error.
"""
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

DEPS = {"calls", "imports", "imports_from", "references", "inherits",
        "method", "re_exports", "defines"}
MIN_UNREAD = 3        # ponytail: coupling threshold; lower = more advisories.
STATE_DIR = Path.home() / ".claude" / "hooks" / "state"
READSET_DIR = STATE_DIR / "blindspot_readset"
INDEX_DIR = STATE_DIR / "blindspot_idx"
MAX_LIST = 6          # dependents to name in the advisory
SESSION_TTL = 2 * 86400   # prune read-sets older than 2 days


def _emit(ctx: str) -> None:
    """Non-blocking advisory injection, hidden from the transcript. Only ever
    called on the PreToolUse(Edit/Write) branch → event stays PreToolUse."""
    _hookout.inject("PreToolUse", ctx)


def _find_graph(start: Path):
    for d in [start, *start.parents]:
        g = d / "graphify-out" / "graph.json"
        if g.exists():
            return d, g
    return None, None


def _prune_old(d: Path) -> None:
    now = time.time()
    try:
        for f in d.glob("*.json"):
            if now - f.stat().st_mtime > SESSION_TTL:
                f.unlink()
    except OSError:
        pass


def _readset_path(session: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session)[:80]
    return READSET_DIR / f"{safe or 'nosession'}.json"


def _load_readset(session: str) -> set:
    try:
        return set(json.loads(_readset_path(session).read_text()))
    except Exception:
        return set()


def _add_readset(session: str, rel: str) -> None:
    p = _readset_path(session)
    try:
        READSET_DIR.mkdir(parents=True, exist_ok=True)
        cur = _load_readset(session)
        cur.add(rel)
        p.write_text(json.dumps(sorted(cur)))
    except Exception:
        pass


def _build_index(graph: Path) -> dict:
    """{source_file: [files that reference symbols defined in it]}. Cached to
    disk keyed by the graph's built_at_commit so we parse the big graph once
    per rebuild, not per edit (Ro's CPU runs low — keep per-edit cost tiny)."""
    g = json.loads(graph.read_text())
    commit = g.get("built_at_commit", "")
    key = "".join(c for c in (str(graph) + commit) if c.isalnum())[-90:]
    cache = INDEX_DIR / f"{key}.json"
    try:
        return json.loads(cache.read_text())
    except Exception:
        pass
    id2file = {n["id"]: n.get("source_file") for n in g.get("nodes", [])
               if n.get("id")}
    rev: dict = {}
    for link in g.get("links", []):
        if link.get("relation") not in DEPS:
            continue
        sf_t = id2file.get(link.get("target"))
        sf_s = id2file.get(link.get("source"))
        if sf_t and sf_s and sf_t != sf_s:
            rev.setdefault(sf_t, set()).add(sf_s)
    out = {k: sorted(v) for k, v in rev.items()}
    try:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(out))
    except Exception:
        pass
    return out


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    event = data.get("hook_event_name", "")
    tool = data.get("tool_name", "")
    session = str(data.get("session_id", "") or "")
    fp = str((data.get("tool_input", {}) or {}).get("file_path", "") or "")
    if not fp:
        return

    abspath = Path(fp if os.path.isabs(fp) else os.path.join(os.getcwd(), fp))
    repo, graph = _find_graph(abspath.parent)
    if not repo:
        return  # not a graphify repo → no-op

    try:
        rel = os.path.relpath(str(abspath), str(repo))
    except ValueError:
        return

    # Record every file we touch (read OR edit) as "seen".
    _add_readset(session, rel)

    # Advisory only before an edit.
    if event != "PreToolUse" or tool not in ("Edit", "Write", "MultiEdit"):
        return

    index = _build_index(graph)
    deps = index.get(rel, [])
    if not deps:
        return
    seen = _load_readset(session)
    unread = [d for d in deps if d not in seen]
    if len(unread) < MIN_UNREAD:
        return

    shown = ", ".join(unread[:MAX_LIST])
    more = f" (+{len(unread) - MAX_LIST} more)" if len(unread) > MAX_LIST else ""
    _emit(
        f"CODE-MAP HEADS-UP (graphify): {rel} is referenced by {len(unread)} "
        f"file(s) you haven't opened this session — {shown}{more}. A change here "
        f"can break those callers. Before editing, run `graphify explain {rel}` "
        "(or read the ones you'll affect) so you're editing with the pipeline in "
        "view, not blind."
    )
    _prune_old(READSET_DIR)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open: never wedge a tool call over an advisory
