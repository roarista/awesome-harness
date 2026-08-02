# Claude Code memory/continuity forensic audit

Scope: read-only inspection on 2026-08-02. The transcript corpus contained 3,775 JSONL files (including 843 subagent files) and 89 `memory/*.md` records. I streamed JSONL one record at a time; no transcript was read wholesale. Figures labelled “sample” are not claims of an exhaustive causal reading.

## Recall Precision

**11.3% record precision (27 relevant of 240 injected records in a stratified 120-injection sample); 88.7% irrelevant.** The population has 3,432 `UserPromptSubmit` recall-hook injections in 2,852 sessions. The injected payload averages 280.9 characters (median 233), or about 70 tokens/injection at 4 characters/token. At the sampled error rate, this is **about 62 irrelevant tokens per injected session** (roughly 177k irrelevant tokens across the observed 2,852 sessions).

Method: I paired each hook attachment containing `🧠 maybe-relevant memory` with its triggering user prompt, coded each of its one or two records independently as relevant only when it constrained or informed that exact task, and stratified across normal project sessions and the `/private/var/folders/.../previz_vlm_claude_*` worker sessions. The hook itself confirms it forms one global FTS OR-query from the first ten prompt words and returns the top two global records: [`~/.claude/hooks/recall-inject.py`](/Users/rodrigoarista/.claude/hooks/recall-inject.py).

Concrete false positives (the quotes are the injected descriptions):

- Session `1689239d-2afb-4dfd-a444-fe9fcf6ae620`, line 12, was a harness-scout request yet received “`clyde-licencia-sigue-al-contexto-del-flow`” and “`clyde-arquitectura-decision`”; transcript: [`1689239d-…jsonl:12`](/Users/rodrigoarista/.claude/projects/-/1689239d-2afb-4dfd-a444-fe9fcf6ae620.jsonl:12).
- CAD-classifier session `4ad774fb-13bb-419d-af85-a3ccd49ed36`, line 12, received “`clyde-captura-tiempos-api`” and “`clyde-copilot-roadmap`”; its actual task begins “This image shows ONE isolated CAD layer”; [`4ad774fb-…jsonl:12`](/Users/rodrigoarista/.claude/projects/-private-var-folders-l2-cx20tsz578l4fgjqhxj9_g980000gn/T/previz_vlm_claude-z5ot83kl/4ad774fb-13bb-419d-af85-a3ccd49ed36.jsonl:12).
- ENGL session `67afc3d8-578f-4bd8-8035-4391db07e900`, line 2,373 received harness research plus a humanizer record while the user was correcting literary voice; [`67afc3d8-…jsonl:2373`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-ENGL2328/67afc3d8-578f-4bd8-8035-4391db07e900.jsonl:2373).

The ranking is visibly sticky, not project-scoped: `clyde-licencia-sigue-al-contexto-del-flow` appeared 686 times, `HARNESS_SCOUT_2026-07-26` 669, `clyde-arquitectura-decision` 539, and `RESEARCH_agent_code_quality_2026-06-29` 519 times. The high-volume CAD worker examples above show why these counts are not evidence of usefulness.

## Recall Utility

**74.1% re-derivation rate (20 of 27 relevant sampled records were followed by fresh discovery/tool work for the same fact); only 7/27 had observable direct use without re-derivation.** Sample: the 27 relevant records from the precision sample, with the following assistant/tool sequence inspected until the next substantive turn. “Re-derivation” means the agent re-opened/searches sources to establish the very fact in the injected description; verification of a volatile claim counts as re-derivation because the injected summary did not save the work.

Examples:

- In Consulting session `1f52a6ce-82d7-4ba0-b188-9cfc5e4d73f9`, the recalled `clyde-power-automate-blocker` was then opened/updated rather than used as settled context; the recall result is at [`…jsonl:769`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Consulting/1f52a6ce-82d7-4ba0-b188-9cfc5e4d73f9.jsonl:769). The record itself contains an old “NO está provisionado” claim followed by a correction, making a fresh check rational: [`clyde-power-automate-blocker.md`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Consulting/memory/clyde-power-automate-blocker.md).
- Relevant, direct-use cases were mostly narrow worker tasks: CAD workers receiving `Apartment Render` / `vividlist-codebase-reality` could answer the sheet-classification prompt without opening repository material, e.g. [`018d2b8d-…jsonl:12`](/Users/rodrigoarista/.claude/projects/-private-var-folders/l2/cx20tsz578l4fgjqhxj9_g980000gn/T/previz_vlm_claude-z74nhfqi/018d2b8d-a6dc-4ab5-9aa1-ec0ee65f7e68.jsonl:12). This is contextual relevance, not evidence that the record’s detailed claims were applied.

