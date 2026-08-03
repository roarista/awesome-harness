---
name: orient
description: THE PROCEDURE steps 1-3 in ONE call — RECALL (memgraph + mulch + MEMORY.md) then UNDERSTAND (front door, graphify + repowise, ponytail reuse ladder) then the REUSE/ADAPT/REJECT verdict and STOP/PLAN/BUILD gate. Run before writing code, before proposing something that may already exist, or when a request would add a feature/module/pipeline stage/schema/integration/dependency, materially refactor, or connect two subsystems. Replaces running `recall` and `codebase-first` separately. Skip for trivial one-line edits, docs-only wording, or a workflow already known this session.
---

<!-- MIRROR: copy of ~/.claude/skills/orient/SKILL.md (authoritative = the live ~/.claude copy). Re-sync: cp ~/.claude/skills/orient/SKILL.md skills/orient/SKILL.md -->

# orient — recall + understand + gate, one skill

> **Steps 1-3 of THE PROCEDURE** (`/awesomeharness`): ORIENT(0) -> **RECALL -> UNDERSTAND -> GATE** -> DECOMPOSE -> BUILD -> VERIFY -> PERSIST. On BUILD, hand off to `code-decompose`; on STOP, hand back to Ro.

Merges the old `recall` and `codebase-first` skills — they were sequential steps of one pipeline that nobody invoked separately (0 and 0 real invocations across 2,997 transcripts). One call now does the whole pre-code phase and ends in a single pasteable block.

## Part A — RECALL (memgraph + mulch + MEMORY.md)

1. `python3 ~/.claude/tools/memgraph/mem.py query "<topic from the task>"` — ranked full-text hit(s); read the top hit(s), `mem.py graph <name>` to pull linked records if load-bearing.
2. In a repo with `.mulch/`: `ml search "<topic>"` (or `ml prime` at session start) for the repo's own decisions/conventions/failures — memgraph is Ro's global memory, mulch is this repo's.
3. **Read budget: <=5 file reads.** Hop card-by-card (`mem query` -> top hit -> `mem graph` the one linked record) rather than bulk-reading; if 5 reads don't answer it, narrow the query, don't widen the reads.
4. Heavy recall (many hits, need several full bodies) -> spawn ONE `Explore` subagent to run the queries and return only the synthesis.
5. **Exit artifact: <=5 bullets** (prior decisions, known failure modes, any `scaffold-<category>.md`) — this is what feeds Part B as "prior art," not a transcript dump.
6. Missing index -> `python3 ~/.claude/tools/memgraph/build.py` first. Read-only; never mutate memory records as a side effect. Dangling `[[links]]` are expected TODOs, not errors.

## Part B — UNDERSTAND (front door -> map -> reuse ladder)

Owns the missing middle: `user goal -> front door/live state -> capability/reuse discovery -> proven gap -> decomposition`. Does NOT own builder routing, code audit, or state handoff.

**Run when:** the request adds a feature/module/service/pipeline stage/schema/integration/dependency/reusable helper; materially refactors or replaces a workflow; connects two subsystems; risks a second implementation of something that may already exist; or moves from research/design into code.
**Skip when:** genuinely trivial one-line edits; docs-only wording with no architecture claim; an already-known workflow. Even for a tightly-scoped urgent fix, still check callers/blast radius.

### Discovery ladder (stop at the first rung that FULLY satisfies the goal)
1. **Need** — does current behavior already satisfy this? Deterministic answer: `REPO=<repo> tools/chains/c2-prior-art.sh <concept> [name-regex]` — the three-leg codebase-first gate (structural/nominal/declared); never stop at leg 1. Feeds the REUSE/ADAPT/REJECT verdict below.
2. **Front door** — which files define current truth (architecture, commands, active handoff/state, forbidden/retired paths)?
3. **Map — graphify + repowise together, refresh first.** State the **search intent** before searching: `REPO=<repo> tools/retrieve.sh <intent> <query>` — intents `name enumerate exists blast slice verify history diagnose` (table + invariants: `tools/chains/README.md`). Then:
   - **repowise** (semantic/risk/history): `get_answer` (cite when `confidence: high`), `get_context(include=["callers","decisions","metrics"])`, `search_codebase`, `get_symbol`, `get_why`, `get_risk(targets[, changed_files])`.
   - **graphify** (structural, deterministic): `graphify update .` then `graphify query/explain/path`, `~/.claude/tools/graphify-blast.sh <touch-files>`.
   - Pairing: repowise to locate + understand + gauge risk, graphify to confirm exact structure + blast. Neither is authority — verify load-bearing claims against real source ranges. No map -> record `GRAPH: unavailable`, fall back to repo-native indexes / `rg`. Literal rename-every-callsite sweeps -> plain `Grep` regardless.
