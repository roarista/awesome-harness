# Harness baseline — 2026-09-30

Phase 0 measures observable code review, verification, rework and usage signals before evaluating the model router. Window: **2026-09-01 00:00 UTC to 2026-10-01 00:00 UTC** (30 calendar days). Sources were read only; unknown means missing or ambiguous evidence, never success.

| Metric | Value | n | Method |
|---|---:|---:|---|
| Builds: delegation attempts / linked tasks | 2,149 / 2,032 | 2,149 unique tool IDs | Deduplicate Claude Agent/Task calls; join result agentId to transcript |
| Builds: build-intent tasks | 965 | 2,032 linked tasks | Non-audit description/prompt-first-500 build/implement/fix/refactor/patch/code/add/write/create match |
| Builds: observed source-edit tasks | 438 | 2,032 linked tasks | Native Edit/Write/MultiEdit outside Markdown, agent-reports and /tmp; lower bound |
| Builds: post-edit test execution | 76.3% (334/438) | 438 source-edit tasks | Shell-tokenized test command + completed result after last observed native edit; not a pass rate |
| Builds: possible audit follow-up | 39.4% (380/965) | 965 build-intent tasks | Later audit, same caller file, within 24h, exact shared non-Markdown path; candidate only |
| Builds: attributable audit/retry/git outcome | unknown | 965 build-intent tasks | No durable build→audit→commit key; path candidates cannot prove attribution |
| Builds: check-all execution | unknown (0 direct matches) | 2,032 linked tasks | No explicit check-all executable matched; component tests/backend execution differ |
| Code quality: audit reject rate | 29.1% (152/522) | 522 explicit final verdicts | REJECT / (PASS or ACCEPT + REJECT); 129 ambiguous/conditional/missing finals excluded |
| Code quality: fix commits / titled reverts | 156 / 0 | 1,766 commits; 18 repos | All local refs, hashes deduplicated; anchored fix(scope): / fix: / revert subjects |
| Code quality: 72h rework proxy, Ro cohort | 6.21% (105/1,691) | 1,691 commits | Fix shares path with previous commit ≤72h; excludes third-party jobs/crm |
| Code quality: 72h rework proxy, all repos | 7.76% (137/1,766) | 1,766 commits | Same method including third-party clone; not causal defect rate |
| Context: mean / median / max prompt bytes | 1,960 / 1,688 / 12,645 | 2,032 prompts | UTF-8 bytes before truncation; token count unknown |
| Context: potentially unused path context | 23.3% (465/1,996) | 1,996 path-containing prompts | Prompt path and basename absent from child text/tool inputs; absence is not non-use proof |
| Knowledge: wrong or unverified claims | 6.7% (2/30) | 30 purposively sampled claims | 28 supported, 2 unverified, 0 contradicted; parent + descendant tool evidence |
| Usage: Claude fresh-input/output/cache-write/cache-read | 0.432M / 42.911M / 304.325M / 8,716.442M | 73,829 real-model messages | Deduplicate (message.id, requestId); last usage per ID; cache categories separate |
| Usage: Codex sessions / native subagents | 3,800 / 1,070 | 3,800 session IDs | First session_meta identity; subagent metadata; sessions are not builds |
| Usage: Codex input / cached-input / output | 1,914.080M / 1,770.465M / 11.999M | 37,306 unique snapshots | Cumulative deltas; copied fork history removed; cached-input is included in input |
| Taskset: outcomes | 2,032: 370 pass, 152 reject, 1,510 unknown | 2,032 linked tasks | Full linked census across strata; no task-linked reworks/reverts established |

## Findings

