#!/usr/bin/env bash
# _lib.sh — shared plumbing for tools/chains/*.sh
#
# CONTEXT HYGIENE CONTRACT (hard requirement):
#   Every chain prints a VERDICT of <= 15 lines to stdout. The full tool output goes to
#   a file, and the last stdout line is always `FULL: <path>`. The main agent reads the
#   verdict; only a subagent that needs detail opens the file.
#   Set CHAIN_RECORD=1 to also append the full dump to tools/finding.sh's ledger.
#
# Every chain also prints exactly one PREFLIGHT line proving the tools did not silently
# fail, and one FALLBACK line whenever a primary tool returned empty.

set -euo pipefail

HARNESS_ROOT="${HARNESS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
RULES="$HARNESS_ROOT/tools/semgrep"
REPO="${REPO:-$PWD}"
REPO_NAME="$(basename "$REPO")"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUTDIR="${CHAIN_OUTDIR:-/tmp/chains/$REPO_NAME}"
mkdir -p "$OUTDIR"

export SEMGREP_SEND_METRICS=off SEMGREP_ENABLE_VERSION_CHECK=0

# Shared exclusions. `.claude/worktrees` matters: stale agent worktrees contain full
# copies of the tree and will make a dead dependency look alive (measured: `tenacity`
# in virality-pipeline shows 3 imports, all inside abandoned worktrees, 0 in the live tree).
EXCL="--exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=venv \
--exclude-dir=graphify-out --exclude-dir=.git --exclude-dir=.claude \
--exclude-dir=.repowise --exclude-dir=dist --exclude-dir=build"

# --- verdict buffer: nothing reaches stdout until the chain ends -------------
VERDICT=()
say() { VERDICT+=("$*"); }
FULL=""
full_file() { FULL="$OUTDIR/$1-$STAMP.txt"; : > "$FULL"; echo "$FULL"; }

finish() {
  local n=${#VERDICT[@]}
  if [ "$n" -gt 14 ]; then
    printf '%s\n' "${VERDICT[@]:0:13}"
    echo "… ($((n-13)) more lines suppressed by the context-hygiene cap)"
  else
    [ "$n" -gt 0 ] && printf '%s\n' "${VERDICT[@]}"
  fi
  if [ -n "$FULL" ]; then
    if [ "${CHAIN_RECORD:-0}" = "1" ] && [ -x "$HARNESS_ROOT/tools/finding.sh" ]; then
      local id; id="$("$HARNESS_ROOT/tools/finding.sh" record "chain $CHAIN_NAME · $REPO_NAME" < "$FULL" 2>/dev/null || true)"
      [ -n "$id" ] && echo "FULL: $FULL  (finding $id)" && return 0
    fi
    echo "FULL: $FULL"
  fi
}
trap finish EXIT

# --- R-0a: never trust a semgrep zero from an unvalidated rule ---------------
validate_rules() {
  local cfg="$1" out
  if ! out="$(semgrep scan --validate --config "$cfg" --metrics=off 2>&1)"; then
    say "PREFLIGHT FAIL: semgrep rule(s) in $cfg do not parse — a zero here would be a LIE."
    printf '%s\n' "$out" >> "$FULL"
    exit 3
  fi
  say "PREFLIGHT ok: $(printf '%s' "$out" | grep -o '[0-9]* rule(s)' | head -1) validated (R-0a)."
}

sg() { # sg <config> [extra find args...] -> json on stdout
  local cfg="$1"; shift
  semgrep --config "$cfg" --quiet --json --metrics=off \
    --exclude=node_modules --exclude=.venv --exclude=venv --exclude=graphify-out \
    --exclude=remotion "$@" "$REPO" 2>/dev/null || true
}

# --- R-0b: graphify `affected` is blind on a graph with dangling import edges -
graph_gate() { # exit 0 = affected is trustworthy
  [ -f "$REPO/graphify-out/graph.json" ] || return 1
  python3 - "$REPO/graphify-out/graph.json" <<'PY'
import json,sys
g=json.load(open(sys.argv[1]))
ids={n['id'] for n in g['nodes']}
imp=[l for l in g['links'] if str(l.get('relation','')).startswith('import')]
d=sum(1 for l in imp if l['target'] not in ids)
print(f"{len(imp)} {d}")
sys.exit(1 if imp and d/len(imp)>0.5 else 0)
PY
}
