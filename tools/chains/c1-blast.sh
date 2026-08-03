#!/usr/bin/env bash
# c1-blast.sh <file-or-symbol> — "I'm about to change X. What breaks? What do I run?"
# Prevents: P4 (ships a change without knowing what it breaks), P5 (claims a
#           verification that could not have run).
#
# Primary  : graphify affected   (exhaustive over the graph, 0 tokens) — ONLY if R-0b passes
# Fallback : a generated semgrep importer rule (deterministic, works on a dirty graph)
# Cross-chk: repowise impacted-tests (coverage-backed; empty = UNKNOWN, never "no tests")
#
# Usage: REPO=/path tools/chains/c1-blast.sh src/foo/bar.py
set -euo pipefail
CHAIN_NAME=c1-blast
. "$(dirname "$0")/_lib.sh"
[ -n "${1:-}" ] || { echo "usage: c1-blast.sh <file-or-symbol>" >&2; exit 2; }
TARGET="$1"
full_file "c1-$(basename "$TARGET" | tr -c 'A-Za-z0-9' '-')" >/dev/null
BASE="$(basename "${TARGET%.py}")"
# semgrep patterns below splice $BASE into Python source, so it must be a valid
# Python identifier; dashed basenames (e.g. northstar-inject) are not. Sanitize
# for the GENERATED RULE ONLY — $BASE itself (file filtering, labels) stays original.
BASE_ID="$(printf '%s' "$BASE" | tr '-' '_')"
case "$BASE_ID" in
  [A-Za-z_]*) : ;;
  *) BASE_ID="_$BASE_ID" ;;
esac
PROD=""; TESTS=""; SRC=""
if ! printf '%s' "$BASE_ID" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*$'; then
  echo "== c1-blast $REPO_NAME target=$TARGET" >> "$FULL"
  say "PREFLIGHT: '$BASE' has no valid Python-identifier form ('$BASE_ID') → semgrep importer rule skipped. FALLBACK: literal grep."
  # widen grep to the TARGET's own extension (a .sh target must search *.sh, etc.)
  case "$TARGET" in
    *.*) TARGET_EXT=".${TARGET##*.}" ;;
    *) TARGET_EXT="" ;;
  esac
  case "$TARGET_EXT" in
    "") GREP_INCLUDES=(--include='*.py' --include='*.sh') ;;
    *) GREP_INCLUDES=(--include="*$TARGET_EXT") ;;
  esac
  if gg="$(graph_gate)"; then
    say "PREFLIGHT ok: graph import/dangling = $gg → graphify affected is trustworthy (R-0b), running alongside literal grep."
    graphify affected "$TARGET" --depth 2 --relation calls --relation imports \
        --relation imports_from --relation references 2>/dev/null >> "$FULL" || true
    GPROD=$(grep -oE '(^|[^A-Za-z0-9_/])((src|scripts|hooks|tools|app|lib)/[^:"[:space:]]+\.(py|ts|js|sh))' "$FULL" \
           | grep -oE '(src|scripts|hooks|tools|app|lib)/.*' | grep -v '^tests/' | sort -u || true)
    TESTS=$(grep -oE '(tests?/[^:"[:space:]]+\.(py|ts|js))' "$FULL" | sort -u || true)
  else
    say "PREFLIGHT: graph dangling gate FAILED (${gg:-no graph}) → graphify affected is BLIND. Literal grep only."
    GPROD=""
  fi
  IMP=$(grep -rlE "(^|[^A-Za-z0-9_])${BASE}([^A-Za-z0-9_]|$)" "$REPO" "${GREP_INCLUDES[@]}" 2>/dev/null | sed "s|^$REPO/||" | grep -v "/$(basename "$TARGET")\$" | sort -u || true)
  { echo; echo "== grep-literal importers of $BASE (semgrep skipped: invalid identifier)"; printf '%s\n' "$IMP"; } >> "$FULL"
  PROD=$(printf '%s\n%s\n%s\n' "$PROD" "$GPROD" "$IMP" | grep . | sort -u || true)
  [ -n "$SRC" ] || SRC="literal-grep + graphify fallback (invalid identifier for semgrep)"
  np=$(printf '%s' "$PROD" | grep -c . || true); ni=$(printf '%s' "$IMP" | grep -c . || true)
  nt=$(printf '%s' "$TESTS" | grep -c . || true)
  say "BLAST: $np production file(s) (UNION of $SRC)."
  printf '%s\n' "$PROD" | grep . | head -5 | sed 's/^/  · /' | while read -r l; do echo "$l"; done > "$OUTDIR/.h" || true
  while read -r l; do say "$l"; done < "$OUTDIR/.h"; rm -f "$OUTDIR/.h"
  [ "$np" -gt 5 ] && say "  … $((np-5)) more in FULL"
  IT=$(repowise impacted-tests "$TARGET" 2>/dev/null | grep -E '\.(py|ts|js)' || true)
  { echo; echo "== impacted tests (graph)"; printf '%s\n' "$TESTS"; echo "== impacted tests (repowise coverage)"; printf '%s\n' "$IT"; } >> "$FULL"
  if [ "$nt" -gt 0 ]; then
    say "RUN: $nt test file(s) from the graph — see FULL, then: pytest \$(…)"
  elif [ -n "$IT" ]; then
    say "RUN: coverage-backed tests listed in FULL."
  else
    say "RUN: UNKNOWN — no coverage map ingested and the graph named no tests. Do NOT report 'no tests needed' (P5)."
  fi
  [ "$np" = 0 ] && say "VERDICT: no importers found by EITHER method (grep fallback). Check dynamic/importlib loading before believing it."
  exit 0
