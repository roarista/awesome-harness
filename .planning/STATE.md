# Harness Hardening — State

## NOW
Enforcement audit + Codex parity + auditor synthesis all SHIPPED (e639ff5 → 70e1713, pushed).
The 2026-07-27 session that did this was deleted mid-flight; context recovered from transcript
`~/.claude/projects/-Users-rodrigoarista-Downloads-awesome-harness/1a72c93c-*.jsonl` on 07-28.

## Active Resume Point

**Last updated:** 2026-08-13 — LIGHTWEIGHT HARNESS PLAN
**Status:** PLAN ONLY. Evidence and delivery units are in
`.planning/LIGHTWEIGHT-HARNESS-PLAN.md`; no harness or target-repo behavior changed.
**Resume:** Run Unit 0's seven-day measurement contract, then implement and A/B the thin
`/awesomeharness` unit before touching target-repo continuity files.

**THE REFRAME — I aimed at the wrong target and the data corrected me.**
Hooks are 14.70% of billed main-session INPUT but **~5.5% of DOLLARS**, because 93.1% of
input is `cache_read` at 0.1x. Meanwhile **the delegation fleet is 1,798M tokens vs 1,664M
for its parents = 51.9% of ALL tokens, ~55% of cost-weighted spend**, entirely outside the
context window audit 04 measured. ~41 subagents/session at ~1.42M each. **One avoided
subagent launch is worth ~22% of the entire hook-diet prize.** Cutting prompt text is
cosmetic next to cutting a launch.

**THE KILLER NULL:** evidenced-completion rate is **31% with the harness vs 33% without** —
identical. The thing the harness exists to fix, it demonstrably did not move. Ro's thesis is
**confirmed on cost** (+23 ktok standing floor before task difficulty can act; +42% tok/turn
with the skill) and **NOT established on efficiency** (cheaper per durable edit 3.33 vs
3.97M; interrupts LOWER at 1.6 vs 2.7 per 100 turns; first productive action at turn 1 in
29/29). Only component with positive evidence: **auditor subagents** (12% of fleet, 39/55
rejects, 36 invented-API catches).

**BUILT AND MEASURED (13-context-diet):** feasibility answer to "can hooks be taken out of
context" is **partly — but the useful part fully**. Hook text cannot be invisible-but-present;
anything the model reads becomes a permanent attachment re-sent every call. BUT **a hook that
exits 0 printing nothing costs literally zero** (proved: `PostToolUse:Agent`, 186 fires, 0
bytes). So the fix is silence-by-default, not hiding.
- `_hookout.once()` — fail-open session-scoped sentinel, the idempotency primitive
- `coding-routing-guard` (was **17,160 tok/session**) — silent unless a spawn ACTUALLY writes
  code AND is misrouted; its 421-token policy was already verbatim in `~/.claude/CLAUDE.md`,
  so 192 of its fires were pure duplication
- `post-agent-guard` (3,140) — once/session, was 186x
- `caveman-discipline` — condensed 5-line form on compact/resume (1756 -> 459 bytes)
- NEW `skill-reinject-guard.py` — 85 tokens instead of re-loading the 13,300-token skill body
**Measured 30.2 -> 8.5 ktok/session (-71.8%).** Backups: `hooks/.bak-contextdiet/`,
`~/.claude/settings.json.bak-contextdiet-20260802`. Smoke-tested live: a non-code spawn now
produces **0 bytes**. Untouchable: `skill_listing` (14.5K) and compact summaries (15.6K) are
Claude Code internals — the only levers are fewer skills and compacting less (all 54 triggers
were `manual`).

**TWO CORRECTIONS TO MY OWN EARLIER REPORTING — tell Ro, do not bury:**
1. I said "zero blocking-hook fires, guards are unproven." **Corpus artifact.**
   `irreversible-pause` fired and blocked a real destructive delete twice during this wave.
2. `irreversible-pause` is **mention-matching, not command-matching** — it blocked a plain
   `cat >>` to a notes file merely for containing the phrase. Same inversion bug already
   listed under CARRIED. Real false-positive cost.

