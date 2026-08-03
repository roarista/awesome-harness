#!/usr/bin/env bash
# retrieve.sh <intent> <query> [scope] — the intent-classified retrieval router.
#
# WHY: docs/audits/2026-08-02/10-search-intent.md measured 1,456 search episodes.
# Three intents (name-recovery 46.2%, enumerate 41.9%, check-existence 51.5%) burn
# ~46% of all search spend on episodes that never resolve. grep is the wrong
# instrument for them and the right instrument for slice/verify/history (69-77%).
# This script routes on the STATED intent instead of reflex-grepping.
#
# INVARIANTS enforced here (each fixes a measured failure):
#   I1  --include is ALWAYS single-quoted   (137 searches never ran under zsh)
#   I2  ONE search per invocation, no `echo === ; cmd1; cmd2` bundles (634 hid an empty section)
#   I3  3-attempt circuit breaker on the same (intent,query) (33.6% of episodes flailed)
#
# Usage: REPO=/path tools/retrieve.sh <name|enumerate|exists|blast|slice|verify|history|diagnose> <query> [scope]
set -euo pipefail
CHAIN_NAME=retrieve
LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/chains/_lib.sh"

INTENT="${1:-}"; QUERY="${2:-}"; SCOPE="${3:-}"

routing_table() {
  cat <<'TBL'
retrieve.sh <intent> <query> [scope]  — state the intent, do not guess the command.
 intent     winning combination                              measured  receipt owed
 name       graphify/graph.json vocab dump -> copy the token  46.2%->  literal id+label+file
 enumerate  semgrep rule (committed or generated), COUNT      41.9%->  a count, never `| head`
 exists     grep -c with QUOTED --include + scope receipt     51.5%->  zero + scope + file count
 blast      label->node id, then c1-blast.sh (graphify+semgrep) 48.5%-> union size + source
 slice      grep -n 'X' -A30 <file>   (grep WINS — keep it)   69.8%    non-empty lines
 verify     grep -n '<new string>' <file> (grep WINS)         77.1%    non-empty lines
 history    git log --grep / -S / --stat (git WINS)           59.4%    commit hashes
 diagnose   NOTHING we have wins; stop at 3 and escalate      49.5%    an honest non-answer
TBL
}

case "$INTENT" in
  name|enumerate|exists|blast|slice|verify|history|diagnose) ;;
  *) routing_table >&2; exit 2 ;;
esac
[ -n "$QUERY" ] || { echo "intent '$INTENT' needs a <query>." >&2; routing_table >&2; exit 2; }

. "$LIB"
SCOPE="${SCOPE:-$REPO}"
KEY="$(printf '%s|%s' "$INTENT" "$QUERY" | tr -c 'A-Za-z0-9' '-')"
full_file "retrieve-$KEY" >/dev/null
echo "== retrieve intent=$INTENT query=$QUERY scope=$SCOPE repo=$REPO_NAME" >> "$FULL"

# --- I3: 3-attempt circuit breaker ------------------------------------------
CB="$OUTDIR/.attempts-$KEY"
# stale sentinels (>24h old) never expired, so a FIRST search of an old
# (intent,query) pair from a prior session would wrongly hit the breaker.
if [ -f "$CB" ] && [ -z "$(find "$CB" -mmin -1440 2>/dev/null)" ]; then
  rm -f "$CB"
fi
N="${RETRIEVE_ATTEMPT:-$(( $( [ -f "$CB" ] && cat "$CB" || echo 0 ) + 1 ))}"
echo "$N" > "$CB"
if [ "$N" -ge 4 ]; then
  say "CIRCUIT BREAKER: attempt $N on the same ($INTENT,$QUERY). STOP SEARCHING."
  say "  33.6% of measured episodes flail; 142 issued 8+ searches on one question."
  say "  Flailing is the signature of a WRONG INSTRUMENT, not a hard question."
  say "  Change method: name->vocab dump, enumerate->semgrep, blast->graphify affected,"
  say "  or escalate to a subagent / ask Ro. Do not issue a fourth pattern."
  say "  (reset: rm $CB)"
  exit 4
