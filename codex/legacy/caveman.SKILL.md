---
name: caveman
description: Use for awesome-harness Codex sessions, or whenever the user asks for Caveman discipline, terse progress, delegated code changes, or evidence-led implementation.
---

# Caveman discipline

Keep the main session small: orchestrate, inspect evidence, and report the outcome. This is a behavioral workflow, not a claim of mechanical role enforcement.

For a bounded multi-file or non-trivial change:

1. Write an atomic contract: `CONTEXT`, `CHANGE`, `GOAL`, `VERIFY`.
2. Delegate that one contract to a builder. Do not recursively fan out.
3. Give a distinct, read-only auditor the same contract. It independently runs the verification and returns PASS or FAIL with evidence.
4. Keep the actual verification command and its exit code (R2) in the handoff/final evidence.

Do not delegate a genuinely trivial one-line edit; make the smallest safe change and leave a runnable check when the logic is non-trivial.

When `graphify-out/graph.json` exists, use `graphify query` or `graphify explain` before codebase exploration; after code changes, run `graphify update .`. Run the repository's factory/check-all gate before and after a change whenever it provides one.

At intermediate milestones, emit only `caveman` when the surface requires progress messages; otherwise emit nothing. The final response is self-contained.

## Boundary

Native hooks cannot safely distinguish a main orchestrator from a delegated builder, nor cover every hosted tool, prose, or delegation action. Direct patches, model chat, and delegation therefore cannot be safely role-gated mechanically. Treat the workflow and its recorded verification as the enforcement boundary; use Git hooks as a commit-time backstop.
