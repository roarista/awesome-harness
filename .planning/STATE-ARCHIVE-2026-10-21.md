## Active Resume Point — 2026-08-02 (late night) — WAVE 5: RO WAS RIGHT

**Status:** SHIPPED + pushed `fa8fa6c` (91 commits). check-all OVERALL READY. Tree clean.

**RO'S DOUBT WAS CORRECT, just not where either of us expected.** An independent read-only
sweep verified 9/10 shipped claims on disk AND reachable from `origin/main`, `0/0`
ahead-behind. So the *code* was pushed. **But the harness's own boot document in the repo was
a full session stale and actively wrong:** `skills/awesomeharness/SKILL.md` (last touched
`d8f85e2`, Aug 1) still taught `codebase-first`, `state-trim`, `recall`, `harness-audit`,
`harness-scout` — **five skills that no longer exist** — and never mentioned `retrieve.sh`,
`route-model.sh`, `bash-write-fence`, `orient` or `harness-intel`. Only the un-backed-up
`~/.claude` copy had been updated. **Restoring from GitHub onto a fresh machine would have
installed a harness pointing at deleted skills.**
Worse: the repo had **no `agents/` dir at all**. `codex.md`, `opus.md`, `gemini.md` and all
43 hook registrations in `~/.claude/settings.json` existed ONLY on this laptop.

**FIXED — the live layer is now version-controlled:** `skills/{awesomeharness,orient,
harness-intel}`, `agents/{codex,codex-audit,opus,gemini}.md`, `templates/settings.json`.
Live `~/.claude` stays AUTHORITATIVE; each mirror carries its own re-sync command in a header
comment. `settings.json` grepped for credentials before committing — clean (only match was
the filename `token-discipline.py`).
**STANDING RULE FROM NOW ON: any edit to a live `~/.claude` skill/agent/settings must be
mirrored into the repo in the same turn, or it is not shipped.**

**CODEX-FIRST — Ro's explicit directive**, verbatim: *"no me gusta Opus... queremos usar
Codex más porque nos dan más créditos"*, plus *"si es cuántos lanzas, pero también es qué
modelo. Eso importa igual."* The global CLAUDE.md permits this ("if Ro names a model, use
that instead").
- Audits -> NEW `codex-audit` agent (Read/Grep/Glob/Bash only, `codex exec --sandbox
  read-only`). **Proven live**: it reviewed a buggy file, reported the defect as text, and
  `git status` in the probe dir stayed clean — no writes, no stray `.now.md`/`STATE.md`.
- Mechanical/enumeration -> codex (was haiku). Builds -> codex; >15 files -> gemini.
- Opus survives ONLY as an explicit second-pass escalation on irreversible-class work.
- **The old hard-lock that let the auditor rule beat an explicit override is DELETED.**
  `ROUTE_MODEL=<m>` / `--model <m>` now wins over everything. 12/12 routing tests pass.
- **OPEN RISK, do not forget:** opus-as-auditor is the ONE component with positive measured
  evidence (39/55 rejects, 36 invented-API catches). **codex-as-auditor is UNMEASURED and is
  now the default.** Settle it by running both against the same known-bad diff and comparing
  reject rate. REVERT = uncomment the row marked `restore by uncommenting` in
  `tools/route-model.sh`.

**`hooks/contract-nudge.py` (NEW)** — the subagent return contract was enforced **NOWHERE**
(zero grep hits across every hook), while 64.3% of returns exceed the line budget and ~75% of
each return is dropped on arrival. A PostToolUse hook cannot shrink a return already in the
transcript, so it fires on the **SPAWN side**: silent when the outgoing prompt already states
a contract, else ONE nudge, once/session. Fail-open, `CONTRACT_NUDGE=off`.

**CONFIRMED UNENFORCEABLE — stop trying:** "one final message, zero mid-turn chat" cannot be
hooked. There is no hook event on model text; Stop/SubagentStop fire only after the prose is
already emitted. The skill states this honestly. It is behavioural, on me, permanently.

**Fence gap still open:** `bash-write-fence` is scoped to the repo cwd, so a `.py` write
OUTSIDE the repo root passes silently.

**NEXT (ranked):** 1) measure codex-audit vs opus on a known-bad diff 2) wire
`route-model.sh` into a real spawn path (still nothing calls it) 3) subagent necessity ledger
4) ASK-LEDGER hook 5) restate-and-hold gate 6) fix `irreversible-pause` mention-matching
(3 false positives in one day) 7) CUT the repowise tier + 280 dead MCP tools 8) LAST:
repowise MCP restart.

## 2026-08-11 — secrets guarded at the permission layer

`permissions.deny` in `~/.claude/settings.json` now carries **19 rules** covering `.env` and its
named variants, `*.pem/.p12/.pfx`, `id_rsa`, `id_ed25519`, `.ssh/**`, `.aws/**`, `.gnupg/**`,
`service-account*.json`, `*credentials*.json`. Mirrored into `templates/settings.json` so
`install.sh` ships it. **No new hook** — this is rung 3 of the ponytail ladder, native platform
enforcement instead of another script to maintain, and it is the one class the 2026-08-09
simpler-harness audit said to keep: irreversible harm.

RECEIPTS (fresh headless sessions, not this one — deny rules load at session start):
`.env` BLOCKED · `.env.local` BLOCKED · `.env.example` readable · `server.pem` BLOCKED via the
Read tool AND via `wc -l` in Bash.

**Deny beats allow, always.** The first attempt denied `Read(**/.env.*)` and allow-listed
`Read(**/.env.example)`; the probe still returned BLOCKED. There is no negation syntax —
enumerate the risky variants.

ROLLBACK: `cp ~/.claude/settings.json.bak-canary-2026-08-11 ~/.claude/settings.json`

**DELEGATION FAILURE, twice in two turns:** a codex agent scoped to two doc files reverted
`templates/settings.json` "to restore pristine state", undoing a change made before it was
spawned. Its own DIFFSTAT was accurate about what it meant to touch and silent about what it
destroyed. Verify with `git diff --stat` against the files YOU changed pre-spawn.

NEXT (ranked): 1) grep/semgrep 55:1 routing gap 2) claim-check 3) decide .now.md vs STATE.md
(flagged 23x imbalance across three auditor passes) 4) measure codex-audit vs opus on a
known-bad diff.
