# Codex coding-layer audit

## Final re-audit

Verdict: PASS — all previously reported HIGH findings are resolved; no HIGH/CRITICAL blocker remains.

- Historical Caveman integrity is exact: both `git show HEAD:codex/skills/caveman/SKILL.md` and `codex/legacy/caveman.SKILL.md` hash to `99f28882944222b51d5026b325fde623d62d41f7a74b8b41bda168f867852123`, and `cmp` passes. A disposable real-upgrade probe removed that exact old copy while preserving a subsequently user-modified copy; `tests/test_codex_install.sh:12-14,24-29,41-44` covers both behaviors.
- Manual guard probes returned the intended decisions: deny `mv` with `.northstar.md` as source or destination; allow source-side `cp`; deny destination-side `cp`; deny `Path('.northstar.md').open(mode='w')`; deny `env -u NAME rm -rf build`. Matching regression cases are present in `codex/hooks/pre_tool_use.py:470-541`.
- Receipt enforcement still requires an existing confined regular report, rejects traversal, and a manual leaf-symlink probe returned `block`; `stop_hook_active` prevents continuation loops.
- Verification passed: `pre_tool_use.py --selftest` (30 cases), `subagent.py --selftest` (8), `tests/test_codex_install.sh`, historical hash/cmp, disposable upgrade/preservation probe, and `git diff --check`.
- Remaining non-blocking proof gap: the authenticated runtime smoke still exercises PreToolUse only; SubagentStart/SubagentStop wire compatibility is supported by installed Codex 0.147.0 schemas and direct hook selftests, not an end-to-end spawned-agent smoke.

## Re-audit after builder fixes

Verdict: FAIL — two HIGH blockers remain; the report-path MEDIUM and most original command cases are fixed.

1. **HIGH — exact-known Caveman migration still does not match the actual installed legacy file.** `install.sh:38-39` removes only when `codex/legacy/caveman.SKILL.md` compares byte-for-byte, which is the correct preservation strategy, but the newly added legacy fixture begins with the literal `+---` and has an extra trailing blank line. It differs from `HEAD:codex/skills/caveman/SKILL.md` (`sha256 b36f…` versus actual `99f2…`). The installer therefore preserves the real old skill. `tests/test_codex_install.sh:12-13` seeds the malformed fixture and gives a false pass. Replace the fixture with the exact deleted source and assert its hash/equality in the test.

2. **HIGH — north-star mutation coverage still allows a standard destructive move and common interpreter writes.** `codex/hooks/pre_tool_use.py:181-185` treats `mv` like `cp` and checks only the final destination, so `mv .northstar.md /tmp/saved` is allowed even though it removes the protected file. The interpreter heuristic at `:186-193` also allows standard forms such as `Path('.northstar.md').open(mode='w').close()` and a heredoc assigning the path before `p.open('w')`. At minimum, deny any `mv` operand naming `.northstar.md` and add tests for `Path.open`; if interpreter support remains intentionally syntactic rather than comprehensive, narrow the README claim accordingly.

Resolved from the prior audit: `command`/`sudo` wrappers and `git -C … reset --hard` are now denied; read-only `sed -n` and source-side `cp` now pass; apply_patch's actual `tool_input.command` shape is covered; receipt paths are flat/confined, must exist as regular files, and leaf symlinks are rejected by `codex/hooks/subagent.py:38-49`. `stop_hook_active` still prevents retry loops.

Residual MEDIUM: `env -u NAME rm -rf build` still bypasses `executable_segment` because `-u` consumes a value that is not skipped (`pre_tool_use.py:112-126`). The runtime smoke still covers only PreToolUse, not live SubagentStart/SubagentStop continuation dispatch.

Reverification: PASS `pre_tool_use.py --selftest` (27), `subagent.py --selftest` (8), `tests/test_codex_install.sh`, `git diff --check`; manual probes reproduced the two HIGH cases above.

