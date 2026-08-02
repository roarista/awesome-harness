# 11 — Does the harness pay for itself?

**Thesis under test (Ro):** *"pareciera que por usar el harness estamos gastando MÁS y siendo MENOS
eficientes cuando debería ser de la otra manera."*

**Method.** Read-only. Streaming pass over `~/.claude/projects/` — 2,861 project-root session JSONL
(1.93 GB) plus 935 subagent transcripts under `<project>/<session>/subagents/`. Nothing was `cat`ed;
every file was decoded line-by-line. Token counts come from `message.usage`
(`input_tokens + cache_read + cache_creation + output`), i.e. real billing records, not char/4
estimates — except for per-component attribution, where the component's own text is measured at
chars/4 and then amplified across the API calls it survives (compaction boundaries reset the
amplification). No source file was edited. This report is the only file written.

**Prior audits are taken as given, not re-derived**: 02 (17 validated false-claim incidents),
03 (~75% of subagent returns dropped on arrival), 04 (hook cost, amplification, turn-1 floor),
05 (~60 redirect events, 1 in 8 messages), 06 (280/304 MCP tools never invoked), 07 (zero recorded
blocking-hook fires; caveman compliance 35.7%), 08 (66.7% evidence-free completion claims),
09 (recall precision 11.3%).

---

## 0. THE HEADLINE, BEFORE THE CAVEATS

Three numbers, all measured, all new:

