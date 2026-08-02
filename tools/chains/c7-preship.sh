#!/usr/bin/env bash
# c7-preship.sh [revspec] — the pre-ship gate: score the change, then re-run the
# committed predicates ONLY over the files it touched.
# Prevents: P3 (a change lands next to 4 other blocking sites nobody looked at),
#           P4 (ships without knowing the blast radius), P5 (claims a verification).
#
# Primary  : repowise risk   (defect score from the DIFF SHAPE — no index, no LLM, no wiki)
# Cross-chk: semgrep over the changed files only (new WARNING findings this change introduces)
# Cross-chk: c1-blast on the largest changed file (who imports what you just edited)
#
# Usage: REPO=/path tools/chains/c7-preship.sh            # uncommitted working tree
#        REPO=/path tools/chains/c7-preship.sh HEAD       # last commit
#        REPO=/path tools/chains/c7-preship.sh main..HEAD # a branch
set -euo pipefail
CHAIN_NAME=c7-preship
. "$(dirname "$0")/_lib.sh"
REV="${1:-}"
full_file c7-preship >/dev/null
echo "== c7-preship $REPO_NAME rev=${REV:-WORKING-TREE}" >> "$FULL"

git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || { say "PREFLIGHT FAIL: not a git repo."; exit 3; }

if [ -n "$REV" ]; then
  CHANGED=$(git -C "$REPO" diff --name-only "$REV" 2>/dev/null || git -C "$REPO" show --name-only --format= "$REV")
else
  CHANGED=$(git -C "$REPO" status --porcelain | awk '{print $NF}')
fi
NC=$(printf '%s' "$CHANGED" | grep -c . || true)
if [ "$NC" = 0 ]; then say "PREFLIGHT: nothing changed for '${REV:-working tree}'. Nothing to gate."; exit 0; fi
say "PREFLIGHT ok: $NC changed file(s) in ${REV:-the working tree}."
{ echo; echo "== changed"; printf '%s\n' "$CHANGED"; } >> "$FULL"

# 1. diff-shape defect risk (works with zero index and zero wiki pages)
if [ -n "$REV" ]; then
  R=$(repowise risk "$REV" --path "$REPO" --format json 2>/dev/null | sed -n '/^[{[]/,$p' || true)
  if jq -e . >/dev/null 2>&1 <<<"$R"; then
    printf '%s\n' "$R" >> "$FULL"
    say "RISK: $(jq -r '"\(.classification // .level // "?") · \(.risk_percentile // .percentile // "?")th pct · review=\(.review_priority // "?")"' <<<"$R")"
  else
    repowise risk "$REV" --path "$REPO" >> "$FULL" 2>&1 || true
    say "RISK: table form written to FULL (json unavailable for this revspec)."
  fi
else
  say "RISK: skipped — repowise risk scores a commit or range, not an uncommitted tree."
fi

# 2. the committed predicates, scoped to the changed files ONLY
validate_rules "$RULES"
LIST="$OUTDIR/changed.txt"; printf '%s\n' "$CHANGED" | sed "s|^|$REPO/|" > "$LIST"
J=$(semgrep --config "$RULES" --quiet --json --metrics=off \
      $(while read -r f; do [ -f "$f" ] && printf ' %s' "$f"; done < "$LIST") 2>/dev/null || echo '{"results":[]}')
printf '%s\n' "$J" | jq -r '.results[]|"\(.extra.severity) \(.check_id|sub(".*\\.";"")) \(.path):\(.start.line)"' | sed "s|$REPO/||" | sort >> "$FULL"
W=$(jq -r '[.results[]|select(.extra.severity=="WARNING")]|length' <<<"$J")
I=$(jq -r '[.results[]|select(.extra.severity=="INFO")]|length' <<<"$J")
say "RULES on changed files: $W warning(s), $I enumeration hit(s)."
jq -r '.results[]|select(.extra.severity=="WARNING")|"  ! \(.check_id|sub(".*\\.";"")) \(.path):\(.start.line)"' <<<"$J" \
  | sed "s|$REPO/||" | head -4 > "$OUTDIR/.h7" || true
while read -r l; do say "$l"; done < "$OUTDIR/.h7"; rm -f "$OUTDIR/.h7"

# 3. blast radius of the single biggest changed source file
BIG=$(printf '%s\n' "$CHANGED" | grep -E '\.(py|ts|js)$' | head -1 || true)
if [ -n "$BIG" ]; then
  say "NEXT: blast radius of $BIG → tools/chains/c1-blast.sh $BIG"
fi
if [ "$W" -gt 0 ]; then say "VERDICT: HOLD — fix the warnings above or record why they are acceptable."
else say "VERDICT: clean on the committed predicates. That is NOT a test run (P5)."; fi
exit 0
