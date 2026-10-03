# Does /awesomeharness do anything? (2026-10-02)

Read-only. Window: 2026-09-02 → 2026-10-02. Sources: Claude transcripts `~/.claude/projects/*/*.jsonl`
(main sessions; deduped by message `uuid` because resumed/forked files copy lines), Codex rollouts
`~/.codex/sessions/**/rollout-*.jsonl`, live `~/.claude` + `~/.codex` layers, repo HEAD `eab2bfb`
(branch `codex-procedure-parity`). Scripts: `/tmp/ah/{inv,dedup,ctx,effect2,show,within}.py`.

## Verdict (one line each)

- **A. Invocation:** heavily used: **171 unique invocations in 32 sessions across 7 repos**. 166 were
  typed `/awesomeharness <args>` and 5 were Skill-tool calls. It works as Ro's **post-compaction re-prime**:
  138 of 139 re-invocations come right after a compaction, with the previous turn's final summary pasted
  as args. The **reinjection guard exists and has never denied anything.** It is `PreToolUse(Skill)`, so it
  only sees model-initiated Skill-tool calls. Typed slash commands bypass it entirely. Its 2h TTL also
  ignores compaction, which is the one case where reloading is correct. The guard is harmless but dead.
- **B. Effect:** **the measurable delta is mostly selection and hooks, not the skill.** The skill's own
  unique asks are almost never followed after invocation: GOAL/DONE-WHEN 3%, REUSE 1%, `/orient` 0,
  `/code-decompose` 0, `route-model.sh` 1%, `check-all` 2%. Delegation, audits and tests are 2-4x higher
  in AH segments, but 86 of 119 of those segments are in virality-pipeline. That repo is `.route-only`
  armed (main source writes are hook-denied) and is the heavy-build repo. **Net: it re-asserts rules
  already in CLAUDE.md and hooks; it adds no unique behavior that shows up.**
- **C. Coverage:** stale and drifting. The live Claude copy lacks the router line (`install.sh` was not
  re-run after `75f49f6`). "Run one Codex builder per unit" contradicts CLAUDE.md's router-decides rule.
  The skill never mentions cross-family audits, the shared verdict rubric, reset-credit consent, the git
  pre-commit ratchet, compact-prep or `.now.md`, agent types, `general-purpose` being blocked, or
  map-refresh. Details in §C.
- **D. Codex:** it works. It is listed in 99.8% of rollouts and read in 37%, driven by
  `~/.codex/AGENTS.md:74`, and no load or router errors occurred. Ro typed `$awesomeharness` 8× (all
  2026-10-02, Consulting). After those, GOAL/DONE-WHEN appeared in 0 of 133 replies. The `l1.py` and
  `skeleton.py` paths are relative and missing from `~/.codex/tools`.

---

## A. Invocation

### Counts (unique by message uuid, 2026-09-02 → 10-02)

| repo | typed `/awesomeharness` | Skill tool | sessions |
|---|---:|---:|---:|
| virality-pipeline | 102 | 0 | 9 |
| Consulting | 33 | 3 | 8 |
| school | 14 | 0 | 5 |
| ~ (home dir) | 9 | 0 | 4 |
| intrn-v2 | 5 | 0 | 2 |
| jobs | 3 | 0 | 2 |
| awesome-harness | 2 | 0 | 2 |
| **total** | **166** | **5** (3 unique tool_use ids, copied into forked files) | **32** |

Raw (non-deduped) count is 180, which matches gate-adherence G09's "180 invocations". Heaviest sessions:
`4d5625f0-9212-44a7-8b77-f2defe648895` (virality, 39×), `d98073eb-4f60-4a0e-bfb2-ca25393e311f` (22×),
`b1947e1e-d8ff-4239-845d-bc53d2ac8df7` (21×), `ca09109e-0776-4cb3-9201-28dc066da40c` (Consulting, 13×).

### How Ro actually uses it

- 166/171 carry `<command-args>`. The args are Ro pasting the previous final summary. Examples: "SURVIVES:
  main @ 0876c1a pusheado · PLAN-POOLB-APIFY.md …", "Antes de compactar, un tropiezo mío: …".
- Of 139 same-session re-invocations, **138 follow a `compact_boundary` / compact summary**. Only 3 have
  no compaction in between, and 8 fall within 2h of the previous one.
- So `/awesomeharness` is in practice **the resume command after /compact**: contract plus "here's where
  we were". All 171 were followed by the full skill body (the "Use this contract for the rest of the
  session" marker in the next ≤5 lines). None were blocked.

