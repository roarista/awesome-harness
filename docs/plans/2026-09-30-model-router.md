# free-model-router — plan, 2026-09-30

Status: Phase 0 + Laya spike RUNNING. Decisions made (bottom). Repo: ~/Downloads/free-model-router (local, not yet on GitHub).

## What it does

You describe a task. The router returns a decision and the reason for it:

```
route "add retry to the uploader and verify it"
→ difficulty 3/5 · type build+verify · risk low · agents 2 (builder + auditor)
→ BUILD  claude opus-5.5  effort medium   (codex weekly 84% used, resets Oct 6, so save Codex)
→ AUDIT  codex gpt-5.x    effort medium
→ skills: code-decompose, check-all
→ WHY: best SWE-bench score in your stack for this task type; Claude 5h window is at 20% and resets in 2h
```

Only models you can reach through your **subscriptions** are candidates. No API keys and no pay-per-token usage.

## Facts verified today (not assumed)

| Thing | Finding | Source |
|---|---|---|
| Laya | A 421M ModernBERT (English) or 322M mmBERT (multilingual) **classifier**. It does not generate text. It answers typed questions in one forward pass: `choice` (label + probabilities), `score` (ordinal rubric), `noul` (calibrated P(true)). It takes about 33 ms per call, runs on CPU or MPS, uses `pip install laya`, Apache-2.0, and has a 512-token context. | github.com/NandhaKishorM/laya, HF card |
| "Jev" | **Jev is a separate competing model** in Laya's benchmark (Jev scores 0.727 vs Laya's 0.766). The local model you mean is Laya. | Laya README |
| Laya limits | It was trained on email, ticket and content triage. It has **never been tested on "how hard is this coding task."** It knows nothing about LLMs or benchmarks. Its built-in `Router` chooses among Laya's own checkpoints, not among LLMs. | same |
| Codex usage | Readable locally. `~/.codex/sessions/**/rollout-*.jsonl` → `rate_limits.primary.used_percent / window_minutes / resets_at`, plus `plan_type` and `credits`. **Right now: 84% of the weekly limit used, resets Oct 6 20:07, plan `prolite`, credits 0.** | your machine |
| Claude usage | Claude Code sends `rate_limits.five_hour.used_percentage` and `seven_day.used_percentage` to the statusline. Your `~/.claude/statusline-command.sh` already reads them, but nothing saves them, so other tools can't read the value. | your machine |
| Sakana Fugu | It presents "a multi-agent system delivered as one model." TRINITY assigns Thinker, Worker and Verifier roles across several LLMs. Conductor learns coordination strategies with RL. **Worth stealing:** the role split (we already have builder and auditor) and learning the routing from outcomes instead of hand-writing it. | sakana.ai/fugu |

## Design: Laya rates the task, deterministic code picks the model

Laya should **not** choose the model. It can't know that a model released last week is good at Rust. It is only used to rate the task. A plain, readable Python policy makes the choice. That keeps every decision explainable and lets `update-model` change behaviour by editing data, not retraining.

```
task text ──► Laya (local, ~40ms) ─► features {difficulty 1-5, type, risk, multi_agent, skills}
                                         │
stack.yaml (your plans) ─┐               ▼
models.yaml (cards)  ────┼──►  policy.py (deterministic, ~150 lines)  ──► decision + WHY receipt
usage.py (live %) ───────┘               │
                                         ▼
                              decisions.jsonl  ◄── outcome (audit PASS/REJECT, retries, your correction)
```

### Components

1. **`stack.yaml`** comes from an `init` step that asks which plans you have. Today that would be Claude (tier?) and ChatGPT Pro-lite with Codex CLI. Models outside your stack never show up as candidates.
2. **`models.yaml`** holds one card per model: provider, which plan grants it, effort levels, benchmark numbers with **source URL and date** (SWE-bench Verified, Terminal-Bench, Aider polyglot, LMArena), strengths, and relative usage burn per plan.
3. **`update-model "<name>"`**: you say "a new model dropped, update the harness". A Codex research agent fills a card with sourced numbers and shows it as a diff for you to approve. Any number without a source is rejected. It never auto-merges.
4. **`usage.py`** reads the Codex rollout files (already working) and a Claude usage cache. The cache needs a one-line `tee` in your statusline script that writes the `rate_limits` JSON to `~/.cache/free-model-router/claude.json`. It computes **headroom vs time to reset**:
   - lots left and a reset soon → spend freely ("use it or lose it")
   - little left and the reset far off → conserve