Conclusion: the injection usually costs context and then still requires source reconstruction. The record descriptions are too short to replace discovery, while several describe point-in-time UI/licensing facts that must be rechecked.

## Staleness

**25.0% stale-record rate (6 of 24 load-bearing records sampled; each has at least one now-false or unresolved file/command claim).** I sampled across the five stores, checked explicit paths/skills/commands with filesystem existence tests, and checked self-contradictory supersession within records. This is a lower bound: it does not assert that an external Microsoft/Claude product fact is false merely because it is old.

Named stale records:

- [`essay-forge-skill.md`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-ENGL2328/memory/essay-forge-skill.md) names `~/.claude/skills/essay-forge/SKILL.md` and `essay-writing-skill/SKILL.md`; both paths are absent.
- [`project_bolsa_trabajo_mexicali.md`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista/.claude/projects/-Users-rodrigoarista/memory/project_bolsa_trabajo_mexicali.md) says the project lives at `/Users/rodrigoarista/Downloads/bolsa-trabajo-mexicali/` and names a zip there; neither exists.
- [`project_antidrift_northstar.md`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista/.claude/projects/-Users-rodrigoarista/memory/project_antidrift_northstar.md) names `/.handoff.md` and temporary test paths that no longer exist.
- [`reference_model_roster.md`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista/.claude/projects/-Users-rodrigoarista/memory/reference_model_roster.md) names a version-placeholder plugin script path rather than a resolvable installed path.
- [`project_ci_red_and_local_hang_2026_08_01.md`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Vividlist/memory/project_ci_red_and_local_hang_2026_08_01.md) contains a literal truncated `/Users/rodrigoarista/Downloads/Vividlist/...` path, not a usable live reference.
- [`clyde-power-automate-blocker.md`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Consulting/memory/clyde-power-automate-blocker.md) retains the now-false historical statement “Power Automate NO está provisionado” above its correction. The hook can surface its description without that corrective context, as seen in [`8b9b6691-…jsonl:22`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Consulting/8b9b6691-2b03-4e43-90b0-fe11be3fcc73.jsonl:22).

## Coverage Gaps

**10 repeated fact/task clusters had 3+ independent-session re-derivations; the largest is 1,584 sessions.** Counts are conservative session counts from the 3,432 hook-linked prompts, grouped by semantic task rather than repeated lines. These are the facts that the current memory layer failed to make warm; for worker prompts, a prompt-template/configuration record is the appropriate memory, not a global business fact.

1. CAD sheet classification contract (meaning vs exact-coordinates, allowed layer categories): **1,584** sessions; e.g. [`f4207d75-…jsonl:12`](/Users/rodrigoarista/.claude/projects/-private-var/folders/l2/cx20tsz578l4fgjqhxj9_g980000gn/T/previz_vlm_claude-zejhipbe/f4207d75-6e84-4b77-b40d-53cf893c0e9a.jsonl:12).
2. CAD schedule-table extraction schema: **612** sessions; e.g. [`eb895ea0-…jsonl:12`](/Users/rodrigoarista/.claude/projects/-private-var/folders/l2/cx20tsz578l4fgjqhxj9_g980000gn/T/previz_vlm_claude-z1swgbiw/eb895ea0-9ff5-481f-93e8-e67e18e32dcf.jsonl:12).
3. CAD isolated-layer classifier choices/confidence rules: **421** sessions; [`4ad774fb-…jsonl:12`](/Users/rodrigoarista/.claude/projects/-private-var/folders/l2/cx20tsz578l4fgjqhxj9_g980000gn/T/previz_vlm_claude-z5ot83kl/4ad774fb-13bb-419d-af85-a3ccd49ed36.jsonl:12).
4. CAD region-separation test (real drawing split vs whitespace): **287** sessions; [`25133719-…jsonl:12`](/Users/rodrigoarista/.claude/projects/-private-var/folders/l2/cx20tsz578l4fgjqhxj9_g980000gn/T/previz_vlm_claude-zswmh2w8/25133719-bd59-4cff-b1d5-09f9d2fe4682.jsonl:12).
5. Harness-scout bounded/proposal-only contract: **19** sessions; [`1689239d-…jsonl:12`](/Users/rodrigoarista/.claude/projects/-/1689239d-2afb-4dfd-a444-fe9fcf6ae620.jsonl:12).
6. Resume-handoff seven-section/ratchet contract: **12** sessions; [`473b413a-…jsonl:15`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista/473b413a-302d-4144-9407-ad4ffb2bd869.jsonl:15).
7. Clyde Power Automate/Copilot licensing and access state: **11** sessions; [`c66b7abf-…jsonl:18`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Consulting/c66b7abf-c8c5-4376-825f-46f4a8864274.jsonl:18).
8. Vividlist intake codebase/current route: **9** sessions; [`0cf80704-…jsonl:596`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Vividlist/0cf80704-06f4-464c-9afd-c9c90e80b516.jsonl:596).
9. Health MVP ingestion loop (`/log -> add.py -> day.py`): **7** sessions; [`20111f9c-…jsonl:220`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-health-system/20111f9c-57b7-4771-93f6-14e369bcae55.jsonl:220).
10. Midland coursework/workflow and voice constraints: **5** sessions; [`67afc3d8-…jsonl:1053`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-ENGL2328/67afc3d8-578f-4bd8-8035-4391db07e900.jsonl:1053).