### The reinjection guard (SKILL.md:94 says "the reinjection guard denies it")

- Implementation: `~/.claude/hooks/skill-reinject-guard.py` (repo copy `hooks/skill-reinject-guard.py`,
  docstring-only diff). It is registered as `PreToolUse` matcher `Skill` in `~/.claude/settings.json`.
  `BIG_SESSION_SKILLS={"awesomeharness"}` (line 28) and `TTL=2*3600` (line 29) use `_hookout.once`.
- **Does it work?** Mechanically, yes. `~/.claude/hooks/state/once/` holds exactly 3 marker files, dated
  2026-09-17 02:32–02:34 local, which are the 3 Skill-tool loads (07:32–07:34Z, Consulting sessions
  `b088e621…`, `df032683…`/`5dad6e66…`, `0256b865…`). All 3 were first loads and were allowed (`"Launching
  skill: awesomeharness"`).
- **Has it ever denied?** No. Its deny string ("already loaded in this session … context-diet guard")
  appears in zero transcripts in the window.
- **Why not:** typed slash commands are expanded by the CLI and never pass through `PreToolUse(Skill)`.
  That is 166/171 invocations.
- **Is that bad?** No. The guard would be *wrong* here anyway: 138/139 re-invocations follow compaction,
  where the earlier body has been summarized away, and its 2h TTL has no compaction awareness. Its
  docstring premise ("13.3 K tokens", "3.0×/session") is also stale. The body is now 6.2 KB (≈1.6K
  tokens), so 171 loads ≈ 270K tokens per month in total, which is negligible.
- **SKILL.md:94 is effectively false:** a re-invoked `/awesomeharness` always reloads the body.

## B. Effect on behavior

### Method

Main-session transcripts were cut into **segments**. A segment starts at a real user prompt that is
either an `/awesomeharness` invocation (AH) or the first prompt of a session or after a compaction
(CTRL). Built-in command echoes like `/compact` and `/model` are excluded. A segment ends at the next
compaction, the next AH, or end of file. Per segment, from assistant blocks and tool calls only:

- GOAL/DONE-WHEN text, REUSE/ADAPT/REJECT text
- Agent spawns whose prompt carries CONTEXT+CHANGE+VERIFY (decomposition)
- Builder spawns (non-auditor `subagent_type`) and auditor spawns (`opus`, `codex-audit`, `opus48-audit`)
- Main `Edit/Write` on source extensions; Bash write patterns
- Test commands; `check-all`; `ml|mulch record`; `.now.md`/STATE writes
- `route-model.sh|fmr route`; `/orient`, `/code-decompose`

Rates are per segment (%) or per user turn. Segments have ≥3 turns. "Ended in compaction" matches
both sides on the compact-prep ritual.

### Results — all repos, ≥3 turns, ended in compaction

| group | n | GOAL | REUSE | decomp spec | /orient | /code-decomp | route | check-all | mulch | resume card | builders/turn | audits/turn | tests/turn | main src edits/turn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| AH post-compact | 119 | 3% | 1% | 42% | 0 | 0 | 1% | 2% | 82% | 94% | 1.15 | 0.52 | 1.15 | 0.22 |
| CTRL post-compact | 16 | 0 | 0 | 25% | 0 | 0 | 0 | 6% | 38% | 100% | 0.24 | 0.09 | 0.26 | 0.16 |
| CTRL other (start) | 18 | 0 | 0 | 44% | 0 | 0 | 6% | 11% | 22% | 89% | 0.57 | 0.16 | 0.19 | 0.24 |

### Within repo (≥3 turns)

| repo | AH n / turns | CTRL n / turns | builders/turn AH vs CTRL | audits/turn | tests/turn | main src edits/turn | decomp% |
|---|---|---|---|---|---|---|---|
| virality-pipeline | 88 / 505 | 6 / 31 | 1.66 vs 0.84 | 0.86 vs 0.48 | 2.08 vs 2.10 | 0.33 vs 0.81 | 51 vs 50 |
| Consulting | 26 / 308 | 5 / 18 | 0.42 vs 1.17 | 0.08 vs 0.06 | 0 vs 0 | 0.06 vs 0.00 | 19 vs 80 |
| school | 11 / 125 | 26 / 366 | 0.35 vs 0.14 | 0.02 vs 0.02 | 0 vs 0 | 0.10 vs 0.06 | 0 vs 19 |
| ~ (home) | 8 / 73 | 23 / 174 | 0.97 vs 0.32 | 0.66 vs 0.05 | 0.22 vs 0.03 | 0.07 vs 0.09 | 12 vs 9 |

