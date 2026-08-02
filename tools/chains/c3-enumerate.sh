#!/usr/bin/env bash
# c3-enumerate.sh <rule-name|path> — "what is EVERY place that does Y?"
# Prevents: P3 (auditor misses a blocking site because it is one of 13 scattered ones)
#           P6 (concludes "the repo doesn't do X" from a silently-broken query).
#
# THIS IS THE CLASS ONLY SEMGREP CAN ANSWER. A ranked retriever returns a top-k ordered
# by similarity; an aggregation question needs the complete set defined by a predicate.
# Measured on the N=13 deny-site ground truth in awesome-harness:
#   semgrep 100%/100% · grep 80%/92% · repowise search_codebase 80%/62% · graphify query 0%/0%
#
# Usage: REPO=/path tools/chains/c3-enumerate.sh deny-sites
#        REPO=/path tools/chains/c3-enumerate.sh             # all committed rules
set -euo pipefail
CHAIN_NAME=c3-enumerate
. "$(dirname "$0")/_lib.sh"
WHICH="${1:-}"
if [ -z "$WHICH" ]; then CFG="$RULES"; LABEL="all-rules"
elif [ -f "$WHICH" ]; then CFG="$WHICH"; LABEL="$(basename "$WHICH")"
elif [ -f "$RULES/$WHICH.yaml" ]; then CFG="$RULES/$WHICH.yaml"; LABEL="$WHICH"
else echo "no such rule: $WHICH (have: $(ls "$RULES" | tr '\n' ' '))" >&2; exit 2; fi
full_file "c3-${LABEL%.yaml}" >/dev/null
echo "== c3-enumerate $REPO_NAME rules=$CFG" >> "$FULL"

validate_rules "$CFG"        # R-0a: a zero from an unvalidated rule is a lie
J=$(sg "$CFG")
ERRS=$(echo "$J" | jq -r '.errors|length' 2>/dev/null || echo 0)
TOT=$(echo "$J" | jq -r '.results|length')
echo "$J" | jq -r '.results[]|"\(.check_id|sub(".*\\.";"")) \(.path):\(.start.line)"' | sed "s|$REPO/||" | sort >> "$FULL"
echo "$J" | jq -r '.errors[]?|"ERROR \(.message)"' >> "$FULL" || true

if [ "$ERRS" != 0 ]; then
  # A file semgrep cannot parse is SKIPPED, not flagged: the set is silently short (P6).
  say "PREFLIGHT WARN: $ERRS file(s) semgrep could not parse — they are MISSING from the set below:"
  echo "$J" | jq -r '.errors[]?.path // .errors[]?.message' | sed "s|$REPO/||" | sort -u | head -3 \
    | while read -r l; do echo "  ! unparsed: $l (grep it by hand)"; done > "$OUTDIR/.he" || true
  while read -r l; do say "$l"; done < "$OUTDIR/.he"; rm -f "$OUTDIR/.he"
else
  say "PREFLIGHT ok: semgrep parsed every file, 0 scan errors — the set below is complete."
fi
say "SET: $TOT site(s) for '$LABEL' in $REPO_NAME — this set is COMPLETE over the predicate."
echo "$J" | jq -r '.results[].check_id|sub(".*\\.";"")' | sort | uniq -c | sort -rn | head -8 \
  | while read -r c r; do echo "  $c × $r"; done > "$OUTDIR/.h3" || true
while read -r l; do say "$l"; done < "$OUTDIR/.h3"; rm -f "$OUTDIR/.h3"

if [ "$TOT" = 0 ]; then
  # FALLBACK: a validated rule returning zero is credible, but prove the predicate is
  # expressible at all before reporting "this repo never does Y".
  say "FALLBACK: zero hits from a VALIDATED rule. Confirm with a literal grep before you"
  say "  report absence — and check the rule's paths.include actually matches this repo's layout."
fi
say "Full site list (path:line, sorted) is in FULL. Do not paste it into the main context."
exit 0
