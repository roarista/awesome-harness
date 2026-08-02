# Decomposition quality forensic audit

## Scope and method

This was a **read-only** audit of the Claude Code history under `~/.claude/projects/` for the five named repositories. The on-disk corpus has grown since the request's inventory: **2,033 session JSONL files and 852 `subagents/*.jsonl` files** (the request said 2,025/843). Counts below use the on-disk corpus as of 2026-08-02.

I never loaded a whole transcript: Python 3 opened each JSONL and iterated one line at a time, JSON-decoding each line; large string fields were classified with regular expressions and only final subagent text was retained. I censused all 1,011 `Agent`/`Task` launches (361 virality-pipeline, 263 Vividlist, 149 Consulting, 162 awesome-harness, 76 intrn). The outcome sample is the **72 main-session launches classified as mutating builder work** after excluding research/explore/audit prompts (20/11/20/17/4 respectively). This is a deterministic content classifier, not a claim that every “write a markdown” task was production code.

Definitions matter: a field counts only when it is a heading at line start; “runnable VERIFY” requires a command/test/expected observable result, not a sentence saying “make sure it works”; evidence means a final subagent report contains an exit code, `rc=0`, a pass count, or equivalent real command output. The corpus does not reliably link every audit to one builder task, so relationship metrics below are explicitly labelled estimates where needed.

## 1. Spec quality

| Builder-prompt field | Present | Rate |
|---|---:|---:|
| CONTEXT | 12 / 72 | 16.7% |
| CHANGE | 13 / 72 | 18.1% |
| GOAL | 13 / 72 | 18.1% |
| VERIFY | 20 / 72 | 27.8% |
| REUSE | 8 / 72 | 11.1% |
| All five | 5 / 72 | **6.9%** |

**REUSE is omitted most** (64/72). The common pattern is no named unit headings at all (52/72); five prompts carried all five fields. This is the central leak: the current `docs/CODING_AGENT_PROMPTING.md` template is strong, but only 5/72 observed builder launches instantiated it.

The small complete-spec group was materially more auditable: all five supplied an intended verification path and four named real source anchors. The corpus does not preserve a stable builder→audit task ID for every async launch, so an exact “accepted first time” correlation would be false precision. The directional evidence is nevertheless clear: the identifiable rework prompts cluster in incomplete specs, not in the five complete ones.

## 2. VERIFY: stated, run, and evidenced

| Check | Count | Rate of 72 builders |
|---|---:|---:|
| Runnable command/assertion named in the prompt | 13 | 18.1% |
| Has a VERIFY heading but only vague wording | 7 | 9.7% |
| Final report claims completion/success | 55 | 76.4% |
| Final report pastes machine-verifiable output | 11 | 15.3% |
| Completion claim with no captured evidence | 48 | **66.7%** |

The 48/72 figure is the operational fake-completion rate: it does **not** prove dishonesty, but it does prove the orchestrator has no retained evidence on which to accept the claimed completion. Several reports say tests passed while the transcript contains neither command output nor an exit status; one complete Unit 3 explicitly reports the last test exited 1.

## 3. Audit outcomes

The broad census found **406 audit launches with a recovered final report**. Most use prose recommendations rather than a machine-readable `PASS`/`REJECT`, so a direct global denominator is unavailable. On the conservative, action-labelled subset (55 reports whose conclusion explicitly says pass/commit/clean or reject/fail/do-not-ship):

| Outcome | Count | Rate |
|---|---:|---:|
| PASS / commit / clean | 16 | 29.1% |
| REJECT / fail / do not ship | 39 | 70.9% |

This is an **actionable-audit sample, not a corpus-wide pass rate**; it over-represents adversarial audits and is therefore a useful estimate of the audit gate’s workload, not product defect prevalence.

Reject reports were multi-label coded (one audit can find several issues): tests/verification 93, scope/contract 77, reuse/duplication 47, concurrency/data integrity 42, invented API/schema 36, and security 24 (from 100 reports containing an explicit rejecting/failing recommendation). Common high-value catches were incorrect live-path wiring, under-reserved spend, race conditions, tests that did not exercise the promised case, and expansion beyond the unit boundary.

