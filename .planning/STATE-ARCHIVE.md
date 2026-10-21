# Harness Hardening — State

## NOW
Forward A/B (router vs legacy pick) live from 2026-10-04; see Active Resume Point. History of older waves below.

## Active Resume Point

**Last updated:** 2026-10-20
**Branch:** awesome-harness main (strict: .harness + .check-all.json). fmr main @ da7e400 (strict; PR #3 pins merged).
**Status:** Enforced-gates release (Ro 10-20: git gates + non-blocking SubagentStart; strict only in `.harness` repos; Intrnv3 pin gpt-6.1-sol/opus-5-5):
- git pre-commit (cf3e016): ratchet everywhere; strict repos BLOCK on missing .check-all.json/runner, check-all fail, Trellis exit 2 on touched TS (baseline .artifacts/trellis/baseline.json advances on pass), source change w/o tracked+staged .now.md. Rulings: check-all timeout warns; merges exempt from Audit trailer.
- git commit-msg: strict, >audit_min_lines (staged .harness, default 20) source lines → `Audit: <report>` with VERDICT PASS / PASS WITH FIXES (fence/quote-aware).
- hooks/subagent-rules.py (e510b56, live in ~/.claude/settings.json): ≤900B rules block for codex/claude/opus/opus48-audit/codex-audit; verified live in a probe subagent.
- agents/codex-audit.md: wrapper runs VERIFY outside sandbox, persists <task>-audit.md + finding.sh record.
- fmr `.harness` pins (builder=/auditor=) via route-model.sh FMR_CWD.
- Scout 10-20 (.artifacts/agent-reports/rule-skip-scout-2026-10-20.md): spec fields skipped ~91%, orchestrator re-verify 77%, orient-before-edit 96%, cross-family audit 48%, --no-verify in 22% of virality commits.
**Next concrete step:** send `job plan` the enforced list + Intrnv3 opt-in steps; watch a week of fmr decisions.
**Open questions for founder:** PreToolUse(Agent) spec-field check (scout #1, 91% skipped) is a blocking Claude hook — only if Ro wants; templates/check-all.json lists "fast"/"full" keys check_all.sh ignores (stale template).
**Blocked on:** nothing. Codex main capped until Oct 6 (gpt-reserve ok; never reset credits).


## LAST_VERIFIED (2026-10-04)
- fmr PR #1 merged → main 57180e9; unittest OK on main
- Backlog re-checked against live state (below); July items 2/3/5-ish resolved or obsolete

## NEXT (open, ranked — re-verified 2026-10-04)
1. Stop-hook violation counter — UX only, NOT a token win (2166 saved vs 4224 spent); low priority
Done 2026-10-04 (inline, not A/B): trashed dead `~/.claude/hooks/manifest/` (only reader was retired manifest-guard.py) and empty `~/.codex/skills/codex-primary-runtime/`. Done 2026-10-04: understand-gate.py retired (repo+live+manifest line; A/B #2 legacy arm codex, opus48 PASS +2 LOW fixed). Obsolete 2026-10-04: creator-list trim — no list file exists; harness-intel SKILL.md names only the PRIMARY trio and the 09-28 run queried only those. Done 2026-10-04: scout prompt now carries its 3 newest prior report paths (A/B #1, router arm, PASS). Resolved since July: `com.ro.engineering-harness-audit` now runs `run-claudemd-trim.sh` (last ran Sep 28, empty err log); scout is weekly (Mon 10:00).

## CARRIED
- Map auto-refresh unwired
- `~/awesome-harness` stale clone, still `UU .now.md`
- `northstar-protect.py` mention-matching inversion sweep
- Codex asymmetry (documented): self-audit, no hooks on the Codex side

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

