#!/usr/bin/env bash
# map-refresh — after a unit of work, make every code map tell the truth again.
#
# The maps are not all the same shape, and treating them as one thing is how
# they rot:
#   L0 / L1 / skeleton   computed LIVE on every call. Nothing to regenerate —
#                        the only real question is "does it still hold?"
#   .codemap             a CACHED file. Goes stale silently; has served a
#                        470 KB stale blob before. Regenerate on sha drift.
#   graphify-out/        a CACHED graph. Same failure mode, worse: a stale
#                        graph answers confidently instead of erroring.
#
# So this script VERIFIES the live tier and REGENERATES the cached tiers, and
# refuses to exit 0 on a check it could not actually perform.
#
#   tools/map-refresh.sh            # verify + regenerate what drifted
#   tools/map-refresh.sh --check    # verify only, change nothing (CI/pre-commit)
#
# Exit 0 only when every applicable check passed. No silent success.
#
# NOTE ON READING THIS OUTPUT: do not pipe it through `tail`/`head` and then
# read `$?` — you get the pager's exit code, not this script's. That mistake
# has now been made three times in this repo's history.
set -uo pipefail

REPO="${REPO:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$REPO" ] || { echo "map-refresh: not a git repo"; exit 1; }
cd "$REPO" || exit 1

CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

TOOLS="$HOME/.claude/tools"
[ -f "$REPO/tools/l0.py" ] && TOOLS="$REPO/tools"

FAIL=0
rows=()
row(){ rows+=("$1|$2|$3"); [ "$2" = FAIL ] && FAIL=1; return 0; }

