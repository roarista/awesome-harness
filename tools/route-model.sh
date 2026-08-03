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
echo "$lower" | grep -qE '\b(audit|review|verify|red.?team|second opinion|architect the|decide (between|whether))\b' && is_judgment=1

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
# everything below EXCEPT the auditor hard-lock (see STEP 3).
# ---------------------------------------------------------------------------
if [[ -n "$OVERRIDE_MODEL" ]] && [[ "$is_judgment" -eq 0 ]]; then
  echo "OVERRIDE"
  echo "AGENT: general-purpose"
  echo "MODEL: $OVERRIDE_MODEL"
  echo "EFFORT: medium"
  echo "WHY: explicit override (ROUTE_MODEL/--model) requested by Ro"
  exit 0
fi

# ---------------------------------------------------------------------------
# STEP 3: HARDCODED TABLE. Order matters — first match wins. Auditor rule is
# checked FIRST and is never overridden: auditors are 12% of the fleet, 39/55
# rejects, 36 invented-API catches — the one component with positive evidence.
# ---------------------------------------------------------------------------
if [[ "$is_judgment" -eq 1 ]]; then
  [[ -n "$OVERRIDE_MODEL" ]] && echo "OVERRIDE-DENIED: audit/judgment tasks are never downgraded, ignoring ROUTE_MODEL=$OVERRIDE_MODEL"
  echo "AGENT: opus"
  echo "MODEL: opus"
  echo "EFFORT: low"
  echo "WHY: judgment/audit task — hard rule, never downgraded (positive-evidence component)"
  exit 0
fi

if echo "$lower" | grep -qE '\b(money|payment|billing|auth|authentication|credential|secret|api.?key|password|delete|data loss|irreversible|prod(uction)? database)\b'; then
  echo "AGENT: general-purpose"
  echo "MODEL: sonnet"
  echo "EFFORT: medium"
  echo "WHY: touches money/auth/security/data-loss — haiku is banned for this class"
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
  echo "AGENT: general-purpose"
  echo "MODEL: haiku"
  echo "EFFORT: low"
  echo "WHY: bounded mechanical/lookup task — cheap tier is safe here"
  exit 0
fi

echo "AGENT: general-purpose"
echo "MODEL: sonnet"
echo "EFFORT: medium"
echo "WHY: default — unclassified/ambiguous/research/multi-step task"
