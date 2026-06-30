#!/usr/bin/env python3
# UserPromptSubmit hook: auto-recall. Queries the memgraph FTS index with the
# user's prompt and injects the top memory hit(s) as context — so agents pull
# relevant durable memory without anyone typing /recall.
# ponytail: FTS-only, no ranking model; good enough for "is this already decided?".
import json, os, re, sqlite3, sys

DB = os.path.expanduser("~/.claude/tools/memgraph/out/memindex.sqlite")
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
        rows = con.execute(
            "SELECT name, description FROM mem WHERE mem MATCH ? ORDER BY rank LIMIT 2",
            (match,),
        ).fetchall()
    except Exception:
        return
    if not rows:
        return
    lines = "\n".join(f"- **{n}**: {d}" for n, d in rows)
    print(f"🧠 Possibly-relevant durable memory (via recall index — verify before relying):\n{lines}")

if __name__ == "__main__":
    main()