fi
say "ATTEMPT $N/3 · intent=$INTENT · scope=$(basename "$SCOPE")"

# SKIPPED_DIRS derived from $EXCL (single source of truth in _lib.sh) — never
# hardcode a second copy that can drift from what was actually excluded.
SKIPPED_DIRS="$(printf '%s' "$EXCL" | grep -oE -- '--exclude-dir=[^ ]+' | sed 's/--exclude-dir=//' | tr '\n' ' ' | sed 's/ $//')"
skipped_dirs_line() { say "SKIPPED-DIRS: $SKIPPED_DIRS"; }

GRAPH="$REPO/graphify-out/graph.json"

# vocab_dump <stem>  -> "id | label | file" lines, from the graph or a source fallback
vocab_dump() {
  local stem="$1"
  if [ -f "$GRAPH" ]; then
    python3 - "$GRAPH" "$stem" <<'PY'
import json,sys
g=json.load(open(sys.argv[1])); s=sys.argv[2].lower()
n=g['nodes']; hit=[x for x in n if s in str(x.get('label','')).lower() or s in str(x.get('id','')).lower()]
print(f"#SCANNED {len(n)} #HIT {len(hit)}")
for x in hit: print(f"{x.get('id')} | {x.get('label')} | {x.get('source_file')}:{x.get('source_location')}")
PY
  else
    # no graph: one-shot local vocab dump (still strictly better than serial guessing)
    local defs
    defs=$(grep -rhoE '^[[:space:]]*(def|class|function|const|[a-z_]+\(\)) [A-Za-z_][A-Za-z0-9_]*' \
             --include='*.py' --include='*.sh' --include='*.ts' --include='*.js' $EXCL "$SCOPE" 2>/dev/null \
           | sed 's/^[[:space:]]*//' | sort -u || true)
    printf '#SCANNED %s #HIT %s\n' "$(printf '%s\n' "$defs" | grep -c . || true)" \
           "$(printf '%s\n' "$defs" | grep -ic -- "$stem" || true)"
    printf '%s\n' "$defs" | grep -i -- "$stem" || true
  fi
}

case "$INTENT" in

# ---------------------------------------------------------------- name -----
name)
  V="$(vocab_dump "$QUERY" || true)"
  printf '%s\n' "$V" >> "$FULL"
  HDR="$(printf '%s\n' "$V" | head -1)"
  BODY="$(printf '%s\n' "$V" | tail -n +2 | grep . || true)"
  NH="$(printf '%s\n' "$BODY" | grep -c . || true)"
  if [ -f "$GRAPH" ]; then say "PREFLIGHT ok: graph vocabulary present ($HDR)."
  else
    say "PREFLIGHT: no graphify-out/graph.json — FALLBACK to a source-derived vocab dump ($HDR)."
    skipped_dirs_line
  fi
  if [ "$NH" = 0 ]; then
    say "VOCAB: 0 identifiers contain '$QUERY'."
    say "FALLBACK: the concept is named something ELSE. WIDEN THE CONCEPT WORD, do not"
    say "  widen the pattern. NEVER issue a 3+-alternation guess-grep (20.8% of all"
    say "  searches, 46.2% success, 1.31M tokens wasted)."
  else
    say "VOCAB: $NH identifier(s) match '$QUERY' — COPY the literal token, do not retype it:"
    printf '%s\n' "$BODY" | head -8 > "$OUTDIR/.rn"
    while read -r l; do say "  $l"; done < "$OUTDIR/.rn"; rm -f "$OUTDIR/.rn"
    [ "$NH" -gt 8 ] && say "  … $((NH-8)) more in FULL"
  fi
  ;;

