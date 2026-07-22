---
name: codebase-first
description: Companion to Ponytail — run BEFORE writing code whenever a request would add a feature/module/pipeline stage/schema/integration/dependency/reusable helper, materially refactor or replace a workflow, connect two subsystems, or move from research/design into code. Ponytail asks "can we solve this with less code?"; codebase-first asks the question just before it — "what does this repo ALREADY have that solves or constrains this?" — and returns a compact, evidence-backed REUSE/ADAPT/REJECT decision plus a STOP/PLAN/BUILD gate. Skip for trivial one-line edits, docs-only wording that makes no architecture claim, or running an already-known workflow.
---

# codebase-first — prove reuse before you build

Ponytail governs *how little code* to write. This skill governs the step **just before**: prove what the repository already has, what can be reused, and what gap actually remains — so decomposition and building start from evidence, not assumption. The deliverable is not "ran a code map." It is a tiny proof: these are the relevant existing systems, what each can/can't do, who consumes the result, one real check that confirmed or disproved the key assumption, and the smallest missing piece. If the proof shows the capability already exists, the correct result is **no new code**.

This owns only the missing middle:

`user goal → front door/live state → capability/reuse discovery → proven gap → decomposition`

It does NOT own builder routing, code audit, factory/check-all, Graphify indexing, or state handoff — existing mechanisms keep those.

## When to run / skip

Run automatically, before decomposition, when a request would: add a feature, module, service, pipeline stage, schema, integration, dependency, or reusable helper; materially refactor or replace a workflow; connect two subsystems; introduce a second implementation of a capability that may already exist; or proceed from research/design into code.

Skip for: genuinely trivial one-line edits; docs-only wording that makes no architecture claim; running an already-known workflow. Even for an urgent tightly-scoped fix where the failing symbol and regression check are already proven, still inspect callers/blast radius.

## Discovery ladder (stop at the first rung that FULLY satisfies the goal)

1. **Need** — Does this need building at all, or does current behavior already satisfy it?
2. **Front door** — Which files define current truth: architecture, commands, active handoff/state, forbidden/retired paths?
3. **Map / Graphify** — What does the repo-native code map identify for THIS task? (see fallback below)
4. **Native / platform** — Does stdlib, the language runtime, framework, OS, DB, browser, or external platform already provide it?
5. **Installed dependency** — Is it in the lockfile/manifest or an already-installed adapter?
6. **Nearby workflow** — Which active implementations do something similar? Inspect real symbols, not just docs.
7. **Downstream contract** — Who consumes the output, and what identity/provenance/error/ordering/coordinate assumptions do they impose?
8. **Empirical probe** — What smallest read-only or disposable check distinguishes competing assumptions on real data?
9. **Gap** — What is actually missing after reuse/adaptation? Name it narrowly.
10. **Plan** — Decompose only that residual gap.

## Context hygiene

- Orchestrator frames the goal + hard constraints in **≤8 lines** and spawns discovery; it does not read the implementation itself.
- **ONE disposable discovery agent** does the heavy reads. It is usually the *same* agent that will then decompose — do not stand up two agents that reread the same code. Parallel specialists only when the task crosses independent domains (e.g. producer, downstream consumer, platform/dependency); they merge into ONE artifact.
- The discovery agent **does not edit and does not spawn**.
- It returns to the orchestrator ONLY: **artifact path + a 5-10 line finding + the gate + the proposed next seam.** Not the raw reading.

## Graphify: first-with-fallback (never wedge on it)

If `graphify-out/graph.json` exists: run a **task-specific** `graphify query` first, `graphify explain` for candidate modules/symbols, `graphify path` when producer/consumer or old/new relationships matter. Graphify is orientation, not authority — **verify every load-bearing conclusion by opening the exact source ranges.** Record the exact commands in the artifact.

If no usable graph exists: do **not** block the task on Graphify. Record `GRAPH: unavailable|stale|insufficient` and use repo-native indexes/LSP, then `rg --files` and narrowly-scoped `rg`, plus dependency manifests/lockfiles and front-door docs. Do not build a graph as part of an unrelated urgent fix unless repo policy requires it.