- **Code quality is mixed, with functioning review but insufficient proof of reliable shipping.** Audits reject 29.1% of explicit final results and identify concrete defects. PASS can retain nonblocking findings; repeat audits and plan/document work are included, so this is not a first-build failure rate or model ranking.
- **The orchestrator usually has evidence for sampled assertions, but overstates provenance and workflow uniformity.** Two of 30 claims lack sufficient receipts; neither is proven false. Passing tests support the named test selection, not production correctness.
- **Telemetry is the router blocker.** 635/2,032 task models are unknown; 642 tasks invoke a secondary CLI and seven expose an unambiguous runtime model banner. Nested audits can also make a Claude build mixed-model; the wrapper is not necessarily the builder backend.
- All 105 Ro-cohort same-path 72h fixes occur in virality-pipeline. Commit naming differs across repos; zero fixes elsewhere is not better-code evidence. Third-party jobs/crm supplies 32/137 raw rework signals.
- Context waste is less certain than expected: only eight prompts contain triple-backtick fences, and none has an unmentioned extracted path. No defensible example proves a large embedded code block unused; path absence must not become a wasted-token estimate.

## Build and audit breakdown

T=linked tasks; B=build-intent proxy; E=observed source-edit tasks; X=post-final-edit test calls; P/R/U=final audit pass/reject/unknown. Audit type/description matches audit/review, including design/document work. Retry counts and causal audit/git outcomes are **unknown for every group**; 363 subsequent corrective user messages are not reliable retry counts. No Agent resume field was observed.
| Agent type | Observed model | T | B | E | X | Audit P/R/U |
|---|---|---:|---:|---:|---:|---|
| codex | claude-haiku-4-5-20251001 | 61 | 25 | 0 | 0 | 0/0/1 |
| codex | gpt-6-astra | 5 | 5 | 0 | 0 | 0/0/0 |
| codex | unknown | 446 | 364 | 0 | 0 | 0/0/22 |
| codex-audit | claude-haiku-4-5-20251001 | 19 | 0 | 0 | 0 | 12/1/6 |
| codex-audit | gpt-6-sol | 2 | 0 | 0 | 0 | 2/0/0 |
| codex-audit | unknown | 175 | 0 | 0 | 0 | 48/89/38 |
| general-purpose | claude-fable-5 | 1 | 0 | 0 | 0 | 0/0/0 |
| general-purpose | claude-fable-5-1 | 18 | 11 | 0 | 0 | 0/0/1 |
| general-purpose | claude-opus-5 | 42 | 40 | 31 | 19 | 0/0/2 |
| general-purpose | claude-opus-5-5 | 340 | 246 | 231 | 199 | 0/0/16 |
| general-purpose | claude-sonnet-5 | 142 | 83 | 68 | 57 | 1/0/2 |
| general-purpose | unknown | 5 | 3 | 4 | 4 | 0/0/1 |
| opus | claude-fable-5 | 9 | 0 | 0 | 0 | 6/3/0 |
| opus | claude-fable-5-1 | 116 | 3 | 0 | 0 | 84/21/6 |
| opus | claude-opus-5 | 157 | 8 | 0 | 0 | 103/34/11 |
| opus | claude-opus-5-5 | 16 | 6 | 0 | 0 | 1/1/0 |
| opus | unknown | 4 | 0 | 0 | 0 | 1/3/0 |
| opus48-audit | claude-opus-4-8 | 124 | 0 | 0 | 0 | 111/0/13 |
| opus48-audit | unknown | 1 | 0 | 0 | 0 | 1/0/0 |
| other | claude-fable-5-1 | 28 | 18 | 11 | 8 | 0/0/5 |
| other | claude-haiku-4-5-20251001 | 1 | 1 | 0 | 0 | 0/0/0 |
| other | claude-opus-5 | 85 | 44 | 32 | 20 | 0/0/4 |
| other | claude-opus-5-5 | 28 | 25 | 23 | 15 | 0/0/1 |
| other | claude-sonnet-5 | 203 | 80 | 35 | 10 | 0/0/0 |
| other | unknown | 4 | 3 | 3 | 2 | 0/0/0 |
Attempt counts by requested type: codex 512; codex-audit 196; opus 302; opus48-audit 125; general-purpose 657; claude 266; other 91. Linked census excludes 117 unmatched/blocked attempts. Other agent types are retained in evidence but schema agent=unknown. Native edits miss Bash/CLI edits; zero E is not zero builds.