Follow-through is visible in chains such as virality Unit 3 and intrn geo/spend work: rejected work was often sent to a “Fix … audit findings” builder then re-audited. But the async history does not retain a universal join key; the defensible minimum is **9/72 builder prompts explicitly name rework/audit-fix/regression**, or 12.5%. I found no evidence that a rejected unit was silently relabelled PASS in the audited final reports; **the residual is unobservable, not clean acceptance**.

## 4. Rework rate and predictors

| Measure | Result |
|---|---:|
| Explicit second/third-pass/rework/audit-fix builder prompts | 9 / 72 | 12.5% minimum |
| Prompts touching a likely hub (`runner`, `pipeline`, `orchestrator`, `db`, `storage`, `config`, `index`) | 17 / 72 | 23.6% |
| Builder prompts with file:line anchors | 17 / 72 | 23.6% |
| Builder prompts with REUSE | 8 / 72 | 11.1% |

The strongest observable predictor is **missing decomposition itself**, especially missing REUSE and runnable VERIFY. Hub-file work is the next visible risk: it appears repeatedly in rework chains because the change affects callers, money/spend gates, or persistence. I did not infer “large diff” from text alone—many async transcripts do not retain a reliable diff size—so no numeric large-diff coefficient is claimed.

## 5. Reuse failures: retry duplication

Known current-state facts were used as a targeted trace: virality-pipeline has 13 hand-rolled retry sites while declaring but not importing `tenacity`; Vividlist has 48 hand-rolled retry loops and 14 named helpers.

| Repository | Corpus trace | Attribution verdict |
|---|---|---|
| virality-pipeline | The corpus shows `tenacity>=9.0` in the manifest and one existing `from tenacity import …`/`@retry` in `src/dissection/dissect.py`; builder prompts around retries generally describe bespoke loops or recovery scripts, not introducing a new production retry abstraction. | **0 attributable new duplicate sites found** in the sampled mutating-builder launches; this is a negative finding, limited to transcript evidence. |
| Vividlist | The transcript explicitly records a new transcript-scraper “12s pacing, backoff, skip-existing” loop and several recovery loops. The corresponding task is operational/research tooling, with no REUSE heading or named existing retry helper. | **1 attributable duplicate-pattern introduction** (operational script), plus no evidence it was checked against the 14 helpers. This does not prove it accounts for one of the 48 production loops. |

The important leak is not merely duplicate count: **64/72 prompts omit REUSE**, so an agent is frequently asked to solve a retry-like problem without being told that the repo already has a solution or that a declared dependency is unused. The prompting standard’s `REUSE` pointer is therefore directly supported by the data.

## 6. Invented APIs

In the rejecting-audit corpus, **36 audit reports contain an invented/nonexistent API, parameter, signature, schema, or undefined-symbol finding** (multi-label case count; not a count of individual calls). Examples include wrong function signatures/parameters, live-path arguments never forwarded, and contract/schema assumptions contradicted by source.

Only **17/72 (23.6%)** builder prompts carry any `file:line` anchor and only **8/72** supply REUSE/source grounding. The log format does not reliably join all 36 findings to their originating task, so it cannot honestly supply an exact anchored-vs-unanchored odds ratio. The traceable complete prompts explicitly say “read the real signatures” and prohibit invented parameters; the failure-heavy general population leaves the builder to discover APIs. That is the causal mechanism the prompt standard already identifies, and the observed missing-anchor rate is its measurable exposure.

## What to change in the template

1. Make `REUSE` and **at least one real `path:line` API/exemplar anchor** a hard required field for every mutating builder prompt; do not allow “follow existing patterns” as a substitute.
2. Make `VERIFY` executable and acceptance-gated: require one exact command plus pasted `rc=0`/test output; otherwise force the final status to **UNVERIFIED**, never “done.”

These two changes target the largest measured holes (88.9% missing REUSE and 66.7% evidence-free completion claims) before adding more process.
