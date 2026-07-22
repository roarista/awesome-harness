#!/usr/bin/env bash
# Gemini-via-opencode bridge for the Claude harness (audit/council member).
# Usage: gemini-opencode.sh "your prompt"   OR   echo "prompt" | gemini-opencode.sh
# Model override: GEMINI_MODEL=google/gemini-2.5-pro gemini-opencode.sh "..."
set -euo pipefail
MODEL="${GEMINI_MODEL:-google/gemini-2.5-flash}"
AUTH="${HOME}/.local/share/opencode/auth.json"
if ! command -v opencode >/dev/null 2>&1; then echo "ERROR: opencode not installed." >&2; exit 127; fi
if [ ! -s "$AUTH" ] || ! grep -qi google "$AUTH" 2>/dev/null; then
  echo "ERROR: Gemini not authed. Run: opencode auth login -> Google -> 'OAuth with Google (Gemini CLI)'." >&2; exit 1
fi
PROMPT="${*:-$(cat)}"
[ -n "${PROMPT// }" ] || { echo "ERROR: empty prompt." >&2; exit 2; }
exec opencode run --model "$MODEL" "$PROMPT"