## Top recurring finding categories

Multi-label keyword screen of HEADLINE/severity-prefixed lines in 152 final REJECT summaries, not individually adjudicated defects. Top five of seven predefined themes; positive clauses can still mention a theme. Quotes demonstrate concrete findings; IDs locate agent-<id>.jsonl recursively under ~/.claude/projects.
| Category | Summaries mentioning it (n=152) | Actual finding quote | Agent ID |
|---|---:|---|---|
| Tests / incomplete verification | 52 | “test.py pins Maya due today to the real clock, suite goes red on 2026-09-22” (inner quotes omitted) | a9dfc1a5394afc408 |
| Specification / semantic mismatch | 42 | “incomplete file type/size spec” | a3ee2bb0e10bcfe61 |
| Validation / malformed inputs | 24 | “malformed input crashes live loop” | a0f4bc430d14dcbf2 |
| Recovery / retries / idempotency | 19 | “is not idempotent” (mark_sent accepts never-approved drafts) | a1e7de32f7f238e08 |
| Security / secrets / trust boundaries | 18 | “leaks input secrets in JSON output” | a3fd29023011b8199 |
Lexicons: tests=test/verif/mutation/coverage/fixture/false-green; spec=spec/contract/mismatch/semantic/wrong/incorrect/inconsisten; validation=validat/malformed/invalid/NaN/schema/missing key or field/type check; recovery=retry/idempoten/resume/recover/duplicate/re-run/double-charge/partial; security=secret/credential/injection/traversal/SSRF/permission/unauthor/consent/argv/escape. Other theme counts: persistence/data loss 13; concurrency/lifecycle 10.

## Orchestrator claims: 30 checked

Purposive sample of root fixed/verified/tests-pass/numeric-green assertions across three repo contexts. S=supported specific assertion; U=unverified; none demonstrated wrong. Evidence includes child tool results; this is a diagnostic sample, not a population estimate.
Root paths under /Users/rodrigoarista/.claude/projects/: A=-Users-rodrigoarista-Downloads-awesome-harness/e34551dd-1363-42fd-a96e-8109c649ebe7.jsonl; B=-Users-rodrigoarista-Downloads-awesome-harness/fdeec44e-31d2-43e1-999f-2e1e16095ac5.jsonl; C=-Users-rodrigoarista-Downloads-Consulting/ca09109e-0776-4cb3-9201-28dc066da40c.jsonl; V=-Users-rodrigoarista-Downloads-virality-pipeline/4d5625f0-9212-44a7-8b77-f2defe648895.jsonl; W=-Users-rodrigoarista-Downloads-virality-pipeline/b1947e1e-d8ff-4239-845d-bc53d2ac8df7.jsonl. Child paths: root-directory/session-ID/subagents/agent-ID.jsonl.
| Claim source:line | Assertion checked | Label | Evidence source:line |
|---|---|---|---|
| A:146 | Codemap globally installed | S | A:137 SessionStart hook command |
| B:43 | Model stage exit 1; 77 unclassified | S | B:31 actual failure/count |
| C:2456 | Citation edits applied; audit launched | S | C:2444,2449,2453 |
| C:3644 | Three design docs structurally complete | S | C:3619,3640 headings/lengths |
| C:3779 | Five audits pass; seguros reject | S | C:3722 and preceding audit notifications |
| C:3794 | Seguros fixes applied; re-audit launched | S | agent-ad6cc52a6f896973e:20–35; C:3791 |
| C:3979 | Connection-reference correction applied | S | agent-a45a9b6ee0230db68:21 parse/readback |
| C:4043 | Fuga script fixed | S | agent-a3f93cdf3a68d9739:23 source readback only |
| V:15596 | 579 tests pass | S | V:15585 |
| V:15719 | gpt-6-astra backend confirmed | U | agent-a93d1be62fa5957a6:16 CLI has no model; no runtime banner |
| V:15782 | 591 tests pass | S | V:15755 |
| V:15879 | 594 tests pass | S | V:15856 |
| V:19994 | 318 tests pass; Ruff clean | S | V:19989 |
| V:20058 | 150 tests pass; Ruff clean | S | V:20047 |
| V:20104 | 927 pass plus one failure | S | V:20096; unrelated-cause assertion not assessed |
| V:38676 | Every new unit fixed and re-audited | U | XR1 audit V:38588; no re-audit before summary |
| V:39176 | 426 production tests pass | S | agent-a5ce6273be598fb01:145,155; agent-a5b7c2caeeed99ada:14 |
| V:39641 | 428 production tests pass | S | V:39370 |
| V:41617 | 468 production tests pass | S | V:41588 |
| V:42481 | 1627 pass, two skipped | S | V:42438 |
| V:49688 | 1762 pass, three xfailed | S | agent-a341bbcc4e7bf14d9:320 |
| V:52120 | 2776 tests pass | S | V:52066 also seven deselected |
| W:824 | 18 specs/order unchanged; 782 pass | S | W:801 ORDER SAME/spec diffs [] |
| W:287 | 746 tests pass | S | W:262 |
| W:570 | 271 tests pass | S | W:554 |
| W:738 | 491 tests pass | S | W:722 |
| W:893 | 784 tests pass | S | W:870 |
| W:1024 | 798 tests pass | S | W:1007 |
| W:1096 | 800 tests pass | S | W:1057 |
| W:1159 | 810 tests pass | S | W:1142 |
Five highest verification-risk examples (only the first two are unverified):

