#!/bin/sh
# graphify-blast — borrow of codebase-memory-mcp's detect_changes idea.
# Map "what I'm about to touch" -> impacted symbols/neighbors via the code graph,
# so a coder gets the blast radius BEFORE editing instead of grepping blind.
#
# Usage:
#   graphify-blast.sh                # uses `git diff --name-only` (unstaged+staged)
#   graphify-blast.sh fileA fileB    # explicit files/symbols
#
# Cheap: a few graphify explain calls, no build. Run from a repo with graphify-out/.
set -eu

GRAPH="graphify-out/graph.json"
[ -f "$GRAPH" ] || { echo "graphify-blast: no $GRAPH here — run from a repo with a graph."; exit 0; }

if [ "$#" -gt 0 ]; then
  TARGETS="$*"
else
  # changed files vs HEAD; fall back to working-tree diff
  TARGETS="$(git diff --name-only HEAD 2>/dev/null; git diff --name-only 2>/dev/null)"
fi

[ -n "${TARGETS:-}" ] || { echo "graphify-blast: nothing changed / no targets."; exit 0; }

# de-dup, then explain each by basename-without-extension (graphify matches symbols/modules)
echo "$TARGETS" | tr ' ' '\n' | sed '/^$/d' | sort -u | while read -r f; do
  base="$(basename "$f")"; name="${base%.*}"
  [ -n "$name" ] || continue
  echo "===== blast radius: $f ($name) ====="
  graphify explain "$name" 2>/dev/null || echo "  (no graph node matched '$name')"
  echo
done