## Continuity Across Compaction

**0 confirmed post-compaction contradictions/rebuilds in a 30-session compaction-summary sample; 21/30 (70.0%) did not demonstrate that `.now.md`, `STATE.md`, or `COMPACT_HANDOFF.md` was read after compaction.** I located 2,635 transcript files containing an actual compact/summary marker, then inspected 30 non-subagent sessions spread across Vividlist, Consulting, intrn, virality-pipeline, health-system, ENGL, and awesome-harness. “Ignored” is deliberately conservative: no post-summary read/tool evidence, not proof that the agent had no latent context.

The most important limitation is that compaction itself preserves substantial in-context summaries, so absence of a contradiction is not success by the durable-file layer. The source files show the problem: this repository’s `.now.md` and [`STATE.md`](/Users/rodrigoarista/Downloads/awesome-harness/.planning/STATE.md) carry a rich resume point, but `STATE.md` explicitly records that the 2026-07-27 session was deleted and recovery required transcript `1a72c93c-*` rather than a handoff. That is a concrete continuity loss, not a clean resume.

Examples inspected: [`1f52a6ce-…jsonl`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Consulting/1f52a6ce-82d7-4ba0-b188-9cfc5e4d73f9.jsonl), [`0cf80704-…jsonl`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Vividlist/0cf80704-06f4-464c-9afd-c9c90e80b516.jsonl), [`775e6ad1-…jsonl`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-intrn/775e6ad1-9328-459e-8f48-78fc8ecc2b77.jsonl), and [`a891d580-…jsonl`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/a891d580-38f5-421b-84b3-2e5725ec3a34.jsonl). The repeated zero-context resume-handoff prompt itself is evidence that continuity is reconstructed ad hoc, e.g. [`23568407-…jsonl:15`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista/23568407-3991-4d39-8e8c-6f8340fde581.jsonl:15).

## Write-Side Compliance

**16.0% full close-out compliance (16 of 100 sampled substantive main-session endings).** “Full” required transcript evidence of (a) a durable memory or `.mulch` update and (b) `.now.md` or `.planning/STATE.md` update at the end of the same session. I sampled 100 non-temp, non-subagent sessions with a substantive task (excluded one-shot quiz answers and pure SDK CAD calls). This is the relevant denominator for the contract, not all 3,775 transcript files.

The low rate is consistent with the store shape: only 89 memory markdown files exist for 2,025 main-session transcripts, and just five `MEMORY.md` indexes were found. The contract says every close should persist `.now.md`, STATE, and memory/mulch, but the standing evidence often appears only in one later repository state, not in the session that did the work.

Positive examples include the Consulting session that actually updated a memory file after investigation: [`1f52a6ce-…jsonl:769`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Consulting/1f52a6ce-82d7-4ba0-b188-9cfc5e4d73f9.jsonl:769), and the current awesome-harness durable state: [`.now.md`](/Users/rodrigoarista/Downloads/awesome-harness/.now.md) plus [`STATE.md`](/Users/rodrigoarista/Downloads/awesome-harness/.planning/STATE.md). Counterexamples include the high-volume Vividlist main session [`10096718-…jsonl`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Vividlist/10096718-230a-4445-b3fe-0123b4f7c3bd.jsonl) and intrn session [`775e6ad1-…jsonl`](/Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-intrn/775e6ad1-9328-459e-8f48-78fc8ecc2b77.jsonl): both contain substantial work/compaction activity but no paired end-of-session evidence of all required durable writes.

Bottom line: this layer does not reliably start sessions warm. The automatic recall path is globally contaminated and mostly irrelevant; the few relevant records are often too stale or thin to prevent re-discovery; and the write-side ritual is observed in only about one in six substantive session endings.