# ------------------------------------------------------------ enumerate -----
enumerate)
  # committed rule? delegate to the chain that already owns ground truth.
  if [ -f "$RULES/$QUERY.yaml" ] || [ -f "$QUERY" ]; then
    say "ROUTE: committed rule -> c3-enumerate.sh (semgrep, complete over the predicate)."
    say "---- c3-enumerate output ----"
    rc=0
    REPO="$REPO" "$HARNESS_ROOT/tools/chains/c3-enumerate.sh" "$QUERY" > "$OUTDIR/.re" 2>&1 || rc=$?
    cat "$OUTDIR/.re" >> "$FULL"
    while read -r l; do say "$l"; done < "$OUTDIR/.re"; rm -f "$OUTDIR/.re"
    [ "$rc" != 0 ] && say "FALLBACK: c3-enumerate exited $rc — this is a CHAIN FAILURE, not a count of zero."
    exit 0
  fi
  case "$QUERY" in
    [A-Za-z_]*)
      IS_IDENT=1
      case "$QUERY" in *[!A-Za-z0-9_]*) IS_IDENT=0 ;; esac
      ;;
    *) IS_IDENT=0 ;;
  esac
  if [ "$IS_IDENT" != 1 ]; then
    # Not a bare identifier: a callable-shaped semgrep pattern generated from
    # this query would be syntactic garbage (R-0a correctly refuses it).
    # Answer with the literal leg instead of pretending at structure.
    GN="$(grep -rc --include='*.py' --include='*.sh' $EXCL -- "$QUERY" "$SCOPE" 2>/dev/null | awk -F: '{s+=$NF} END{print s+0}' || true)"
    grep -rn --include='*.py' --include='*.sh' $EXCL -- "$QUERY" "$SCOPE" 2>/dev/null >> "$FULL" || true
    say "COUNT: $GN literal line(s) for '$QUERY' (grep, NOT a structural set — multi-word queries"
    say "  cannot be turned into a valid semgrep callable pattern, so no COMPLETE structural answer exists here)."
    skipped_dirs_line
    say "  -> for a structural/COMPLETE answer, use \`exists\` or write a hand rule in $RULES/."
    exit 0
  fi
  RULE="$OUTDIR/gen-$KEY.yaml"
  cat > "$RULE" <<EOF
rules:
  - id: enumerate-$KEY
    languages: [python]
    severity: INFO
    message: "use of $QUERY"
    pattern-either:
      - pattern: $QUERY(...)
      - pattern: \$X.$QUERY(...)
      - pattern: $QUERY
EOF
  validate_rules "$RULE"          # R-0a: a zero from an unvalidated rule is a lie
  J="$(sg "$RULE")"
  TOT="$(printf '%s' "$J" | jq -r '.results|length')"
  ERRS="$(printf '%s' "$J" | jq -r '.errors|length')"
  printf '%s' "$J" | jq -r '.results[]|"\(.path):\(.start.line)"' | sed "s|$REPO/||" | sort >> "$FULL"
  say "COUNT: $TOT structural site(s) for '$QUERY' (semgrep, COMPLETE — no \`| head\`, no truncation)."
  [ "$ERRS" != 0 ] && say "PREFLIGHT WARN: $ERRS unparsed file(s) are MISSING from this set (see FULL)."
  if [ "$TOT" = 0 ]; then
    # I1: --include is quoted. Unquoted, zsh glob-expands it and grep NEVER RUNS.
    GN="$(grep -rc --include='*.py' --include='*.sh' $EXCL -- "$QUERY" "$SCOPE" 2>/dev/null | awk -F: '{s+=$NF} END{print s+0}' || true)"
    say "FALLBACK: semgrep found 0 (python-only patterns). Literal grep cross-check: $GN line(s)."
    skipped_dirs_line
    [ "$GN" -gt 0 ] && say "  -> the predicate is NOT python-structural here; use \`exists\` or a hand rule."
  fi
  ;;