4. **Native/platform** — stdlib, runtime, framework, OS, DB, browser, external platform?
5. **Installed dependency** — already in the lockfile/manifest?
6. **Nearby workflow** — which active implementation does something similar (real symbols, not docs)?
7. **Downstream contract + blast radius** — who consumes the output, what identity/provenance/error/ordering assumptions do they impose, what's the blast radius? Pull this here, not as a build-time afterthought.
8. **Empirical probe** — smallest read-only/disposable check that distinguishes competing assumptions on real data.
9. **Gap** — what is actually missing after reuse/adaptation, named narrowly.
10. **Plan** — decompose only that residual gap.

### Context hygiene
Orchestrator frames the goal + hard constraints in <=8 lines and spawns ONE disposable discovery agent (usually the same one that decomposes next) — it does the heavy reads, does not edit, does not spawn. It returns only: **artifact path + a 5-10 line finding + the gate + the proposed next seam.**

### Required artifact — `.scratch/discovery/<slug>.md`
Small, well-localized changes may carry the same facts inline in the unit contract instead (exemption by SCOPE, not confidence).
```markdown
# <goal>: orient discovery
## Prior art (from Part A / RECALL)
- <<=5 bullets>
## Goal and constraints
- Desired behavior / Must not change / Current source-of-truth
## Orientation evidence
- Front door read / Map calls used (repowise + graphify, or GRAPH: unavailable) / Targeted source anchors (file:line)
## Capability inventory
| Candidate | Evidence | Covers | Missing | Verdict |
|---|---|---|---|---|
| stdlib/native/platform | ... | ... | ... | REUSE/ADAPT/REJECT |
| installed dependency | ... | ... | ... | ... |
| nearby workflow | ... | ... | ... | ... |
## Downstream and boundary map
- Producer / Consumers / Schemas / Identity-provenance-coordinate-error assumptions / Forbidden side effects
## Empirical gap proof
- Question tested / Probe / Observed result / Assumption accepted-rejected
## Decision
- Smallest rung that holds / Reuse-adapt plan / Residual gap / New files-deps-abstractions justified / Gate: STOP|PLAN|BUILD / Why
## Next seam
- Decompose / Verify before code
```

## STOP / PLAN / BUILD gate

**STOP** when: current behavior already satisfies the goal; a native/dependency feature covers it with config or one line; the capability lives in retired/forbidden architecture; the source of truth is contradictory enough that implementation would guess; or the downstream contract can't represent the result without a user/architecture decision.

**PLAN** when: reuse is clear but integration spans >1 boundary; an empirical assumption remains untested; a new schema/dependency/abstraction/public API/authority change/destructive migration is proposed; or candidate workflows disagree and need a design decision.

**BUILD** only when ALL hold: every plausible candidate has an evidence-backed verdict; the downstream consumer/trust boundary was inspected; the residual gap is explicit; the proposed edit is the smallest rung that holds; VERIFY is defined before code; any required design audit has zero blockers.

- **On STOP:** end the turn. Final summary = artifact path + existing capability that covers the goal + the one decision Ro must make. Write no code.
- **On PLAN:** surface the residual design question to Ro, then re-run this gate once he answers — do not proceed to `code-decompose`.

## Anti-theater checks (discovery is INVALID if any is true)
- Only evidence is "a map tool was run" with an unrelated/empty query.
- Candidates listed without a REUSE/ADAPT/REJECT verdict and reason.
- A rejection cites a filename/doc without opening the implementation.
- "No existing implementation" claimed without checking native/platform, dependencies, AND the nearest active workflow.
- Downstream consumers omitted for an output/schema/integration change.
- A new dependency/abstraction proposed without showing why lower ponytail rungs fail.
- A builder prompt says "follow existing patterns" without naming the pattern + source anchors.
- The artifact is raw notes with no decision/gate.

## Exit artifact — the block the caller pastes forward

This is what `understand-gate` (and the next agent) looks for — either the `.scratch/discovery/<slug>.md` path, or this block inline:

```
ORIENT
RECALL: <<=5 bullets prior art>
GATE: STOP | PLAN | BUILD
REUSE/ADAPT/REJECT: <verdict + one-line reason per candidate considered>
RESIDUAL GAP: <narrow statement, or "none — STOP">
NEXT SEAM: <decompose target, or the one question for Ro>
```

## What hooks can / cannot enforce (honesty note)
Hooks can require a `REUSE`-evidence **pointer** (a `.scratch/discovery/...` path or inline `REUSE:/ADAPT:/REJECT:`) on recognized mutating builder spawns. They cannot judge whether a map query was relevant, prove the agent understood returned symbols, or judge whether a rejection reason is correct. Mechanically requires a pointer; evidence QUALITY stays behavioral and audit-backed.
