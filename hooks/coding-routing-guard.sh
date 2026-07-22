#!/bin/sh
# PreToolUse(Task) — fires when the orchestrator spawns a subagent.
# Reminds the orchestrator of Ro's standing routing policy. Cheap; the
# orchestrator applies the CODING half only when the spawn WRITES/EDITS code,
# and the COUNCIL half only when it's an LLM-council / second-opinion spawn.
cat <<'EOF'
ROUTING POLICY (Ro's standing default — main session ORCHESTRATES, it does not build):
- BUILDER (writes/edits code) = codex 5.5 (`codex` / `codex --edit`). Codex carries
  the coding load (billing). NEVER Claude as the builder — Claude only orchestrates.
- AUDITOR (reviews the build) = Opus 4.8 (low effort) (spawn an `opus` subagent, low effort). A non-builder always checks the builder.
- LLM COUNCIL / second opinion = 2 models: Opus 4.8 (low effort) + Codex 5.5 (Gemini-via-opencode optional third).
- Override: if Ro named a model for this task, use THAT instead (Claude or any other).
BEFORE prompting the builder:
- CODEBASE-FIRST FIRST: run the reuse ladder (evidence-backed REUSE/ADAPT/REJECT per
  candidate + STOP/PLAN/BUILD gate, verdict captured in a discovery artifact) before you
  decompose or route the build — not just `graphify query`.
- run `graphify query/explain/path` to check whether the thing already exists / where
  it lives, and pass that context down (orchestrator knows the codebase; coder does not).
- run `~/.claude/tools/graphify-blast.sh <files>` and pass the blast radius down.
- PREPEND ~/.claude/BUILDER_STANDARD.md + ponytail discipline (laziest working solution,
  reuse before writing, shortest diff, leave one runnable check) to the builder's prompt.
PROMPT SHAPE (few points — full guide: ~/awesome-harness/docs/CODING_AGENT_PROMPTING.md):
- CONTEXT: give the map not the maze — graphify output + exact file:line anchors + how
  this codebase already does X (so the coder matches existing patterns, not invents).
- CHANGE / GOAL / VERIFY: state the concrete change, the done-condition, and the runnable
  check that must pass. Forbid invented APIs — use only symbols shown in the context.
- Then Opus 4.8 (low effort) audits codex's diff before you accept it.
(Read the full doc only when scoping a non-trivial build; this checklist covers routine spawns.)
EOF
