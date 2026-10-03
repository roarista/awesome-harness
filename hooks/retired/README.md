# Retired hooks (unregistered 2026-10-03)

Rule (Ro, 2026-10-03): keep a blocking hook only if agents comply after a block; delete hooks agents route around. Evidence: `docs/audits/2026-10-03/hook-circumvention.md` and `docs/audits/2026-10-02/rule-value-audit.md`. `scripts/merge_settings.py` (RETIRED) strips these from existing installs.

- `bash-write-fence.py`: 52% false blocks, and main routed around 29 of its 57 real blocks (Edit/python/kill-switch used 35x). Its message ("use codex exec") also contradicts the router.
- `claude-spawn-gate.py`: the only behavior it produced was renaming `general-purpose` to `claude` (same model, same cost). The rule already lives in CLAUDE.md.
- `compact-prep-gate.py`: of its real blocks, 28 were ignored (the rate window lets the next Stop through), and 19 fired on sessions with nothing to persist. Its "delegate" message contradicts G6.
- `graphify-gate.py`: 23 of 32 blocks were ritual unlocks (`graphify query x | head; cat file`). The advisory `graphify-blindspot.py` stays.
- `coding-routing-guard.sh` / `.py`: 1.6 KB per spawn teaching the retired "codex builds / GLM audits / never Claude" policy. Measured effect was negative.
- `harness-enforce.py`: a 4th copy of the caveman rule plus a stale GLM `[routing]` line on every prompt.
- `caveman-discipline.sh`: a SessionStart copy of CLAUDE.md G1. G1 is now the single copy.
- `post-agent-guard.py`: duplicates G2 (rule-value row 23, CUT), and its receipt text sends work to "the `codex` agent".
- `abs-path-nudge.py`: Stop-hook nudge that was unregistered in live settings but still listed in `merge_settings.py` HOOKS. Rule-value row 26 (dead unregistered hook files, CUT). It duplicates the job contract's "absolute paths in the final message" rule.
