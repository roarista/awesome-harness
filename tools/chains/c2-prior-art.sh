#!/usr/bin/env bash
# c2-prior-art.sh <concept> [name-regex] — "does this repo ALREADY do X?"
# Prevents: P1 (invents an API that does not exist — the vestigial-dependency trap)
#           P2 (re-implements something the repo already has).
# The codebase-first gate, in three legs. Never stop at leg 1; a single "no" IS the failure.
#   leg 1 STRUCTURAL  semgrep, complete over the shapes you wrote  -> tools/semgrep/<concept>.yaml
#   leg 2 NOMINAL     grep for the NAME, catches shapes you didn't write
#   leg 3 DECLARED    a library for X in the manifest, imported zero times = VESTIGIAL
#
# Usage: REPO=/path tools/chains/c2-prior-art.sh retry 'retry|backoff|tenacity'
set -euo pipefail
CHAIN_NAME=c2-prior-art
. "$(dirname "$0")/_lib.sh"
CONCEPT="${1:?usage: c2-prior-art.sh <concept> [name-regex]}"
RE="${2:-$CONCEPT}"
full_file "c2-$CONCEPT" >/dev/null
echo "== c2-prior-art $REPO_NAME concept=$CONCEPT re=$RE" >> "$FULL"

# leg 1 — structural
CFG=""
for c in "$RULES/$CONCEPT.yaml" "$RULES/reuse-$CONCEPT.yaml"; do [ -f "$c" ] && CFG="$c"; done
S1=0
if [ -n "$CFG" ]; then
  validate_rules "$CFG"
  J=$(sg "$CFG")
  { echo; echo "== leg1 structural ($CFG)"; echo "$J" | jq -r '.results[]|"\(.check_id|sub(".*\\.";"")) \(.path):\(.start.line)"' | sort; } >> "$FULL"
  S1=$(echo "$J" | jq -r '.results[].path' | sort -u | wc -l | tr -d ' ')
  say "leg1 STRUCTURAL: $S1 file(s) already implement a '$CONCEPT' shape."
  echo "$J" | jq -r '.results[]|"\(.check_id|sub(".*\\.";"")) \(.path):\(.start.line)"' | sed "s|$REPO/||" | sort | head -3 \
    | while read -r l; do echo "  · $l"; done > "$OUTDIR/.h2" || true
  while read -r l; do say "$l"; done < "$OUTDIR/.h2"; rm -f "$OUTDIR/.h2"
else
  say "leg1 STRUCTURAL: SKIPPED — no rule tools/semgrep/$CONCEPT.yaml. Write one; that is how this becomes durable."
fi

# leg 2 — nominal
S2F=$(grep -rIn --include='*.py' --include='*.ts' --include='*.js' --include='*.sh' \
      $EXCL --exclude-dir=tests \
      -E "(def|class|function|const) [A-Za-z_]*($RE)|@($RE)" "$REPO" 2>/dev/null | sed "s|^$REPO/||" || true)
n2=$(printf '%s' "$S2F" | grep -c . || true)
{ echo; echo "== leg2 nominal /$RE/"; printf '%s\n' "$S2F"; } >> "$FULL"
say "leg2 NOMINAL: $n2 definition(s) named like '$RE' (catches what the pattern missed)."

# leg 3 — declared but never imported
DECL=""
for m in "$REPO/pyproject.toml" "$REPO/requirements.txt" "$REPO/package.json"; do
  [ -f "$m" ] || continue
  DECL="$DECL$(grep -iE "$RE" "$m" 2>/dev/null | sed 's/^[[:space:]]*//' || true)
"
done
{ echo; echo "== leg3 declared"; printf '%s\n' "$DECL"; } >> "$FULL"
VEST=""
for lib in $(printf '%s' "$DECL" | grep -oiE "[a-z][a-z0-9_-]*" | grep -iE "$RE" | tr 'A-Z' 'a-z' | sort -u); do
  # NOTE: `set -o pipefail` + grep's exit-1-on-no-match kills the script here without the
  # inner `|| true`. That is exactly the P6 shape (a silent zero) reproduced in our own tooling.
  n=$({ grep -rIn --include='*.py' $EXCL \
       -cE "^[[:space:]]*(import|from) $lib" "$REPO" 2>/dev/null || true; } | awk -F: '{s+=$2} END{print s+0}')
  if [ "$n" -eq 0 ] 2>/dev/null; then VEST="$VEST $lib"; fi
done
true
if [ -n "$VEST" ]; then
  say "leg3 VESTIGIAL:$VEST declared in the manifest and imported ZERO times. Do NOT import it (P1)."
else
  say "leg3 DECLARED: nothing matching /$RE/ is declared-but-unused."
fi

if [ "$S1" = 0 ] && [ "$n2" = 0 ]; then
  say "VERDICT: BUILD — no prior art found by either leg (both legs ran and validated)."
else
  say "VERDICT: REUSE/ADAPT — prior art EXISTS ($S1 structural + $n2 named). Read FULL before writing a new one."
fi
exit 0