fi

echo "== c1-blast $REPO_NAME target=$TARGET" >> "$FULL"

if gg="$(graph_gate)"; then
  say "PREFLIGHT ok: graph import/dangling = $gg → graphify affected is trustworthy (R-0b)."
  graphify affected "$TARGET" --depth 2 --relation calls --relation imports \
      --relation imports_from --relation references 2>/dev/null >> "$FULL" || true
  PROD=$(grep -oE '(^|[^A-Za-z0-9_/])((src|scripts|hooks|tools|app|lib)/[^:"[:space:]]+\.(py|ts|js|sh))' "$FULL" \
         | grep -oE '(src|scripts|hooks|tools|app|lib)/.*' | grep -v '^tests/' | sort -u || true)
  TESTS=$(grep -oE '(tests?/[^:"[:space:]]+\.(py|ts|js))' "$FULL" | sort -u || true)
  SRC="graphify affected (depth 2)"
else
  say "PREFLIGHT: graph dangling gate FAILED (${gg:-no graph}) → graphify affected is BLIND. FALLBACK engaged."
fi

# FALLBACK / CROSS-CHECK: deterministic importer enumeration via a generated rule.
RULE="$OUTDIR/imp-$BASE_ID.yaml"
cat > "$RULE" <<EOF
rules:
  - id: importer-of-$BASE_ID
    languages: [python]
    severity: INFO
    message: "imports $BASE (as $BASE_ID)"
    pattern-either:
      - pattern: import $BASE_ID
      - pattern: from $BASE_ID import \$Y
      - pattern: from \$M.$BASE_ID import \$Y
      - pattern: import \$M.$BASE_ID
      - pattern: $BASE_ID.\$F(...)
EOF
# a bare symbol (no .py) is also called directly — add the call form
case "$TARGET" in
  *.py|*.ts|*.js|*.sh) ;;
  *) printf '      - pattern: %s(...)\n' "$BASE_ID" >> "$RULE" ;;
esac
validate_rules "$RULE"
IMP=$(sg "$RULE" | jq -r '.results[].path' | sed "s|^$REPO/||" | grep -v "/$BASE\.py$" | sort -u || true)
{ echo; echo "== semgrep importers of $BASE"; printf '%s\n' "$IMP"; } >> "$FULL"

# UNION, always. Measured: on a FILE target `graphify affected` returned 1 file where the
# semgrep importer rule returned 14; on a SYMBOL target graphify returned 15 and semgrep 12.
# Neither is a superset of the other, so taking the union is the only completeness-safe move.
UNION=$(printf '%s\n%s\n' "$PROD" "$IMP" | grep . | sort -u || true)
if [ -z "$PROD" ]; then SRC="semgrep importer rule (fallback)"; fi
[ -n "$SRC" ] || SRC="semgrep importer rule"
PROD="$UNION"

np=$(printf '%s' "$PROD" | grep -c . || true); ni=$(printf '%s' "$IMP" | grep -c . || true)
nt=$(printf '%s' "$TESTS" | grep -c . || true)
say "BLAST: $np production file(s) (UNION of $SRC + semgrep; semgrep alone: $ni)."
if [ "$np" -gt 0 ] && [ "$ni" -gt 0 ] && [ "$np" != "$ni" ]; then
  say "  DISAGREEMENT ($np vs $ni) — trust the UNION; both sets are in FULL."
fi
printf '%s\n' "$PROD" | grep . | head -5 | sed 's/^/  · /' | while read -r l; do echo "$l"; done > "$OUTDIR/.h" || true
while read -r l; do say "$l"; done < "$OUTDIR/.h"; rm -f "$OUTDIR/.h"
[ "$np" -gt 5 ] && say "  … $((np-5)) more in FULL"

# tests to run
IT=$(repowise impacted-tests "$TARGET" 2>/dev/null | grep -E '\.(py|ts|js)' || true)
{ echo; echo "== impacted tests (graph)"; printf '%s\n' "$TESTS"; echo "== impacted tests (repowise coverage)"; printf '%s\n' "$IT"; } >> "$FULL"
if [ "$nt" -gt 0 ]; then
  say "RUN: $nt test file(s) from the graph — see FULL, then: pytest \$(…)"
elif [ -n "$IT" ]; then
  say "RUN: coverage-backed tests listed in FULL."
else
  say "RUN: UNKNOWN — no coverage map ingested and the graph named no tests. Do NOT report 'no tests needed' (P5)."
fi
[ "$np" = 0 ] && say "VERDICT: no importers found by EITHER method. Validated rules, so this zero is real — but check dynamic/importlib loading before believing it."
exit 0
