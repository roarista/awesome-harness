# Rule value audit: which harness rules earn their keep (2026-10-02)

Ro's ask: "the 200-lines-per-file rule seems good, but maybe some other rules aren't. Look at all of them and say which are good and which aren't."

This audit is read-only and nothing else was edited. It reuses `docs/audits/2026-10-01/gate-adherence.md` (**GA**), `docs/audits/2026-10-01/opus48-cross-audit.md` (**XA**), `docs/audits/2026-09-30/harness-baseline.md` (**B**) and the memory dir. New measurements come from these sources:
- **T30**: the 9,366 Claude transcript files modified in the last 30 days. Hook-result lines only; assistant text that merely mentions a hook is excluded.
- Live probes of each injecting hook with its real event.
- Per-attachment byte sizes from real transcripts: `919382d5` (virality root), `116ee60d` (awesome-harness root), `344c6fdf` (a virality product `claude -p` call).
- `~/.claude/settings.json` diffed against `settings.json.bak.1790958359` (2026-09-28).

Scripts are in `/tmp/rva/` (ephemeral).

Classes:
- **KEEP**: clear value.
- **FIX**: good intent, but broken, mis-scoped or contradicting another rule. The fix is named.
- **CUT**: cost is higher than value, or the rule is a duplicate.
- **UNKNOWN**: needs a named measurement.

## 0. The headline nobody asked for: 24 of 32 hooks were re-wired today

- On 2026-09-28 `settings.json` registered **8** hooks.
- At **2026-10-02 14:06** it registers **32**. The 24 added include harness-enforce, caveman-discipline, compact-prep-gate, graphify-gate, coding-routing-guard.sh, northstar-inject, recall-inject, reread-guard and manifest-guard.
- `~/.claude/BUILDER_STANDARD.md` and `~/.claude/tools/graphify-blast.sh` reappeared at 11:25 the same day.
- **This reverses Ro's standing call of 2026-08-16** (memory `rules-in-claudemd-not-hooks`): "the hooks were deliberately unwired… they ate context and blocked agents… agents found workarounds." The only recorded exception is the git pre-commit ratchet plus check-all (2026-10-01).
- I found no Ro message on 10-02 asking for the re-wire. **Provenance is unknown. Confirm with Ro before trusting any hook below.**
- Most of the friction measured below dates from the last ~30 hours:
  - compact-prep-gate first fired 2026-10-02 19:06Z.
  - graphify-gate was silent from 08-01 until 10-02.
  - The restored set carries July-era policy text, such as GLM 5.2 as auditor.

## 1. Ranked table (worst value first, then KEEPs)

Cost terms:
- **B/prompt** means bytes injected on each user prompt. They are cumulative, because the transcript is append-only and re-sent on every later call. Cache-read makes this about 0.1x in dollars (memory `subagent-fleet-is-the-real-cost`), but it still uses window space.
- **Blocks** means a denied tool call or turn, counted in T30.