# --------------------------------------------------------------- exists -----
exists)
  # I1: the quoting fix, literally. NEVER write --include=*.py unquoted.
  CMD="grep -rn --include='*' $EXCL -- '$QUERY' $SCOPE"
  HITS="$(grep -rn --include='*' $EXCL -- "$QUERY" "$SCOPE" 2>/dev/null || true)"
  printf '%s\n' "$HITS" >> "$FULL"
  NH="$(printf '%s\n' "$HITS" | grep -c . || true)"
  NF="$(grep -rl --include='*' $EXCL -- '' "$SCOPE" 2>/dev/null | wc -l | tr -d ' ')"
  say "PREFLIGHT ok: grep ran (exit captured), --include is QUOTED (I1: 137 measured searches"
  say "  never executed because zsh glob-expanded an unquoted --include=*.py)."
  skipped_dirs_line
  if [ "$NH" = 0 ]; then
    say "ZERO — and here is the receipt, because a bare zero is not evidence of absence:"
    say "  scope     : $SCOPE"
    say "  files seen: $NF"
    say "  command   : $CMD"
    say "  This zero means: not present as this literal string, in these files, under this scope."
    say "  It does NOT mean the concept is absent — run \`retrieve.sh name $QUERY\` next."
  else
    say "EXISTS: $NH line(s) across $(printf '%s\n' "$HITS" | cut -d: -f1 | sort -u | grep -c .) file(s) in $NF scanned."
    printf '%s\n' "$HITS" | cut -d: -f1 | sort | uniq -c | sort -rn | head -5 > "$OUTDIR/.rx"
    while read -r l; do say "  $l"; done < "$OUTDIR/.rx"; rm -f "$OUTDIR/.rx"
  fi
  ;;

# ---------------------------------------------------------------- blast -----
blast)
  TARGET="$QUERY"
  if [ -f "$GRAPH" ] && [ ! -e "$REPO/$QUERY" ]; then
    ID="$(python3 - "$GRAPH" "$QUERY" <<'PY'
import json,sys
g=json.load(open(sys.argv[1])); q=sys.argv[2].lower()
ex=[n for n in g['nodes'] if q in (str(n.get('id','')).lower(),str(n.get('label','')).lower())]
fz=[n for n in g['nodes'] if q in str(n.get('label','')).lower() or q in str(n.get('id','')).lower()]
c=ex or fz
print(c[0]['id'] if c else '')
PY
)"
    if [ -n "$ID" ]; then
      say "RESOLVED: label '$QUERY' -> node id '$ID' (graphify affected on a LABEL returns a"
      say "  silent false negative — 'No affected nodes found' is the output of a WRONG id)."
      TARGET="$ID"
    else
      say "FALLBACK: '$QUERY' resolves to NO node id in the graph. NOT reporting a zero."
      say "  Passing the raw string to c1-blast.sh, whose semgrep importer leg works on a dirty graph."
    fi
  else
    say "PREFLIGHT: target is a path (or no graph) — passing through unresolved."
  fi
  say "---- c1-blast output ----"
  rc=0
  REPO="$REPO" "$HARNESS_ROOT/tools/chains/c1-blast.sh" "$TARGET" > "$OUTDIR/.rb" 2>&1 || rc=$?
  cat "$OUTDIR/.rb" >> "$FULL"
  while read -r l; do say "$l"; done < "$OUTDIR/.rb"; rm -f "$OUTDIR/.rb"
  if [ "$rc" != 0 ]; then
    say "FALLBACK: c1-blast exited $rc (not a zero-callers answer — the chain FAILED)."
    say "  Do NOT read this as 'nothing depends on $TARGET'. Retry with the SYMBOL, not the path,"
    say "  or run: retrieve.sh enumerate <symbol>  for a structural cross-check."
  fi
  ;;