Verdict: FAIL — three HIGH blockers remain against `.scratch/discovery/compact-codex-coding-layer.md`; no CRITICAL finding.

## HIGH findings

1. The obsolete Caveman skill survives upgrades, so the claimed compact six-skill install is false for the existing users this migration targets. `install.sh:37-40` simply stops copying `caveman` but never removes the previously installed `$CODEX_HOME/skills/caveman/SKILL.md`; `tests/test_codex_install.sh:25-29` asserts absence only in a brand-new temporary home. Reproduction: seed that path, run `install.sh --codex`, and it remains discoverable. Remove only the installer-owned legacy file (ideally after exact-content/hash validation, preserving user-modified files) and add an upgrade fixture.

2. The irreversible-command guard is trivially bypassed by normal executable prefixes/global Git options. `codex/hooks/pre_tool_use.py:107-134` inspects only the first executable token and assumes the Git subcommand is `args[0]`; therefore `command rm -rf build`, `sudo rm -rf build`, and `git -C /tmp/repo reset --hard HEAD` all return allow. This undercuts the stated safety outcome in `README.md:79` and the spec's requirement to deny recognized destructive actions. Normalize common `command`/`env`/`sudo` prefixes and Git global options before matching, with explicit regression cases.

3. North-star protection blocks read-only operations while still missing common writes. `codex/hooks/pre_tool_use.py:137-147` treats every `sed` or `cp` mention of `.northstar.md` as a write, so `sed -n 1,20p .northstar.md` and `cp .northstar.md /tmp/copy` are denied; meanwhile a Python `Path('.northstar.md').write_text(...)` is allowed. This violates the narrow/precise safety boundary in the spec. Model operand direction and write flags for supported commands, and either explicitly scope/document unrecognized interpreter writes or cover them without broad text heuristics.

## MEDIUM findings / risks

- `codex/hooks/subagent.py:18-55` accepts a receipt solely because its text contains a matching string. It neither verifies the report exists nor confines the normalized path below `.artifacts/agent-reports`; `.artifacts/agent-reports/../../escape.md` and a nonexistent report both pass. The one-retry loop shape and `stop_hook_active` escape are correct, but the promised “durable report” is not enforced. Resolve the captured path against `cwd`, reject traversal, and require a regular file; test missing/traversal/existing cases.
- The runtime smoke test exercises only `PreToolUse` (`tests/test_codex_runtime_smoke.sh:39-99`). The new `SubagentStart`/`SubagentStop` dispatch and continuation behavior are covered only by direct function selftests, so current Codex wire compatibility is not end-to-end proven. Add a disposable subagent lifecycle smoke or explicitly mark this proof pending.

## Verification run

- PASS: `python3 codex/hooks/pre_tool_use.py --selftest` (19 cases).
- PASS: `python3 codex/hooks/subagent.py --selftest` (6 cases).
- PASS: `bash tests/test_codex_install.sh`.
- PASS: `bash -n install.sh install-repo.sh tests/test_codex_install.sh tests/test_codex_runtime_smoke.sh`.
- PASS: `python3 -m py_compile codex/hooks/pre_tool_use.py codex/hooks/subagent.py scripts/merge_codex_hooks.py` and `git diff --check`.
- Manual edge probes reproduced all bypasses/false positives above. No authenticated runtime smoke was run because it can consume an external model call and was not needed to establish the blockers.

## Positive observations

- Native Codex 0.147.0 strings confirm `PreToolUse`, `SubagentStart`, `SubagentStop`, `stop_hook_active`, `last_assistant_message`, the nested start `additionalContext` wire, and stop `{decision:block, reason}` are current schema concepts.
- Hook merging preserves unrelated event entries and is idempotent for the new managed commands in the clean fixture.
- The SubagentStart context is compact, and SubagentStop correctly allows the retry completion when `stop_hook_active` is true, preventing an infinite continuation loop.
