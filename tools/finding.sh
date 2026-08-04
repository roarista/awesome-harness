#!/usr/bin/env bash
# finding.sh - subagent ledger. Append-only, never deletes. See .scratch/design-subagent-ledger.md
#   record <title> < dump   record stdin as a finding, print the id
#   get <id>                print the full dump
#   list [session]          id · date · title · lines
#   search <words>          grep titles + dumps, print matching ids + titles
# Absence of an index line means UNKNOWN (crash before record), never "nothing happened".
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
D=.findings

# a session must be a single safe path component: no empties, no "/", no ".."
sess_ok() {
  local s="$1"
  [ -n "${s//[[:space:]]/}" ] || return 1
  [ "${#s}" -le 96 ] || return 1
  # single path component already (no "/"), so ".." can only be the whole string
  case "$s" in */*|.|..) return 1 ;; esac
  return 0
}

sess() {
  if [ -n "${HARNESS_SESSION:-}" ]; then
    sess_ok "$HARNESS_SESSION" || {
      echo "finding.sh: invalid HARNESS_SESSION '$HARNESS_SESSION' (no empty, '/', '..', or >96 chars)" >&2; exit 2; }
    echo "$HARNESS_SESSION"; return
  fi
  local today; today="$(date +%Y-%m-%d)"
  if [ -s "$D/.current" ]; then
    local c; c="$(head -1 "$D/.current")"
    # a bad .current is ignored and recomputed below (self-healing);
    # a .current dated before today is also stale and recomputed (rotates daily)
    if sess_ok "$c" && case "$c" in "$today"-*) true ;; *) false ;; esac; then
      echo "$c"; return
    fi
  fi
  # same tty+PID derivation as tools/git-sync.sh:40-41
  local t; t="$(tty 2>/dev/null || true)"
  case "$t" in /dev/*) T="$(basename "$t")-$$" ;; *) T="$(hostname -s 2>/dev/null || echo host)-$$" ;; esac
  local s; s="$today-$T"
  mkdir -p "$D"; printf '%s\n' "$s" > "$D/.current"
  echo "$s"
}

case "${1:-}" in
record)
  # guard FIRST: with a tty on stdin `cat >` would block forever and leave an empty dump
  if [ -t 0 ]; then
    echo "finding.sh: record reads the dump from stdin; pipe it in" >&2; exit 2
  fi
  S="$(sess)"; shift; TITLE="${*:-untitled}"
  mkdir -p "$D/$S"; ID="$(date +%H%M%S)-$$"
  cat > "$D/$S/$ID.md"
  # the dump exists now — print the id before indexing, so a python3 failure can't lose it
  echo "$ID"
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
' ;;
get)
  [ "$#" -ge 2 ] || { sed -n '2,7p' "$0"; exit 2; }
  id="$2"
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
  SDIR="$D/$S" IDX="$D/$S/index.jsonl" python3 -c '
import glob, json, os
p, sdir = os.environ["IDX"], os.environ["SDIR"]
seen = set()
if os.path.exists(p):
    for n, line in enumerate(open(p, encoding="utf-8"), 1):
        line = line.strip()
        if not line: continue
        # one bad byte must not hide every other finding (same guard as `search`)
        try:
            r = json.loads(line)
            if not isinstance(r, dict): raise ValueError("not an object")
        except Exception:
            print("%s · MALFORMED" % n); continue
        seen.add(r.get("id"))
        t = " ".join(str(r.get("title","")).split())
        print("%s · %s · %s · %s lines" % (r.get("id"), r.get("ts"), t, r.get("lines")))
# a dump with no index line means UNKNOWN (crash before record), never "nothing happened"
for f in sorted(glob.glob(os.path.join(sdir, "*.md"))):
    fid = os.path.basename(f)[:-3]
    if fid not in seen:
        print("%s · UNINDEXED · %s" % (fid, f))
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