**SEARCH — Ro's actual question, finally answered (10-search-intent).** Not mechanics:
PURPOSE and SUCCESS, over a census of **1,456 episodes**.
| intent | n | success | wasted |
| name-recovery-hedge | 303 (20.8%) | 46.2% | 1.31M |
| enumerate-occurrences | 234 (16.1%) | **41.9%** | 1.20M |
| check-existence | 196 (13.5%) | 51.5% | 0.79M |
| history/prior-art | 229 | 59.4% | 0.41M |
| targeted-slice-read | 162 | **69.8%** | 0.19M |
| verify-landed | 35 | **77.1%** | - |
The expensive-AND-failing three are **half of all episodes and ~46% of all search spend
(3.3M tokens wasted)**. `blast-radius` is asked only **2.3%** of the time — that is an
AGENDA bug, not a tool bug: we don't ask what breaks.
**Two real bugs found:** 137 searches (3.1%) died because zsh glob-expanded an unquoted
`--include=*.py` so grep never ran — **49 were never retried**; and 634 (14.5%) had a
silently empty sub-section inside an `echo ===` compound bundle. 33.6% of episodes flail
(3+ searches), 142 hit 8+.
**Routing table:** name uncertain -> dump the graph label/id vocab and copy the literal token,
never guess-grep alternations · "all places" -> `semgrep -e` with a COUNT, never `| head` ·
what-breaks -> `graphify affected "<node_id>" --depth 1` (a LABEL instead of the id returns
`No affected nodes found` = silent false negative, verified live) · prove absence -> a zero
PLUS the printed scope and file count · slice-read / verify-landed / git history -> keep grep,
it wins · diagnose-failure -> nothing we have, stop at 3.
**Three invariants:** quote `--include`; ONE search per Bash call; 3-search circuit breaker.

**THE PROCEDURE DOES NOT RUN (12) — Ro's suspicion was right.** n=22 substantive coding
sessions, 615 source writes, 301 commits.
- **`codex:codex-rescue`: 84 transcripts, ZERO source writes, ever.** It is a forwarder. Of
  102 forwards: 15% substantive, 17% hard-failed, **48% (49) returned a receipt that never
  resolved** -> **27 units evaporated**, 19 silently redone by a Claude agent, 3 committed
  anyway. No fabricated "done" claims found, which is the one mercy.
- **"Main NEVER writes feature code": violated in 73% of sessions.** Main wrote 90/763
  (11.8%), and **55 of those 90 (61%) via Bash**, invisible to `main-edit-guard`.
- check-all: **32%** of sessions, **18%** of commits (biggest gap). `git-sync.sh`: **9%** of
  commits. push 41%. **32% of sessions end with uncommitted source**, 6 never committed.
- What DOES work: recall 91%, graphify 95%, delegate-at-all 95%, auditor 77%, orient 77%,
  decompose 68%. repowise step: **5% -> CUT**.
- **Decay measured:** second half of a session = +66% source writes with **-50% audits and
  -66% decompose spawns**. Post-compaction sessions score HIGHEST (9,9,8) — fresh context
  restores compliance.

**NEXT SESSION = BUILD, NOT AUDIT. Ranked by the ROI data, not by loudness:**
1. **Subagent necessity ledger** — the fleet is 51.9% of spend and ~75% of returns are
   dropped. Biggest single lever by far.
2. **8-line subagent return contract** (verdict/headline/evidence/next/risks/finding-id).
3. **ASK LEDGER hook** — Stop hook blocks the final summary until every enumerated ask is
   DONE or DEFERRED (kills the 36 "declared done, sub-ask untouched").
4. **RESTATE-AND-HOLD gate** — GOAL/NOT-GOAL/DONE_WHEN/PROOF before the first write.
5. **Search routing rules + the 3 invariants** into the skill.
6. **CUT:** `codex:codex-rescue` as default builder · the repowise tier in CLAUDE.md · the
   unenforceable "main NEVER writes" claim · 280 never-invoked MCP tools (~3.09%) ·
   `manifest-guard` -> `systemMessage` · `phantom-edit-guard`.
