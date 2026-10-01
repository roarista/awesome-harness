# Gate adherence: is the harness being followed? (2026-10-01)

Window: 2026-09-01 to 2026-10-01. Read-only. Sources: 2,239 Claude transcripts (152 root sessions + 2,087 subagent files), 4,217 Codex rollouts (Sept + Oct 1), and git history for 10 repos (virality-pipeline, Consulting, intrn-v2, intrn, Vividlist, jobs, virality-trends, scholarships, greyrock, awesome-harness). vozctl, boat and dallas-trip have no git root. free-model-router and school have no commits. The jobs/crm third-party clone is excluded. This builds on `docs/audits/2026-09-30/harness-baseline.md` (B) and does not repeat it.

Classes: FOLLOWED is ≥70%. PARTIAL is 30–69%. IGNORED is under 30%. CONFLICT means two live rules disagree. UNMEASURABLE means there is no trace, and "unknown" is reported rather than a guess. The methods are python scans of the JSONL and git. The heuristics are listed under "Method limits" at the end.

Rule sources: **S** = `~/.claude/skills/awesomeharness/SKILL.md`, **G** = `~/.claude/CLAUDE.md`, **P** = `awesome-harness/.claude/CLAUDE.md`.

## Top table

| ID | Gate | Src | Adherence | n | Class | Recommendation |
|---|---|---|---|---|---|---|
| G01 | Zero intermediate chat | G | 22.7% of root text blocks come before a tool call (1,394); 546 of them are ≤60 chars | 6,129 text blocks | PARTIAL | KEEP, but exempt background jobs, whose system prompt says "Narrate" |
| G02 | Each turn ends compaction-safe (.now/STATE, mulch) | G,S7 | .now/STATE native edits in 11/152 roots; `ml record` in 17/152; compact-prep ran 100× | 152 roots | IGNORED (per turn) | ENFORCE through compact-prep only. Drop the "every turn" wording |
| G03 | Main session orchestrates and does not write code | G | Native code edits in 21/152 roots (250 edits; 21/41 build roots = 51%); ≤251 Bash-write candidates in 33 roots | 152 roots | PARTIAL | ENFORCE in prose plus a check-all "author" receipt. A hook would be routed around |
| G04 | Builder = Codex ("siempre Codex") | G | 367/834 builder spawns are codex (44%); 443 Claude subagent files made native code edits | 834 spawns | CONFLICT | Router owns this; Ro said 09-22 "Opus 5.5 para construir". Rewrite G |
| G05 | Default effort MEDIUM | G | medium 98 / low 229 / unknown 1,705 | 2,032 tasks | IGNORED (when known) | Router emits effort; drop the static rule |
| G06 | Councils = Codex + Gemini | G | gemini agent spawned 24×; denominator of council requests unknown | — | UNMEASURABLE | KEEP as prose |
| G07 | `route-model.sh` decides agent and model | G | 7 calls (5 root, 2 agent) against 834 builder spawns | 834 | IGNORED | Replace with the router in the spawn path |
| G08 | Graphify before cold browsing | P,S | 72 Claude calls; 165/4,217 Codex sessions; in Codex build sessions, 11/411 before the first patch | 411 | IGNORED (pre-edit) | KEEP as a tool; enforce through the REUSE evidence line (G14) |
| G09 | Load awesomeharness before code | G | 38/152 roots (180 invocations, mostly typed /awesomeharness); Codex: 163/411 build sessions read it before the first patch | 152 / 411 | IGNORED / PARTIAL | Router attaches it per task |
| G10 | Zoom ladder: l1 → skeleton before bodies | S | skeleton.py 157 Claude calls; l1.py 10 | no denominator | PARTIAL (used) | KEEP |
| G11 | Repowise CLI only in c5/c7; no MCP | P | 3 CLI calls, 0 MCP | 30d | FOLLOWED | KEEP |
| G12 | GOAL / NOT-GOAL / DONE-WHEN / PROOF stated | S1 | DONE-WHEN or PROOF in 34/2,109 spawn prompts (1.6%); NOT-GOAL 35 | 2,109 | IGNORED | DROP as a separate block; merge into the spec's GOAL/VERIFY |
| G13 | REUSE/ADAPT/REJECT (orient / codebase-first) before build | S2 | Claude build roots oriented first: 3/41 (7%). Codex build sessions with orient/graphify/semgrep/skeleton before the first patch: 99/411 (24%); rg 261/411. `/orient` invoked 0× | 452 | IGNORED | ENFORCE: the spec must carry a REUSE line with file:line evidence, and the auditor rejects a spec without it |
| G14 | Ponytail ladder; `ponytail:` comments | S2 | 573 `ponytail:` code comments in 10 repos, 293 added in Sept; /ponytail* skills invoked 0×; 10-diff sample: 8 LEAN, 2 SOME-BLOAT, 0 new deps | 10 diffs | FOLLOWED (output) | KEEP. It works without the skill being invoked |
| G15 | code-decompose CONTEXT/CHANGE/GOAL/VERIFY specs | S3 | All 4 fields: Claude builders 98/834 (12%), Codex build sessions 127/411 (31%), pooled 18%. ≥3 fields: 25% / 47%. Skill invoked 0× in Claude | 1,245 | IGNORED | ENFORCE in the builder agent definitions (precedent: the return contract) and through router templates |
| G16 | Source file ≤200 lines (300 ceiling; touching a big file means shrinking it) | S | 1,160/3,933 non-test source files >200 now (29%). Since the rule, crossings fell from 24.6 to 8.9 per 100 source commits. Edits to >200-line files still grew the file 43% of the time | 1,057 source commits | PARTIAL | ENFORCE as a ratchet in check-all, which today warns only at **800** lines |
| G17 | One builder per unit; no concurrent siblings in a dirty checkout | S4 | 0/628 assistant messages spawned two or more builders; background overlap unmeasured | 628 | FOLLOWED (partial measure) | KEEP |
| G18 | Independent auditor on the same spec; re-audit to no HIGH | S5 | 605/834 builder spawns are followed by an audit within the next 5 spawns (72.5%; B's stricter path-matched proxy: 39.4%); 151/152 REJECTs get a later audit in the same session | 834 / 152 | FOLLOWED (loose) / PARTIAL (strict) | KEEP. Router pairs builder and auditor |
| G19 | Review with a different model | S | codex → codex-audit (same family): 89/605 audited builds (15%) | 605 | FOLLOWED | Router guarantees a cross-family auditor |
| G20 | Audits default to codex-audit; Opus only as escalation | G | Audits: opus 302, opus48 127, codex-audit 212 (33%) | 641 | CONFLICT | Ro 09-22 made opus48 the auditor. Rewrite G and let the router decide |
| G21 | Unit check + repo gate + check-all before ship | S6 | `check_all.sh` ran before the first commit in 0/28 Claude session trees (2 executions in 30d) and in 22/34 Codex commit sessions; pooled 22/62 (35%). Post-edit tests: 76.3% (B) | 62 | PARTIAL (Claude: IGNORED) | ENFORCE in the commit path (git pre-commit runs check-all --fast) |
| G22 | map-refresh before a commit that adds or moves files | S7, agent | map-refresh agent spawned 1×; 2 Claude roots and 2 Codex rollouts; there were 1,381 commit commands | 1,381 | IGNORED | DROP as a step; fold `graphify update` into check-all |
| G23 | Spawn contract: report path + ≤8-line return | S | report path in 1,601/2,109 (76%); ≤8 lines in 1,289/2,109 (61%) | 2,109 | FOLLOWED / PARTIAL | KEEP. Already in the agent definitions |
| G24 | Quality gates: reviewer lens, mutation-proof tests | S | Audit prompts naming a lens: 436/628 (69%); opus48 PASS reports citing mutations: 17/112 (15%) | 628 / 112 | PARTIAL | KEEP 1–2 lenses. Router attaches the lens by risk |
| G25 | Quality gates: reproduce before fix, run twice, fresh machine | S | no trace | — | UNMEASURABLE | Put PROOF on the receipt (B change 2) |
| G26 | Preserve dirty work (no reset/clean/stash/restore) | S | 18 candidate destructive git commands (4 root, 14 agent); target not adjudicated | 30d | PARTIAL? | KEEP. Check-all could detect a lost diff |
| G27 | No unauthorized spend or prod mutation | S | no trace | — | UNMEASURABLE | KEEP |
| G28 | claude-api skill denied here | P | 0 invocations | 30d | FOLLOWED | KEEP (the deny works) |
| G29 | Mulch durable learning per unit | S7 | `ml` calls: 173 root, 13 agent; `ml record` in 17/152 roots | 152 | IGNORED (per unit) | Keep through compact-prep |

## Per-gate notes (only where the why matters)

**G16 (200-line cap): behavior moved, but nothing enforces it.**
- Now, non-test source over 200 lines: virality 253/1,157, intrn 364/1,182, Vividlist 506/1,048, awesome-harness 24/88, Consulting 9/65, virality-trends 3/17 (vendored), greyrock 1/69. intrn-v2 (0/93) and jobs (0/210) were born under the rule, and their largest files sit at exactly 199–200 lines. intrn and Vividlist had no commits after the cap, so they are legacy debt and not violations.
- Before and after: two equal 24.2-day windows split at 90d2810 (2026-09-07 14:57), counting source commits on all refs.

  | Window | Source commits | Crossed 200 | New files >200 | Per 100 commits | Touched >200 files: grew / shrank |
  |---|---:|---:|---:|---:|---|
  | Before | 431 | 28 | 78 | 24.6 | 82% / 9% |
  | After | 626 | 23 | 33 | 8.9 | 43% / 26% |

- So the gate changed behavior. But "touching it means shrinking it" is still broken 43% of the time. Example: da81248d grew `src/spine/costs.py` from 513 to 524 lines.
- Confound: most of the after-window work is virality's video_v2, which was greenfield-heavy.
- **Why it isn't fully followed:** the only deterministic checker is check-all, and its `file-size` check is `warn` at **>800 lines** (`~/.claude/skills/check-all/SKILL.md:44`). The tool contradicts the rule.

**G13 / G15 (orient and decompose): the skills are never invoked, but the shape partly survives.**
- Claude invoked `/orient` 0×, `/code-decompose` 0× and the check-all skill 0× in 30 days. Codex reads the SKILL.md files often (orient in 1,177 sessions, code-decompose in 613), because its AGENTS layer points at them.
- Reading the skill is not the same as producing a spec. Only 31% of Codex build prompts carry all four fields.
- Builder prompts often use their own working format instead ("EDITABLE FILES — ONLY THESE FOUR … GOAL …"). That format is good on scope fences and has no CONTEXT/CHANGE/VERIFY fields.
- Why: the skills only got wired into awesomeharness on 09-15 (cda97aa). They are long, and they trigger on the same words as the builder spawn itself, so the orchestrator skips straight to the spawn.
- What has worked before: putting the contract inside the agent definition. The return contract went from 0 agent definitions to 61% compliance.

**G03 / G04 / G20 (who builds and who audits): the rules contradict each other.**
- G says "siempre Codex" and "audits → codex-audit". The opus48-audit definition records Ro's 2026-09-22 directive: "Opus 5.5 para construir y Opus 4.8 para auditar". Codex is also at its weekly cap.
- So 56% of builds and 67% of audits "violate" G by following Ro.
- The `claude-spawn-gate.py` hook now blocks `general-purpose` spawns, which this audit hit itself. It is a third, unwritten version of the policy.
- Main-session code edits cluster in virality (144 of 250) and school/Consulting scripts. They are mostly small fixes during live debugging, which is the "tiny" exemption stretched.

**G21 (check-all): Codex runs it and Claude does not.**
- `check_all.sh` was executed in 390 Codex rollouts, mostly codex-audit runs, and twice in all Claude transcripts.
- The 1,381 commits made from Claude session trees had check-all executed before them 0 times. A same-day text mention of check-all appears near 127 of those commits; that is a mention, not a run.
- Why: check-all is a skill to "remember", not a step in the commit path.

**G22 (map-refresh): dead as a step.** L0, L1 and the skeleton are live (computed per call). Only .codemap and graphify are cached. One spawn in 30 days, so remove the step and regenerate the caches inside check-all.

**G14 (ponytail): followed without the skill.**
- Sample of 10 builder commits with more than 40 added source lines (virality b75ad75a, cdf8211b, da81248d, b24f6646; virality-trends bf96d76; Consulting 06ca5ef, 57430c3; jobs a62ccd2, c3904ab, 6ec3e49).
- None added a dependency or a single-implementation ABC/Protocol/registry. The TS `interface`s in 06ca5ef are data shapes.
- SOME-BLOAT, da81248d: a new env knob `VIRALITY_LOCAL_TEXT_VULTR_CAP_USD` (costs.py:9) plus growth of the 513-line file.
- SOME-BLOAT, 6ec3e49: `--force` is added to two parsers with a `JOBS_ACTOR` env backdoor (app/cli_source.py:102,104). This may have been requested ("Ro only").
- The CLI flags in the jobs commits (`--dry`, `--apply` default dry-run) are safety rails, not bloat.
- Verdict: 8 LEAN, 2 SOME-BLOAT, 0 BLOATED. n=10, judged from the diffs only.

**G01 (chat discipline):** the background-job system prompt explicitly requires narration ("Narrate … one line on your approach") and this conflicts with "ZERO intermediate chat". 23% of text blocks are intermediate. Many are ≤60-char status lines, which is the job convention, so this is not misbehavior.

## opus48-audit: 112 PASS / 0 REJECT. Diet or rubber stamp?

The bench, verbatim in spirit: on 2026-10-01, opus48-audit scored **6/6 planted defects plus 1 valid extra and 0 false positives** on `docs/audits/2026-08-03/fixture-known-bad.py`. On the same fixture, opus scored 6/6 and codex-audit 5/6. Yet in the 30-day taskset opus48-audit has **112 PASS / 0 REJECT** (13 unknown).

What opus48 was actually given (127 agent files, model claude-opus-4-8):
- **Narrow diet.**
  - Repos: 120/127 virality-pipeline. Dates: 107/125 runs fall on 09-22 to 09-24 (one decomposed video_v2 plan).
  - Builders: 108 of its audits follow a `general-purpose` build (Opus 5.5) and 3 follow a codex build.
  - Every unit came pre-decomposed with an owned-paths fence. Median prompt is 1,701 B.
- **Not a re-audit diet.** Only 13/112 PASS prompts are re-audits. No PASS came from a resumed agent; only 1 file has an earlier REJECT text inside it.
- **Not rubber-stamping by behavior.**
  - Median 12 tool calls per audit.
  - 106/112 PASSes list at least one LOW finding with file:line; 7 list MEDIUM findings; 17 report running mutations.
  - Example: the openai_images re-audit checked record-before-decode ordering at specific lines and a test that fails on the old ordering.
- **But the threshold is lenient and uncalibrated.**
  - The agent definition has no verdict rubric. The orchestrator's prompts define "PASS = no HIGH/CRITICAL", so everything graded MEDIUM or below passes.
  - In the same sessions over the same period (≥09-22), codex-audit hard-REJECTed 56/88 (64%) and opus 5/21 (24%). Those auditors mostly saw Codex-built units under a different, three-tier rubric (ACCEPT / ACCEPT WITH FIXES / REJECT), so the rates are not comparable.
  - In the 8 units that had two auditors, opus48 never contradicted a later REJECT on the same unit with certainty: U4C was opus REJECT, then opus48 PASS, likely after a fix. n is too small.

**Verdict:** a diet and threshold effect, not rubber-stamping. Opus48 does the work and finds things, but it audits one repo's Opus-built, tightly fenced units under a "below HIGH passes" rule. The fixture only shows it can *detect* obvious planted defects. It says nothing about whether it **grades severity** like the others, which is the one thing that turns findings into a REJECT.

That calibration is **unknown**. To settle it:
1. Blind re-audit 10 opus48 PASS units with codex-audit and opus using one shared rubric.
2. Plant a MEDIUM-looking-but-HIGH defect in a real unit, not the fixture.

## Top 5 enforcement changes, ranked by impact

1. **Put check-all in the commit path and fix its size rule.** Install a git `pre-commit` (`core.hooksPath`) in the active repos that runs `check_all.sh --fast`. Change file-size from warn-at-800 to a fail ratchet:
   - a new file over 200 lines fails;
   - a file that crosses 200 fails;
   - a >200 file that grows fails.

   Fold `graphify update` / codemap regen into the same run. This closes G16, G21 and G22 deterministically, at the one door that 1,381 commits a month go through. Bash cannot route around a check that `git commit` itself runs; `--no-verify` is the only escape, and it is greppable.
2. **The router attaches the gate bundle to every task** (plan §Components 6). `route` returns a spec template besides agent, model and effort. The template holds CONTEXT/REUSE(file:line)/CHANGE/GOAL/VERIFY, the required skills (code-decompose, check-all) and a reviewer lens chosen by risk. Put the same template check into the `codex`, builder and `opus48-audit` agent definitions: a builder flags a spec missing fields; an auditor REJECTs "spec incomplete". This moves G15 off 18% and G13 off 7–24% without a hook. Today `route-model.sh` is called 7× against 834 builder spawns, so the router has to sit *in* the agent definitions, not beside them.
3. **One shared auditor rubric plus a calibration canary.** Write the PASS/REJECT rule, with severity definitions and the rule that a MEDIUM in data-loss/money/secret lenses means REJECT, into the opus48-audit, opus and codex-audit definitions. Run the 10-unit blind cross-audit and a monthly real-unit planted canary. That decides whether the 0% reject is real, and it makes reject rates comparable for the router's outcome labels.
4. **Reconcile the contradicting rules in compact prose.**
   - Rewrite G's Models/Delegation section to "builder/auditor/effort come from the router; cross-family audit always; Ro's named model wins".
   - Retire "siempre Codex", "default MEDIUM" and "audits → codex-audit" (G04/G05/G20 CONFLICT).
   - Exempt background jobs from zero-chat (G01).
   - Write the spawn-gate hook's policy into CLAUDE.md, or remove the hook.
5. **Prune gates that never fire and keep the ones that work.**
   - Drop map-refresh as a step (G22). Merge GOAL/NOT-GOAL/DONE-WHEN/PROOF (1.6%) into the spec's GOAL/VERIFY (G12). Replace the "every turn" persistence rule with compact-prep (G02/G29).
   - Keep ponytail (followed), the spawn contract (76%), the audit-after-build loop (72.5%) and the zoom tools. Their adherence comes from being inside tools and agent definitions, which is where the rest should move.

## Method limits

- **Build-intent spawns** are matched by keywords (build/implement/fix/…) excluding read-only/audit prompts. This includes some research.
- **Audit-after-build** pairs a build with the next 5 spawns in the same session, not by unit. B's path-matched figure (39.4%) is the strict bound.
- **Codex "build session"** means an `apply_patch` touching a code file. Codex exec sessions launched by the Claude `codex` agent are counted here as well as being spawned from Claude, so the pooled Claude+Codex rates double-count some units.
- **Bash-write detection** is a regex upper bound (sed -i, redirection or tee to code paths, python write with a code-path literal, excluding /tmp).
- **The 200-line windows** are split at the 90d2810 commit time and use all refs. "Crossed" means ≤200 lines in the parent and >200 after.
- **Not measured:** run-twice/fresh-machine proof, spend authorization, the orchestrator's silence while agents run, and background builder overlap.
- **Scripts:** `/tmp/ga/*.py`, which are ephemeral.