Within session (17 sessions with both kinds): AH vs CTRL is 1.01 vs 0.49 builders/turn, 0.35 vs 0.12
audits/turn, 0.72 vs 0.21 tests/turn and 0.16 vs 0.23 main src edits/turn. Decomp is 41% vs 40%,
check-all 4% vs 8%, GOAL 3% vs 0%.

### Reading it honestly: skill-caused vs already-enforced

| behavior the skill asks for | after AH | unique to the skill? | verdict |
|---|---|---|---|
| State GOAL/NOT-GOAL/DONE-WHEN/PROOF (SKILL.md:29) | 3% of segments | yes, nowhere else in CLAUDE.md or hooks | **not followed** |
| REUSE/ADAPT/REJECT, `/orient` (SKILL.md:30) | 1%, `/orient` 0× | yes; gate-adherence G13 already IGNORED | **not followed** |
| Decompose, `/code-decompose` (SKILL.md:33) | CONTEXT/CHANGE/VERIFY spec in 42% vs 40% within session; skill 0× | no: `post-agent-guard.py` injects "CONTEXT/CHANGE/GOAL/VERIFY" after every Agent return | **hook-driven, no skill delta** |
| Builder subagent, main doesn't code (SKILL.md:35) | 2× more builders | no: CLAUDE.md Delegation, `route-only-gate.py` (virality is `.route-only`), `bash-write-fence.py`, `coding-routing-guard.sh` | **confounded: virality's 86/119 segments are hook-forced** |
| Independent auditor (SKILL.md:36) | 0.52 vs 0.09 per turn | no: CLAUDE.md "Audits are always cross-family", agent definitions | **correlated, unattributable** (heavy-build sessions both audit and re-prime) |
| Tests / check-all (SKILL.md:37) | tests up; check-all 2% | check-all is also in the pre-commit gate (opt-in `.check-all.json`) | **check-all not followed** |
| Mulch + resume card (SKILL.md:38) | 82% / 94% | no: `compact-prep-gate.py` (Stop, hard) plus the compact-prep skill | **hook-driven**; the 82% vs 38% gap is session type (virality runs `ml record` in compact-prep) |
| ≤200-line files (SKILL.md:34,87) | 0 Writes >200 lines on either side | no: `tools/git-hooks/pre-commit` ratchet (10 repos) | **enforced at commit, not by the skill** |
| Sub-agent ≤8-line return, silent orchestrator (SKILL.md:42-50) | not measured | no: all 4 agent definitions, `caveman-discipline.sh`, `post-agent-guard.py`, CLAUDE.md | **duplicate** |
| route via `tools/route-model.sh` (repo SKILL.md:27) | 1% | CLAUDE.md says the same | **not followed; also absent from the live copy** |

Confounders, stated plainly:

1. **Selection.** Ro types `/awesomeharness` when resuming *heavy build work* (virality: 102 of 171).
   The CTRL post-compact segments are mostly school and light sessions (12/16).
2. **Session phase.** Within-session CTRL segments are mostly the first segment, i.e. orientation before
   building, so they would show fewer builds anyway.
3. **Same rules elsewhere.** CLAUDE.md is reloaded after compaction regardless, and 32 hooks fire
   whether or not the skill was invoked.
4. **Regex measurement.** Text signals (GOAL, REUSE) could miss paraphrases. The near-zero counts
   agree with gate-adherence G13 (3/41 roots oriented, `/orient` 0×).

**Verdict B:** the skill **duplicates CLAUDE.md and hooks** for everything that is happening. The steps
that live *only* in the skill (GOAL/DONE-WHEN/PROOF, REUSE proof, `/orient`, `/code-decompose`, router
receipt, check-all, quality gates) **show no follow-through after invocation**. Its real, observable
function is a **context re-prime after compaction**: Ro's pasted summary rides in its args. That
function would survive as a much shorter command.

## C. Coverage gap and stale statements

### Copies

- `skills/awesomeharness/SKILL.md` (repo, 94 lines) vs `~/.claude/skills/awesomeharness/SKILL.md`
  (live, 92 lines, mtime 2026-09-15): the **live copy lacks repo line 27** (the route-model.sh / fmr
  router line, added in `75f49f6` on 2026-10-01). `install.sh:79` copies with `cp -R` and was not re-run.
  **Claude sessions have never seen the router instruction.**
