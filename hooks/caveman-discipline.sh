#!/bin/sh
# Per-turn contract + the harness FLOOR — injected at SessionStart.
# CONTEXT DIET 2026-08-03: trimmed to ~250B (was 43 lines/1756B).
# FLOOR ADDED 2026-08-04: /awesomeharness was typed 108x in 30d across 7 repos
# purely to re-assert these lines. Auto-injecting them makes that typing optional;
# the slash command still exists for the full PROCEDURE + component map.
cat <<'EOF'
CONTRACT: (a) zero prose between tool calls, only final message; (b) ONE thorough
standalone final summary; (c) every turn ends compaction-safe: update .now.md + state.
FLOOR (no need to run /awesomeharness for these):
- Start from the .codemap above, not exploratory grep/ls/find. It is a map, not proof.
- "all the places where X" = semgrep, never grep. `command grep`, not `grep -r`.
- Main orchestrates; code writes go to the codex subagent. Audits go to codex-audit.
- Every claim about repo state carries its receipt: exact command + real output.
- Not verified until you RAN the exact command string you told the user to run,
  in the repo it will actually run in. A number from one repo is not evidence
  about another.
- Spawn prompts <=200 words: REUSE/REJECT, CONTEXT, CHANGE, GOAL, VERIFY.
- Structure questions -> `graphify query/explain` (field is `relation`, not `type`).
Full PROCEDURE, routing table and component map: run /awesomeharness.
EOF
