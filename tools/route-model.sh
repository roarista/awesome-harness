#!/usr/bin/env bash
# route-model.sh — deterministic, hardcoded task->model table. No network, no LLM call.
#
# Usage:
#   tools/route-model.sh "<task description>" [--files N] [--model X]
#   ROUTE_MODEL=<model> tools/route-model.sh "<task description>"
#
# Prints a NECESSITY verdict first (LAUNCH / DO-NOT-LAUNCH), then, if LAUNCH,
# AGENT / MODEL / EFFORT / WHY. Edit the table below by hand — that is the point.
set -euo pipefail

TASK=""
FILES=0
OVERRIDE_MODEL="${ROUTE_MODEL:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --files) FILES="$2"; shift 2 ;;
    --model) OVERRIDE_MODEL="$2"; shift 2 ;;
    *) TASK="$1"; shift ;;
  esac
done

if [[ -z "$TASK" ]]; then
  echo "usage: route-model.sh \"<task description>\" [--files N] [--model X]" >&2
  exit 2
fi

lower="$(echo "$TASK" | tr '[:upper:]' '[:lower:]')"

# ---------------------------------------------------------------------------
# STEP 1: NECESSITY CHECK — fires before any model is picked. 51.9% of all
# tokens go to the subagent fleet; the fix is fewer launches, not cheaper ones.
# ---------------------------------------------------------------------------
is_judgment=0
echo "$lower" | grep -qE '\b(audit|review|verify|red.?team|second opinion|architect the|decide (between|whether)|forensic|analys[a-z]*|investigat[a-z]*|inspect|read.?only|do not edit|don.t edit|no edits|survey|census|mine the transcripts)\b' && is_judgment=1

if [[ -z "$OVERRIDE_MODEL" ]]; then
  if [[ "$FILES" -le 1 ]] && echo "$lower" | grep -qE '^(read|cat|show|print|what does|what is in|look at) '; then
    echo "NECESSITY: DO-NOT-LAUNCH: single-file read main can do from context directly"
    exit 0
  fi
  if echo "$lower" | grep -qE '\b(one.?line|single.?line|typo|rename this variable|bump (the )?version)\b' && [[ "$is_judgment" -eq 0 ]]; then
    echo "NECESSITY: DO-NOT-LAUNCH: trivial one-line edit main can make directly, no subagent needed"
    exit 0
  fi
fi

echo "NECESSITY: LAUNCH"

# ---------------------------------------------------------------------------
# STEP 2: OVERRIDE — Ro's explicit "run this one with model X". Wins over
# EVERYTHING below, no exceptions, including audit/judgment tasks. Ro's
# directive 2026-08-02: "si Ro nombra un modelo, se usa ese" — the previous
# auditor hard-lock that beat the override is gone. Ro always wins.
# ---------------------------------------------------------------------------
if [[ -n "$OVERRIDE_MODEL" ]]; then
  echo "OVERRIDE"
  echo "AGENT: general-purpose"
  echo "MODEL: $OVERRIDE_MODEL"
  echo "EFFORT: medium"
  echo "WHY: explicit override (ROUTE_MODEL/--model) requested by Ro — wins over every rule below"
  exit 0
fi

# ---------------------------------------------------------------------------
# STEP 3: HARDCODED TABLE. Order matters — first match wins.
#
# Codex-first directive (Ro, 2026-08-02, verbatim): "no me gusta, por ejemplo,
# Opus. No, porque justo queremos usar Codex. Queremos usar Codex más porque
# nos dan más créditos." Codex credits are cheap/abundant for Ro; Opus is not.
# Codex is now the default for judgment/audit tasks too, not just builds.
#
# HONEST CAVEAT (do not delete): the one harness component with POSITIVE
# MEASURED evidence was the opus auditor (12% of the fleet, 39/55 rejects,
# 36 invented-API catches). Codex-as-auditor is UNMEASURED as of this change.
# This is Ro's explicit call, executed here. To re-measure: run both an opus
# and a codex audit against a known-bad diff and compare reject rate.
# ---------------------------------------------------------------------------
if [[ "$is_judgment" -eq 1 ]]; then
  # NARROW escalation: a SECOND audit pass, opus, ONLY after a codex audit has
  # already returned PASS on something irreversible (money/auth/credential/
  # data-loss). Caller must say so explicitly (e.g. "second pass after codex
  # passed the auth change") — the router is stateless and cannot infer this.
  if echo "$lower" | grep -qE '\b(money|payment|billing|auth|authentication|credential|secret|api.?key|password|delete|data loss|irreversible|prod(uction)? database)\b' \
     && echo "$lower" | grep -qE '\b(second pass|after codex (passed|approved)|post.?codex|escalat)\b'; then
    echo "AGENT: opus"
    echo "MODEL: opus"
    echo "EFFORT: low"
    echo "WHY: second audit pass on an irreversible-class change after a codex PASS — the one narrow opus escalation kept (REVERT: see docs/audits/2026-08-02/14-model-router.md)"
    exit 0
  fi
  echo "AGENT: codex-audit"
  echo "MODEL: codex"
  echo "EFFORT: medium"
  echo "WHY: judgment/audit task — codex default per Ro's directive (credits); UNMEASURED as auditor, opus escalation available for irreversible second-pass"
  exit 0
fi
# --- commented-out original opus-default row, restore by uncommenting: ---
# if [[ "$is_judgment" -eq 1 ]]; then
#   echo "AGENT: opus"
#   echo "MODEL: opus"
#   echo "EFFORT: low"
#   echo "WHY: judgment/audit task — hard rule, never downgraded (positive-evidence component)"
#   exit 0
# fi

if echo "$lower" | grep -qE '\b(money|payment|billing|auth|authentication|credential|secret|api.?key|password|delete|data loss|irreversible|prod(uction)? database)\b'; then
  echo "AGENT: codex"
  echo "MODEL: codex"
  echo "EFFORT: medium"
  echo "WHY: touches money/auth/security/data-loss — codex builder (haiku is banned for this class); pair with a follow-up audit before merge"
  exit 0
fi

if echo "$lower" | grep -qE '\b(implement|build|refactor|fix|patch|write code|migrate|add (a |the )?(feature|function|endpoint))\b'; then
  if [[ "$FILES" -gt 15 ]]; then
    echo "AGENT: gemini"
    echo "MODEL: gemini"
    echo "EFFORT: medium"
    echo "WHY: code write with wide blast radius (>15 files) — large-context non-Claude pass"
    exit 0
  fi
  echo "AGENT: codex"
  echo "MODEL: codex"
  echo "EFFORT: medium"
  echo "WHY: code write with a known/bounded target file — synchronous codex builder"
  exit 0
fi

if echo "$lower" | grep -qE '\b(large.?context|whole.?repo|entire codebase|vision|screenshot|image|non.?anthropic|second (llm )?opinion)\b'; then
  echo "AGENT: gemini"
  echo "MODEL: gemini"
  echo "EFFORT: medium"
  echo "WHY: large-context sweep / vision / explicit non-Claude voice"
  exit 0
fi

if echo "$lower" | grep -qE '\b(list|count|grep|find|locate|rename|extract|format|inventory|bulk|mechanical)\b' && [[ "$FILES" -le 5 ]]; then
  echo "AGENT: codex"
  echo "MODEL: codex"
  echo "EFFORT: low"
  echo "WHY: bounded mechanical/enumeration task — codex default per Ro's directive (credits)"
  exit 0
fi

echo "AGENT: general-purpose"
echo "MODEL: sonnet"
echo "EFFORT: medium"
echo "WHY: default — unclassified/ambiguous/research/multi-step task"
