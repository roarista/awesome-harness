# Harness Hardening — State

## NOW
Enforcement audit + Codex parity + auditor synthesis all SHIPPED (e639ff5 → 70e1713, pushed).
The 2026-07-27 session that did this was deleted mid-flight; context recovered from transcript
`~/.claude/projects/-Users-rodrigoarista-Downloads-awesome-harness/1a72c93c-*.jsonl` on 07-28.

## Active Resume Point

**Last updated:** 2026-08-01
**Status:** Auditor REJECT redispatch (13 ordered fixes + 1 extra) APPLIED by a fresh builder, uncommitted. Trimmer collision resolved: `tools/claudemd-trim.py` KEPT, `tools/claudemd_trim_audit.py` + `templates/…plist` DELETED. understand-gate reverted to global `warn` with repo opt-in via a `.understand-gate` marker (this repo is marked). check-all stamp moved to the END of the run and now carries `ok`. Scaffold capture is ambient off a GREEN check_all.sh (SCAFFOLD_CATEGORY/APPROACH/ITERS/AUDITOR env).
**Next concrete step:** Human review of the working tree, then commit. Separately: grant Full Disk Access to `/usr/bin/python3` (step 0 of `tools/launchd/INSTALL-claudemd-trim.md`) BEFORE loading `tools/launchd/com.ro.engineering-harness-audit.plist` — the launchd denial was that binary itself. Job stays UNLOADED until then.
**Blocked on:** This workspace cannot write or load `~/Library/LaunchAgents`; nested `codex exec` is sandbox-blocked, so live model-stage verification remains for the installed job.

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
