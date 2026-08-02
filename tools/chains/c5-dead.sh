#!/usr/bin/env bash
# c5-dead.sh — "what is dead and safe to delete?"
# Prevents: P1 (agent imports a near-identically-named DEAD module — measured: an agent
#           would write `remotion.render()` when the live module is remotion_bridge.py).
#
# Primary  : repowise dead-code (AST + graph reachability; works at ZERO wiki pages)
# Cross-chk: graphify explain per candidate — a DIFFERENT parser. Agreement = deletable.
#            DISAGREEMENT is where the dynamic-import false positives live — never bulk-delete.
# Third    : grep the basename. Free, catches config/CI entry points the graphs miss.
#
# Usage: REPO=/path tools/chains/c5-dead.sh [min-confidence]
set -euo pipefail
CHAIN_NAME=c5-dead
. "$(dirname "$0")/_lib.sh"
MINC="${1:-0.8}"
full_file c5-dead >/dev/null
echo "== c5-dead $REPO_NAME min-confidence=$MINC" >> "$FULL"

if [ ! -d "$REPO/.repowise" ]; then
  say "PREFLIGHT FAIL: no .repowise/ index — run: repowise update --index-only $REPO"; exit 3
fi
say "PREFLIGHT ok: .repowise/ present (dead-code needs the index, NOT the wiki)."

repowise dead-code "$REPO" --min-confidence "$MINC" --safe-only --format json 2>/dev/null \
  | sed -n '/^[[{]/,$p' > "$OUTDIR/dead.json" || true
if ! jq -e . "$OUTDIR/dead.json" >/dev/null 2>&1; then
  say "FALLBACK: repowise dead-code returned no parseable JSON. Treat as UNKNOWN, not 'nothing dead'."
  cp "$OUTDIR/dead.json" "$FULL" 2>/dev/null || true; exit 0
fi
FILES=$(jq -r '(if type=="array" then .[] else (.findings//.results//empty)[] end)
               | select((.kind//.type//"")|test("unreachable_file|dead_file"))
               | (.file_path//.path//.file)' "$OUTDIR/dead.json" 2>/dev/null | sort -u || true)
EXPORTS=$(jq -r '(if type=="array" then .[] else (.findings//.results//empty)[] end)
               | select((.kind//.type//"")|test("unused_export|unused_symbol"))
               | (.file_path//.path//.file)' "$OUTDIR/dead.json" 2>/dev/null | wc -l | tr -d ' ')
nf=$(printf '%s' "$FILES" | grep -c . || true)
say "repowise: $nf unreachable file(s), $EXPORTS unused export(s) at confidence >= $MINC."

# cross-check each candidate with the second parser + a name grep
AGREE=0; DISPUTED=""
{ echo; echo "== per-candidate cross-check"; } >> "$FULL"
while read -r f; do
  [ -n "$f" ] || continue
  b="$(basename "${f%.*}")"
  ge="$(graphify explain "$f" 2>/dev/null || true)"
  inbound=$(printf '%s' "$ge" | grep -ciE '(imports|calls|references).*->|<- *(imports|calls)' || true)
  hits=$({ grep -rIn --include='*.py' --include='*.toml' --include='*.cfg' --include='*.yaml' \
            --include='*.yml' --include='*.json' --include='*.sh' $EXCL \
            -e "$b" "$REPO" 2>/dev/null || true; } | { grep -v "^$REPO/$f:" || true; } | wc -l | tr -d ' ')
  { echo "-- $f  graphify_inbound=$inbound  name_mentions=$hits"; printf '%s\n' "$ge" | head -20; } >> "$FULL"
  if [ "$inbound" = 0 ] && [ "$hits" -lt 3 ]; then AGREE=$((AGREE+1)); else DISPUTED="$DISPUTED $f"; fi
done <<< "$FILES"

say "CROSS-CHECK: $AGREE/$nf candidates agreed by all three methods → safe to delete."
if [ -n "$DISPUTED" ]; then
  say "DISPUTED (do NOT bulk-delete; dynamic import / config entry point lives here):"
  for f in $DISPUTED; do echo "  ? $f"; done > "$OUTDIR/.h5d"
  head -4 "$OUTDIR/.h5d" | while read -r l; do echo "$l"; done > "$OUTDIR/.h5e"; rm -f "$OUTDIR/.h5d"
  while read -r l; do say "$l"; done < "$OUTDIR/.h5e"; rm -f "$OUTDIR/.h5e"
fi
printf '%s\n' "$FILES" | grep . | head -4 | while read -r f; do echo "  · dead: $f"; done > "$OUTDIR/.h5" || true
while read -r l; do say "$l"; done < "$OUTDIR/.h5"; rm -f "$OUTDIR/.h5"
say "Full candidate list + per-file graph evidence in FULL."
exit 0
