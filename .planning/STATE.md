# awesome-harness — State
Canonical policy: .northstar.md. History: STATE-ARCHIVE.md, then STATE-ARCHIVE-2026-10-21.md (verbatim).

## Active Resume Point
**Last updated:** 2026-10-21
- Claude-conservation release (Ro 10-21: Claude ~80% weekly, Codex 34% + 2 reset credits; "use Codex more, never run out of Claude"):
  - fmr cd092b2: allowance balance ((remaining% + 100/credit) / days to reset), cheap_first respects it, conserve_claude guard, Sonnet 5.5 audits Codex builds while conserving.
  - agent-gate 08ad7eb (live): blocks Claude-family subagents while conserve_claude unless the prompt has a router ID with an anthropic pick; blocks codex/claude specs missing the 5 fields.
  - harness slim: SKILL.md 3477→2198 B, global CLAUDE.md 3015→~2.3 KB, `state-distiller.py <repo> --budget` prune check (step 0 of /awesomeharness), check-all template uses base_command.
- Root cause measured: 51% of Claude usage in 5 days = Opus subagents (claude 807 dispatches vs codex 320); main sessions 34%; jobs project 57% of all Claude usage.
**Next:** watch a week of fmr decisions + Claude/Codex weekly %; tune only with data. Codex-led orchestration terminals are Ro's call.
**Open for Ro:** grant revert of the CURRENT_STATUS lines a builder appended to free-model-router/.northstar.md; ~/.codex/config.toml interactive effort low→medium?; old ~/awesome-harness clone.
