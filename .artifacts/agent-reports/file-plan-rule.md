# File-plan rule: orchestrator owns structure (2026-10-03)

Ro's decision: the 200-line structure belongs to the orchestrator, not to builders. Background reading: `.artifacts/agent-reports/pocock-structure-research.md`. It recommends an orchestrator-approved module/interface plan before dispatch, and units written as a DAG with blocking edges.

## Changes
- `skills/code-decompose/SKILL.md` (10,066 -> 11,104 B): new **Phase 0b FILE PLAN** (orchestrator, mandatory, before any unit). It covers:
  - `wc -l` on every touched or created file.
  - A table with columns path | responsibility | public interface | lines now -> budget (<=200).
  - Any over-budget file gets its split as its own first unit: move-only, cut at function/module boundaries, never mid-function, and later units are `after: U1`.
  - CHANGE may name only planned files. A decomposer or builder that needs another file stops and reports back.
  - The unit template's `DEPENDS` becomes `AFTER` (blocking edges, a DAG, dispatch the frontier).
- `codex/skills/code-decompose/SKILL.md` (5,323 -> 6,276 B): the same change as Phase 0. Phase 2 now builds in AFTER (DAG) order.
- `skills/awesomeharness/SKILL.md` (2,731 B) and `codex/...` (2,738 B), both under 2,750:
  - Added the line "Orchestrator owns file structure (FILE PLAN in code-decompose). Builders never create unplanned files or split code; if a file would exceed its budget they stop and report back."
  - Cut "split to a new module first" from the non-negotiables (it contradicted the new rule), plus two small trims to stay under budget.
- Builder side, 2 lines each:
  - `agents/codex.md`, also mirrored to `~/.claude/agents/codex.md`: on a budget breach, return STATUS: FAILED.
  - `BUILDER_STANDARD.md`: this is the `claude` builder's prompt, because code-decompose Phase 3 pastes it into every worker. It installs to `~/.claude` and `~/.codex`.
- Retired `hooks/size-nudge.py`:
  - Moved it to `hooks/retired/` and added the reason to the README.
  - Removed it from `merge_settings.HOOKS`, added it to `RETIRED` and stripped it from `templates/settings.json`.
  - Deleted `tests/test_size_nudge.py` and removed the README row mention.
  - Deleted the live `~/.claude/hooks/size-nudge.py`, the same way `bash-write-fence` was handled.
  - The git pre-commit 200-line ratchet stays as the backstop.
- `tests/test_product_call_isolation.py`: the positive control now uses filesize-cap (2,001-line Read) instead of size-nudge. It only asserts that the guarded hook is loud. The stripped-equality check was dropped for this control because filesize-cap imports `_hookout` only on the guard line, so the stripped copy can't inject. Every registered hook still gets the guarded == stripped check in the loop.
- `install.sh`: fixed a pre-existing break from 67ea14e. The Codex skill loop still listed the pruned `check-all` and `recall`, so `cp` failed before BUILDER_STANDARD was copied.

## Verification
- `./install.sh`: "merged 0 new entries, removed 1 retired". `diff` of settings.json before and after shows only the size-nudge PostToolUse block removed (10 diff lines).
- `./install.sh --codex`: complete. `~/.codex` code-decompose, awesomeharness and BUILDER_STANDARD match the repo (cmp).
- `python3 tests/test_product_call_isolation.py`: 5 tests OK. This is the only test that reads merge_settings or the settings template.
- `bash tools/skill-drift.sh`: 11 copies in sync.
- `python3 tools/desc-bytes.py`: 0 over cap.

## Open
- `codex/skills/awesomeharness/SKILL.md` still says `$check-all`, a skill that 67ea14e pruned. That dangling reference predates this change and was not touched.
- `docs/plans/2026-10-03-context-diet.md` still mentions size-nudge as historical plan text. Left as is.