| # | ID | Rule / mechanism | Cost (measured) | Value (measured) | Class | Fix / action |
|---|---|---|---|---|---|---|
| 1 | H14 | `coding-routing-guard.sh` PreToolUse:Task | **1,590 B on every Agent spawn** (12,720 B / 8 spawns in session 116ee60d). The silent `.py` rewrite exists, but settings registers the old `.sh` | Negative. It teaches a retired policy (see C2) | **CUT** | Unregister the `.sh`. If anything, register the silent `.py` |
| 2 | H22 | `harness-enforce.py` UserPromptSubmit | 433–536 B/prompt. **2,604 fires in T30, 2,526 of them inside production `claude -p` calls** (§3) | The `[routing]` line contradicts the router (C2). Ponytail, graphify and mulch lines: no adherence lift measured (GA G08 graphify 11/411 before first patch; ponytail is followed without it, G14) | **CUT** | It is the fourth copy of the caveman rule. If a re-assertion is wanted, keep only ponytail and graphify, and never in `-p` sessions |
| 3 | H23 | `compact-prep-gate.py` Stop (exit 2) | **92 main-session blocks in ~30 h across 23 sessions; 20 in one session (b1947e1e), 16 in another.** Each block costs one extra model turn. Its message orders "delegate … to a cheap sub-agent", which adds a fleet launch to every stop. In background jobs every stop is ≥60 s apart, so it fires on every stop | GA G02: per-turn persistence was IGNORED (.now/STATE edits in 11/152 roots) while compact-prep at real compaction ran 100×. The gate enforces the half that was never valued | **FIX → effectively CUT** | Move to PreCompact plus session end only, or exempt `$CLAUDE_JOB_DIR` jobs and subagents. Change the message to "edit .now.md directly". G-rule "direct main edits are fine for orientation files" already allows it. Drop "every turn" from G4 |
| 4 | H12 | `bash-write-fence.py` PreToolUse:Bash | **882 blocks / 522 transcripts; 639 (72%) hit SUB-agents (the builders).** 44 commands set `BASH_WRITE_FENCE=off`. 126 targets were `.json` data files (manifest.json, r.json, 04-definicion.json). Next action after a block: Edit/Write 292, Bash retry 436, often a python-heredoc rewrite of the same write | Main writes via Bash fell from 61% (procedure-does-not-run, 08-02), but main-edit-guard (its pair) is NOT registered, so main can still write source with Edit. The fence blocks the wrong population | **FIX** | Main-only (`agent_id` absent). Exempt `.json/.yaml` data, `$CLAUDE_JOB_DIR`, `.artifacts/`. Change the message: "use codex exec" is wrong for Claude builders (C2) |
| 5 | H11 | `irreversible-pause.py` PreToolUse:Bash | **288 blocks** (114 main / 176 sub). ≥97 are `rm -rf` of tmp/build/`$CLAUDE_JOB_DIR` dirs; many "other" are false positives on heredoc bodies or `cat > note.md`. 16 force-push, 42 sql/other | Real catches are plausible for the 16 force-pushes. Prevented incidents: **unmeasured** | **FIX** | Allowlist `/tmp`, `/var/folders`, `$CLAUDE_JOB_DIR`, `node_modules`, `dist`, `build`, `__pycache__`. Do not regex-scan heredoc bodies. Keep force-push and DROP/TRUNCATE |
| 6 | H13 | `claude-spawn-gate.py` blocks `general-purpose` / `Explore` | **153 blocks.** Next spawn: `general-purpose` again 55×, `codex` 31×, **`claude` 12×** | Its cost rationale (pure-Claude sidechains) is defeated by renaming the agent to `claude`, which is equally pure-Claude and is what G10 tells you to use. Its message says "use `codex` for build/analysis", which contradicts G7 | **FIX** | Either delete it, since the rule is in CLAUDE.md G10, or change the message to "use `claude` (or the router's pick)". It also blocks Explore, which the system offers for read-only fan-out |
| 7 | H2, G1–G3 | Caveman "zero intermediate chat" (CLAUDE.md + SessionStart 1,844 B + harness-enforce + post-agent-guard) | Written **4×** (G1, H2, H22, H18), about 2.7 KB per session plus 343–445 B per agent return. **Injected into 2,526 product `claude -p` calls** | GA G01: 22.7% of root text blocks are intermediate, mostly ≤60-char status lines. Benefit: Ro reads less noise (unmeasured). Contradicts the background-job contract (C1) | **FIX** | Keep ONE copy (G1) and exempt background jobs and `-p` sessions. Delete the H2 SessionStart copy and the H22 line. "Thorough final message" (G3) stays |
| 8 | H20 | `recall-inject.py` UserPromptSubmit | ~400–525 B/prompt (5,250 B over 10 prompts in 116ee60d). It injected a `clyde-laptop` memory into a virality comment-analysis product call | Zero measured hits that changed a decision. The index was "3 stale rows" (memory push-retrieval…, 08-16) | **UNKNOWN** | Measure precision: sample 30 injections and judge whether each was relevant. Never run it in `-p` sessions |
| 9 | H4 | `manifest-guard.py` SessionStart | **2,098 B (systemMessage plus alert) in EVERY session right now**, including product calls, because the baseline was not re-blessed after today's re-wire | A real guard against neutered hooks. Value: 0 detections so far. Currently crying wolf | **FIX** | Re-bless the baseline, or the alert trains everyone to ignore it |
| 10 | H21 | `northstar-inject.py` UserPromptSubmit | 1,400–2,359 B **per prompt** in virality/Vividlist/intrn (all have `.northstar.md`); 2,145 B measured in 919382d5 | Anti-drift: unmeasured. The NOW line is cheap, but the north-star paragraph repeats verbatim every prompt | **FIX** | Inject the north star once per session (SessionStart and post-compact). Per prompt, inject only NOW (≤300 B) |
| 11 | H5 | `graphify-gate.py` deny Read/Grep until a graphify call | 26 blocks (24 main), nearly all 10-02 | GA G08: graphify before the first patch is 11/411. The gate turns that into a ritual `graphify query` to unlock. Memory `graphify-earns-it` says graphify is useful, but forced first calls are not proven useful | **UNKNOWN** | Measure: after a gate block, is the graphify output referenced in the next 5 calls? If <30%, CUT (advisory H8 blindspot already exists) |
| 12 | H1 | `codemap-inject.py` SessionStart | virality 1,474 B (L0). **awesome-harness ~11 KB gets replaced by a 2,269 B `<persisted-output>` pointer**, so the agent there sees a file path, not the map | Memory "codemap 445:1" in awesome-harness; "names ZERO files" in big repos | **FIX** | Cap at <2 KB so it is not persisted, or skip in the harness repo |
| 13 | K6 | Ponytail plugin SessionStart banner | **4,038 B every session, twice after compaction**, including product `-p` calls | GA G14: FOLLOWED (573 `ponytail:` comments, 8/10 diffs LEAN) without the skill ever being invoked | **KEEP** (the content) / FIX the scope | Exclude `-p` sessions. Consider a 1 KB version; the 4 KB body is mostly examples |
| 14 | L1 | GOAL / NOT-GOAL / DONE-WHEN / PROOF block | Skill prose | GA G12: 1.6% adherence (34/2,109) | **CUT** | Merge into the spec's GOAL/VERIFY (GA rec 5) |
| 15 | K8 / L7 | map-refresh agent before commits that add/move files | Skill step | GA G22: 1 spawn vs 1,381 commits | **CUT** | Fold `graphify update` and codemap regen into check-all |
| 16 | L0, G7 | "Route every launch through route-model.sh / fmr" | Prose plus a script | Router works (probe: "fix a typo" → DO-NOT-LAUNCH). Usage: **34 recorded decisions** vs ~834 builder spawns/30d (GA G07: 7 calls). **The installed `~/.claude/skills/awesomeharness/SKILL.md` lacks the route line** that the repo copy has | **FIX** | Re-install the skill (repo ↔ live drift). Put the router call inside the agent definitions or the spawn path (GA rec 2) |
| 17 | L4 | "Run one **Codex** builder per unit" | Prose | Contradicts G7 and Ro 09-22 ("Opus 5.5 para construir"). GA G04: 44% codex | **FIX** | Change to "one builder (router's pick) per unit". The concurrency half is KEEP (G17 FOLLOWED 0/628) |
| 18 | L5 | "re-audit until no HIGH/CRITICAL remains" | Prose | XA: that exact bar let opus48 PASS 3 units the shared rubric REJECTs. 2 money/data-loss defects (units 01, 05) still sat in virality HEAD on 10-01 | **FIX** | Replace with "until VERDICT ≠ REJECT under the shared rubric (MEDIUM on money/secrets/data-loss = REJECT)" |
| 19 | K1, K2, K3 | /orient, /code-decompose, /check-all as skills | 9.7 KB / 9.9 KB / 5.5 KB on demand | GA: invoked **0×** in Claude in 30d. Spec format 18%. Check-all before commit 0/28 Claude trees | **FIX** (move, don't delete) | Content into agent definitions and router templates (GA rec 2). check-all is now in the pre-commit path where opted in (X2) |
| 20 | N2 vs K3 | check-all file-size **warns at 800** | — | Contradicts N2's cap of 200 (C7). The ratchet (X1) now covers the 200-line cap at commit time | **FIX** | Change the check-all file-size check to call `ratchet.py`, or delete it |
| 21 | H24/H25 | PreCompact `pre_compact_global.sh` + `precompact-handoff.py` (haiku call) | One haiku call per compaction, only in repos with `.northstar.md` | Unmeasured. Overlaps compact-prep (K4) | **UNKNOWN** | Measure whether a post-compact session reads the handoff file |
| 22 | H15/H19/H17/H8/H9 | filesize-cap, token-discipline, session-checkpoint, graphify-blindspot, now-gate | Silent unless a threshold trips (memory `low-firing-count-is-not-dead`) | Small and targeted. reread-guard (H3) blocked once; its pathology is 65 re-reads at 4.2 M tokens | **KEEP** | Leave them. They cost 0 B when quiet |
| 23 | H18 | `post-agent-guard.py` PostToolUse:Agent | **343 + 445 B per agent return** (two attachments) | Duplicates G2 and D2. Its "next code spawn: CONTEXT(graphify…)" text duplicates H14 | **CUT** | — |
| 24 | H10 | route-only-gate | 17 blocks in 11 sessions | Armed per repo. Docstring names "codex 5.5 builder / glm 5.2 auditor" | **KEEP** with a message fix | Fix the message (C2) |
| 25 | G4, K4 | "Every turn ends compaction-safe" + compact-prep skill (14.8 KB) | Rule written 4× (G4, H2, H22, H23) | Skill at real compaction: ran 100× (GA G02), so valued. Every-turn version: ignored | **FIX** | Keep the skill. Delete "every turn" from G4 and H2 (GA rec 5) |
| 26 | — | Unregistered hook files: main-edit-guard, builder-fence, check-all-commit-gate, git-destructive-guard, agent-worktree-guard, spawn-necessity, contract-nudge, advertised-command-guard, phantom-edit-guard, understand-gate, abs-path-nudge, speak, kill-stuck-sessions | 0 runtime cost; maintenance and confusion cost (the ask itself listed 3 of them as live) | — | **CUT the dead ones / UNKNOWN for one** | **git-destructive-guard is the exception.** taskset prompts quote "a builder already destroyed work today with `git checkout`" (virality 09-01). N3 has no mechanical guard; builders are told in prose every time. It was never wired; whether to wire it is Ro's call (08-16 rule). Measure: count `git checkout --/restore/reset --hard` by builders in T30 |
| 27 | X1 | git pre-commit **200-line ratchet** | 14 blocks in T30; 6 `SKIP_RATCHET=1`; 17 `--no-verify` tool calls (not all ratchet). Installed in virality, intrn-v2, Vividlist (Layer 4) | GA G16: crossings fell **24.6 → 8.9 per 100 source commits** under prose alone. Born-under-rule repos (intrn-v2 0/93, jobs 0/210 over 200). Ratchet closes the "touched a big file and grew it" hole (43% before) | **KEEP** | Install in jobs, Consulting, free-model-router (no shim today). Audit the 6 SKIP_RATCHETs |
| 28 | X2 | pre-commit check-all `--fast` (opt-in `.check-all.json`) | Opted in: virality, intrn, intrn-v2. **Vividlist's own Layer 3 `factory:check` blocks EVERY commit on a 48-day-stale STATE_CURRENT.md**; the rollout agent bypassed it with a stub `npm` on PATH (hook-rollout.md §3) | GA G21: before it, check-all ran before 0/28 Claude commit trees. 397 check-all runs logged in `state/check-all.jsonl` | **KEEP** (X2) / **FIX** (Vividlist) | Refresh Vividlist STATE_CURRENT.md, or make factory:check's freshness check warn-only. A gate that always fails trains bypasses |
| 29 | X4 | Shared verdict rubric in opus / opus48-audit / codex-audit defs | ~1 KB per auditor def | XA: separated 3 REJECT + 2 PASS-WITH-FIXES from opus48's old PASSes; 2 HIGHs reproduced | **KEEP** | Fix opus48-audit.md:7 "verdict PASS/FIX", which contradicts its own :16 PASS / PASS WITH FIXES / REJECT |
| 30 | D1, X5 | Spawn return contract (report path + ≤8 lines) in agent defs | Prose in defs | GA G23: report path 76%, ≤8 lines 61% (was 0 agent defs before) | **KEEP** | — |
| 31 | G9, QG4 | Cross-family audit, different-model review | Auditor launches | Memory: auditors are the one fleet component with positive evidence (39/55 rejects, 36 invented-API catches). B: 152 rejects / 522 verdicts | **KEEP** | Router pairs them |
| 32 | N2 | 200-line cap (prose, skill) | Skill prose | As X1 | **KEEP** | — |
| 33 | N1, L2 | Minimum code / ponytail ladder | Prose | GA G14 FOLLOWED | **KEEP** | — |
| 34 | L4b | No concurrent sibling builders in a dirty checkout | Prose | GA G17 0/628 | **KEEP** | — |
| 35 | N3 | Preserve dirty work | Prose (every builder prompt repeats it) | GA G26: 18 candidate destructive commands; a real incident (row 26) | **KEEP** | See row 26 for the guard question |
| 36 | N4, G8 | No unauthorized spend or prod mutation; Codex reset credits need Ro's yes | Prose | Unmeasurable (GA G27), but cheap and high-stakes | **KEEP** | — |
| 37 | G5 | Main session stays on Anthropic | Prose | Cheap safety | **KEEP** | — |
| 38 | G12 | Ro naming a model overrides | Prose | Resolves C2 when followed | **KEEP** | — |
| 39 | P1–P5 | graphify is the map; repowise CLI only in c5/c7; repowise MCP removed; c0-preflight first; claude-api skill denied | 2,357 B project CLAUDE.md | GA G11 FOLLOWED (3 CLI, 0 MCP); G28 deny works (0 invocations; saves ~237 K tokens per accidental load) | **KEEP** | P4 c0-preflight usage is unmeasured. Measure it or drop the line |
| 40 | H6 | skill-reinject-guard | 27 denies at ~25 B each | Each deny avoids a 13.3 K-token re-load (≈360 K tokens/30d) | **KEEP** | — |
| 41 | H7 | northstar-protect (Write + Bash) | 0 blocks in 30d | Guards the one fixed point. Low firing ≠ dead (memory) | **KEEP** | — |
| 42 | H16 | harness-usage-telemetry | 0 B to context (writes 1.5 MB jsonl) | Feeds the audits | **KEEP** | — |
| 43 | R1–R6, G13 | Retrieval routing (codemap → l1 → skeleton; graphify; semgrep; rg) | Skill prose | GA G10: skeleton 157 calls, l1 10 | **KEEP** | — |
| 44 | QG1–QG5 | 26 quality gates (summarised) | ~2.5 KB of skill | GA G24 partial (lens 69%, mutation 15%); G25 unmeasurable | **KEEP** (QG3, QG4) / **UNKNOWN** (QG1, QG2, QG5) | Put PROOF on the receipt (B change 2) to measure QG5 |
| 45 | D2, D3 | Orchestrator silent while agents run; agent reports are claims until verified | Prose | B: 28/30 orchestrator claims supported, 2 unverified, 0 contradicted | **KEEP** (D3) / merge D2 into G1 | — |
| 46 | K5 | /goal skill | 9.2 KB, on demand | Invocations unmeasured here (memory: 0 in the 08-03 window) | **UNKNOWN** | Count invocations in T30 |

**Counts (46 rows, each counted once under its dominant class):**
- KEEP: 22 (rows 13, 22, 24, 27–45). Row 13 means keep the content; its scope fix is listed separately.
- FIX: 14 (rows 3–7, 9, 10, 12, 16–20, 25)
- CUT: 6 (rows 1, 2, 14, 15, 23, 26)
- UNKNOWN: 4 (rows 8, 11, 21, 46)

Split verdicts:
- Row 26: the dead hook files are CUT, but git-destructive-guard is UNKNOWN.
- Row 28: X2 is KEEP; Vividlist's own gate needs a FIX.
- Row 44: QG3 and QG4 are KEEP; QG1, QG2 and QG5 are UNKNOWN.

## 2. Contradictions (the rules that fight each other)

| ID | Rule A | Rule B | Evidence | Resolve to |
|---|---|---|---|---|
| **C1** | G1 "ZERO intermediate chat" plus H2 plus H22 | Background-job system prompt: "Narrate. One line on your approach… after each chunk" | GA G01: 23% intermediate blocks, mostly ≤60-char status lines, i.e. the job convention. G1 already says "background/headless jobs may narrate", but H2 and H22 do not carry that exemption | G1 wording wins. Delete H2 and the H22 caveman line |
| **C2** | G6/G7/G9/G10/G11: router decides; Claude builds go to the `claude` agent; cross-family audit; councils = Codex + Claude (Gemini optional) | **H14** "NEVER Claude as the builder… AUDITOR = glm 5.2… COUNCIL = Opus 4.8 + Codex 5.5 + GLM 5.2". **H22** `[routing]` "code writes → codex 5.5, glm 5.2 audits". **H13** "use `codex` for build/analysis". **H12** "use codex-companion/codex exec". **H10** docstring "codex 5.5 builder / glm 5.2 auditor" | `~/.claude/agents/glm.md.disabled`: the GLM auditor does not exist. Ro 09-22: "Opus 5.5 para construir y Opus 4.8 para auditar". GA G04/G20: 56% of builds and 67% of audits "violate" the hooks by following Ro | CLAUDE.md wins. CUT H14 and the H22 routing line. Fix the H13, H12 and H10 messages |
| **C3** | Caveman "Ro reads ONLY the final message" plus ponytail brevity | G3 "FINAL message = thorough, we DO want it long" | H2 carries a precedence clause (thorough final overrides ponytail) | Not a real conflict. It is a duplicate, so delete H2 and keep G1–G3 |
| **C4** | H23 "delegate .now.md + STATE update to a cheap sub-agent" | G6 "direct main edits are fine ONLY for orientation files (.now.md / STATE / memory)". Memory `subagent-fleet-is-the-real-cost`: "one avoided subagent launch is worth ~22% of the hook-diet prize" | 92 gate blocks in ~30 h; each block invites a launch | G6 wins: edit directly. Fix the H23 message, or CUT H23 |
| **C5** | Skill L4 "one **Codex** builder per unit" | G7 router decides | GA G04 CONFLICT | Make it "router's builder" |
| **C6** | Memory `rules-in-claudemd-not-hooks` (Ro 08-16: no blocking hooks except the git pre-commit) | 32 hook registrations live today, about 10 of which can block (H3, H4, H5, H6, H7, H10, H11, H12, H13, H23) | settings.json diff 09-28 → 10-02 14:06 | **Ro decides.** If his 08-16 call stands, revert to the 09-28 set minus H13 and add nothing else |
| **C7** | N2 200-line cap | check-all file-size warns at >800 (`~/.claude/skills/check-all/SKILL.md:39`) | GA G16 | Ratchet is authoritative. Point check-all at `ratchet.py` |
| **C8** | Skill L5 "fix and re-audit until no HIGH/CRITICAL" | Shared rubric "any MEDIUM touching money/secrets/data-loss → REJECT" | XA 3/10 | Rubric wins. Rewrite L5 |
| **C9** | Repo `skills/awesomeharness/SKILL.md` (has the "Route every launch…" line) | Live `~/.claude/skills/awesomeharness/SKILL.md` (lacks it) | `diff`: line 27 | Re-install. Memory `live-claude-layer-must-be-mirrored` predicted this |
| **C10** | opus48-audit.md:7 "verdict PASS/FIX" | opus48-audit.md:16 "PASS / PASS WITH FIXES / REJECT" | Same file | Make it one vocabulary |

## 3. New defect: harness prose is injected into production LLM calls

virality-pipeline calls `claude -p` as an LLM backend (`src/originated/_subagent_client.py:61`). Each call runs the user's full hook set.

**Scale:** in the ~1.5 days since the re-wire, **2,526 of 7,060** such product sessions received HARNESS ENFORCE and MESSAGE DISCIPLINE.

**Example:** transcript `344c6fdf` is a "describe HOW these people talk" comment-analysis call. Before the product prompt it got:
- Vercel plugin context: 4,803 B
- ponytail banner: 4,038 B
- MESSAGE DISCIPLINE: 1,844 B ("update .now.md… write pending.md")
- HOOK-INTEGRITY ALERT: 2,098 B
- HARNESS ENFORCE including the GLM routing line: 536 B
- a recall-inject memory about a different client (`clyde-laptop-papa-import`): 397 B

That is **≈13.7 KB of instructions unrelated to the product task, on every call.**

**Risks:**
- Output contamination. Instructions like "zero prose, write pending.md" sit on top of a JSON-returning prompt.
- Token spend on every pipeline call.
- Cross-client memory leaking into a prompt.

**Impact on outputs:** unmeasured. The sampled reply was still valid JSON.

**Fix, in either layer:**
- In the hooks: no-op when the session is non-interactive (`-p` / SDK entrypoint) or the cwd is under `/var/folders`.
- In virality: have `_subagent_client.py` launch with an isolated settings source so user hooks and plugins do not load.

Severity: **HIGH**, because it is a product correctness and cost risk, not a harness nicety.

## 4. What to do, in order

1. **Ask Ro about the 10-02 re-wire (C6).** Everything else depends on whether the 08-16 "no blocking hooks" call still stands.
2. **Stop the injection into production `claude -p` calls (§3).**
3. **Remove the retired routing policy from hooks (C2):** unregister `coding-routing-guard.sh`, drop harness-enforce `[routing]`, and fix the H13, H12 and H10 messages.
4. **Defang compact-prep-gate (C4):** PreCompact or session end only, exempt jobs, no sub-agent delegation.
5. **Narrow bash-write-fence to main and source files, and give irreversible-pause a tmp/build allowlist.** Together they are 1,170 blocks in 30 days, ~72% of the fence blocks hit builders, and 44 kill-switch bypasses.
6. **Fix the skill text:** L4 builder → router, L5 bar → shared rubric. Re-install the live skill (C9). Cut L1 (GOAL/NOT-GOAL block) and map-refresh.
7. **Re-bless manifest-guard; cap codemap under the persist limit; make northstar-inject inject the north star once per session.**
8. **Keep and spread the ratchet** to jobs, Consulting and free-model-router. Unstick Vividlist's stale-STATE commit gate.

## 5. Unmeasured (named so they can be measured)

- recall-inject precision: sample 30 injections and judge relevance.
- graphify-gate yield: is gated graphify output used in the next 5 calls?
- precompact-handoff read-back rate after compaction.
- /goal and c0-preflight invocation counts.
- Destructive git commands by builders in T30, which decides whether to wire git-destructive-guard.
- Whether the harness text in `-p` calls changed any product output: diff 20 calls with and without hooks.
- Whether `pending.md` is actually used. Transcript mentions are contaminated by the injected text itself.
- Provenance of the 10-02 re-wire.

## Method limits

- T30 counts hook-result lines (`type: user` tool_result or `stop_hook_summary` / `hook_additional_context` attachments). A blocked command retried N times counts N.
- The "next action after a block" figures are the first tool_use after the block in the same file.
- The irreversible-pause tmp/build split is a regex on the command, so the 97 is a lower bound for false positives.
- taskset.jsonl outcome correlations are **not usable for rule value**. Its 522 labelled rows are audit prompts, not build prompts. Reject rate is set by auditor identity (codex-audit 59%, opus 24%, opus48 0/112), not by rule features. Every prompt-feature split stayed within ±2 points of the 29% base, except `tests_ran` (15% vs 56% reject), which is the audit running tests rather than a build rule.
- Byte costs are raw UTF-8. Dollar weight is about 0.1x under cache-read (memory), but window occupancy is 1x.
