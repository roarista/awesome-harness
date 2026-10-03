# Apply hook decisions (2026-10-03)

Ro approved two things on 10-03: (a) keep a blocking hook only if agents comply after it blocks, and (b) "sure" to the rule-value CUT/FIX list. Evidence: `docs/audits/2026-10-03/hook-circumvention.md` and `docs/audits/2026-10-02/rule-value-audit.md`.
Backup: `$CLAUDE_JOB_DIR/tmp/settings.json.bak-2026-10-03` (= `/Users/rodrigoarista/.claude/jobs/116ee60d/tmp/`).

## Registered hooks: 32 before, 22 after

**Before (32):**
- SessionStart: codemap-inject, caveman-discipline.sh, reread-guard, manifest-guard, graphify-gate
- PreToolUse Skill: skill-reinject-guard
- PreToolUse W/E/ME: northstar-protect, graphify-blindspot, now-gate, route-only-gate
- PreToolUse Bash: northstar-protect, irreversible-pause, bash-write-fence
- PreToolUse Task|Agent: claude-spawn-gate
- PreToolUse Task: coding-routing-guard.sh
- PreToolUse Read: graphify-gate, reread-guard, filesize-cap
- PreToolUse Grep: graphify-gate
- PostToolUse: harness-usage-telemetry, session-checkpoint
- PostToolUse Task|Agent: post-agent-guard
- PostToolUse Read: graphify-blindspot, reread-guard, token-discipline
- PostToolUse Bash: graphify-gate
- UserPromptSubmit: recall-inject, northstar-inject, harness-enforce
- Stop: compact-prep-gate
- PreCompact: pre_compact_global.sh, precompact-handoff

**After (22):**
- SessionStart: codemap-inject, reread-guard, manifest-guard, **northstar-inject** (new: full star once per session; also fires after compaction)
- PreToolUse Skill: skill-reinject-guard
- PreToolUse W/E/ME: northstar-protect, graphify-blindspot, now-gate, route-only-gate
- PreToolUse Bash: northstar-protect, irreversible-pause
- PreToolUse Read: reread-guard, filesize-cap
- PostToolUse: harness-usage-telemetry, session-checkpoint
- PostToolUse Read: graphify-blindspot, reread-guard, token-discipline
- UserPromptSubmit: recall-inject, northstar-inject (NOW line only)
- PreCompact: pre_compact_global.sh, precompact-handoff

**Unregistered and moved to `hooks/retired/`** (repo and live; the README there gives the reason for each): bash-write-fence, compact-prep-gate, graphify-gate (all 4 registrations), claude-spawn-gate, coding-routing-guard.sh and .py, harness-enforce, caveman-discipline.sh, post-agent-guard. post-agent-guard was not named in the brief. It is rule-value row 23 (CUT, approved), and its receipt text sends work to "the `codex` agent". No remaining registered hook teaches "codex builds / GLM audits / never Claude". The route-only-gate message now points at the router.

## Changes
1. **irreversible-pause**: the rm detector moved to `hooks/_rmscan.py` (97 lines); the hook is now 188 lines, down from 300. It shlex-tokenizes heredoc-stripped text one line at a time, so quoted text and comments are never treated as commands.
   - Flags count only when they come directly after an `rm` in command position.
   - Disposable targets are allowed: /tmp, /private/tmp, /var/folders, strictly under `$CLAUDE_JOB_DIR`/`$TMPDIR`, mktemp vars, `.claude/worktrees/*`, and node_modules/dist/build/out/`__pycache__`/.pytest_cache. A target containing `..` is never allowed.
   - New: it recurses into `bash -c '...'`. The old code missed that, and it is the shape of the audit's huggingface circumvention.
   - All other families are unchanged.
   - The selftest moved to `tests/test_irreversible_pause.py`.
2. **route-only-gate**: returns early when `agent_id` is present, so sub-agents are never blocked. Message: "delegate … to the router's builder".
3. **northstar-inject**: SessionStart injects the star, NOW and git. UserPromptSubmit injects only NOW, at most 300 B. The drift counter and per-prompt git line are gone. 376 → 351 lines.
   - **manifest-guard**: re-blessed (36 files) and silent now.
   - **codemap-inject**: output capped at 2,000 B (awesome-harness: about 11 KB → 1,936 B), same 318 lines.