5. **Laya features** come from typed questions:
   - `score` for difficulty
   - `choice` for task type (build / audit / research / mechanical / design)
   - `noul` for irreversible risk (money, auth, data loss)
   - `noul` for whether it needs more than one agent
   - `choice` for top skills
6. **`policy.py`** works in four steps:
   - Filter the stack by a capability floor for the difficulty.
   - Rank by benchmark score for the task type.
   - Weight by your preference: **code and review get best quality first**, research and mechanical work get cheapest first.
   - Penalize scarce usage.

   Existing hard rules stay as guardrails: your override always wins, and irreversible work always gets an audit.
7. **Harness wiring**: `tools/route-model.sh` calls `free-model-router route --json` when it's installed. Otherwise it falls back to today's regex table, so nothing breaks.

### What happens to the "always Codex" rule

It becomes a **weight that follows live usage**, not an absolute rule. With Codex at 84% and 6 days until reset, the router would move builds to Claude this week. A hard "always Codex" rule can't do that. CLAUDE.md already says "the router is the source of truth", so this keeps your rule's intent (spend the cheap credits) without its failure mode. It needs your sign-off because it changes the rule written in CLAUDE.md.

## Phases (each one has a gate, and a phase that fails its gate is not built on)

- **Phase 0. Baseline the harness (your "how is the harness doing" question). Run this first.** Mine the last 30 days of transcripts for:
  - per build: model, audit verdict, retries, reverts, whether tests ran;
  - how often the main session's claims about the code turned out wrong (an existing memory says unverified claims are the root cause);
  - how often subagents got context they didn't need.

  Output: a scorecard plus a **labelled task set** (task text → which model → outcome). The router needs this set to be evaluated against anything better than vibes. Run by codex (analysis) and codex-audit, report only.
- **Phase 1. Usage and stack, no AI.** `stack.yaml`, `usage.py`, the statusline tee, and `models.yaml` filled for current Claude and OpenAI models with sources, plus a `free-model-router status` command. This is useful on its own because routing can see your quotas.
- **Phase 2. Laya scorer plus policy.** Install Laya locally and run it against the Phase 0 task set. **Gate:** Laya's difficulty and type features must beat the current regex router at predicting good outcomes. If they don't, keep the regex features and Laya stays out. It is not shipped on faith.
- **Phase 3. `update-model` command** plus a check that warns when a card's benchmarks are older than 60 days.
- **Phase 4 (parked, later). Learning loop and context engineering.** Use `decisions.jsonl` outcomes to re-weight the policy, and if there's enough data, fine-tune Laya's `typed-decisions` head on your own labels. After that, a "context pruner" that uses Laya `noul` to judge "is this file or memory relevant to this subtask" before passing context to subagents. Your instinct on this is right, but it needs Phase 0 data first.

## Repo layout (its own GitHub repo, and plugged into awesome-harness)

```
free-model-router/
  free-model-router/{cli.py, usage.py, policy.py, laya_features.py, cards.py}
  data/{models.yaml, stack.example.yaml}
  tests/test_policy.py     # fixtures: usage scarce/abundant × difficulty → expected pick
  README.md
```

Awesome-harness gets: the `route-model.sh` delegation, an `awesomeharness` skill line ("route with `free-model-router route`"), and the statusline tee.

## Decisions (Ro, 2026-09-30)

1. Stack = **Claude Max 20x + ChatGPT Pro-lite (Codex, "10x")**. Nothing else. No API.
2. Repo name **free-model-router**.
3. "Always Codex" is **retired** — global CLAUDE.md now says the router decides from live usage.
4. Phase 0 approved and launched.