- `codex/skills/awesomeharness/SKILL.md` = `~/.codex/skills/awesomeharness/SKILL.md` (84 lines, synced
  2026-10-02 14:27 via `66245e6`/`a1db69b`). The Codex copy is now *ahead* of Claude's: it has
  cross-family audits, the reset-credit rule, "launch the builder and auditor the router names", and a
  no-subagent fallback.

### Mechanism inventory vs skill mention (Claude skill, repo version)

| mechanism (exists now) | where | mentioned in skill? |
|---|---|---|
| Router decides builder/auditor/model/effort (`fmr route`) | CLAUDE.md:14, `tools/route-model.sh` | repo yes (l.27); **live no**. l.35 still says "Codex builder" |
| Spend rules / Codex reset credits need Ro's yes | CLAUDE.md:15 | **no** (Codex skill yes) |
| Audits always cross-family | CLAUDE.md, agents | **no**: l.36 says "independent auditor" only |
| Shared verdict rubric | `~/.claude/agents/{opus,codex-audit,opus48-audit}.md` | **no** |
| Agent types: `claude`/`codex`; `general-purpose` blocked | CLAUDE.md, `claude-spawn-gate.py` | **no** |
| Main orchestrates; main writes only orientation files | CLAUDE.md:13 | implied by l.35 only |
| Git pre-commit 200-line ratchet + opt-in check-all (10 repos) | `tools/git-hooks/pre-commit`, `ratchet.py` | the 200-line rule yes (l.87-90); **the ratchet no** (rule stated as willpower, not "commit will be blocked") |
| `route-only` gate (hard deny of main source edits where armed) | `route-only-gate.py`, `virality-pipeline/.route-only` | **no** |
| Bash write fence | `bash-write-fence.py` | **no** |
| compact-prep Stop gate + `/compact-prep` skill | `compact-prep-gate.py` | **no**; l.38 says "update the resume card" generically |
| `.now.md` + northstar re-injection every turn | `northstar-inject.py`, `now-gate.py` | **no**: l.9 says read `STATE_CURRENT.md` else `.now.md`, but northstar already injects `.now.md` every turn |
| recall auto-inject (UserPromptSubmit) | `recall-inject.py` | **no**; l.14 says do `ml search` manually |
| harness-enforce rotating nudges (ponytail/graphify/mulch) | `harness-enforce.py` | **no** |
| codemap injected at SessionStart | `codemap-inject.py` | yes (l.8, l.15) |
| graphify gate/blindspot | `graphify-gate.py`, `graphify-blindspot.py` | graphify yes, hooks no |
| map-refresh agent (before commit after file moves) | `~/.claude/agents/map-refresh.md` | **no** |
| reinjection guard | `skill-reinject-guard.py` | yes (l.94), **but inaccurate** (see A) |
| Codex parity (AGENTS.md, Codex skill, `~/.codex/tools/route-model.sh`) | `codex/` | **no** |

### Statements that are now false or stale

| SKILL.md line | statement | status |
|---|---|---|
| 35 | "Run one Codex builder per unit." | **Contradicts CLAUDE.md:14** ("No fixed 'always Codex'… retired 2026-09-30/10-01"). The Codex copy already fixed this. (Related: `coding-routing-guard.sh` still says "NEVER Claude as the builder… auditor = glm 5.2", stale as well.) |
| 27 | `tools/route-model.sh "<task>"` | **Relative path.** It only resolves in awesome-harness. Use `~/.claude/tools/route-model.sh` (it exists). It is also **absent from the live copy**. |
| 27 | `$FMR_HOME/.venv/bin/python -m fmr outcome` | `FMR_HOME` is not guaranteed set. The Codex copy uses `${FMR_HOME:-~/Downloads/free-model-router}`. `fmr` is not on PATH. |
| 94 | "the reinjection guard denies it" | **False for 166/171 invocations** (slash bypasses `PreToolUse(Skill)`). |
| 55 | "the 26 quality gates" | The section has 5 bullets; "26" can't be checked from the text. gate-adherence counts 29 gates in all, and G24/G25 (skill-only quality gates) are PARTIAL/UNMEASURABLE. |
| 9 | "Read `STATE_CURRENT.md` when present, otherwise `.now.md`" | `.now.md` is already injected every turn by `northstar-inject.py`, so reading it again is redundant. |
| 14 | "Recall: targeted `ml search`" | `recall-inject.py` now auto-recalls every prompt. Not false, but the manual step is redundant. |
| 30, 33 | `/orient`, `/code-decompose` | The skills exist. **0 invocations** in 30 days, both here and in gate-adherence. These are dead pointers in practice. |
| 37 | "`check-all`" | 2–3% of segments. It only runs automatically via the pre-commit gate where `.check-all.json` exists. |
| 36 | "independent auditor" | Should be "cross-family auditor, shared rubric" per CLAUDE.md and the agents. |
| Codex l.17-18 | `tools/l1.py` / `tools/skeleton.py` | **Relative.** `~/.codex/tools/` has `route-model.sh` but **no `l1.py`/`skeleton.py`**, so this only resolves when cwd is awesome-harness. |
| guard docstring | "13.3 K tokens… mean 3.0×" | Stale. The body is now about 1.6K tokens. |