4. **Skills**:
   - code-decompose Phase 3: builder = the router's pick. Phase 4: cross-family auditor.
   - awesomeharness (Claude): the hook list now equals the 22-entry set and points to the retired README. It had no map-refresh step.
   - awesomeharness (Codex): unchanged. It lists Codex-native hooks, not the Claude settings, and has no map-refresh step.
   - check-all: `MAX_FILE_LINES` and the `max_file_lines` default go from 800 to 200 (= ratchet cap). The `.scratch` prune is kept. Both SKILL copies are updated.
5. **Installer**:
   - `scripts/merge_settings.py` HOOKS now equals the 22-entry set, plus a RETIRED list that strips old entries from existing installs. Proven: merging the pre-change backup produces exactly the live set (11 removed, 1 added).
   - `templates/settings.json` hooks block = live.
   - README hook table rewritten.
6. **Live sync**:
   - All 17 registered scripts plus `_hookout`/`_rmscan` in `~/.claude/hooks` are byte-identical to the repo. This also replaced the July-era text in skill-reinject-guard, northstar-protect, now-gate, recall-inject, route-only-gate, irreversible-pause and northstar-inject; the repo text was newer and correct in every case (grant protocol, recall 600-char cap, slot-aware now-gate).
   - `check_all.sh` and `claudemd_drift.py` were synced to `~/.claude/tools/check-all` (live lacked the `.scratch` prune and semgrep) and to `~/.codex/tools/check-all`.

## Decisions Ro may want to reverse
- **filesize-cap and now-gate are advisory, not blocking.** The repo copies had blocked (exit 2) since 07-19; the live copies were advisory. Syncing repo to live verbatim would have quietly added two new blocks that no one has measured, which goes against rule (a) and Ro's 08-16 no-blocking call. The audit also counts both as non-blocking. Only the exit path changed (it now injects advice).
- **The 08-10 diet conflict.** The README and template said the 08-10 audit cut the harness to 8 entries. `merge_settings.py` was never updated, which is very likely how the 10-02 reinstall re-registered roughly 25 hooks. This brief explicitly keeps 22, so the installer now encodes the 22-entry set. If Ro wants the 8-entry set back, that is a separate decision.
- **Codex `pre_tool_use.py` irreversible regex was not narrowed.** It is a separate system and out of scope here.

## Verification
- settings.json and template JSON valid.
- `test_product_call_isolation.py`: OK on repo and on live (`HOOKS_DIR=~/.claude/hooks`). Its mutation check moved from the retired caveman hook to northstar-inject.
- `tools/git-hooks/test_pre_commit.sh`: 29 passed, 0 failed.
- New tests:
  - `test_irreversible_pause` (4): OK on new code. On old code 3 FAIL: false blocks, exit codes, and `bash -c` danger missed.
  - `test_route_only_gate` (3): OK on new code; 2 FAIL on old.
  - `test_northstar_inject` (2): OK on new code; 1 FAIL on old.
  - All three also pass on the live copy.
- irreversible-pause mutation check: with `_safe_target` neutered to always-true, `rm -rf ~/x` is allowed, so the danger assertion would fail.
- Every registered hook was run once with realistic stdin: 22 of 22 exit 0 with no traceback. The PreCompact pair ran in a throwaway git repo.
- Selftests (now-gate, filesize-cap, manifest-guard, codemap-inject) pass. `tools/skill-drift.sh`: 16 copies in sync.
- During the work, the old fence and the old irreversible-pause each blocked me once on false positives (a .py write, then rm text inside a heredoc and a comment). I complied: the fence after it was unregistered, and the heredoc case via a script file once the new hook was synced.

## Follow-up: audit REJECT of cf687c4 (HIGH), fixed
- `_rmscan.py`:
  - Command position now resets after separators and after then/do/else/elif/if/while/until/`{`/`!`/time.
  - Prefix commands (sudo, doas, env, timeout, nohup, nice, stdbuf, xargs, exec, command, caffeinate, ionice) are skipped together with their options, option arguments, VAR=x and durations.
  - `sh`/`bash`/`zsh` strings are recursed into for any flag group containing `c`, and so is `eval`.
  - Safe targets are now checked after `os.path.realpath`, so a /tmp symlink to ~ is not safe.
