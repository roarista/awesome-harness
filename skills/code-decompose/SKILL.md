---
name: code-decompose
description: Ro's standard coding workflow — decompose a code change maximally before writing it, so cheap models can execute reliably. Use whenever you (or a subagent) are about to write or change code beyond a one-line edit: features, refactors, bug fixes, new modules, pipeline stages. The orchestrator stays context-light and delegates: a decomposer subagent reads the code and returns compact unit specs (CONTEXT/CHANGE/GOAL/VERIFY), cheap coder subagents execute one unit each, auditor subagents check each unit against its own spec. Activates on "build", "implement", "add this feature", "refactor", "write the code for", "change X to do Y". Skip only for truly trivial single-line edits.
---

# code-decompose

The whole point: **the change must be fully understood before any code is written — both the code that exists and the code we intend to write — and that understanding must be written down precisely enough that a cheap model can execute it without judgment.** Decomposition is the expensive thinking step; execution is the cheap step done at volume. If the spec is complete, a cheaper coder can be trusted — that trust is the entire reason this skill exists.

**Context hygiene is the core design constraint.** The main orchestrator must NOT read the whole codebase to do this — that floods its context with implementation detail it doesn't need and can't afford to carry across a long session. Instead, the heavy code-reading happens inside a **decomposer subagent** whose context is disposable. The orchestrator holds only the general goal and the compact specs that come back. Never skip to coding; a vague instruction makes the same wrong assumption repeatedly and confidently.

## Phase 0 — Frame the goal (orchestrator — stay light)

The orchestrator does NOT read the implementation. It writes a short brief and nothing more:
- The general intent in plain language (what should be true when done).
- Hard constraints / what not to break, and pointers to where the work likely lives (a dir, a module — not a full read).
- Then it spawns the decomposer subagent. That's it. The orchestrator's context stays clean.

## Phase 1 — Decompose (decomposer SUBAGENT, premium model: Opus 4.8 / Fable 5)

This runs as a **subagent**, not in the main loop, so all the code-reading context stays here and never touches the orchestrator. Its prompt is the Phase-0 brief. It returns ONLY the distilled output below — not the raw code it read.

The decomposer produces:
1. **Understanding** (3-6 lines max): what exists now (with `file:line` anchors), what we want, and the gap. Compact — this is a summary, not a transcript of everything it read.
2. **Units** — the gap split into the **smallest independently-verifiable pieces**. Keep splitting until each is mechanical to execute. Each unit is a self-contained spec, because the coder will have NO prior context:

```
UNIT <n>: <one-line title>
  CONTEXT  — what exists, with file:line. Exactly the code/state the coder will touch.
  CHANGE   — exactly what to write/modify. Precise enough that there is one correct interpretation.
  GOAL     — the outcome this unit produces and why (so the coder resolves ambiguity correctly).
  VERIFY   — the concrete check that proves this unit is done: the command to run, the test,
             the expected output, or the file state to inspect. Defined BEFORE execution.
  DEPENDS  — which other units must land first (for ordering).
```

A unit without a concrete VERIFY is not ready — the decomposer must define the check or split further. The decomposer writes NO production code; it only specs.

## Phase 2 — Receive & route (orchestrator — still light)

The orchestrator gets back the compact specs (not the codebase). It sanity-checks them against the goal, surfaces the plan to Ro if the change is large or has real trade-offs, then routes each unit to a coder subagent. It carries only the specs forward — never the decomposer's raw reading.

## Phase 3 — Execute (BUILDER = Codex 5.5 — NEVER Claude)

The builder is always the `codex` CLI (gpt-5.5); Claude only orchestrates and never writes the code itself. glm 5.2 / kimi 2.7 are acceptable alternate builders if Codex is unavailable — but never a Claude subagent. Before spawning, the orchestrator runs `graphify query/explain/path` to confirm whether the unit already exists / where it lives, and passes that down (ponytail: reuse before writing).

Spawn one worker per independent unit (parallel where DEPENDS allows; sequential where it doesn't). Each worker prompt = the **BUILDER CODING STANDARD** (`~/.claude/BUILDER_STANDARD.md`) + that unit's full spec + "implement exactly this; run VERIFY; report the VERIFY output verbatim; do not expand scope." Because the spec is complete, a cheaper model is sufficient — the more decomposed the spec, the cheaper the model you can trust. Respect the global spawn depth limit (2). On a worker stall, kill its process tree.

Before spawning, the orchestrator runs `~/.claude/tools/graphify-blast.sh <files-the-unit-touches>` (or `graphify-blast.sh` from the repo to use `git diff`) to get the blast radius — impacted symbols/neighbors of what's about to change — and passes that down so the coder doesn't grep blind.

If a `scaffold-<category>.md` exists for this task-category (it surfaces via recall), pass its verified approach to the decomposer/coder as the starting decomposition — don't re-invent it.

## Phase 4 — Audit (auditor = a NON-builder model, rotate) — gets the SAME spec

Auditor rotates across sonnet 4.6 / codex 5.4 / glm 5.2 / kimi 2.7 — anything except the model that built the unit (independent eyes). Claude IS allowed as auditor (just never as builder).

For each unit (or each batch), spawn an auditor with the **same CONTEXT/CHANGE/GOAL/VERIFY spec** plus the worker's diff. The auditor checks the implementation *against its spec*, not against vibes:
- Does the change match CHANGE exactly? Anything extra (scope creep) or missing?
- Does it actually achieve GOAL, including the edge cases from Phase 1?
- Bugs, inconsistencies, broken assumptions, violated conventions.
- Did VERIFY genuinely pass, or was the result assumed? (Demand the real output.)

Auditor returns: PASS / FAIL + specific findings tied to spec lines. On FAIL, the orchestrator hands the finding back to a worker (re-spec if needed). If a unit fails audit twice, the orchestrator handles it directly — don't spin a third worker.

## Phase 5 — Integrate & close (orchestrator)

1. Run the **real, deterministic verifier** for the whole change (full test suite / real-DB suite / run the app / screenshot — whatever proves the feature works in practice, not just that it compiles).
2. `ml record` the durable lessons: any failure mode hit, any decision + rationale, any new convention. This is what makes the next change smarter.
   - **Scaffold capture (Ornith ledger).** If the change passed the real verifier, capture the winning APPROACH (not the code) for reuse next time the same category recurs:
     `echo "<the decomposition/routing that worked>" | ~/.claude/tools/scaffold-record.py <task-category> <iterations_it_took_to_pass> --auditor <the auditor model>`
     It only keeps the scaffold if it beat the prior one (fewer iterations) — promote-on-beat. Recall re-injects it next time. Run this from the orchestrator after a real PASS only — never let a builder write its own scaffold.
3. Follow the **compact-safe close** from `global_orchestration_rules.md` (commit → record → update state → push).

## Why this beats one big prompt

- The decomposer surfaces a **compact understanding** (what exists, what changes, why) to you and the orchestrator — so you grasp the change without dumping the whole codebase into the main context. Understanding is preserved; the token cost of every line is not (the orchestration tax stays low).
- The heavy code-reading lives in a disposable subagent, so the orchestrator's context stays clean across a long session.
- The verifier is defined before the code, so "done" is objective.
- The auditor grades against a written spec, not a guess, so it catches real inconsistencies.
- The expensive model thinks once (decompose); cheap models do the volume (execute). That is the token-efficiency win.

See `~/.claude/projects/-Users-rodrigoarista/memory/global_orchestration_rules.md` for model routing, the loop framework, and the mechanical-gate principle.
