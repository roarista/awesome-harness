# Harness Hardening — State

## NOW
Enforcement audit + Codex parity + auditor synthesis all SHIPPED (e639ff5 → 70e1713, pushed).
The 2026-07-27 session that did this was deleted mid-flight; context recovered from transcript
`~/.claude/projects/-Users-rodrigoarista-Downloads-awesome-harness/1a72c93c-*.jsonl` on 07-28.

## Active Resume Point

**Last updated:** 2026-10-03
**Branch:** codex-procedure-parity (PR #5 open → main)
**Status:** Hook decisions applied + audited PASS (511502d). Context-diet plan written, awaiting Ro.
**Current workstream:** cut startup context. Plan + measurements: docs/plans/2026-10-03-context-diet.md (ours = 18.5K of a 36.6K `-p` start; interactive ~57K).
**Next concrete step:** on Ro's go — P1 config (disable vercel/power-automate, unused claude.ai connectors, ponytail→CLAUDE.md), then builder units P2-P4; re-run the gate command in the plan after each.
**Open questions for founder:** merge PR #5; P1 config yes/no; keep 22 hooks vs Aug-10's 8.
**Blocked on:** Ro. Codex main capped until Oct 6 (gpt-reserve ok; never reset credits).


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

## Active Resume Point — 2026-08-02 (late) — WAVE 3: BUILT, NOT AUDITED

**Status:** SHIPPED + pushed `a42c07f` (87 commits on origin/main). check-all OVERALL READY.

**Ro's #1 ask, delivered: `tools/retrieve.sh`** — the intent-classified retrieval front door.
8 intents: `name enumerate exists blast slice verify history diagnose`. Routing (from the
1,456-episode census in `docs/audits/2026-08-02/10-search-intent.md`):
- `enumerate` -> semgrep (the ONLY tool returning a complete set: 100%/100% vs grep 80%/92%)
- `blast` -> label->node-id resolution then `c1-blast.sh` (graphify affected UNION semgrep)
- `name` -> graphify vocab dump to COPY a literal token; never guess-grep alternations
- `exists` -> grep + a receipt: zero is printed WITH scope, file count, exact command
- `slice` / `verify` / `history` -> **grep and git KEPT** (69.8% / 77.1% / 59.4% — they win)
- `diagnose` -> honest non-answer; nothing we own wins this; stop at 3
- unknown intent -> prints the table, exit 2. Never guesses.
Invariants in-script: quoted `--include`; ONE search per call; 3-attempt circuit breaker.
Table: `tools/chains/README.md`. Folded into `~/.claude/skills/awesomeharness/SKILL.md:62`.

**`hooks/bash-write-fence.py`** (NEW, live + registered, backup
`~/.claude/settings.json.bak-bashfence-2026-08-02`) — PreToolUse:Bash, blocks MAIN writing
source via Bash. Closes the measured 61%-of-illegal-writes hole that main-edit-guard cannot
see. 12 block cases exit 2 / 9 pass cases 0 bytes. Silent by default; fails open.
`BASH_WRITE_FENCE=off|warn|enforce`. Allowed for main: `*.md`, `.planning/`, `docs/`,
`.mulch/`, memory, `/tmp`. Scope is the repo cwd only — `~/.claude/**/*.py` is still writable.

**MY OWN RE-TEST CAUGHT A GAP THE BUILDER MISSED:** `sed -i '' ...` (the macOS BSD form,
i.e. the most likely real case on this machine) passed with exit 0. GNU and `-i.bak` blocked
fine. Fixed and re-verified. Do not accept a fence's self-report without re-running it.

**`~/.claude/agents/codex.md`** (NEW) — a REAL builder. `codex exec` (codex-cli 0.145.0,
`~/.npm-global/bin/codex`) IS synchronous and writes to disk; only the `codex:codex-rescue`
PLUGIN is the forwarder. The documented default builder was MISSING, not impossible.
Dogfooded twice this wave (the sed/c1-blast fix, and the SKILL.md edit) — both PASS.

**`tools/chains/c1-blast.sh`** — dashed basenames (`northstar-inject`) produced an
unparseable semgrep rule and exit 3. Now sanitized (`-`->`_`); an invalid identifier falls
back to a LABELLED literal grep instead of a silent zero.

**Skills (survey, `14-model-router.md` + agent report):** 16 global skills, 32.2 ktok of
SKILL.md; **8 NEVER invoked across 2,997 transcripts** (check-all, clean-symbols,
codebase-first, harness-audit, notes-inbox, recall, state-trim, ui-console-debug).
`essay-writing-skill` -> ENGL2328 + GOVT2305; `clyde-pdf` -> Consulting. Originals in
`~/.claude/skills/.bak-scoping-20260802/` (moved, never deleted). Destinations are NOT
gitignored (ENGL2328/GOVT2305 are not git repos at all). `deep-research/` is an empty dead
dir. **PENDING RO'S CALL — 4 folds worth ~11 ktok at zero measured usage loss:**
harness-audit+harness-scout -> `harness-intel`; state-trim -> compact-prep;
clean-symbols -> essay-writing-skill. REGRESSION RISK: a directory-scoped skill is invisible
when cwd is elsewhere.

**Model routers — honest null:** every maintained OSS router (RouteLLM, LiteLLM Auto Router
v2, vLLM Semantic Router, LLMRouter, Morph, NotDiamond) routes **API calls at a proxy
layer**. None can set the Agent-tool `model=` at spawn time without proxying via
`ANTHROPIC_BASE_URL`, which the global CLAUDE.md forbids. A 30-line dependency-free
heuristic is proposed in `docs/audits/2026-08-02/14-model-router.md`, NOT wired up. And it
is second-order: at 51.9% of tokens the fleet's problem is launch COUNT, not launch price.

**`irreversible-pause` false-positived a THIRD time today** — on `rm -f /tmp/chains/*/.attempts-*`,
a temp sentinel cleanup. Mention/glob matching, not command matching. Now confirmed 3x. FIX IT.

**NEXT (ranked, unchanged by ROI):** 1) subagent necessity ledger 2) 8-line return contract
3) ASK-LEDGER hook 4) restate-and-hold gate 5) decide the 4 skill folds 6) fix
irreversible-pause 7) CUT the repowise tier + 280 dead MCP tools 8) LAST: repowise MCP restart.