1. **Backend identity:** V:15719, session 4d5625f0-9212-44a7-8b77-f2defe648895, “model gpt-6-astra confirmed this time”; report/config cannot prove backend identity for src/video_v2/run_stage.py / container_vocab.py.
2. **Uniform workflow:** V:38676, same session, “Each unit went build → audit → fix → re-audit”; XR1 (scripts/production/run_test.py, tests_page.py) has one PASS audit with two LOW findings, no matching re-audit before this claim.
3. **Fix versus runtime proof:** C:4043, session ca09109e-0776-4cb3-9201-28dc066da40c, “Fuga script fixed”; edits to Clyde&Co-Garzatello/deliverables/fabrica/eduardo/fuga-inter-oficina/04-script.ts are supported, but “should yield 3 candidatos/5h” is not fixture execution.
4. **Suite scope:** V:52120 accurately reports 2,776 passes but output also has seven deselected tests; tests/video_v2 + tests/creative_rag are the scope.
5. **Root-only checks create false accusations:** V:49688 reports 1,762 passes versus the parent’s latest 1,723; descendant agent-a341bbcc4e7bf14d9.jsonl:320 proves 1,762/three xfailed.

## Context and Claude usage

Prompt bytes exclude system instructions, inherited history, injected skills and file expansion. Token counts are unknown. Literal path absence is only a candidate: globs, directory reads, aliases and hidden CLIs may use a file without naming it.