## New facts (2026-09-30, verified on Ro's machine)

- **Codex full usage incl. limit-reset credits is readable**: `codex app-server` (stdio JSON-RPC) → `initialize` → `account/rateLimits/read` returns `rateLimitsByLimitId` + `rateLimitResetCredits` {availableCount, credits[{status, grantedAt, expiresAt, title:"Full reset"}]}. Today: codex weekly 85% used, resets Oct 6; **2 full resets available, expire Oct 22 and Oct 29**. There is also `account/rateLimitResetCredit/consume` (router must NEVER call it without Ro's yes).
- **gpt-5.6-luna has its OWN quota** (`base_model_inference`, name `gpt-reserve`, 0% used, separate weekly window). So Luna does **not** drain the main Codex limit — it is a near-free tier for cheap classification/triage, the natural rival to Laya.
- Rollout files' `rate_limits` are per-session snapshots and can be stale/out of order (saw 84% and 31% with the same resets_at) — app-server is authoritative; rollouts are the offline fallback.
- **Claude usage now persisted**: `~/.claude/statusline-command.sh` writes `{ts, rate_limits}` to `~/.cache/free-model-router/claude.json` on every render (backup at `.bak-2026-09-30`). The installer must do this patch for every user (merge into an existing statusline, or install ours if none).

## Router policy additions

- **Reset-aware spending**: a reset credit is extra quota with an expiry. Effective Codex headroom = (100 − used) + 100 × resets usable before expiry. Expiring-soon resets push work TO Codex; router proposes "consume a reset now" only when the window is at ~100% and a reset expires before it'd be used anyway.
- **Bakeoff, Laya vs gpt-5.6-luna as the task rater** on the Phase 0 taskset: accuracy at predicting outcome, latency, and quota drain (luna's `gpt-reserve` used% before/after). Also an ensemble: several Laya calls in parallel (different question phrasings / checkpoints) majority-voted — only kept if it beats one batched call.
- **Improving Laya**: (1) temperature-fit calibration on Ro's labels (cheap, built in), (2) fine-tune the typed-decisions head on taskset labels, (3) distill: have luna/opus label 1-2k historical tasks, train Laya on those labels so the free local model inherits the expensive one's judgment.

## Rater decision (Ro, 2026-10-01)

- **Laya stays the live rater**: it is local and costs no plan quota. Luna does have its own quota, but Ro still uses it.
- **gpt-5.6-luna is the teacher, not the runtime.** Luna labels about 1-2k historical tasks once, offline. Laya is then fine-tuned on those labels plus the real build→audit outcomes. After that, routing costs zero quota.
- **"Heavier, same path"** means bigger encoder checkpoints in the same family, tried in order: `laya-typed-decisions` (fine-tuned, 0.766), then a ModernBERT-large head trained on our labels. Each is kept only if it beats the smaller one on the held-out taskset.
- **Parallel Laya instances are out** (MPS crash). Use one batched call with all questions, and run different checkpoints one after another.
- Until fine-tuning lands, use Laya for **type and skill** only. **Difficulty and risk** stay rule-based, because zero-shot difficulty is flat.
- **Router output carries the gates.** Each decision returns the agent, model and effort, plus a spec template (CONTEXT / REUSE file:line / CHANGE / GOAL / VERIFY), the required skills and a review lens. Reason: docs/audits/2026-10-01/gate-adherence.md shows rules embedded in tools get followed and skills don't.

## Backlog seen while dogfooding (2026-10-01)
- **Wait vs downgrade.** Claude 5h was at 96% with 14 minutes to reset, and the router sent two code builds to gpt-reserve (a cheap tier). For quality_first tasks, when the best provider resets within about 30 minutes, the router should offer "wait N min for <model>" next to the downgrade.
- **gpt-reserve as a builder** is being measured on two small units: the labeler and the route-model.sh delegation. Record the outcomes with `fmr outcome`.
