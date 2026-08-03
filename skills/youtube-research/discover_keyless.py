#!/usr/bin/env python3
"""Keyless YouTube discovery via yt-dlp (no API key, no quota).

Workaround for ytintel `discover` hitting the YouTube Data API 429/quota.
Usage:
  discover_keyless.py "query one" "query two" ...   [--per 10] [--top 15]
Aggregates ytsearch results across queries, dedups by id, sorts by view_count.
Then feed the chosen ids to `ytintel transcript <id>`.
"""
import json, subprocess, sys

def search(query, per):
    try:
        out = subprocess.run(
            ["yt-dlp", f"ytsearch{per}:{query}", "--flat-playlist",
             "--dump-json", "--no-warnings"],
            capture_output=True, text=True, timeout=120)
    except Exception as e:
        print(f"# search failed for {query!r}: {e}", file=sys.stderr); return []
    rows = []
    for line in out.stdout.splitlines():
        try:
            v = json.loads(line)
            rows.append({"id": v.get("id"), "ch": v.get("channel") or "?",
                         "t": (v.get("title") or "?"), "views": v.get("view_count") or 0,
                         "dur": v.get("duration") or 0})
        except Exception:
            pass
    return rows

def main(argv):
    per, top, queries = 10, 15, []
    i = 0
    while i < len(argv):
        if argv[i] == "--per": per = int(argv[i+1]); i += 2
        elif argv[i] == "--top": top = int(argv[i+1]); i += 2
        else: queries.append(argv[i]); i += 1
    if not queries:
        print(__doc__); return 1
    seen = {}
    for q in queries:
        for r in search(q, per):
            if r["id"] and r["id"] not in seen:
                seen[r["id"]] = r
    rows = sorted(seen.values(), key=lambda r: -r["views"])[:top]
    for r in rows:
        print(f"{r['id']} | {r['views']:>9} v | {int(r['dur']/60)}m | {r['ch'][:24]:24} | {r['t'][:60]}")
    print("\nIDS:", " ".join(r["id"] for r in rows))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