7. **FIX:** default-on check-all gate in Vividlist/virality/intrn; `irreversible-pause`
   mention-matching inversion.
8. **LAST:** restart the repowise MCP (kills this session — Ro's explicit ordering).

**Prior status (superseded):**

**Last updated:** 2026-08-02 (late) — SELF-AUDIT WAVE
**Status:** SHIPPED + pushed `6191ef1`. Nine forensic audits over the REAL corpus
(2,033 sessions + 852 subagent transcripts, ~826 MB, 103,750 records, 0 parse errors).
Reports in `docs/audits/2026-08-02/`. **Nothing has been BUILT off these findings yet** —
that is the next session's whole job.

**THE DIAGNOSIS (one line):** the harness optimizes the ROUTE (which model, which skill,
which hook) because the route is the only checkable thing in a prompt. Ro names a
mechanism in 55% of asks but a finish condition in only **6.0%**. So agents declare
victory on a route they followed instead of an outcome they reached. **DONE and PROOF
are what's missing.**

**THE THREE INTERVENTIONS THE DATA SUPPORTS (build these, in order):**
1. **ASK LEDGER** — a hook enumerates every ask in a Ro message; the Stop hook blocks the
   final summary until each is DONE or explicitly DEFERRED. Targets the largest drift
   category: 36 cases of "declared done with a named sub-ask untouched".
2. **RESTATE-AND-HOLD gate** — GOAL / NOT-GOAL / DONE_WHEN / PROOF / TARGET FILES stated
   before the first write. `NOT-GOAL` is load-bearing (Ro: "if I don't mention something
   it's because I probably just think it's good"). Targets scope-widened (24) +
   solved-nearby-problem (24) + over-delivered (9).
3. **8-line subagent return contract** (verdict / headline / evidence / next / risks /
   `finding.sh` id). Median return today is 3,448 chars and 64.3% blow the 15-line
   contract; the cap cuts median parent input ~85% and p90 ~96%.

**MEASURED FACTS — do not re-derive, cite `docs/audits/2026-08-02/`:**
- MEMORY (09): recall precision **11.3%** (88.7% noise, ~177k wasted tokens); **74.1%
  re-derivation** even when relevant; **25%** of memory records name files that no longer
  exist; end-of-session write compliance **16%**; top re-derived fact repeated 1,584 sessions.
- BUILDERS (08): all-5-field specs **5/72 (6.9%)**; REUSE missing **64/72 (88.9%)**;
  completion claimed with no captured evidence **48/72 (66.7%)**; audits REJECT **70.9%**
  of the actionable subset; only 23.6% of prompts carry a `file:line` anchor; 36
  invented-API findings.
- HOOKS (07): **ZERO recorded exit-2 fires** in the attributable corpus → workaround rate
  is UNMEASURABLE and no guard has demonstrated effect. caveman compliance **35.7%**
  (144/403). Verdict: CUT phantom-edit-guard, caveman-discipline, coding-routing-guard
  (186 fires), post-agent-guard (180), manifest-guard. DEMOTE builder-fence,
  understand-gate, northstar-inject. **PROMOTE: none** — promotion would be evidence-free.
- DUMPS (03): n=852; median return 3,448 chars / 24 lines, p90 12,162 / 98 lines, max
  48,703; **64.3% exceed the 15-line contract**; parent reuses ~24% of vocabulary (UPPER
  BOUND) and **2.49% verbatim** → ~75% dropped on arrival; median session absorbs
  **31,315 tok**, p90 **119,299**, max **203,611**.
- CONTEXT (04): hooks cost **61.4 ktok/session** (15.7% raw); **~48.4 ktok/session is
  byte-identical re-injected text** (awesomeharness skill body 3.0x, compact summary 2.5x,
  skill_listing 5.5x; worst session 186 K); mean amplification **390x**; turn-1 floor
  **57.5 ktok** median; 50% of a 200K window by turn 3, 80% by turn 6-7; 20/22 sessions
  compacted, all `trigger: manual`. `PreToolUse:Agent` fires 48x/session with an identical
  421-token policy. Cuts ranked: per-project MCP/tool-schema pruning (~25-40 ktok),
  idempotent skill/listing injection (~48 ktok), trim PreToolUse:Agent + rate-limit
  hook_additional_context to once/turn (~35-45 ktok).
- SEARCH (01): **4,918 Bash `rg`/`grep`/`find` vs ONE native Grep, zero Glob, zero Task**;
  Read 2,138 calls of which **72.31% are FULL-file**; 380 extra re-reads = **784,736
  wasted tokens**; orientation tax median **9** tool calls before the first Edit (p90 27);
  229 search-flailing episodes.
- ADOPTION (06): graphify **7.3%** of available sessions with **82.1% immediate fallback**
  to grep/Read; semgrep 0.3%; recall 2 calls total; finding.sh 1 session; repowise CLI
  **49% failure rate** and never left awesome-harness; **280 of 304 exposed MCP tools
  never invoked** (~28-56 ktok standing cost).
- WRONG ANSWERS (02): 580 lexical hits → **17 validated incidents**. Top mode: **claimed
  ABSENT when PRESENT (5/17)**. Real cases: "cero retrieval bajo `src/originated/`" (false);
  "el S2 no está en el camino" (it was renamed `src/s2` → `src/strategy_folded`); 9 failing
  tests dismissed as "las 9 de siempre" that were never diagnosed (rotten dates); 18 of 19
  blocking rules pointed at fields that exist in NO model. Honest limit: this counts only
  DOCUMENTED self-corrections, so it is a lower bound.
- GOALS (05): 501 genuine Ro messages, 2026-07-11 → 08-02. Repeated expectations (repetition
  = harness failure rate): verify-before-claiming **149**, delegate-to-subagents **102**,
  scope fences **75**, evidence-not-inference **74**, cost discipline **65**. Drift: declared
  done w/ named sub-ask untouched **36**, solved a nearby problem **24**, scope widened **24**,
  process abandoned **14**, over-delivered **9**. **~60 redirects = 1 in 8 Ro messages exists
  only to stop a confidently-wrong trajectory.**

**PROCESS FINDING:** the `codex:codex-rescue` subagent is a FORWARDER — it hands off to a
background Codex runtime and returns immediately, so it never reports results back. Two of
the nine audits also died under it (read-only sandbox blocked their temp files) and were
re-run as `general-purpose`. Do not use codex-rescue when you need the result in-session.

**Prior status (superseded):**

**Last updated:** 2026-08-02
**Status:** SHIPPED + pushed `a7d082d`. Ro redirected: do NOT cut tools, COMBINE them, and
first check whether the bad scores were OUR misuse. Three agents ran; the redirect was right.

**(1) graphify — misuse confirmed on all three counts.** Source read at
`~/.local/share/uv/tools/graphifyy/lib/python3.13/site-packages/graphify/` (v0.8.47).
`query` scored 0/3 because we never ran graphify's OWN mandatory "Step 0 — constrained
query expansion" (`skills/claude/references/query.md`): dump the graph's label vocab, pick
<=12 tokens FROM it, query with THAT string, not the user's question. There is no stopword
list (`serve.py:91` keeps any token >2 chars) so NL questions seed on junk like "How".
Also `serve.py:390` silently rewrites the traversal graph if the question contains
"calls"/"imports"/"returns", and the default `--budget 2000` truncates the EDGE lines away
— we were reading a node list and calling it an answer. Correct form: 2.5/3.
`uses` is 100% precise against its OWN definition (`extract.py:8942`: for each
`from M import Name` in file F, edge from every class in F to Name) = a co-import /
blast-radius signal, NEVER a call graph. 30/30 vs its definition, 18/30 vs ours: the "27%"
was our measurement error. Dangling edges are DELIBERATE (`extract.py:3835`,
`build.py:179/315` call them "expected"); the real defect is bare `import _hookout`
targeting id `hookout` while the file node is `hooks_hookout` (`extract.py:1282`).
`graphify update .` fixed it here — dangling now 0/1, and the phantom node disappeared with it.

**(2) Real-task benchmark (26 questions mined from 1011 + 537 commits, 14 hand-ground-truthed
BEFORE any tool ran).** Genres won: **Grep 8, graphify 3, semgrep 2, repowise 0-for-13.**
Grep is still the default and beats the fancy tools on prior-art / config-owner / abandoned-
approach questions because those span code AND prose. semgrep wins write-site enumeration
decisively: +79pp recall in Python (grep misses multi-line `conn.execute(\n "INSERT…`),
+25pp precision in TS (grep's `.update(` collides with `createHash().update()`).
graphify is symbol-level depth-1 ONLY — file-name queries return the wrong node silently,
depth-2 precision ~30%.

**(3) Chains + rules shipped and tested** (`tools/chains/`, `tools/semgrep/`): 7 chains,
12 rules in 5 files, all `--validate` clean, all run on awesome-harness AND virality-pipeline.
Every chain caps stdout at 14 lines via `_lib.sh finish()`; full dump -> `/tmp/chains/<repo>/`,
`CHAIN_RECORD=1` files it via `tools/finding.sh`. **No chain needs the MCP** (`repowise
risk`/`dead-code` are CLI), so all 5 repos work despite the pin.
Verified independently by main: `c3-enumerate` -> 72 sites + honest unparsed-file warning;
`c1-blast "_hookout"` -> 11/11 importers via the semgrep fallback leg after graphify's node
vanished — the UNION design is what saved that answer.

**FOUR SILENT-FAILURE CLASSES found (all exit 0) — these are the real product of the day:**
- repowise `Total pages = 0` in the other 4 repos -> "No results found" == true negative.
- repowise MCP pinned to awesome-harness -> answers about the WRONG repo, silently.
- **semgrep `--validate` says VALID for a rule that returns 0 when 116 exist** (`...` inside
  a string literal is not an ellipsis). `--validate` is NECESSARY BUT NOT SUFFICIENT; the
  only real guard is a positive control asserting non-zero. Also: semgrep silently SKIPS
  files it cannot parse (hid 2 deny sites from a "complete" 13) — chains now warn.
- graphify `explain "<file>.ts"` returned a throwaway node with 1 importer instead of the
  real one with 12; `affected "BrandResearch"` -> "No unique node match" with no candidates.
- Bonus bug worth a sweep: `set -o pipefail` + grep's exit-1-on-no-match killed a chain at
  the exact moment it found something. Audit harness scripts for `x=$(… | grep …)`.

**Semgrep first real findings:** forclosurehomes 591 (164 of 235 HTTP calls with no
`timeout=`), Vividlist 463 (48 hand-rolled retry loops + 14 named helpers), virality-pipeline
172 (reproduced the original burn: 13 retry sites + `tenacity` declared/never-imported),
awesome-harness 72, intrn 50 (29 hardcoded `/Users/...` paths).

**Wiki verdict: 1 of 5 keeps one, 0 of 5 get one generated.** awesome-harness YES (60 pages
already exist, sunk cost, MCP-reachable). The other four NO — every chain ran on
virality-pipeline today at 0 wiki pages. Vividlist is the best FUTURE candidate, after its
463 findings are harvested.

**NOT DONE (next session):** fold survivors into the `/awesomeharness` skill (asked 3x now);
cut `graphify query` from its 12 doc refs OR replace them with the Step-0 form; wire
`c2-prior-art` -> codebase-first, `c1-blast` -> code-decompose, `c7-preship` -> check-all;
`graphify update` on the other 4 repos; **LAST: restart the repowise MCP** (Ro's explicit
order — everything else first, since the restart kills this session).
NOTE `.claude/CLAUDE.md` is GITIGNORED — the scope warning added there is local-only and
does NOT propagate to the other repos; each needs its own.

**Prior status (superseded):**

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
