# How the operator works (read before calling anything "waste")

Edit this file to describe YOUR deliberate patterns. harness-coach feeds it to
the model so intentional technique isn't misread as inefficiency. Delete the
examples that don't apply; add your own. Keep it short and high-signal.

- **Conversational vs command-driven?** If you never invoke skills/slash-commands
  by name, say so — then the coach won't propose fixes that need manual
  invocation (they'd never get used); it will prefer ambient hooks / CLAUDE.md.

- **Deliberate subagent fanout?** If you spawn subagents to read/summarize a
  project on purpose (to keep the orchestrator's context lean), say so — that's
  the fix for bloat, not bloat. Then only redundant fanout (same file re-fetched,
  unused outputs, a subagent for a trivial grep) gets flagged.

- **Compaction ritual?** If session-start re-reads of STATE/handoff files are
  intended re-grounding, note it so they aren't flagged as churn.

- **Long autonomous runs?** If high tool-call counts are normal for you, tell the
  coach to judge sessions by error rate + repeated identical failures, not raw
  call count.

- **Hardware limits?** Note them (e.g. low-CPU machine → don't recommend heavy
  local compute, VMs, or large parallel fan-out).

- **Installed orientation tools** (north-star injection, a code-map, mulch, etc.)
  — list them so reads through them are understood as intended, not waste.
