---
name: awesomeharness
description: Activate Ro's context-light coding loop, tool routing, sub-agent discipline, verification, and persistence.
---

# awesomeharness

Use this contract for the rest of the session. The `.codemap` is already injected; do not reload or
re-derive it. Read `STATE_CURRENT.md` when present, otherwise `.now.md`. Never read historical STATE
or archive files during routine orientation.

## Route

- Recall: targeted `ml search <term>` or one domain prime. Do not prime everything.
- Inventory: injected `.codemap`.
- Structure/reach: Graphify query/explain/path.
- Complete AST occurrences: Semgrep.
- Literal text, slices, history: `rg` / git.
- Repowise: CLI only where a named workflow already consumes it; never enable its MCP by default.
- Load specs, skills, MCPs, and plugins only when the task needs them.

## Code loop

1. State GOAL / NOT-GOAL / DONE-WHEN / PROOF.
2. Prove REUSE / ADAPT / REJECT against live files; STOP if existing behavior already covers it.
3. Decompose into units: CONTEXT / REUSE / CHANGE / GOAL / VERIFY.
4. Run one Codex builder per unit. Never run sibling builders concurrently in a dirty checkout.
5. Give the same spec to an independent auditor; fix and re-audit until no HIGH/CRITICAL remains.
6. Run the unit check, repository gate, and `check-all`; claims require real output.
7. Commit scoped files, record durable learning in Mulch, update the repo's single resume card, push.

## Sub-agent discipline

Every spawn prompt says: keep reads scoped and context lightweight; be concise; write the complete
result to the repo's agent-report folder (default `.artifacts/agent-reports/<task>.md`); return only a
decision-complete summary of <=8 lines plus the report path. The summary includes verdict, essential
finding/change, verification, risk, and next action. Never paste raw logs, diffs, code, or research
into the parent transcript.

The orchestrator says nothing while agents run or return. If the interface requires progress, use
<=4 words. Wait for all requested agents, then give one complete final summary. Agent reports are
claims until the orchestrator independently verifies the relevant tree and command output.

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
- Keep stable instructions byte-stable for cache reuse, but optimize context bytes before cache rate.
- If invoked again in the same session, do not reload the body; the reinjection guard denies it.
