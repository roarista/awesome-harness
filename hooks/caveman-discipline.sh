#!/bin/sh
# Per-turn contract — injected at SessionStart. Ro reads ONLY the final message.
# CONTEXT DIET 2026-08-03: trimmed to <=3 lines / ~250B (was 43 lines/1756B).
cat <<'EOF'
CONTRACT: (a) zero prose between tool calls, only final message; (b) ONE thorough
standalone final summary; (c) every turn ends compaction-safe: update .now.md + state.
EOF
