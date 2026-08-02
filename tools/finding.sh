#!/usr/bin/env bash
# finding.sh — subagent ledger. Append-only, never deletes. See .scratch/design-subagent-ledger.md
#   record <title> < dump   record stdin as a finding, print the id
#   get <id>                print the full dump
#   list [session]          id · date · title · lines
#   search <words>          grep titles + dumps, print matching ids + titles
# Absence of an index line means UNKNOWN (crash before record), never "nothing happened".
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
D=.findings

sess() {
  [ -n "${HARNESS_SESSION:-}" ] && { echo "$HARNESS_SESSION"; return; }
  [ -s "$D/.current" ] && { head -1 "$D/.current"; return; }
  # same tty+PID derivation as tools/git-sync.sh:40-41
  local t; t="$(tty 2>/dev/null || true)"
  case "$t" in /dev/*) T="$(basename "$t")-$$" ;; *) T="$(hostname -s 2>/dev/null || echo host)-$$" ;; esac
  local s; s="$(date +%Y-%m-%d)-$T"
  mkdir -p "$D"; printf '%s\n' "$s" > "$D/.current"
  echo "$s"
}

case "${1:-}" in
record)
  S="$(sess)"; shift; TITLE="${*:-untitled}"
  mkdir -p "$D/$S"; ID="$(date +%H%M%S)-$$"
  cat > "$D/$S/$ID.md"
  N=$(awk 'END{print NR}' < "$D/$S/$ID.md")
  ID="$ID" TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)" TITLE="$TITLE" TERM_ID="${S#????-??-??-}" \
  DUMP="$D/$S/$ID.md" LINES="$N" IDX="$D/$S/index.jsonl" python3 -c '
import fcntl, json, os
rec = {"id": os.environ["ID"], "ts": os.environ["TS"], "title": os.environ["TITLE"],
       "terminal": os.environ["TERM_ID"], "dump": os.environ["DUMP"],
       "lines": int(os.environ["LINES"])}
line = json.dumps(rec, ensure_ascii=False) + "\n"
with open(os.environ["IDX"], "a", encoding="utf-8") as f:
    fcntl.lockf(f, fcntl.LOCK_EX)
    f.seek(0, os.SEEK_END)
    f.write(line)
    f.flush()
    fcntl.lockf(f, fcntl.LOCK_UN)
'
  echo "$ID" ;;
get)
  id="${2:?id}"
  case "$id" in */*|.|..) echo "finding.sh: no dump for id $id" >&2; exit 1 ;; esac
  matches=(); for f in "$D"/*/"$id".md; do [ -f "$f" ] && matches+=("$f"); done
  [ "${#matches[@]}" -gt 0 ] || { echo "finding.sh: no dump for id $id" >&2; exit 1; }
  if [ "${#matches[@]}" -gt 1 ]; then
    { echo "finding.sh: ambiguous id $id — ${#matches[@]} matches:"
      printf '  %s\n' "${matches[@]}"; } >&2
    exit 1
  fi
  cat "${matches[0]}" ;;
list)
  S="${2:-$(sess)}"
  IDX="$D/$S/index.jsonl" python3 -c '
import json, os, sys
p = os.environ["IDX"]
if not os.path.exists(p):
    sys.exit(0)
for line in open(p, encoding="utf-8"):
    line = line.strip()
    if not line: continue
    r = json.loads(line)
    t = " ".join(str(r.get("title","")).split())
    print("%s · %s · %s · %s lines" % (r.get("id"), r.get("ts"), t, r.get("lines")))
' ;;
search)
  shift; [ "$#" -gt 0 ] || { sed -n '2,7p' "$0"; exit 2; }
  q="$*"
  { { grep -liF -- "$q" "$D"/*/*.md 2>/dev/null || true; } | sed 's#.*/##; s/\.md$//'
    { grep -hiF -- "$q" "$D"/*/index.jsonl 2>/dev/null || true; } |
      python3 -c '
import json, sys
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: print(json.loads(line)["id"])
    except Exception: pass
'; } | sort -u |
  while read -r id; do
    [ -n "$id" ] || continue
    { grep -hF "\"id\": \"$id\"" "$D"/*/index.jsonl 2>/dev/null || true; } | head -1 |
      python3 -c '
import json, sys
line = sys.stdin.readline().strip()
if line:
    r = json.loads(line)
    print("%s · %s" % (r.get("id"), " ".join(str(r.get("title","")).split())))
'
  done ;;
*) sed -n '2,7p' "$0"; exit 2 ;;
esac