## Audit REJECT fixes (3 HIGH, 2026-10-03)
1. **Builder rule wording:** `BUILDER_STANDARD.md` and `agents/codex.md` now say builders "create/split exactly what the unit's FILE PLAN names, nothing unplanned". The budget rule is unchanged: stop and report instead of splitting.
2. **References to deleted skills, replaced with real tools or removed:**
   - `codex/AGENTS.md`: `check-all` -> `~/.codex/tools/check-all/check_all.sh`, and RECALL -> `ml search`.
   - `BUILDER_STANDARD.md:3`: `check-all` -> `tools/check-all/check_all.sh`.
   - `skills/code-decompose`: recall -> `ml search`; `[[orient]]` and orient -> discovery (graphify / `skeleton.py` / `rg`); scaffolds via recall -> `~/.claude/scaffolds/`.
   - `harness-intel`: removed the `notes-inbox` clause, and recall -> memgraph.
   - `MEMORY_STANDARD.md`: `recall` -> `ml search`, and `state-trim` -> `tools/state-distiller.py` plus agent judgment.
   - `templates/FRONT_DOOR.md`: `state-trim` / `/harness-audit` -> `tools/state-distiller.py` / `harness-intel` (AUDIT).
   - `docs/CODING_AGENT_PROMPTING.md`: recall -> `~/.claude/scaffolds/`.
   - `README.md:81,128`: the skill list is now 4 skills, plus the check_all.sh path.
3. **Gate path:**
   - `codex/skills/awesomeharness/SKILL.md:21` now points to `~/.codex/tools/check-all/check_all.sh`. The file was 2,789 B after 3477378 and is now trimmed to 2,747 B.
   - `codex/skills/code-decompose` now uses the `~/.codex/...` path.
   - `ls` confirms that `~/.claude/tools/check-all/check_all.sh`, `~/.codex/tools/check-all/check_all.sh` and `tools/check-all/check_all.sh` all exist, and zero `tools/check_all.sh` references remain.

**Verification after the fixes:**
- A bash grep for `/x`, `$x`, `[[x]]`, `` `x` `` and "x skill" across all 11 deleted names finds 0 invocations in skills, codex, agents, the standards, FRONT_DOOR, CODING_AGENT_PROMPTING and README. The positive control `$check-all and /orient` matches 1.
- `test_product_call_isolation.py` OK, skill-drift 11 in sync, desc-bytes 0 over cap.
- Reinstalled live, both `./install.sh` and `--codex`. The live copies of the standards, `agents/codex.md` and `codex/AGENTS.md` match the repo (cmp). The settings.json diff is still only the size-nudge block (10 lines).

## Re-audit REJECT fixes (2026-10-03)
1. **awesomeharness, both copies:** now says "Builders create or split only the files the FILE PLAN names; anything unplanned or over budget → stop and report." Sizes are 2,733 B and 2,749 B, both within the 2,750 B cap.
2. **Deleted-skill names in instruction text:**
   - `hooks/northstar-inject.py:262,275`: `state-trim` -> `python3 ~/Downloads/awesome-harness/tools/state-distiller.py <repo> --apply`.
   - `hooks/understand-gate.py:62,68`: `orient` -> "discovery (graphify/skeleton.py/rg, code-decompose)".
   - `tools/scaffold-record.py`: recall/check-all -> `ml search`/memgraph and `check_all.sh`.
   - `tools/goal/goal_judge.py`: /goal -> "goal/done loop".
   - `tools/chains/README.md:51,55`.
   - `tools/run-harness-scout.sh`: now says "harness-intel SCOUT output format".
   - `.planning/LIGHTWEIGHT-HARNESS-PLAN.md:68` and `docs/compact-prep-why.md:163`.
   - Every edit is line-neutral (`wc -l` unchanged). northstar-inject (351) and understand-gate (229) were already over 200 lines and did not grow.
   - Removed the unregistered stale live copies of the retired `codemap-inject`, `manifest-guard`, `recall-inject` and `reread-guard` from `~/.claude/hooks`. The repo copies remain in `hooks/retired/`.
3. **Remaining grep hits, none of them instruction text:**
   - `check-all` path segments in `claudemd-trim.py:41` and `codex/hooks/pre_tool_use.py:233`.
   - Gitignored `.scratch/` research notes.
   - Historical prose in `.planning/STATE.md`, `HARNESS_DIRECTION.md`, `LIGHTWEIGHT-HARNESS-PLAN.md:34` and `compact-prep-why.md:170`.
   - A runtime checkpoint JSON in `~/.claude/hooks/state`.
   - `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` have 0 hits.

**Verification:**
- `test_northstar_inject.py` OK, `test_product_call_isolation.py` OK, skill-drift 11 in sync, desc-bytes 0 over cap. Both hooks compile and the scout script passes `bash -n`.
- Reinstalled live with `./install.sh` and `--codex`. The live northstar-inject and understand-gate match the repo (cmp). The settings.json diff is still only size-nudge.
