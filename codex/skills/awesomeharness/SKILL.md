---
name: awesomeharness
description: Activate Ro's context-light coding procedure, evidence-led tool routing, bounded builder/auditor delegation, verification, and persistence. Use when Ro invokes awesomeharness or /awesomeharness, or for substantive implementation, refactors, and audits in an awesome-harness repository.
---

# awesomeharness

Use this contract for the rest of the session. Read the repository's root `CLAUDE.md` when it is a compact project router, then `STATE_CURRENT.md` when present; do not routine-load historical STATE or archives.

## Route

- Recall: targeted `ml search <term>` or one domain prime.
- Inventory: the injected `.codemap`; do not reopen it wholesale.
- Structure/reach: Graphify query/explain/path.
- Complete AST occurrences: Semgrep.
- Literal text, slices, history: `rg` / git.
- Load specs, skills, MCPs, and plugins only when the task needs them.

## Code loop

1. State `GOAL / NOT-GOAL / DONE-WHEN / PROOF`.
2. Prove `REUSE / ADAPT / REJECT` against live files; stop if existing behavior covers the goal.
3. Decompose units as `CONTEXT / REUSE / CHANGE / GOAL / VERIFY`.
4. For each non-trivial unit, launch one bounded builder, wait, then launch a distinct auditor against the same spec. Main-agent ability is not a reason to skip either launch. Never run sibling builders concurrently in a dirty checkout.
5. Fix and re-audit until no high/critical finding remains; independently inspect the tree and verification output.
6. Run the unit check, repository gate, and `check-all`; claims require real output.
7. Commit scoped files, record durable learning in Mulch, update the repository's compact resume card, and push.

If subagents are unavailable, preserve the same separation sequentially: finish the spec, build, then re-read the diff with independent-auditor eyes.

## Agent discipline

Every delegated prompt requires scoped reads and a complete report at `.artifacts/agent-reports/<task>.md`. Return only a decision-complete summary of at most eight lines with verdict, evidence, verification, risk, next action, and report path—never raw logs or diffs.

## Quality Gates

Every green is a claim — a passing test, an empty review, a design that "looks right". Make each one
earn itself. (Source: the 26 quality gates, Glitch Cat Club, 2026-08-16; each gate is a real defect
that got past someone without it.)

- **Before a fix:** reproduce it through the exact door the user used, or don't fix it. Treat the
  report as a symptom and re-check whatever it claims is fine. Find the commit that introduced it,
  how long it has been live, and what a real user experiences when it fails. Before a rework, list
  every behaviour this area promises and mark each proven-by-test / proven-by-history / assumed. Then
  sweep the codebase for siblings — a fix closes the class or it isn't closed.
- **Attack the design before building it:** walk it as if built (first run, re-run, resume, retry
  after failure). List every caller mechanically with search, not judgment. Grep docs and README for
  sentences the change makes untrue. Ask what a death between two writes leaves behind and whether
  the next run heals it. Try disk-full, no network, slow machine, synced folders. Probe parsers and
  path checks with real inputs — spaces, quotes, CRLF — never lab-clean ones. Trace where this kind
  of data crosses boundaries, not where the pattern happened to appear. Ask how the area would look
  built with this requirement on day one; the right rework deletes more than it adds.
- **Tests that can't lie:** at least one test must produce the failure the way the machine produces
  it — no mocking the broken part, no hand-planted state. Mutation-proof each test: make the change
  that should break it, watch it fail by name, revert, watch it pass. For each planned test ask
  "would this be green on the broken version?" Explain a red before touching it.
- **Review that finds things:** review with no memory of writing it, then with a different model.
  Give each reviewer one lens (data loss / races / tests green by construction / rewrite it and say
  if yours is simpler). "No findings" must list what was attacked and found sound. Reproduce a
  finding before acting on it *and* before dismissing it. Every finding is fixed now or gets a
  written reason and a tracked home; severity sets order, never whether. If a fix turns out wrong,
  full stop — explain why every earlier gate missed it before resuming.
- **Before it ships:** walk the whole flow under real conditions through the real entry point. Run it
  twice, then inspect the files and data it left behind, not the output. Prove any claim about the
  user experience on a fresh machine, never the dev machine.

## Non-negotiables

- Minimum code; no speculative abstractions or dependencies.
- Preserve unrelated dirty work; never force/reset/clean/stash/restore it away.
- No unauthorized spend, production mutation, messages, or destructive action.
- Keep progress terse and the final summary complete.
