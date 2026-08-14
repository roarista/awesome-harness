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

## Non-negotiables

- Minimum code; no speculative abstractions or dependencies.
- Preserve unrelated dirty work; never force/reset/clean/stash/restore it away.
- No unauthorized spend, production mutation, messages, or destructive action.
- Keep stable instructions byte-stable for cache reuse, but optimize context bytes before cache rate.
- If invoked again in the same session, do not reload the body; the reinjection guard denies it.
