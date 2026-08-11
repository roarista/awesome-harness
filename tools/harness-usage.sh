#!/bin/bash
set -euo pipefail
LOGFILE="$HOME/.claude/hooks/state/harness-usage.jsonl"
DAYS=${1:-14}
[[ -f "$LOGFILE" ]] || { echo "Error: harness usage log not found at $LOGFILE" >&2; exit 1; }
python3 << EOPYTHON
import json, sys, os
from datetime import datetime, timedelta
from collections import Counter, defaultdict
with open(os.path.expanduser("~/.claude/hooks/state/harness-usage.jsonl")) as f:
    lines = f.readlines()
events = [json.loads(l) for l in lines if l.strip()]
event_types = Counter(e["event"] for e in events)
sessions = set(e["session"] for e in events)
dates = [datetime.fromisoformat(e["ts"]) for e in events]
date_min, date_max = min(dates).date(), max(dates).date()
cutoff = datetime.now() - timedelta(days=$DAYS)
daily = defaultdict(lambda: defaultdict(int))
for e in events:
    ts = datetime.fromisoformat(e["ts"])
    if ts >= cutoff: daily[ts.date()][e["event"]] += 1
detail_counts = Counter(e.get("detail", "N/A") for e in events if e["event"] == "subagent_spawn")
print(f"\\n=== HARNESS USAGE SUMMARY ===")
print(f"Date range: {date_min} to {date_max}")
print(f"Total lines: {len(lines)}")
print("\\nEvent totals:")
for evt in sorted(event_types.keys()): print(f"  {evt}: {event_types[evt]}")
print(f"\\nDistinct sessions: {len(sessions)}")
print(f"\\nPer-day summary (last $DAYS days):")
print("  Date        subagent_spawn  orient_read  graphify_run")
for day in sorted(daily.keys()):
    s = daily[day].get("subagent_spawn", 0)
    o = daily[day].get("orient_read", 0)
    g = daily[day].get("graphify_run", 0)
    print(f"  {day}       {s:6d}          {o:6d}       {g:6d}")
print("\\nTop 10 subagent_spawn detail values:")
for detail, count in detail_counts.most_common(10): print(f"  {detail}: {count}")
print()
EOPYTHON