- Candidate: /Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-Consulting/5dad6e66-bb0c-45a6-9db2-5a8ed7ce851d/subagents/agent-a6a12324df2c7878c.jsonl:46 → agent-aa098781ea965b76e, 12,645 bytes; tools/test-edgar-seguros-fixtures.py, tools/buzon.py absent by full path and basename from child assistant text/tool inputs. Not proof of wasted context.
- Candidate: /Users/rodrigoarista/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/d98073eb-4f60-4a0e-bfb2-ca25393e311f.jsonl:53574 → agent-a6228a46a9ab0d9a1, 7,565 bytes; src/s1/paths.py, .planning/PLAN_PERSONAS_V2_2026-09-23.md absent by full path and basename from child assistant text/tool inputs. Not proof of wasted context.
Each usage cell is model = distinct root-or-agent files / total tokens in millions, including fresh input + cache creation + cache reads + output. H=claude-haiku-4-5-20251001; O48=claude-opus-4-8; O5=claude-opus-5; O55=claude-opus-5-5; S5=claude-sonnet-5; S46=claude-sonnet-4-6; F5=claude-fable-5; F51=claude-fable-5-1. Names are recorded telemetry, not externally validated product names.
| Repo | Claude model = files / total M tokens |
|---|---|
| Consulting | F51=31/481.548; H=113/88.872; O48=1/0.650; O5=28/543.797; O55=5/124.869; S5=86/114.739 |
| Ideas | F51=1/1.145 |
| Vividlist | O5=1/0.770 |
| _admisiones-y-carrera | O5=1/0.083 |
| alonso-resume | H=1/0.242; O5=1/4.838 |
| awesome-harness | F51=2/0.247; O5=2/1.465; O55=3/0.243 |
| boat | O55=9/42.184 |
| dallas-trip | H=3/3.390; O55=3/46.155; S5=7/36.206 |
| diego-resume | H=1/0.925; O5=2/5.338 |
| greyrock | F51=21/48.192; H=4/0.435; O48=2/0.768; O55=6/29.980; S5=1/1.444 |
| health-system | O5=1/21.119 |
| intrn | O5=2/0.853 |
| intrn-v2 | F5=2/38.918; F51=2/11.949; H=26/23.014; O5=3/43.625; S5=62/44.799 |
| jobs | F51=1/0.516; H=81/79.993; O48=3/0.791; O5=47/181.086; O55=29/442.174; S5=20/11.357 |
| lecturewatch-extension | F51=1/0.292 |
| rayovende | H=1/0.179; O55=1/1.885 |
| scholarships | O5=1/45.586 |
| school | F51=7/32.490; H=26/31.582; O5=33/575.338; O55=16/190.404; S46=3/0.267; S5=38/43.195 |
| unknown | F51=12/42.567; H=21/7.636; O48=1/0.011; O5=14/34.593; O55=17/68.148; S46=1/0.030; S5=4/0.692 |
| virality-pipeline | F5=14/234.472; F51=119/783.847; H=436/344.623; O48=120/30.397; O5=205/1099.472; O55=354/2610.332; S5=161/407.353 |
Files can appear under multiple models/cwds. Window-active Claude files: 2,184 = 142 roots + 2,042 agents. Task models strip the [1m] context suffix; CLI-offload models remain unknown absent a runtime banner. Claude wrapper tokens remain Claude usage, separate from Codex usage.

## Codex usage

