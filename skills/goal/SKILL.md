---
name: goal
description: Turn a fuzzy objective into a running, self-verifying loop. Use when the user wants to "create a loop", run something "until it's done", or hand off a multi-step objective instead of hand-prompting each step ("/goal", "loop until", "keep going until tests pass", "build X autonomously"). The skill manufactures a strong SEED (heavy plan → maximal decomposition → verifiable checklist) and only then runs the loop with cheap workers + an independent verifier + mulch memory + hard stop conditions. Repo-agnostic — the same flow fits every pipeline. Do NOT use for one-shot edits or goals with no verifiable end-state (see "When NOT to loop").
---

# goal — design the loop, don't hand-prompt

The core truth from every loop-engineering source: **the seed is everything.** A loop runs hundreds
of steps on the assumptions baked into the original spec. If the spec is vague, the loop doesn't make
a bad assumption once — it makes the same one repeatedly and confidently, burning tokens at scale.
So this skill spends almost all of its care up front: heavy planning, then maximal decomposition into
a verifiable checklist. Only then does it loop. **Prompting didn't die; it moved to the seed.**

A loop is exactly five parts — all required: **trigger + goal + verifier + stop condition + memory.**
Miss any one and you have either a hand-prompt or a runaway burn.

## When NOT to loop (read first — this matters more than people think)
- **No verifiable end-state.** If you can't state a concrete check for "done," don't loop — you'll
  automate failure. Define the verifier first or do it by hand.
- **One-shot / trivial work.** A single edit doesn't need a loop's overhead.
- **Live work mid-flight.** Don't point a loop at a pipeline with an active session in the same
  working tree — you'll race it ([[concurrent-live-sessions-per-repo]]).
- **Exploration where requirements are still forming.** Loops need the end defined up front; if you're
  still discovering what you want, stay in the conversation.

## Phase 1 — SEED (premium model; the user stays in the loop)
This is 90% of the value. Do `/plan`-grade thinking and produce a durable **seed doc** on disk
(e.g. `.planning/goals/<slug>.md`, or repo-appropriate) so it survives compaction. The seed states:
- **Objective + end-state** — what is true when done, in plain language.
- **Good vs bad output** — concrete examples of a pass and a fail, so the verifier is unambiguous.
- **Constraints / what not to break.**
- **The verifier** — the independent, ideally mechanical check that proves done (test / script / hook
  / lighthouse / screenshot / judge model). Defined NOW, before any code.
- **Stop conditions** — goal met OR max iterations OR budget cap OR stall. No open-ended loops.
- **Budget cap** — a hard token/output ceiling. The romantic vision is you sleep while it works; the
  real job is making sure it stops. Set the cap here.

If any of these can't be filled in, STOP — the goal isn't loop-ready yet. Surface that to the user.

## Phase 2 — DECOMPOSE (decomposer subagent; disposable context)
Hand the seed to a **decomposer subagent** (per [[code-decompose]]) so the heavy code-reading never
touches the orchestrator's context. It returns a compact **checklist** — the goal split into the
SMALLEST independently-verifiable units, each a self-contained spec:

```
UNIT <n>: <one-line title>
  CONTEXT — what exists, file:line.
  CHANGE  — exactly what to write/modify (one correct interpretation).
  GOAL    — the outcome + why.
  VERIFY  — the concrete check that proves this unit done, defined before execution.
  DEPENDS — which units must land first.
```

**The checklist IS the definition of completion.** The loop is not done until every item is checked
off, verified, and recorded. A unit without a concrete VERIFY is not ready — split it further.

## Phase 3 — LOOP (cheap workers; one agent / one prompt / one task)
Iterate over unverified checklist items. For each (parallel where DEPENDS allows, respecting the CPU
fan-out cap and spawn-depth 2):
- Spawn ONE cheap worker subagent. Its prompt = that unit's full spec + "implement exactly this; run
  VERIFY; report the VERIFY output verbatim; do not expand scope." Fresh context each iteration so the
  model doesn't drift.
- Route the model: premium only on the seed/decompose; **free CLI / cheap models do the volume.**
- On a worker stall, **kill its process tree** (the user's machine runs hot — never leave workers loaded).

## Phase 4 — VERIFY (independent; never self-grade)
A loop that grades its own work is an efficient way to produce confident mistakes. For each unit, a
**separate** verifier confirms it: mechanical first (the unit's VERIFY command / test / hook), else a
cheap judge model that did NOT write the code. Only a passing independent verify checks the item off.
Then `ml record` the lesson from this iteration (failure mode, decision, convention) so the next
iteration is smarter — durable improvement comes from the lessons the loop accumulates, not the loop.

## Phase 5 — STOP + CLOSE
- **Stop** when: all items verified ✓ OR max iterations OR budget cap hit OR stall. Then kill any
  remaining worker process trees. Report what's done, what's not, and why it stopped.
- **Orchestration-tax guard:** keep the checklist and diffs reviewable. The danger isn't loud failure —
  it's quiet success on code nobody understands anymore. Surface progress to the user; don't let the gap
  between shipped and understood grow.
- **Compact-safe close** (from [[global_orchestration_rules]]): commit (feature branch unless the repo
  says otherwise) → `ml record` + `ml sync` → update the front-door state file → push → then it's safe
  to compact. A well-closed loop can be resumed cold by a fresh session.

## Triggers (how a loop starts)
- **Manual** — the user runs `/goal <objective>` now.
- **Scheduled** — a recurring tick (use the harness's scheduler) re-enters the loop until done.
- **Event** — PR opened, CI red, etc.
Whichever the trigger, the loop body is identical: read state → do the next unverified unit → verify →
record → check stop condition.

## What this composes (don't reinvent)
- Heavy planning → `/plan`-grade thinking in Phase 1.
- Decomposition → the decomposer-subagent pattern from [[code-decompose]].
- Memory → mulch (`ml prime` at start, `ml record` per iteration).
- Model routing, the mechanical-gate principle, and the compact-safe close → [[global_orchestration_rules]].

The compounding advantage is NOT the loop — it's the reusable seed, skills, and recorded lessons the
loop invokes every iteration. Invest in those and a cheap model loops reliably; skip them and you just
automate failure faster.