# ------------------------------------------------- slice / verify / history --
slice)
  [ -f "$SCOPE" ] || { say "slice needs a FILE as scope: retrieve.sh slice '<anchor>' <file>"; exit 2; }
  say "PREFLIGHT ok: grep is the RIGHT tool here (69.8% success, cheapest intent). Not escalating."
  grep -n -A30 -- "$QUERY" "$SCOPE" >> "$FULL" 2>/dev/null || true
  NH="$(grep -c -- "$QUERY" "$SCOPE" 2>/dev/null || true)"
  if [ "${NH:-0}" = 0 ]; then say "FALLBACK: anchor '$QUERY' not in $SCOPE — re-anchor via \`retrieve.sh name $QUERY\`."
  else say "SLICE: $NH anchor hit(s) in $SCOPE; 30 lines of context per hit are in FULL."; fi
  ;;

verify)
  say "PREFLIGHT ok: grep is the RIGHT tool here (77.1% — best tool/intent fit in the corpus)."
  skipped_dirs_line
  H="$(grep -rn --include='*' $EXCL -- "$QUERY" "$SCOPE" 2>/dev/null || true)"
  printf '%s\n' "$H" >> "$FULL"
  NH="$(printf '%s\n' "$H" | grep -c . || true)"
  if [ "$NH" = 0 ]; then say "NOT LANDED: '$QUERY' absent from $SCOPE. The edit did not take (or went elsewhere)."
  else
    say "LANDED: $NH occurrence(s) of '$QUERY'."
    printf '%s\n' "$H" | head -4 | cut -c1-110 > "$OUTDIR/.rv"
    while read -r l; do say "  $l"; done < "$OUTDIR/.rv"; rm -f "$OUTDIR/.rv"
  fi
  ;;

history)
  say "PREFLIGHT ok: git is the RIGHT tool here (59.4%, 4 calls, 1,242 tokens median)."
  { echo "== git log --grep"; git -C "$REPO" log --oneline --grep="$QUERY" -20;
    echo "== git log -S"; git -C "$REPO" log --oneline -S"$QUERY" -20; } >> "$FULL" 2>&1 || true
  G="$(git -C "$REPO" log --oneline --grep="$QUERY" -20 2>/dev/null || true)"
  S="$(git -C "$REPO" log --oneline -S"$QUERY" -20 2>/dev/null || true)"
  ng="$(printf '%s\n' "$G" | grep -c . || true)"; ns="$(printf '%s\n' "$S" | grep -c . || true)"
  say "PRIOR ART: $ng commit(s) by message, $ns commit(s) that changed the string '$QUERY'."
  printf '%s\n%s\n' "$G" "$S" | grep . | sort -u | head -6 | cut -c1-110 > "$OUTDIR/.rh" || true
  while read -r l; do say "  $l"; done < "$OUTDIR/.rh"; rm -f "$OUTDIR/.rh"
  [ "$ng" = 0 ] && [ "$ns" = 0 ] && say "FALLBACK: no commit touches '$QUERY' — it is new, or named differently (\`name\`)."
  ;;

# ------------------------------------------------------------- diagnose -----
diagnose)
  say "NO ROUTE. Measured honestly: diagnose-failure is 49.5% success, 35.8% flail, and"
  say "  NOTHING in our toolbox wins it. The bottleneck is causal reasoning, not retrieval."
  say "  A better index will not move this number."
  say "DO INSTEAD: (1) read the ACTUAL error text, not a grep of it;"
  say "  (2) \`retrieve.sh name <symbol-from-the-error>\` to get the real identifier;"
  say "  (3) \`retrieve.sh slice <symbol> <that-file>\` to read the site."
  say "  (4) \`retrieve.sh history <symbol>\` ONLY if this is a regression with a good baseline."
  say "STOP RULE: at attempt 3 on '$QUERY', escalate to a subagent or ask Ro. Do not grep again."
  ;;
esac
exit 0
