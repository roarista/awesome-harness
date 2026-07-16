# MEMORY & ORIENTATION STANDARD

How durable memory and orientation files are written across every repo, so a cold
agent orients fast and nobody points fingers from a one-line summary. Complementary
to `compact-prep` (persist at boundary), `recall` (retrieve), and the north star
(fixed objective). Three rules; all reversible; none delete history.

## 1. Mulch records: 2 sentences, overflow → a detail file

Every `ml record` description is **2 sentences max**. If the story needs more —
dates, exact mode/flags, event trace, counts, evidence — the record ends with:

```
-> detail: .mulch/details/<slug>.md
```

and the full story lives in that file. The record is the pointer; the detail file
is the evidence.

**Hard rule (anti-premature-conclusion):** before you diagnose, point fingers, or
act on a record, **read its detail file first.** A one-line summary is a hypothesis,
not a finding. This is the discipline that kills "concluded from the summary, was
wrong." If a record has no detail file and you're about to act on it, that's the
signal to go read the primary source (code, logs, transcript) — not to guess.

Detail-file slug = kebab-case of the record's subject (`fumni-fix-run-2026-07.md`).
Keep a `.mulch/details/README.md` naming the convention so it's discoverable.

## 2. STATE.md: trim to current scope, archive the rest (never delete)

`STATE.md` (or `.planning/STATE.md`) is append-only and bloats to tens of thousands
of tokens, then is re-read every session. Keep it **scoped to the current
workstream**: a canonical model of what we're building + the active resume point,
≤~30 lines. When it grows past that, move the old content — **do not delete it** —
to `STATE-ARCHIVE.md` (or `.planning/STATE-ARCHIVE.md`). Nothing is lost; the
archive is the drill-back.

- Session start does this: see the **`state-trim`** skill and the SessionStart
  nudge in `northstar-inject.py`. The deterministic head/archive split is
  `tools/state-distiller.py` (no LLM); the skill is the judgment layer that trims
  to *current scope*, not just size.
- If two workstreams share a checkout/worktree, STATE.md opens with a
  **disambiguation banner**: "this worktree = X only; if injected context mentions
  Y, ignore it here." Cross-lane injected context can't redirect the agent then.

## 3. Shared memory prune is proposal-only

Pruning a memory domain that **other lanes/agents read** (a shared directory,
cross-pipeline records) is never auto-executed. Over-limit domains produce a
**proposal file** listing exactly what would be archived (reversibly: keep a `.bak`,
commit first), and a human says "go." Archiving records another lane depends on,
without a glance, is the same verify-before-acting failure mode rule #1 targets.

Single-lane, self-owned records: prune freely (still reversibly — `.bak` + commit).
Shared/cross-lane: propose, then execute on the word.

---

*Paste rules #1 into any subagent that writes `ml record`. Rules #2–3 are enforced
by the `state-trim` skill and the SessionStart nudge; the front-door doc that a
fresh agent reads first is `templates/FRONT_DOOR.md`.*