- `irreversible-pause.py`: force-push now catches flag groups containing f (`-fu`, `-uf`) and `+refspec`.
- `abs-path-nudge`: retired properly (moved to `hooks/retired/`, README line, added to RETIRED in `merge_settings.py`). It had been unregistered live already.
- Tests: 19 bypasses and the symlink case are must-block. Run against cf687c4, 2 tests FAIL (19 bypasses missed; symlink case not blocked). After the fix, all 5 pass on repo and live. All false-block cases still pass.
- Live == repo for the 17 registered scripts plus `_rmscan.py`. manifest-guard re-blessed (35 files).

## Follow-up 2: re-audit REJECT of ec11506, fixed
- New `hooks/_heredoc.py` (81 lines) gives heredocs exact shell semantics.
  - An opener is an unquoted `<<`/`<<-` (never `<<<`, never inside quotes or a comment; quote state carries across lines).
  - The body ends at the FIRST line exactly equal to the delimiter (`<<-` strips leading tabs only). What follows that line is scanned.
  - A heredoc fed to a shell or ssh is scanned as code.
  - An unquoted-delimiter body has its `$(...)`/backticks scanned.
- `_rmscan.py` (151 lines) uses the robust rule: any `rm` token anywhere with r+f blocks unless every target is safe. Redirections are not counted as targets.
  - Scanned recursively: `$(...)`/backtick bodies, `sh -c` flag groups, eval, here-strings fed to a shell, and arguments piped into a shell.
  - A mktemp var is trusted only if its LAST assignment (including `for`/`read`) is mktemp.
- Force-push regex adds `--mirror`, `--delete`, `-d` groups, `--prune`, and `:ref`.
- Tests: 20 new must-block cases, including the exact EOF-inside-data repro. On ec11506, 20 danger cases are missed and 2 tests FAIL; all pass now on repo and live. False-block cases were added (redirects, `HEAD:main`, `<<-` tab end, quoted-delimiter body, `cat <<<`).
- **Backup note:** `$CLAUDE_JOB_DIR/tmp` was wiped during the re-audit, likely by the auditor's accidental real `rm` run. The 32-entry pre-change settings were rebuilt from the before list to `~/.claude/settings.json.bak-2026-10-03-pre-apply`.

## Follow-up 3: re-audit REJECT of 88aab6b, fixed
- `_rmscan.py` (161 lines): the CONTENTS of every quoted string are now scanned as code (covers `ssh host "..."`, `python3 -c`, `node -e`). The exception is a command that is plain data: echo/printf/grep/egrep/fgrep/rg/ag/sed, or `git commit`.
- A shell anywhere in a pipeline consumes every upstream stage (`echo .. | tee | sh`).
- Tests: 5 new must-block cases (all missed on 88aab6b) and 8 must-pass cases (`git commit -m "remove rm -rf ~/x hack"`, `echo "rm -rf ~"`, `grep 'rm -rf' file`, rg, sed, `echo | tee`, `ssh ls`, `python -c print`). All pass on repo and live.
- Stray `/tmp/x.sh` from the audit incident removed.

## Follow-up 4: re-audit REJECT of 74b4a60, fixed
- Quoted text is DATA again (no data-command allowlist). Rescanned as code only: $(...)/backtick bodies (heredoc bodies stripped unless fed to a shell; single-quoted spans masked as literal), shell -c, ssh remote command, eval, trap, here-strings and pipelines into a shell, system/exec/run/execSync-style call literals in python/node/perl/ruby -c/-e code.
- `_heredoc.openers` keeps a quote/substitution context stack, so a heredoc opened inside a double-quoted command substitution (the commit-message form) is real and its body is stripped. Shell-fed is decided by the heredoc owning command only, not by any word on the line.
- mktemp-trusted vars flow into every recursive rescan.
- Tests: 13 must-pass + 9 must-block added. On 74b4a60: 14 false blocks + 1 miss; now 0/0 (51 safe / 90 danger) on repo and live.
- This commit used the git commit -m "$(cat <<EOF ...)" form and passed the live hook.