Created sessions / native subagent sessions and input/cache/output in millions. Cached input is a subset of input. Tokens use window activity and contemporaneous model/cwd; created sessions use final recorded model. These denominators intentionally differ.
| Repo | Model | Sessions / subagents | Input M | Cached M | Output M |
|---|---|---:|---:|---:|---:|
| Consulting | gpt-5.5 | 1/1 | 0.637 | 0.582 | 0.011 |
| Consulting | gpt-5.6-sol | 97/50 | 60.352 | 55.929 | 0.546 |
| Consulting | gpt-6-astra | 178/83 | 158.491 | 149.464 | 0.791 |
| awesome-harness | gpt-6-astra | 3/1 | 3.385 | 3.066 | 0.011 |
| boat | gpt-5.6-luna | 15/0 | 15.228 | 13.916 | 0.122 |
| boat | gpt-6-astra | 26/11 | 40.114 | 38.298 | 0.115 |
| boat | gpt-6-sol | 9/2 | 8.926 | 8.442 | 0.049 |
| dallas-trip | gpt-6-astra | 12/8 | 11.394 | 10.949 | 0.061 |
| intrn-v2 | gpt-5.6-sol | 12/5 | 6.374 | 5.874 | 0.057 |
| jobs | gpt-6-astra | 158/77 | 142.993 | 135.860 | 0.659 |
| jobs | gpt-6-sol | 39/5 | 13.158 | 11.377 | 0.156 |
| scholarships | gpt-5.5 | 82/2 | 59.875 | 53.164 | 0.655 |
| school | gpt-5.6-sol | 13/7 | 15.961 | 14.806 | 0.081 |
| school | gpt-6-astra | 101/61 | 93.445 | 88.425 | 0.408 |
| school | gpt-6-sol | 3/0 | 0.264 | 0.204 | 0.002 |
| virality-pipeline | gpt-5.6-sol | 643/364 | 473.644 | 446.015 | 2.836 |
| virality-pipeline | gpt-6-astra | 741/361 | 505.150 | 480.484 | 2.264 |
| virality-pipeline | gpt-6-sol | 247/2 | 113.137 | 100.346 | 0.808 |
| virality-trends | gpt-6-astra | 39/19 | 16.489 | 15.349 | 0.095 |
| unknown/temp | gpt-5.3-codex-spark | 44/0 | 0.800 | 0.516 | 0.188 |
| unknown/temp | gpt-5.6-sol | 3/0 | 0.259 | 0.206 | 0.003 |
| unknown/temp | gpt-6-astra | 45/11 | 62.038 | 59.193 | 0.208 |
| unknown/temp | gpt-6-luna | 12/0 | 1.385 | 0.143 | 0.008 |
| unknown/temp | gpt-6-sol | 1222/0 | 110.468 | 77.767 | 1.865 |
| unknown/temp | unknown | 0/0 | 0.114 | 0.088 | 0.001 |
Additional zero-token sessions: virality-pipeline gpt-4o=3 and unknown=41; jobs unknown=3; gpt-6-astra alonso-resume=1, diego-resume=2, greyrock=3, rayovende=2. Unknown fixture model strings include pytest/json.tool/low. No in-window Codex-created Vividlist/intrn sessions. Temp/evaluation sessions remain unmapped. Tokens are telemetry, not monetary spend; 92.5% of input was cached.

## Git coverage and computation

| Repo | Commits | fix: | ≤72h same-path fixes |
|---|---:|---:|---:|
| virality-pipeline | 1219 | 118 | 105 |
| Consulting | 342 | 0 | 0 |
| intrn-v2 | 88 | 0 | 0 |
| jobs/crm (third-party) | 75 | 38 | 32 |
| virality-trends | 14 | 0 | 0 |
| scholarships | 11 | 0 | 0 |
| greyrock | 7 | 0 | 0 |
| jobs | 6 | 0 | 0 |
| awesome-harness | 2 | 0 | 0 |
| Vividlist | 1 | 0 | 0 |
| jobs/outreach | 1 | 0 | 0 |
Zero-commit repos: forclosurehomes, intrn, free-model-router, research-method, school, recovered/_clean/floorplan-to-3d, recovered/_clean/foreclosure-method. vozctl was not found; _dictado-voz has no Git root through depth four. All-repos coverage means discovered local repositories, not inaccessible/deleted/remotes. jobs/crm authors: grim (74), dependabot (1); excluded from Ro cohort.

- Discover Git from transcript cwd ancestors + Downloads directories; canonical Git common directory deduplicates worktrees. Read git log --all --since=2026-08-29T00:00:00Z --until=2026-10-01T00:00:00Z --format=... --name-only; strict committer-time filtering with three days of lookback. For conventional fix/revert, latest prior commit on any exact pathname ≤72h qualifies; rename identity/unconventional titles are not followed.
- Examples: virality 486997710081 touches src/spine/free_inference.py 0.11h after 6ed7458da559; d884e56b3ff5 touches tests/video_v2/test_run_chain_voiceover.py 3.71h after d6d4cc27f33a. This is temporal proximity, not task-level defect attribution; no taskset reworked/reverted labels were invented.

## Transcript methods and limits

