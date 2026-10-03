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