## Active Resume Point — 2026-08-02 (night) — WAVE 4: AUDITED, REJECTED, FIXED

**Status:** SHIPPED + pushed `bf998f5` (89 commits). check-all OVERALL READY.

**THE AUDIT REJECTED WAVE 3.** An independent `opus` auditor found the shipped retrieval
router violated its own #1 spec on the exact branch built to prevent it. Both criticals were
"confident empty, exit 0" — the class we built the thing to eliminate:
1. `tools/retrieve.sh:147` — `enumerate` on a TRUE ZERO died rc=1 under `set -euo pipefail`
   (grep exits 1 on no match, pipefail propagates) BEFORE reaching the `FALLBACK:` line.
   The only case the fallback existed for was the one case it never printed.
2. `tools/chains/c1-blast.sh` invalid-identifier branch — dropped the graphify leg entirely
   and grepped `*.py` only, so `c1-blast tools/finding.sh` said "no importers found by EITHER
   method" while 7 files reference it.
Plus 9 fence bypasses and **2 fence FALSE POSITIVES that replicated `irreversible-pause`'s
mention-match bug** (blocked `git diff > x.patch` on the bare word "patch"; blocked
`grep 'cat > x.py'` by scanning inside quoted args).
**All 6 fixed by a FRESH builder and re-verified by main directly.** Lesson: the auditor is
the component with positive measured evidence, and it just earned it again.

**Fence — deliberately left open, documented:** `ed`, `ex`, `rsync`, `truncate`, `xargs`,
`find -exec`, `cp $(...)`. Precedence rule: a false positive costs more than a bypass. It is
a behavioural nudge, not a sandbox; `BASH_WRITE_FENCE=off` always wins.

**`tools/route-model.sh` (NEW, 128 lines)** — Ro's deterministic router. Hardcoded,
hand-editable case table at the top of the file. No network, no API key (proved with
`env -i`). Prints **NECESSITY first** (`LAUNCH` / `DO-NOT-LAUNCH: <reason>`) because the
fleet is 51.9% of all tokens and the problem is launch COUNT, not price. Named rule in every
verdict so the mapping is arguable. **Auditors hard-locked to `opus` — the lock beats even an
explicit `ROUTE_MODEL` override** (chosen deliberately, documented in
`docs/audits/2026-08-02/14-model-router.md`). Override for everything else: `ROUTE_MODEL=<m>`
or `--model <m>`. **NOT WIRED — nothing calls it yet. That is the top open item.**

**Skills 15 -> 10.** Motivation: **8 of 16 had ZERO invocations across 2,997 transcripts,
including `codebase-first` and `recall` — steps 1-2 of THE PROCEDURE.**
- `orient` = recall + codebase-first (14,888B -> 9,336B). Emits an `ORIENT` block ending in
  `GATE: STOP|PLAN|BUILD`, folds in `tools/retrieve.sh` at the search rung.
- `harness-intel` = harness-audit + harness-scout (27,973B -> 7,547B), Mode A / Mode B.
- `state-trim` -> `compact-prep` step 4b. `clean-symbols` -> `essay-writing-skill` (both
  course repos). `deep-research` was a BROKEN SYMLINK (target repo gone).
- Net ~33KB / ~8.7 ktok off the per-session listing. All originals in
  `~/.claude/skills/.bak-folds-20260802/` — nothing deleted.
- **Dead slash commands now:** `/recall` `/codebase-first` `/state-trim` `/harness-audit`
  `/harness-scout` `/clean-symbols`. Muscle memory will miss.

**`hooks/understand-gate.py`** — now recognizes orient's exit block (`ORIENT_RE`). It blocked
a legitimate spawn of mine mid-session, which is how we found it. Still default `warn`.
**`hooks/recall-inject.py`** — 600-char hard cap with an explicit truncation marker.

**TencentDB-Agent-Memory: REJECTED.** Self-hostable (no cloud lock-in) BUT license is
NOASSERTION on the GitHub API vs README's MIT claim, 413 open issues, created 2026-04-07.
Fixes **none** of our five measured memory failures (11.3% precision, 74.1% re-derivation,
25% stale records, 16% write compliance, `recall` skill invoked 0 times). Only stealable
idea was the injected-context budget cap — taken, one hook edit, no dependency.

**Builders both PROVEN WORKING live:** `codex exec` authenticated and returned a real diff;
`gemini -p` returned `google/gemini-2.5-pro`. Reference card:
`docs/HOW_TO_CALL_BUILDERS.md`. **codex wart:** it leaves stray `.planning/STATE.md` and
`.now.md` in the target directory.

**NEXT (ranked):** 1) wire `route-model.sh` into a spawn path 2) subagent necessity ledger
3) 8-line return contract 4) ASK-LEDGER hook 5) restate-and-hold gate 6) fix
`irreversible-pause` mention-matching (**3 false positives today alone**) 7) CUT the repowise
tier + 280 dead MCP tools 8) LAST: repowise MCP restart.

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