- Claude: recursively read 3,055 JSONL files. Actual layout is project/root.jsonl plus session/subagents/agent-*.jsonl; record timestamp filtering; deduplicate Agent/Task by tool ID; join agentId from structured result or result text. No malformed JSON lines observed. Current baseline delegation excluded.
- Claude usage: last usage for (message.id, requestId), excluding synthetic model records; never add parent tool-result usage again. Repo uses first /Downloads/<project> cwd component; outside that map remains unknown. Task source context can be a subdirectory/project rather than a canonical Git repository.
- Codex: 8,389 August/September rollouts (~4.22 GB). Deduplicate copied fork usage by (turn_id, sorted total_token_usage fields), keeping earliest timestamp; sum counter deltas, use last_token_usage on counter reset. First session_meta ID identifies session despite inherited metadata; active turn_context model identifies token source. This approximates recorded use, not billing.
- Audit: final assistant text only; line-leading PASS/REJECT/ACCEPT or explicit Verdict. Conditional WITH FIXES becomes unknown, including PASS (ACCEPT WITH FIXES); nonblocking findings alone do not negate PASS. Earlier rounds inside one resumed agent are not separate audit observations. No attributable audit/git evidence means unknown. An audit task’s verdict labels the reviewed target, not reviewer competence.
- Tests: shell-tokenize Bash commands so quoted instructions to a CLI do not count as execution. Require a nonempty completed result; background-launch notices alone are insufficient. Source-edit metric requires call after final observed native edit. Match pytest/unittest, package test commands, cargo/go test, test-named Python/Node scripts, selftest and bash/sh script test. Direct audit tests can be true despite CLI offload; hidden/background-only execution is null. False means no recognized completed call in available direct transcript. Native edit tracking misses shell/backend writes.
- Taskset is the complete 2,032 linked-task census, preserving agent/model/outcome strata rather than balancing them. task_text is first 1,500 actual prompt characters; session comes from caller filename; evidence has original path:line/tool ID. Build outcomes remain unknown without attributable audit or Git proof; taskset has 0 reworked and 0 reverted, not proof that neither occurred.
- Strong repo/outcome imbalance and repeat audits prevent causal model ranking. Split evaluation by session/repo to prevent leakage; no observation establishes which alternative model would have succeeded. Actual Codex builds and true retry counts remain unknown.

## Top 5 changes, ranked by expected impact

1. **Emit a linked outcome receipt per unit.** Record task ID, builder/auditor IDs, resolved backend model/effort, commit hash, verdict history and retry number. Without these links, routing cannot be evaluated causally.
2. **Bind completion claims to execution receipts.** Persist command, exit code, test selection and output location after final edit; show skips/deselections and source-only fixes. Require backend runtime identity rather than wrapper/config assertions.
3. **Target regression checks at recurring failure classes.** Use bounded checks for malformed input, retries/crashes/idempotency, secrets and specification mismatches at the changed boundary. Retain independent audits and findings instead of treating PASS as defect-free.
4. **Create a clean router evaluation cohort.** Separate build/research/audit tasks, third-party clones, temporary benchmarks and mixed-model wrappers; keep unknowns and stratify by repo/risk. Current labels support observational triage, not counterfactual model choice or unknown=fail training.
5. **Measure context use before pruning it.** Record explicit prompt bytes separately from inherited/injected context and file-access receipts. Compare smaller prompts on matched tasks; current path heuristics cannot establish code-block waste.

## Validation and handoff

Validation completed: all 2,032 rows checked for exact source prompt prefix, required keys/enums, date window, unique tool IDs and outcome totals; 226-line report satisfies cap. Independent read-only review checked 19 prompt prefixes, verdict/model/test examples, arithmetic and Git claims; conditional verdict and test-matcher corrections applied. Only the two requested outputs were written; no source edits, commits, memory or resume-card changes.
Resume point: Phase 0 artifacts at docs/audits/2026-09-30/harness-baseline.md and .artifacts/router/taskset.jsonl; main-agent review next, model ranking still limited by missing causal/model receipts.
