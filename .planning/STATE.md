# Harness Hardening — State

## NOW
Enforcement audit + Codex parity + auditor synthesis all SHIPPED (e639ff5 → 70e1713, pushed).
The 2026-07-27 session that did this was deleted mid-flight; context recovered from transcript
`~/.claude/projects/-Users-rodrigoarista-Downloads-awesome-harness/1a72c93c-*.jsonl` on 07-28.

## Active Resume Point

**Last updated:** 2026-08-01 (late)
**Status:** SHIPPED + pushed `468067d`. (1) The weekly CLAUDE.md trimmer finally RUNS. Full Disk Access for `/usr/bin/python3` turned out to be UNACHIEVABLE — `/usr/bin` is hidden in the Finder picker, so Ro cannot add it. Replaced with `tools/launchd/run-claudemd-trim.sh`: launchd runs a bash shim that drives Terminal.app via `osascript` (argv-passed path, injection-safe), borrowing the grant Terminal already holds. The shim must live OUTSIDE `~/Downloads` — launchd cannot even read a script inside a TCC-protected dir (exit 126) — so the canonical copy is in the repo and an identical copy is installed at `~/.claude/tools/run-claudemd-trim.sh`, which is what the plist runs. Keep them in sync. NOTE: the plist logs now prove only DISPATCH; trimmer failures show up in the Terminal window or in `~/engineering-harness/reports/claudemd-trim/`. (2) `tools/git-sync.sh` stamps every commit with a `Terminal: <id>` trailer (`--terminal` > `$HARNESS_TERMINAL` > tty+PID > host+PID) and runs a read-only pre-commit survey classifying other remote branches AHEAD / RECENT / STALE (`GIT_BRANCH_STALE_DAYS`, default 3). AHEAD branches are ALWAYS printed regardless of the 20-line display cap. The survey never merges, deletes, or blocks.

**Prior status (superseded):** Auditor REJECT redispatch (13 ordered fixes + 1 extra) APPLIED by a fresh builder, uncommitted. Trimmer collision resolved: `tools/claudemd-trim.py` KEPT, `tools/claudemd_trim_audit.py` + `templates/…plist` DELETED. understand-gate reverted to global `warn` with repo opt-in via a `.understand-gate` marker (this repo is marked). check-all stamp moved to the END of the run and now carries `ok`. Scaffold capture is ambient off a GREEN check_all.sh (SCAFFOLD_CATEGORY/APPROACH/ITERS/AUDITOR env).
**Next concrete step:** Decide `~/.route-only` — the written verdict in `.scratch/route-only-verdict.md` is DELETE. It armed every repo (zero-byte file at `$HOME`, dated Jul 11) and today pushed three builders to write via Bash heredoc instead of Edit, which ALSO blinds the uncommitted-work notice (it only sees Write/Edit/MultiEdit rows).
**Blocked on:** nothing. FDA is no longer needed — the Terminal-borrowing shim removed that dependency entirely.

## LAST_VERIFIED (2026-07-27)
- `e639ff5` un-inverted guards (mention-matching → write-matching), main-edit-guard/builder-fence/route-only-gate
- `a083ecc` boot-heavy / turn-light injection; `/awesomeharness` re-asserts the full floor
- `d89589a` Codex parity — code-decompose/compact-prep/check-all/recall + both standards + AGENTS.md router
- `70e1713` deduped graphify-blindspot in settings.json; harness-coach fails loud; irreversible-pause blocks graded submits
- Auditor verdict in durable memory: `memory/harness-auditor-yield-verdict.md` (do NOT re-read the 10 reports)

## NEXT (open decisions, ranked)
1. Give harness-coach + harness-scout memory of their own prior reports — highest value, XS effort
2. `launchctl unload` the dead `com.ro.engineering-harness-audit` (exit 1 every Monday since 06-24)
3. Move harness-scout back to weekly (was switched to daily 07-27)
4. Trim the scout creator list
5. Stop-hook violation counter (~30 lines in session-checkpoint.py; UX win, NOT a token win — measured 2166 saved vs 4224 spent)

## CARRIED
- `understand-gate` still in `warn`, never armed to block
- Map auto-refresh unwired
- `~/awesome-harness` stale clone with unresolved `UU .now.md`
- `northstar-protect.py` mention-matching inversion sweep
- `~/.codex/skills/codex-primary-runtime/` is an empty dir — stale artifact?
- Codex asymmetry (documented, not faked): self-audit instead of independent auditor; no hooks fire on the Codex side
