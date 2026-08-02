#!/usr/bin/env bash
# c0-preflight.sh — run ONCE per repo before trusting any other chain.
# Prevents: P5 (claiming a verification that could not have run) and P6 (concluding
#           "the repo doesn't do X" from a silently-broken query).
# Usage: REPO=/path/to/repo tools/chains/c0-preflight.sh
# Verdict tells you which chains are TRUSTWORTHY here and which are BLIND.
set -euo pipefail
CHAIN_NAME=c0-preflight
. "$(dirname "$0")/_lib.sh"
full_file c0-preflight >/dev/null

{ echo "== c0-preflight $REPO_NAME $(date)"; } >> "$FULL"

# 1. semgrep rules parse (R-0a)
validate_rules "$RULES"
semgrep scan --validate --config "$RULES" --metrics=off >> "$FULL" 2>&1 || true

# 2. graphify graph present, fresh, and not dangling (R-0b)
if [ -f "$REPO/graphify-out/graph.json" ]; then
  age=$(( ( $(date +%s) - $(stat -f %m "$REPO/graphify-out/graph.json") ) / 86400 ))
  if gg="$(graph_gate)"; then
    say "graphify: graph ${age}d old, import edges/dangling = $gg → C1 'graphify affected' TRUSTWORTHY."
  else
    say "graphify: graph ${age}d old, import edges/dangling = ${gg:-?} → 'affected' is BLIND here; C1 uses the semgrep fallback."
  fi
  [ "$age" -gt 7 ] && say "  WARN graph is ${age} days stale — run: graphify update $REPO"
  echo "graph age ${age}d, gate=${gg:-fail}" >> "$FULL"
else
  say "graphify: NO graph.json → C1 structural leg unavailable (run: graphify $REPO)."
fi

# 3. repowise index presence — dead-code/risk need it, wiki pages are NOT required
if [ -d "$REPO/.repowise" ]; then
  pages=$(repowise status "$REPO" 2>/dev/null | sed -n 's/.*Total pages *[│|] *\([0-9,]*\).*/\1/p' | head -1)
  pages="${pages:-0}"
  say "repowise: .repowise/ present, $pages wiki pages. dead-code + risk work at 0 pages."
else
  say "repowise: NO .repowise/ → C5 dead-code unavailable (run: repowise update --index-only $REPO)."
fi

# 4. coverage map — the P5 trap: empty tests_to_run means UNKNOWN, not "no tests"
if find "$REPO/.repowise" -name 'coverage*' 2>/dev/null | grep -q .; then
  say "coverage: map ingested → empty tests_to_run means 'none'."
else
  say "coverage: NO map → an empty tests_to_run/impacted-tests means UNKNOWN, never 'no tests needed' (P5)."
fi

# 5. git cleanliness — risk scoring reads the working tree
if git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1; then
  dirty=$(git -C "$REPO" status --porcelain | wc -l | tr -d ' ')
  say "git: $(git -C "$REPO" rev-parse --short HEAD), $dirty uncommitted file(s)."
fi
say "VERDICT: preflight complete for $REPO_NAME. Re-run after any graphify/repowise rebuild."
