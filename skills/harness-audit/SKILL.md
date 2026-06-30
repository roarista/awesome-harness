---
name: harness-audit
description: Audit one repo's agent harness (CLAUDE.md, front-door docs, mulch, STATE, agent specs) against the REAL codebase and produce a proposal-only drift report. Use when the user says "audit the harness", "/harness-audit", "check <repo> for drift", or after a repo has run many sessions and CLAUDE.md may have gone stale. Read-only — never edits the live tree.
---

# Harness Audit — read-only drift detector (proposal-only)

This skill does, on demand, a CLAUDE.md-vs-reality reconcile:
a cheap read-only agent maps codebase reality, diffs it against what the harness *claims*,
and emits an evidence-cited proposal. **It NEVER edits the live tree.** the user reviews; a normal
session applies later, when the file is clean. This is deliberate — CLAUDE.md is the one file
every hot session reads, and self-grading auto-edits are how harnesses drift in the first place.

## Hard rules (non-negotiable)

1. **Proposal-only. Never edit the target repo.** Output goes to `~/Downloads/HARNESS_DRIFT_<repo>_<date>.md`. No writes inside the repo tree, ever — not even "obvious" fixes.
2. **One cheap read-only agent at a time** (this machine may run hot — `keep CPU fan-out low`). Use `gemini-agent` (free, large-context) or a single `Explore`/`general-purpose` agent. Do NOT fan out N agents per repo. Kill any worker process trees on finish.
3. **Evidence or it didn't happen (R1).** Every claimed drift cites `file:line` read THIS run. No finding from memory or assumption. If a check can't be run, mark it UNKNOWN — never guess.
4. **Don't race live sessions.** All 4 repos run live autonomous sessions (`[[feedback-concurrent-live-sessions]]`). Reading is fine; never write, branch, push, or run `ml compact`/`prune` against a repo whose loop may be appending. Note in the report if the tree is dirty (the apply step waits for clean).

## Inputs

- **Target repo path** (required): the absolute path to the repo to audit, e.g. `~/code/my-repo`.
- **Cross-repo baseline:** `~/.claude/memory/global_orchestration_rules.md` (the rules each CLAUDE.md should point to, not restate).

## Procedure

### 1. Scope (orchestrator, cheap)
Confirm the repo path. `cd` in and check: is the tree dirty (`git status --porcelain | head`)? Which branch / worktree? Record it — a dirty tree means "propose now, apply when clean."

### 2. Deterministic pre-pass (NO agent — trust the environment first)
Before spending an agent, run the deterministic tools and capture their output. These find drift mechanically, cheaper and more reliably than a model re-reading the tree. The agent's job (step 3) is then only the *judgment* the scripts can't do, seeded with this evidence.

- **CLAUDE.md-vs-disk drift:** `python3 ~/.claude/tools/check-all/claudemd_drift.py <repo>` — flags doc references to files/paths/commands that no longer exist. Add `--include-state` only if you want the volatile `.planning/STATE.md` checked too (noisy). This catches dead pointers (e.g. a `wiki/index.md` that was never generated) with zero model cost.
- **Code-map for the agent to query, not cold-read:** confirm `<repo>/graphify-out/graph.json` exists and is fresh — `graphify diagnose` or compare its `built_at_commit` to `git rev-parse HEAD`. If stale, NOTE it (don't auto-`graphify update` a live tree). Tell the step-3 agent to use `graphify query/explain/path --graph <repo>/graphify-out/graph.json` instead of grepping — fewer tool calls, less CPU (keep CPU fan-out low).
- Paste both outputs into the agent prompt so it verifies/extends rather than rediscovers.

### 3. Spawn ONE read-only mapper agent
Hand the agent the repo path, the step-2 deterministic output, and this checklist. It uses `graphify query` (not cold grep) to read code + harness docs and returns a structured reality-vs-claims diff. It writes nothing to the repo.

The mapper must check, with `file:line` evidence for each:

- **CLAUDE.md claims vs code reality** — entry points, pipeline/architecture descriptions, file paths, "what's in production" vs deploy status. Flag every claim that no longer matches the code.
- **Front-door freshness** — does the documented source-of-truth order (e.g. `.planning/STATE.md` → `START_HERE.md` → `CLAUDE.md`) still point at files that exist and are current? Is `.planning/STATE.md` stale (last-updated date) or oversized (>200KB → rotation candidate)?
- **Model routing accuracy** — does CLAUDE.md + the `.claude/agents/` specs route correctly: Opus decides/decomposes, **Codex gpt-5.5 codes** (NOT Sonnet), Sonnet reviews/audits, free Gemini for bulk? Flag any agent spec still naming a Sonnet (or other) coder. (`[[global-orchestration-rules]]`)
- **Loop/skill conventions** — does CLAUDE.md reflect loop-first (`/goal`) working, the decompose trio, R1/R2 tool-output-trust rules (where they apply), never-invent provenance (where it applies), compact-safe close?
- **Mulch health** — `ml` domain counts vs the 200/domain hard cap (over-limit = compaction candidate, idle-only); duplicate/near-duplicate domains; any documented `ml` flag that errors in practice (e.g. `--evidence`).
- **MCP/tool bloat** — `.mcp.json` servers actually used vs dead; tools/agents referenced in docs that no longer exist (and vice-versa).
- **Dead-doc burial** — root `.md` files that are pre-pivot relics fresh agents could mistake for current instruction.

### 4. Synthesize the proposal (orchestrator)
From the agent's findings, write `~/Downloads/HARNESS_DRIFT_<repo>_<YYYY-MM-DD>.md` with:
- **Summary** — N drifts found, severity split, tree-clean status.
- **Findings table** — each: claim/location (`file:line`) → reality → proposed fix → severity (BLOCKER/HIGH/LOW) → confidence.
- **Proposed edits** — concrete, ready to apply by a normal session when the file is clean. Quote the exact before/after where useful.
- **Idle-only queue** — mulch compaction, STATE rotation, doc archival (things that must wait for the loop to be idle).
- **Apply checklist** — ordered, with the "wait for clean tree / commit on session's branch / never push" guardrails.

The report lands in `~/Downloads/`, which `~/.claude/tools/memgraph/sources.txt` globs (`HARNESS_*`) — so it auto-indexes into the memory graph on the next `mem rebuild` / nightly cron and becomes recall-able. No extra step needed.

### 5. Hand back
Report: path to the report, the headline drift count, and the single highest-value fix. Do not apply anything. Offer to apply once the user confirms the target file is clean.

### 6. Record (optional)
If the audit surfaced a durable lesson (a recurring drift pattern), note it via `ml record` in the *appropriate repo when idle*, or in the harness-optimization memory. Don't inline transcripts.

## When NOT to use
- Mid-implementation of an unrelated task (this is a periodic hygiene pass, not a blocker).
- On a repo with no agent harness yet (nothing to drift from).
- As a way to auto-fix — it is structurally proposal-only. If the user wants edits applied, that's a separate, explicit, clean-tree apply step.

## Pilot order
Pilot on a repo whose harness is already clean (so any drift is real signal), then your highest-drift / highest-session-volume repos.
