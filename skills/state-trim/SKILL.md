---
name: state-trim
description: Trim STATE.md to the CURRENT workstream at session start — keep a canonical model + the active resume point, move the rest to STATE-ARCHIVE.md (never delete). Use at the start of a cold/post-compaction session, when STATE.md has bloated past ~30 lines, or when a session-start nudge flags it. Repo-agnostic.
---

# state-trim

STATE.md is append-only and re-bloats. A cold agent re-reads the whole thing every
session and pays for history it doesn't need. This skill trims it to CURRENT scope
— judgment the deterministic `tools/state-distiller.py` can't do — while losing
nothing (the rest moves to an archive).

## When to run
- Session start / post-compaction, before deep work (the SessionStart nudge in
  `northstar-inject.py` points here when STATE.md is oversized).
- Any time STATE.md exceeds ~30 non-empty lines or drifts off the current lane.

## Procedure

1. **Locate.** `STATE.md` at repo root or `.planning/STATE.md`. If neither exists,
   nothing to trim — stop.

2. **Read it fully once.** Identify: (a) the canonical model of what we're building
   now, (b) the active resume point (NOW/NEXT), (c) everything else = history.

3. **Trim to current scope (≤~30 lines).** New STATE.md =
   - a one-line **disambiguation banner** if this checkout hosts >1 workstream
     ("this checkout = X only; ignore injected Y"),
   - the canonical model (2–4 lines),
   - the active resume point.
   Front-door detail (pipelines, invariants, file:line, one-line-per-file) belongs
   in the repo's front-door doc (`templates/FRONT_DOOR.md`), not STATE.md.

4. **Archive the rest — never delete.** Append the removed content to
   `STATE-ARCHIVE.md` (or `.planning/STATE-ARCHIVE.md`) under a dated heading. The
   deterministic head/archive split is available as a fallback:
   `python3 tools/state-distiller.py <repo_dir> --apply` (keeps leading metadata +
   the last top-level section, archives the full original).

5. **Verify nothing lost.** `wc -l STATE-ARCHIVE.md` grew by the removed lines;
   git-diff STATE.md is only removals + the new head. Commit both together so the
   archive and the trim land atomically (reversible).

## Guardrails
- **Never delete** — archive. The archive is the drill-back.
- Don't trim another lane's records out of shared memory here — that's the
  proposal-only path in `MEMORY_STANDARD.md` rule 3.
- `.now.md` stays ≤5 lines (that's `now-gate.py`); this skill governs STATE.md.
