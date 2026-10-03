# U10 — hooks (hook-impact verdicts applied) — 2026-10-03

Verdict: PASS. Inputs: `.artifacts/agent-reports/hook-impact-2026-10-03.md`, plan U10.

## Change
1. RETIRED (git mv → `hooks/retired/`, reasons + evidence in `hooks/retired/README.md`): recall-inject, manifest-guard, codemap-inject, reread-guard (3 entries). `scripts/merge_settings.py`: removed from HOOKS, added to RETIRED (strips existing installs). Docs: README hook table (18 registrations), awesomeharness SKILL.md hook list, `.gitignore` comment. Codex skill copies and install.sh had no mentions.
2. irreversible-pause: new `hooks/_rmsafe.py` (split out of `_rmscan.py`, 193→145 lines) — a var whose LAST assignment is an unquoted standalone literal disposable path counts as scratch. `M=/tmp/x; rm -rf $M` passes; `/Users`, reassigned, prefix-form (`M=/tmp/x rm -rf $M`), quoted, `$(...)`, `..`, bare `/tmp`, `~` still block. 15 cases in `tests/test_irreversible_pause.py::test_literal_scratch_var`; mutant (`_literal_safe` → True) fails the suite.
3. filesize-cap: message is now "...Prefer offset/limit, grep the symbol, or graphify over reading all N lines (advisory)." No "blocked" left in the file.
4. NEW `hooks/size-nudge.py` (PostToolUse Write|Edit|MultiEdit, never blocks, `_hookout.exit_if_product()`). SRC_EXT/SKIP_DIRS/CAP mirror `tools/git-hooks/ratchet.py`, and a test asserts they match. `tests/test_size_nudge.py`: 201 fires (exact text), 200 silent, .md/.json silent, product call silent, Read/missing silent. Mutant (`<=`→`<`) fails test_200_silent.
5. precompact-handoff untouched. Also added the missing `clear-resume` (SessionStart:clear) to `templates/settings.json` so it mirrors HOOKS.

## Live install (./install.sh)
Output: "merged 1 new entries, removed 6 retired". Diff of `~/.claude/settings.json`: removes codemap-inject (SessionStart, timeout 20), reread-guard ×3 (SessionStart, PreToolUse:Read, PostToolUse:Read), manifest-guard (SessionStart), recall-inject (UserPromptSubmit); adds PostToolUse `Write|Edit|MultiEdit` → size-nudge.py. Nothing else changed. Verified: all 4 gone, size-nudge present. A re-run merge gives 0 added / 0 removed.

## Verification
- tests/test_irreversible_pause.py 6/6 OK and tests/test_size_nudge.py 6/6 OK, against both repo and live (`HOOKS_DIR=~/.claude/hooks`) copies.
- filesize-cap --selftest PASS. `bash tools/skill-drift.sh`: 16 copies in sync.
- Live hook: `M=/tmp/b5mut; rm -rf $M` exit 0; `M=/Users/x; rm -rf $M` exit 2.
- Touched source files are all ≤200 lines (max irreversible-pause.py 182).

## Risks
- Literal-var resolution uses the LAST assignment anywhere in the command, not the position. `rm -rf $M; M=/tmp/x` would pass while `$M` holds its inherited value (the existing mktemp rule has the same shape). This is a narrow case.
- The retired .py files stay in `~/.claude/hooks/` because install.sh copies and never deletes. They are unregistered and inert.
- Not done here: the plan's recall-inject threshold idea (made moot by the DELETE), and `--force-with-lease` allowance (marked "consider" only).

## Audit fixes (u10-audit.md, PASS WITH FIXES on b369850)
1. `tests/test_product_call_isolation.py`: `> 20` became `assertCountEqual(registered, expected())`, where `expected()` is read from `merge_settings.HOOKS` (live == source of truth; currently 18). `loud >= 2` became `>= 1`, plus a positive control that cannot pass vacuously: size-nudge on a 201-line file, normal env, must print the nudge and match the guard-stripped copy. That control caught a real gap: the strip test removed `import _hookout` and size-nudge then failed silently. size-nudge now has its own `import _hookout as hookout`.
2. Ordering hole closed in `hooks/_rmsafe.py::_tmpvars`, for both mktemp and literal assignments. A var is scratch only if (a) every assignment to it in the command is safe, (b) each is a real assignment (unquoted, at command start or after `;`/newline/`export`, so `false && M=..` and `cd x && M=..` do not count), and (c) no `$VAR` reference comes before the first assignment, unless the var was already scratch in the outer scope. This is stricter than "last assignment before the rm": a later unsafe reassignment also blocks. New blocking cases: `rm -rf $M; M=/tmp/x`, `M=/tmp/x && M=$HOME; rm -rf $M`, `M=/tmp/x; rm -rf $M $HOME`, `false && M=/tmp/x; rm -rf $M`, `cd /nope && M=/tmp/x; rm -rf $M`, `rm -rf $D; D=$(mktemp -d)`, `echo 'D=$(mktemp -d)'; rm -rf $D`, `bash -c "rm -rf $T"; T=$(mktemp -d)`. `M=/tmp/x; rm -rf $M` and every earlier FALSE_BLOCKS mktemp case still pass. Mutants (drop the ref-order check; drop the real-assign check) each fail the suite.
Verification: the 3 touched test files are OK against both repo and live copies; reinstall merged 0 and removed 0; skill-drift has 16 in sync. All files are ≤200 lines (_rmsafe 98).