| | |
|---|---|
| **Harness injections into the main context** | **96.5 ktok raw/session → 14.70% of billed main-session input tokens** (converges with audit 04's 15.7%, derived independently) |
| **The delegation ritual (subagent fleet)** | **1,798 M tokens vs 1,664 M for the parents that spawned them — 51.9% of all tokens, 55% of cost-weighted spend.** Entirely invisible to audit 04, which only measured the main window. |
| **Cache economics** | **93.1% of main-session input tokens are `cache_read`**, billed at ~0.1×. The harness's 14.7% *token* share is only ~12.3% of main-session *dollars*, and ~5.5% of total dollars once subagents are in the denominator. |

**So the loud thing (hooks) is not the big thing (subagents).** Audit 04 correctly identified the
biggest line item *we control inside the window*. This audit finds a line item ten times larger
that sits outside it.

---

## 1. THE NATURAL EXPERIMENT — and how weak it really is

### 1.1 The population

Of 2,861 project-root sessions with ≥1 human turn, **2,832 are not the thing Ro is complaining
about**: 1,641 are `previz_vlm_claude-*` SDK CAD workers (1–2 prompts), ~100 are `/private/tmp`
mutation-test harnesses, and ~1,090 are virality-pipeline batch invocations. The interactive
population — **≥3 real typed user turns, non-worker — is 29 sessions**, spanning 2026-07-11 to
2026-08-01, 1,103 user turns, 1,687 M billed input tokens, ~58 M tokens/session.

Everything below is that 29-session cohort. n=29 is the entire universe, not a sample — but it is
still n=29, and every cohort split below produces arms of 5–20. **There is no statistical power
here. Read every table as a description of what happened, never as an estimate of an effect.**

### 1.2 Four candidate contrasts, and what each is actually contaminated by

I could not find a clean harness-on / harness-off contrast, because **the hooks live in
`~/.claude/hooks` and `~/.claude/settings.json` — they are global.** Every session in the corpus,
including the ENGL2328 essay sessions and the health-system sessions, fires the same injectors.
What varies by repo is only CLAUDE.md, per-repo skills, and MCP server config. That single fact
caps how strong any of these contrasts can be.

**A. `/awesomeharness` invoked vs not** (9 vs 20). The closest thing to an on/off switch for the
*behavioral* harness — THE PROCEDURE only exists if the skill body is in context.
*Confound, and it is fatal:* the skill is invoked on the long, hard, multi-day sessions. Median
turns 66 (invoked) vs 7 (not). **Harness intensity is caused by task difficulty, not the reverse.**

**B. Harness repo vs non-harness repo** (20 vs 9). virality-pipeline / Vividlist / Consulting /
awesome-harness / intrn vs ENGL2328 / health-system / `~` / `-`.
*Confound:* the non-harness arm is essay-writing and note-keeping; the harness arm is code. These
are different jobs, not the same job with a different harness. Also, per §1.2, both arms get hooks.

**C. Time — early (Jul 11–26, n=10) vs late (Jul 27–Aug 1, n=19).** The harness grew through July.
*Confound:* so did the projects. Edits/turn tripled across the boundary (0.19 → 0.61) because the
work shifted from research to build. A harness-vs-time comparison is mostly a research-vs-build
comparison wearing a date.

**D. Turn-1 context floor: SDK worker sessions (31.2 ktok, n=1,641) vs harness repos (45–61 ktok).**
*This is the strongest contrast in the corpus,* because it is measured at call 0 before any task
difficulty can act, and n is large on one side. It isolates the standing per-session configuration
cost. Its limitation is the opposite one: it measures only the floor, and says nothing about what
happens after turn 1.

### 1.3 What the cohorts show

Rates per 100 user turns. `Mtok/turn` is billed input tokens per user turn (i.e. amplified — the
true cost of a turn). `durable%` = share of sessions ending with a write to `.now.md` / `STATE.md` /
`memory/` / `.mulch`.

| cohort | n | turns | Mtok/turn | Mtok/edit | harness tok/sess | 1st-ctx | redirect | self-corr | rework | interrupt | durable% |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **A** `/awesomeharness` invoked | 9 | 629 | **1.76** | **3.33** | 166,634 | 58,062 | 0.8 | **6.4** | **8.9** | **1.6** | **89%** |
| **A** not invoked | 20 | 474 | 1.24 | 3.97 | 64,164 | 50,204 | 0.6 | 1.3 | 5.3 | 2.7 | 60% |
| **B** harness repo | 20 | 881 | 1.69 | 3.50 | 117,648 | 55,183 | 0.8 | 5.0 | 9.0 | 2.4 | 75% |
| **B** non-harness repo | 9 | 222 | 0.94 | 3.73 | 47,781 | 49,678 | 0.5 | 0.9 | 0.9 | 0.9 | 56% |
| **C** early ≤07-26 | 10 | 456 | 1.40 | 7.50 | 112,844 | 51,105 | 0.7 | 0.4 | 2.9 | 2.4 | 60% |
| **C** late ≥07-27 | 19 | 647 | 1.64 | **2.67** | 87,081 | 55,801 | 0.8 | 6.8 | 10.5 | 1.9 | 74% |

**Reading it honestly, in both directions.**

*Supports the thesis (cost):* every harness-heavy arm costs more per turn. `/awesomeharness`
sessions cost **42% more per user turn** than sessions without it (1.76 vs 1.24 Mtok). Harness repos
cost **80% more per turn** than non-harness repos. The turn-1 floor is **23 ktok higher** in a
harness repo than in a bare SDK session (54.3k vs 31.2k) — that is pure configuration, paid before
Ro types a character, and it is the cleanest causal-ish number in the report.

*Refutes the thesis (efficiency):* on the only per-unit-of-output measure available,
**harness-heavy sessions are cheaper per durable edit, not more expensive** — 3.33 vs 3.97 Mtok/edit
for `/awesomeharness`, and 2.67 vs 7.50 Mtok/edit late vs early. Interrupts are *lower* in
harness-heavy arms (1.6 vs 2.7 per 100 turns). Durable-close-out compliance is much higher
(89% vs 60%).

*Neither:* self-correction and rework rates are 3–5× higher in harness-heavy arms. This does **not**
mean the harness causes errors. Per audit 02, self-correction markers count only *documented*
corrections — a session that self-corrects more may simply be a session that is being audited more
and lying less. It is equally consistent with "the harness surfaces errors" and with "the harness
sessions are harder." The metric cannot distinguish these, and I will not pretend otherwise.

**Verdict on the natural experiment: the cost side is real and measurable; the efficiency side is
not identified.** `Mtok/edit` treats an `Edit` call as a unit of value, which it is not — audit 08
found 66.7% of builder units claim completion with no evidence, so an edit is not even evidence of
correct work. The honest summary is that **harness-heavy sessions demonstrably cost more per turn,
and there is no measurement in this corpus that shows them producing more or better output.**

---

## 2. THE COST SIDE — per component, measured

Per interactive session (n=29). `raw` = tokens of the component's own text. `amplified` = raw ×
API calls it survives (reset at compaction boundaries) — the real re-send cost. `%billed` = share
of that session's total billed input tokens.

| component | fires/sess | raw tok/sess | amplified/sess | %billed |
|---|--:|--:|--:|--:|
| `PreToolUse:Agent` — ROUTING POLICY | 40.9 | 17,211 | 1,067,252 | **1.83%** |
| `skill_listing` (inflated by ~20 custom skills) | 5.5 | 13,965 | 1,208,839 | **2.08%** |
| compact summary re-injection | 2.1 | 13,293 | 1,545,334 | **2.66%** |
| `mcp_tool_names` (deferred-tool deltas) | 5.6 | 9,467 | 1,019,158 | 1.75% |
| `hook:northstar` | 34.0 | 9,710 | 682,712 | 1.17% |
| `hook:resume_handoff` | 4.4 | 9,281 | 873,333 | 1.50% |
| `mcp_instructions` (server preambles) | 4.5 | 7,339 | 782,078 | 1.34% |
| `agent_listing` (subagent roster) | 3.4 | 5,977 | 666,789 | 1.15% |
| `skill_body:awesomeharness` | 1.2 | 5,207 | 593,933 | 1.02% |
| `SessionStart:compact` | 11.0 | 4,264 | 515,031 | 0.89% |
| `hook:caveman` (PER-TURN CONTRACT) | 37.5 | 2,708 | 175,851 | 0.30% |
| `hook:graphify` | 32.4 | 2,353 | 159,175 | 0.27% |
| `hook:recall` (🧠 memory) | 21.7 | 1,996 | 142,990 | 0.25% |
| `SessionStart:startup` / `:resume` / `:clear` | 11.5 | 2,904 | 275,719 | 0.48% |
| `hook:manifest` (HOOK-INTEGRITY) | 5.2 | 1,149 | 104,707 | 0.18% |
| `nested_memory` | 0.4 | 961 | 72,283 | 0.12% |
| `skill_body:compact-prep` | 0.2 | 626 | 110,728 | 0.19% |
| `hook:understand_gate` / `builder-fence` | 4.8 | 415 | 24,731 | 0.04% |
| `PostToolUse:Agent` | 36.1 | 219 | 18,453 | 0.03% |
| `hook:checkall_gate` / `:checkpoint` / `:gitsync` / `:repowise` / other | 7.5 | 444 | 23,434 | 0.04% |
| **HARNESS SUBTOTAL** | **~205 injections** | **96,539** | **8.6 M** | **14.70%** |

Standing overhead in plain terms:
- **~205 hook/skill/config injections per session.** More than four per user turn.
- **Turn-1 floor 54.3 ktok median in a harness repo** vs 31.2 ktok in a bare SDK session — a
  **23 ktok standing surcharge**, paid before work starts, then amplified across every call.
- **Turns to first productive action: median 1** — in all 29 sessions, and 0/29 sessions failed to
  reach one. The harness does *not* delay the first useful action. That is a genuine refutation of
  one plausible version of the thesis.
- Total tokens to a completed unit of work: not honestly computable. Audit 08 established that
  66.7% of builder units carry no evidence of completion, so "completed unit" has no reliable
  marker in the logs. This is a measurement gap, not a number I am withholding.

### 2.1 The line item audit 04 could not see

Audit 04 measured the main window. It is the wrong denominator.

| | tokens | cost-weighted units¹ |
|---|--:|--:|
| 22 interactive parents | 1,664 M | 360 M |
| their 911 subagents | **1,798 M** | **440 M** |
| **subagent share** | **51.9%** | **55.0%** |

¹ input ×1.0, cache-write ×1.25, cache-read ×0.10, output ×5.0 — the standard Anthropic ratio shape.
Absolute dollars are not claimed; the ratio is what matters.

**~41 subagents per interactive session, median 1.42 M tokens and 26 API calls each.** Fleet
composition: 557 `general-purpose`, 95 `codex:codex-rescue`, 83 `opus` (auditor), 65
`code-unit-agent`, 61 `Explore`, 27 `code-audit-agent`, 13 `decompose-agent`.

Each one re-boots its own preamble: **median subagent boot floor 32.6 ktok**, 29.5 M/cohort — 1.6%
of subagent spend, which is small, so the cost is not the boot. The cost is that a subagent is a
whole second agent that reads, greps, thinks, and writes for 26 API calls.

**The framing number:** the entire harness injector budget (8.6 M amplified tokens/session) equals
**six subagent launches**, out of ~41. Deleting every hook, skill listing, and MCP block from the
main window buys back less than 15% of the subagent fleet.

---

## 3. THE BENEFIT SIDE — the hard half, done rather than skipped

Each proxy is stated with its weakness *first*, because every one of them is weak.

**3.1 Self-correction rate ("me equivoqué", audit 02's method).**
*Weakness: counts documented corrections only. A rising rate is consistent with either more errors
or more honesty. It is a marker of the audit process, not of the defect rate.*
6.4 per 100 turns in `/awesomeharness` sessions vs 1.3 without; 6.8 late vs 0.4 early. **Direction is
against the harness; interpretation is unavailable.** Not usable as evidence either way.

**3.2 Rework / second-pass builder launches (audit 08).**
*Weakness: audit 08's own floor is 9/72 = 12.5% because async transcripts retain no builder→audit
join key. My regex count is a different, looser floor.*
8.9 vs 5.3 per 100 turns (AH vs not); 10.5 vs 2.9 (late vs early). Again against the harness, again
confounded by the build/research shift. **Not usable.**

**3.3 User redirects and interrupts (audit 05: ~60 events, 1 in 8 messages).**
*Weakness: `[Request interrupted]` is a keystroke, not a judgement — Ro interrupts to redirect and
to save money and to change his mind.*
This is the **one proxy that favors the harness**: interrupts run 1.6/100 turns in `/awesomeharness`
sessions vs 2.7 without, and 1.8 vs 2.6 in the substantive-only split. Explicit textual redirects are
flat (0.8 vs 0.6). So: **weak, consistent, small association between the behavioral harness and
fewer hard stops.** With n=9 vs 20 this is one session away from vanishing.

**3.4 Unverified completion claims.**
Done-claims carrying machine-verifiable evidence: **31% cohort-wide**, 33% with `/awesomeharness`
vs 31% without — **no association whatsoever**. Audit 08's independent measure on builder units
(33.3% evidenced) lands in the same place. **The harness has demonstrably not moved the number it
was most explicitly built to move.** This is the single clearest negative finding in the report,
and it is a genuine null, not an absence of data: both arms are measured, and they are identical.

**3.5 Durable-write ritual at session end.**
89% of `/awesomeharness` sessions vs 60% without; 100% vs 80% among substantive sessions.
*Weakness: this is nearly tautological — the skill instructs the ritual, so compliance measures
compliance, not value.* Audit 09 supplies the missing half and it is unflattering: 70% of
post-compaction sessions show no evidence of reading `.now.md`/`STATE.md`, and 0 contradictions were
confirmed in either arm. **The ritual is performed; nothing shows it being consumed.**

**3.6 Work redone in a LATER session.**
*I could not measure this.* There is no join key between a file touched in session A and a fix in
session B; matching by path is dominated by normal iteration. The rework-prompt counts in 3.2 are
the closest floor available and they are within-session. **Stated as a gap, not answered.**

**3.7 The one component with positive evidence.** Audit 08's audit-gate sample: 39/55 action-labelled
audits REJECT, with 93 test/verification findings, 77 scope/contract, 47 reuse/duplication, 42
concurrency, **36 invented-API/schema**. Audit 02's 17 validated incidents include exactly this class.
The auditor subagents are **110 of 909 transcripts (12%)** and are the only harness component in the
corpus that can point at specific defects it caught before they shipped.

---

## 4. VERDICT — does the harness pay for itself?

**Ro's thesis is CONFIRMED on cost and NOT ESTABLISHED on efficiency.**

*Confirmed:* running the harness is associated with **+42% tokens per user turn** (`/awesomeharness`
vs not) and a **+23 ktok standing floor** per session versus an unharnessed session. Both are
measured. And the harness's own most-repeated rule — delegate — accounts for **55% of all spend**,
of which audit 03 says ~75% is dropped on arrival unread.

*Not established:* nothing in this corpus shows the harness making sessions *less* efficient at
producing output. Per durable edit it is cheaper, not dearer. Time-to-first-productive-action is
turn 1 in every session. Interrupts trend down. The correct statement is not "the harness makes us
slower" — it is **"the harness costs a lot and cannot show what it buys."**

The observational caveat is load-bearing and I will not soften it: `/awesomeharness` is invoked on
hard sessions. Hard sessions cost more. **Every cost number above is contaminated by that selection
in the direction that flatters the thesis.** The clean numbers are the two that are measured before
any task difficulty can act: the 23 ktok turn-1 floor, and the 14.70% injection share.

### Per-component ledger

| component | cost/session | measured benefit | verdict |
|---|--:|---|---|
| **`PreToolUse:Agent` ROUTING POLICY** | 17.2 k raw / 1.07 M amp (1.83%) | none. 40.9 identical re-pastes/session; audit 07 finds no behavior change | **NET NEGATIVE — cut** (evidence-of-absence: it is byte-identical every fire) |
| **`skill_listing`** | 14.0 k / 1.21 M (2.08%) | none; catalogue, not instruction | **NET NEGATIVE — inject once, not 5.5×** |
| **MCP surface** (`mcp_tool_names` + `mcp_instructions`) | 16.8 k / 1.80 M (3.09%) | 24 of 304 tools ever invoked (audit 06); repowise MCP 7 sessions, 49% failure | **NET NEGATIVE — cut to per-project** |
| **`hook:northstar` + `resume_handoff`** | 19.0 k / 1.56 M (2.67%) | none demonstrated; 34 fires/session, >1 per turn, largely unchanged text | **NET NEGATIVE — rate-limit to 1/turn, diff-suppress** |
| **`hook:recall` (memory injector)** | 2.0 k / 0.14 M (0.25%) | 11.3% precision, 74.1% re-derivation (audit 09) | **NET NEGATIVE — cut.** Cheap, but 88.7% of it is wrong, and wrong context is worse than none |
| **`hook:caveman`** | 2.7 k / 0.18 M (0.30%) | 35.7% compliance (audit 07); Ro pasted the spec verbatim 4× anyway (audit 05 T4) | **NET NEGATIVE — cut or make it a hook that blocks** |
| **`hook:graphify`** | 2.4 k / 0.16 M (0.27%) | graphify: 7.3% adoption, 82.1% immediate fallback to Grep/Read (audit 06) | **NET NEGATIVE — cut** |
| **`hook:manifest` (HOOK-INTEGRITY)** | 1.1 k / 0.10 M (0.18%) | 11 broad-drift alerts, no attributable remediation (audit 07) | **NET NEGATIVE — cut** |
| **Blocking guards** (main-edit-guard, now-gate, filesize-cap, irreversible-pause, phantom-edit-guard, …) | ~0.4 k / 0.02 M | **0 recorded blocking fires; 0 `hook_error` attachments corpus-wide** | **UNMEASURABLE.** Cutting these is cutting on *absence of evidence* — and note that one of them (irreversible-pause) is Ro's direct fix-request after the Canvas incident (audit 05 case 3). **Keep the ones guarding irreversible actions; cut the advisory ones.** |
| **`skill_body:awesomeharness`** | 5.2 k / 0.59 M (1.02%) | +29 pt durable-ritual compliance, −1.1/100t interrupts, **0 pt** on evidenced completion | **AMBIGUOUS, lean keep** — cheapest per unit of behavior it does move; selection-confounded |
| **`skill_body:compact-prep`, `check-all`** | 0.6 k / 0.11 M | check-all: 10 invocations, 80% acted on, produced actionable drift output (audit 06) | **WEAK POSITIVE — keep, don't mandate** |
| **Memory write layer** (`.now.md` / STATE / `memory/` / `ml`) | ~0 in-context | 89 memory files for 2,025 sessions; 16% close-out compliance; 25% stale; 70% not read post-compaction | **UNMEASURABLE / leaning negative — see §6 for the experiment** |
| **Delegation ritual — builders** (`general-purpose`, `codex-rescue`, `code-unit-agent`: ~717 of 909) | **~49 M tok/session, ~44% of all spend** | ~75% of returns dropped on arrival, 2.49% quoted verbatim (audit 03) | **THE LARGEST COST IN THE SYSTEM, and it is unmeasurable as a benefit** — this is where the work happens, so its output cannot be separated from the harness's mandate to delegate. **Do not cut; instrument.** |
| **Delegation ritual — auditors** (`opus`, `code-audit-agent`: 110 of 909, ~12%) | ~6 M tok/session | 39/55 actionable audits REJECT; 36 invented-API catches; 93 verification findings | **NET POSITIVE — the only component with named defects it caught. Expand this, not the builders.** |

---

## 5. THE COUNTERFACTUAL FLOOR — a minimal harness

Keep only what has demonstrated value or guards an irreversible action. Everything else goes.

**KEEP:** one SessionStart contract (~800 tok, replacing startup+resume+clear+caveman+northstar) ·
the `awesomeharness` skill body, injected once and idempotent (5.2 k) · `skill_listing` once (2.5 k) ·
per-project MCP only (~3.4 k) · `agent_listing` once (1.8 k) · one `RESUME HANDOFF` per session
(2.1 k) · `nested_memory` (1.0 k) · irreversible-action guards only (~0.4 k) · the **auditor**
subagent lane, expanded.

**CUT:** `PreToolUse:Agent` routing policy (fold into the agent definitions where it already
belongs) · 4.5 of 5.5 `skill_listing` re-injections · 33 of 34 `northstar` fires · `recall` ·
`caveman` · `graphify` · `manifest` · `PostToolUse:Agent` · global MCP servers · 10 of 11
`SessionStart:compact` re-injections.

| | today | minimal | saved |
|---|--:|--:|--:|
| raw harness tokens / session | **96,539** | **≈18,700** | **−77,800 (−81%)** |
| amplified harness tokens / session | **8.60 M** | **≈2.06 M** | **−6.54 M** |
| share of billed main-session input | **14.70%** | **≈3.6%** | **−11.1 pts** |
| share of *total* (main + subagent) cost-weighted spend | ~5.5% | ~1.4% | **−4.1 pts** |

**The number: a minimal harness costs ~18.7 ktok/session raw, against ~96.5 ktok today — an 81%
cut of the injection layer, worth ~11% of main-session tokens and ~4% of total spend.**

And the number that matters more: **~4% of total spend is the entire prize from cutting the whole
injection layer.** One avoided unnecessary subagent launch (median 1.42 M tokens) is worth 22% of
that prize. **If the goal is to spend less, the injection layer is the wrong target and the subagent
fleet is the right one** — 41 launches per session, ~75% of their output discarded on arrival.

---

## 6. WHAT WOULD ACTUALLY SETTLE THIS

Everything above is observational. Three experiments, in order of value:

1. **Subagent necessity ledger (highest value).** Before each `Task`, the orchestrator writes one
   line: what question this launch must answer, and what it will do with the answer. After the
   return, a Stop hook records whether that question was answered and whether the answer changed the
   next action. This turns the 55%-of-spend line item from unmeasurable into measured, and it is the
   only experiment that can move a number that big.
2. **A/B the injectors.** Alternate sessions with `HARNESS_INJECT=0` (routing policy, northstar,
   recall, caveman, graphify off; everything else identical), same repo, same week. Compare
   evidenced-completion rate, interrupts, and tokens/turn. n=20 per arm is reachable in three weeks
   and would settle §3 properly.
3. **Memory-layer read receipt.** Log every read of `.now.md`/`STATE.md`/`memory/*` and every
   recall injection that is subsequently quoted or acted on. Audit 09 measured precision; nobody has
   measured whether the durable-write ritual is ever *consumed*. If it isn't within a month, the
   write side is a candidate to cut on evidence rather than on absence of it.

**Explicit note on delete-over-add:** of the cuts in §5, `PreToolUse:Agent`, `skill_listing`
re-injection, the MCP surface, `recall`, `graphify`, and `caveman` are cut on **evidence of
absence** — each is measured, and each shows no effect on a metric it was built to move. The
blocking guards are cut (partially) on **absence of evidence** — zero recorded fires means we never
observed them working *or* failing. I recommend keeping the irreversible-action ones anyway, because
their failure mode is the Canvas incident and their cost is ~400 tokens.