## Required artifact — `.scratch/discovery/<slug>.md`

For non-trivial changes, write this (or use the repo's existing scratch/research convention). Small, well-localized changes may instead carry the same facts **inline in the unit contract** — the exemption is by **SCOPE, not confidence**.

```markdown
# <goal>: codebase-first discovery

## Goal and constraints
- Desired behavior:
- Must not change:
- Current source-of-truth/handoff:

## Orientation evidence
- Front door read:
- Graph/map commands (or GRAPH: unavailable|stale + fallback used):
- Targeted source anchors (file:line):

## Capability inventory
| Candidate | Evidence | Covers | Missing | Verdict |
|---|---|---|---|---|
| stdlib/native/platform | file/doc/command | ... | ... | REUSE/ADAPT/REJECT |
| installed dependency | manifest + symbol | ... | ... | ... |
| nearby workflow | file:line | ... | ... | ... |

## Downstream and boundary map
- Producer:
- Consumers:
- Schemas/return types:
- Identity/provenance/coordinate/error assumptions:
- Forbidden promotion or side effects:

## Empirical gap proof
- Question tested:
- Probe/fixture/real input:
- Observed result:
- Assumption accepted/rejected:

## Decision
- Smallest rung that holds:
- Reuse/adapt plan:
- Residual gap:
- New files/dependencies/abstractions justified (why lower rungs fail):
- Gate: STOP | PLAN | BUILD
- Why:

## Next seam
- Decompose:
- Verify before code:
```

## STOP / PLAN / BUILD gate

**STOP** when: current behavior already satisfies the goal; a native/platform/dependency feature covers it with config or one line; the capability lives in a retired/forbidden architecture and the user must pick a new direction; the source of truth is contradictory enough that implementation would guess; or the downstream contract can't represent the result without a user/architecture decision.

**PLAN** when: reuse is clear but integration spans more than one boundary; an empirical assumption remains untested; a new schema/dependency/abstraction/public API/authority change/coordinate conversion/destructive migration is proposed; or candidate workflows disagree and need a design decision.

**BUILD** only when ALL hold:
- every plausible existing candidate has an evidence-backed verdict;
- the downstream consumer and trust boundary were inspected;
- the residual gap is explicit;
- the proposed edit is the smallest rung that holds;
- VERIFY is defined before any code;
- any required design audit has **zero blockers**.

## Anti-theater checks (a discovery is INVALID if any are true)

- The only evidence is "Graphify was run" (or the query was unrelated/empty/only `graphify update`).
- Candidates are listed without a `REUSE/ADAPT/REJECT` verdict and a reason.
- A rejection cites only a filename or design doc without opening the implementation.
- "No existing implementation" is claimed without checking native/platform features, dependencies, AND at least the nearest active workflow.
- Downstream consumers are omitted for an output/schema/integration change.
- A new dependency or abstraction is proposed without showing why the lower Ponytail rungs fail.
- A builder prompt says "follow existing patterns" without naming the pattern and source anchors.
- The design audit only checks formatting and does not rerun at least one evidence lookup or probe.
- The discovery agent designs production code before proving the gap.
- The artifact is long raw notes with no decision/gate — the detailed reading stays disposable; the artifact is *synthesis*.

## What hooks can / cannot enforce (honesty note)

Hooks can require a `REUSE`-evidence **pointer** on recognized mutating builder calls — either a `.scratch/discovery/...` path or a short inline `REUSE/ADAPT/REJECT` statement — and re-inject a "codebase-first before decompose" reminder on build-intent prompts. Hooks **cannot** judge whether a Graphify query was relevant, prove the agent opened/understood returned symbols, or judge whether a rejection reason is correct. So the honest claim is: **mechanically requires a reuse-evidence pointer on recognized builder calls; evidence QUALITY is behavioral and audit-backed — never "mechanically guarantees reuse."**