# ---------- live tier: L0 --------------------------------------------------
if [ -f "$TOOLS/l0.py" ]; then
  out="$(cd "$REPO" && python3 "$TOOLS/l0.py" 2>&1)"; rc=$?
  bytes=${#out}
  if printf '%s' "$out" | grep -q 'DILUTED INDEX UNAVAILABLE'; then
    # The resolver itself says it can't produce a hub map for this repo (e.g.
    # too few source files to make hub detection meaningful). Deferred to
    # below: a healthy .codemap covering for it is a supported configuration,
    # not a defect.
    L0_MISSING=1
    L0_MISSING_REASON="l0 reports: $(printf '%s' "$out" | grep 'DILUTED INDEX UNAVAILABLE' | head -1 | sed 's/^ *//')"
  elif [ $rc -ne 0 ]; then
    row L0 FAIL "exit $rc"
  elif [ "$bytes" -lt 300 ]; then
    row L0 FAIL "only $bytes bytes — too thin to be a map"
  elif ! printf '%s' "$out" | grep -q 'MOST-IMPORTED'; then
    row L0 FAIL "no MOST-IMPORTED block — the resolver produced nothing"
  else
    row L0 ok "$bytes bytes, $(printf '%s' "$out" | grep -c '^  ') entries"
  fi

  # Every command L0 advertises must actually run. This is the rule that caught
  # three bugs in one day: verify the pointer, not just the tool.
  adv="$(printf '%s\n' "$out" | sed -n 's/^[A-Za-z ]*: *\([^ ]*\.py\).*/\1/p' | sort -u)"
  bad=""
  for p in $adv; do
    ep="${p/#\~/$HOME}"
    [ -f "$ep" ] || bad="$bad $p"
  done
  if [ -n "$bad" ]; then row ZOOM FAIL "advertised path does not exist:$bad"
  elif [ -n "$adv" ]; then row ZOOM ok "$(printf '%s' "$adv" | wc -w | tr -d ' ') advertised path(s) resolve"
  else row ZOOM skip "no paths advertised"; fi
else
  # L0 unavailable. If a healthy .codemap already serves this repo, that is a
  # supported configuration (e.g. too few source files for hub detection to
  # mean anything) — not a defect. Defer the row until we know whether the
  # codemap tier is healthy; see below.
  L0_MISSING=1
  L0_MISSING_REASON="l0.py not found at $TOOLS/l0.py"
fi

# ---------- cached tier: .codemap -----------------------------------------
if [ -f "$REPO/.codemap" ]; then
  head_sha="$(git rev-parse --short=7 HEAD)"
  map_sha="$(head -3 "$REPO/.codemap" | grep -oE '@[0-9a-f]{7}' | head -1 | tr -d '@')"
  size=$(wc -c < "$REPO/.codemap" | tr -d ' ')
  if [ "$size" -gt 30000 ]; then
    row CODEMAP FAIL "$size bytes — over the 30 KB injection cap, it would be skipped anyway"
  elif [ "$map_sha" = "$head_sha" ]; then
    row CODEMAP ok "@$map_sha current, $size bytes"
  elif [ "$CHECK_ONLY" = 1 ]; then
    row CODEMAP FAIL "stale: @$map_sha vs HEAD @$head_sha"
  elif [ -f "$TOOLS/codemap.py" ]; then
    if python3 "$TOOLS/codemap.py" >/dev/null 2>&1; then
      map_sha="$head_sha"
      row CODEMAP ok "regenerated @$head_sha, $(wc -c < "$REPO/.codemap" | tr -d ' ') bytes"
    else
      row CODEMAP FAIL "regeneration failed, stale @$map_sha still on disk"
    fi
  else
    row CODEMAP FAIL "stale @$map_sha and codemap.py not installed"
  fi
  [ "$size" -le 30000 ] && [ "$map_sha" = "$(git rev-parse --short=7 HEAD)" ] && CODEMAP_HEALTHY=1
else
  row CODEMAP skip "no .codemap (L0 serves this repo)"
fi

# ---------- resolve the deferred L0 row ------------------------------------
# CODEMAP tier may have just regenerated to current, so this must run after it.
if [ "${L0_MISSING:-0}" = 1 ]; then
  if [ "${CODEMAP_HEALTHY:-0}" = 1 ]; then
    n_src=$(git ls-files 2>/dev/null | grep -cE '\.(py|ts|tsx|js|jsx|sh|sql|go|rs)$')
    row L0 n/a "codemap serves this repo ($n_src source files, too few for hubs)"
  else
    row L0 FAIL "${L0_MISSING_REASON:-l0.py not found} and no healthy .codemap to serve this repo"
  fi
fi

# ---------- cached tier: graphify -----------------------------------------
# A stale graph is worse than no graph: it answers confidently. So the test is
# "is any tracked source file newer than the graph", not "does the file exist".
if [ -d "$REPO/graphify-out" ]; then
  G="$REPO/graphify-out/graph.json"
  if ! command -v graphify >/dev/null 2>&1; then
    row GRAPHIFY FAIL "graphify-out/ exists but the CLI is missing — the graph can only rot"
  elif [ ! -f "$G" ]; then
    row GRAPHIFY FAIL "graphify-out/ exists with no graph.json"
  else
    newer=$(git ls-files -z 2>/dev/null \
      | xargs -0 -I{} find {} -newer "$G" -type f -print 2>/dev/null \
      | grep -cE '\.(py|ts|tsx|js|jsx|sh|sql|go|rs)$')
    if [ "${newer:-0}" -eq 0 ]; then
      row GRAPHIFY ok "graph newer than every tracked source file"
    elif [ "$CHECK_ONLY" = 1 ]; then
      row GRAPHIFY FAIL "$newer source file(s) changed since the graph was built"
    elif graphify update >/dev/null 2>&1; then
      row GRAPHIFY ok "updated ($newer file(s) had drifted)"
    else
      row GRAPHIFY FAIL "graphify update failed, $newer file(s) still ahead of the graph"
    fi
  fi
else
  row GRAPHIFY skip "not a graphify repo"
fi

# ---------- report ---------------------------------------------------------
printf '\n=== map-refresh (%s @%s) ===\n' "$(basename "$REPO")" "$(git rev-parse --short=7 HEAD)"
printf '%-9s %-5s %s\n' TIER STATUS DETAIL
printf -- '---------------------------------------------------------------\n'
for r in "${rows[@]}"; do
  IFS='|' read -r a b c <<< "$r"
  printf '%-9s %-5s %s\n' "$a" "$b" "$c"
done
printf -- '---------------------------------------------------------------\n'
if [ "$FAIL" = 1 ]; then
  echo "RESULT: FAIL — a map is lying about this repo. Fix before committing."
  exit 1
fi
echo "RESULT: maps current"
