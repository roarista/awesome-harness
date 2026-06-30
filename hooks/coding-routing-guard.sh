#!/bin/sh
# PreToolUse(Task) — fires when the orchestrator spawns a subagent.
# Reminds the orchestrator of the coding-routing + ponytail/graphify pre-check
# policy. Cheap; emits a short reminder that the orchestrator applies only when
# the spawn is a CODING task (it ignores it for research/audit spawns).
cat <<'EOF'
CODING-SPAWN POLICY (apply only if this subagent will WRITE/EDIT code):
- BUILDER = codex 5.5 (the `codex` CLI). NEVER Claude as the builder. Claude only orchestrates.
- AUDITOR = a NON-builder model, rotate: sonnet 4.6 | codex 5.4 | glm 5.2 | kimi 2.7.
- BEFORE prompting the builder: run `graphify query/explain/path` to check whether
  the thing already exists / where it lives, and pass that context down (the
  orchestrator knows the codebase; the coder does not).
- Put ponytail discipline IN the builder's prompt: laziest working solution,
  reuse before writing, shortest diff, leave a runnable check.
- PREPEND the BUILDER CODING STANDARD (~/.claude/BUILDER_STANDARD.md) to the
  builder's prompt — the correctness/boundary layer (validate input at trust
  boundaries, no swallowed errors, smallest change, leave one runnable check).
- Run `~/.claude/tools/graphify-blast.sh <files>` first; pass the blast radius down.
EOF