## D. Codex

Source: a sub-agent pass over 4,167 Codex rollouts since 2026-09-02, plus the Codex log DB
(09-23 onward). Full evidence: `.artifacts/agent-reports/awesomeharness-codex-usage.md`.

- **Loaded: yes.** awesomeharness is in the injected skills list in **4,160/4,167 rollouts (99.8%)**.
  The model reads SKILL.md itself in **1,550 rollouts (37%)**, mostly automated builder runs, because
  `~/.codex/AGENTS.md:74` says to load it "for any build, review, or pre-ship claim". No config hook
  auto-injects it; nothing in `~/.codex/config.toml` mentions it.
- **Explicit `$awesomeharness`: 8 typed by Ro**, all on 2026-10-02, in two Consulting threads
  (`01a0fa42…` 3×, `01a0fd71…` 5×). All 8 got the full body. Another 13 apparent invocations are
  sub-agent forks that copied the parent's message, and 18 are mentions inside prompts written by Claude
  or scheduled jobs.
- **Version:** those 8 loads were a 5,984-character text that matches **neither** the current 14:27 file
  nor the Aug-17 backup, i.e. an intermediate same-day edit. No rollout has loaded the current router
  version yet.
- **Errors: none from loading the skill.** In real sessions `~/.codex/tools/route-model.sh` ran 9× and
  succeeded every time. The "fmr unavailable"/timeout messages came only from deliberate failure tests on
  10-01. There were no receipt-write failures. The one "Operation not permitted" was a sandbox-blocked
  git commit, unrelated to fmr.
- **Effect after explicit invocation:** router 9×, `claude -p` 9×, sub-agents 24×, test commands 61
  (an overcount). **GOAL/DONE-WHEN stated in 0 of 133 assistant replies.** The Claude side shows the
  same pattern: delegation happens, while the skill-only steps don't.
- **Redundancy:** `~/.codex/AGENTS.md` already carries the procedure skeleton and points to the skill
  for the GOAL/DONE-WHEN and quality-gate details. Both files are byte-identical to their repo copies.
- **Stale in Codex copy:** relative `tools/l1.py` / `tools/skeleton.py` (l.17-18). Neither exists under
  `~/.codex/tools/`, so these only resolve when cwd is awesome-harness.

**Verdict D:** it works in Codex: it loads with no errors and is read far more often than in Claude,
because AGENTS.md mandates it. Typed use is new (8×, today). The skill-only steps are not followed
there either.

## Recommendations (proposal only, nothing changed)

1. **Rename the real job.** Make `/awesomeharness` (or a new `/resume`) the post-compact re-prime it
   already is: ≤25 lines naming the router command, the cross-family rule and the commit ratchet, plus
   "the pasted summary is your resume point". Drop prose the hooks already enforce.
2. **Fix the false lines:** l.35 (router decides), l.27 absolute `~/.claude/tools/route-model.sh` and the
   FMR default, l.36 (cross-family plus rubric), l.94 (delete it or say "slash re-invocations reload by
   design").
3. **Re-run `install.sh`** (or symlink skills) so the live Claude copy stops drifting from the repo.
   Add a drift check (diff repo vs `~/.claude/skills`) to `c0-preflight.sh`.
4. **Retire or repurpose `skill-reinject-guard.py`.** It cannot see slash commands, and
   re-loading after compaction is correct.
5. Steps that only the skill carries (GOAL/DONE-WHEN, REUSE line) need a **receipt checked by the
   auditor**, as gate-adherence G13 already proposed. Prose has had 171 chances and is followed 1–3% of
   the time.
