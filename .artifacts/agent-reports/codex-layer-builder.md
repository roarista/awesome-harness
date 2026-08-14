# Codex compact coding layer — builder report

## Verdict

PASS for U1-U3 implementation after fixing every independent-audit blocker. The minimum native layer now enforces the selected lifecycle boundaries, installs idempotently, and documents the builder/auditor topology without adding dependencies or repeated reminder injection.

## Changes

- `codex/hooks/pre_tool_use.py`: reused the existing guard; added direct Bash/apply_patch protection for `.northstar.md`, narrow executable-form denials for forced recursive removal, hard reset, forced directory clean, and forced push, plus opt-in `check-all --fast` before `git commit` only when `.check-all.json` exists. Malformed hook input and hook execution errors fail open.
- `codex/hooks/subagent.py`: added compact `SubagentStart` context and `SubagentStop` receipt enforcement. A valid receipt has at most eight nonblank lines and names `.artifacts/agent-reports/<task>.md`; `stop_hook_active` permits the retry to stop and prevents a loop.
- `scripts/merge_codex_hooks.py`, `codex/hooks.json.template`, `tests/test_codex_install.sh`: wire `PreToolUse`, `SubagentStart`, and `SubagentStop`, preserve unrelated event entries, migrate only the known legacy command, assert double-install idempotence, and install both hook scripts.
- `install.sh`, `codex/legacy/caveman.SKILL.md`: removed an installed legacy Caveman only when byte-identical to the known shipped source (`sha256 99f288…`); the fixture asserts that historical hash and user-modified copies are preserved.
- `codex/skills/caveman/SKILL.md`: removed the redundant source skill; Ponytail/global `AGENTS.md` plus `awesomeharness` carry its useful coding discipline.
- `codex/AGENTS.md`, `codex/skills/awesomeharness/SKILL.md`, `README.md`: make builder then distinct auditor launch explicit and document the deliberately small six-skill/three-event adapter.

## Verification

- `python3 codex/hooks/pre_tool_use.py --selftest` — PASS, 30 representative payloads, including `env -u`, wrapper/Git-prefix destructive forms, directional `mv`, `Path.open`, and both apply_patch payload fields.
- `python3 codex/hooks/subagent.py --selftest` — PASS, 8 representative payloads, including existing, missing, and traversal report cases plus retry-loop prevention.
- `python3 -m py_compile codex/hooks/pre_tool_use.py codex/hooks/subagent.py scripts/merge_codex_hooks.py` — PASS.
- `bash -n install.sh install-repo.sh tests/test_codex_install.sh` — PASS.
- `tests/test_codex_install.sh` — PASS; its output also reran both hook selftests and verified preservation/idempotence.
- `python3 -m json.tool codex/hooks.json.template` and `git diff --check` — PASS after all audit fixes.
- Skill validator: `awesomeharness` and `check-all` passed before the all-skill loop stopped on pre-existing invalid YAML in unchanged `codex/skills/code-decompose/SKILL.md` (an unquoted colon in its description). No runtime smoke was run, per the stop request.

## Risks / assumptions

- Runtime dispatch of the new native subagent events remains for an optional authenticated smoke; local tests prove decision logic and current JSON shapes, not a live external model call.
- The irreversible matcher is intentionally narrow and executable-aware. It is not a general shell policy engine and does not attempt to detect every destructive wrapper or script.
- The commit gate resolves the installed check-all runner relative to the installed hook location and is deliberately inactive in repositories without `.check-all.json`.
- Existing working-tree material under `.artifacts/` was preserved; only this report was added. No commit or push was performed.
