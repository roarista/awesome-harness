---
name: code-decompose
description: The standard coding workflow for a Codex session — decompose a code change into small, independently-verifiable units BEFORE writing any of it, then execute and self-audit them one at a time. Use whenever you are about to write or change code beyond a one-line edit: features, refactors, bug fixes, new modules, pipeline stages. Activates on "build", "implement", "add this feature", "refactor", "write the code for", "change X to do Y". Skip only for truly trivial single-line edits.
---

# code-decompose (Codex edition)

> **Steps 4-6 of THE PROCEDURE** (`~/.codex/AGENTS.md`). Entry condition: `codebase-first` already returned a **BUILD** gate plus the residual gap. If it hasn't run, run it first — do not re-discover here.

The point: **the change must be fully understood before any code is written — the code that exists and the code you intend to write — and that understanding must be written down precisely enough that it could be executed without further judgment.** Decomposition is the expensive thinking step; execution is the cheap step done at volume.

**Codex has no subagent fleet.** You play decomposer, coder, and auditor yourself, sequentially. The separation of roles is preserved *in time* instead of across processes: you finish specing before you write, and you re-read the diff against the spec before declaring done. Never collapse the three into "just write it and see."

## Phase 1 — Decompose (write the specs first, no code)

Start from the `codebase-first` discovery artifact (`.scratch/discovery/<slug>.md` if present) and carry its REUSE/ADAPT/REJECT verdicts and gate forward verbatim. Then produce:

1. **Understanding** (3-6 lines): what exists now with `file:line` anchors, what we want, and the gap. Include the REUSE/ADAPT/REJECT decisions and the STOP/PLAN/BUILD gate. **If the gate is STOP or PLAN, output that with its reasoning instead of Units and hand back to Ro.**
2. **Units** — the gap split into the smallest independently-verifiable pieces. Keep splitting until each is mechanical. Each unit is self-contained:

```
UNIT <n>: <one-line title>
  CONTEXT  — what exists, with file:line. Exactly the code/state you will touch.
  REUSE    — the exact REUSE/ADAPT decisions + source anchors; no invented APIs;
             CHANGE covers only the residual gap.
  CHANGE   — exactly what to write/modify. One correct interpretation only.
  GOAL     — the outcome this unit produces and why.
  VERIFY   — the concrete check that proves this unit is done: the command, the test,
             the expected output, or the file state. Defined BEFORE execution.
  DEPENDS  — which units must land first (this is your execution order).
```

A unit without a concrete VERIFY is not ready — define the check or split further. Write NO production code in this phase.

If the change is large or has real trade-offs, surface the unit list to Ro before executing.

## Phase 2 — Build, one unit at a time, in DEPENDS order

For each unit, in order:

1. Re-read the unit spec. Hold yourself to `~/.codex/BUILDER_STANDARD.md`.
2. Write the **minimum** code that satisfies CHANGE. Nothing extra — scope creep is a spec violation, not a bonus.
3. Run that unit's VERIFY and keep the real output. Never report a VERIFY you did not run.

Do not start unit N+1 until unit N passes its own VERIFY.

## Phase 3 — Self-audit each unit against its own spec

Immediately after each unit's VERIFY, switch roles: read `git diff` for that unit **against the written spec**, not against your memory of what you meant.

- Does the diff match CHANGE exactly? Anything extra or missing?
- Does it actually achieve GOAL, including the edge cases from Phase 1?
- Bugs, broken assumptions, violated repo conventions?
- Did VERIFY genuinely pass, with real output?

Record PASS / FAIL + findings tied to spec lines. On FAIL, fix and re-verify. If the same unit fails twice, stop and re-spec it — a unit that resists twice is under-decomposed.

The audit is only worth something if you read the diff fresh. Reasoning from what you intended to write is the failure mode this phase exists to catch.

## Phase 4 — Integrate and close

1. Run the **real, deterministic verifier** for the whole change (full test suite, run the app, the repo's gate commands — whatever proves the feature works in practice, not just that it compiles). `~/.codex/skills/check-all/SKILL.md` gives you the universal battery.
2. Close per `~/.codex/skills/compact-prep/SKILL.md` (THE PROCEDURE step 7): commit → record → `.now.md` + STATE → push.

## Why this beats one big prompt

- The written spec makes "done" objective and checkable, instead of a feeling.
- Auditing against a spec you wrote *before* the code catches inconsistencies that re-reading with intent in mind cannot.
- Small units mean a failure is localized to one unit's diff, not to the whole change.
