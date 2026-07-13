#!/usr/bin/env python3
# UserPromptSubmit hook: auto-recall. Queries the memgraph FTS index with the
# user's prompt and injects the top memory hit(s) as context — so agents pull
# relevant durable memory without anyone typing /recall.
# ponytail: FTS-only, no ranking model; good enough for "is this already decided?".
import json, os, re, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

DB = os.path.expanduser("~/.claude/tools/memgraph/out/memindex.sqlite")
# Hebbian usage side-store (fail-open): a bounded tiebreaker that nudges
# frequently-surfaced records slightly higher. If import/anything fails, recall
# behaves exactly as before.
try:
    sys.path.insert(0, os.path.expanduser("~/.claude/tools/memgraph"))
    import usage as _usage
except Exception:
    _usage = None
SKIP = re.compile(r"^(yes|ok|okay|sure|go|continue|do that|do it|thanks?|y|n)\b", re.I)

def main():
    try:
        prompt = (json.load(sys.stdin).get("prompt") or "").strip()
    except Exception:
        return
    if len(prompt) < 40 or SKIP.match(prompt) or not os.path.exists(DB):
        return
    words = [w for w in re.findall(r"[A-Za-z0-9]{3,}", prompt)][:10]
    if not words:
        return
    match = " OR ".join(f'"{w}"' for w in words)
    try:
        con = sqlite3.connect(DB)
        # Fetch a small buffer (6) so the Hebbian tiebreaker can lift a slightly
        # lower-ranked-but-frequently-used record into the injected top 2.
        rows = con.execute(
            "SELECT name, description FROM mem WHERE mem MATCH ? ORDER BY rank LIMIT 6",
            (match,),
        ).fetchall()
    except Exception:
        return
    if not rows:
        return
    # Rerank by usage (bounded tiebreak), then surface top 2. Fail-open: on any
    # error keep the plain relevance order.
    top = rows[:2]
    if _usage is not None:
        try:
            desc = {n: d for n, d in rows}
            order = _usage.rerank([n for n, _ in rows])
            top = [(n, desc[n]) for n in order[:2]]
            _usage.bump_used([n for n, _ in top])
        except Exception:
            top = rows[:2]
    lines = "\n".join(f"- **{n}**: {d}" for n, d in top)
    _hookout.inject("UserPromptSubmit", f"🧠 maybe-relevant memory (recall index, verify first):\n{lines}")

if __name__ == "__main__":
    main()
