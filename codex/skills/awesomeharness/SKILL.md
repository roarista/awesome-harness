---
name: awesomeharness
description: "Ro's coding loop: builder/auditor split, verification, persistence. Use on $awesomeharness or any build, refactor, audit."
---
# awesomeharness

Args summary = resume point; else `STATE_CURRENT.md`. Delegation: AGENTS.md.
Tools: `ml search`; `~/Downloads/awesome-harness/tools/{l1,skeleton}.py`, bodies last; graphify structure, Semgrep AST, `rg` text. Load specs/skills/MCPs only when needed.

## Code loop
1. Prove REUSE / ADAPT / REJECT on live files; STOP if existing code covers it. Ponytail ladder first.
2. Units spec `CONTEXT / REUSE / CHANGE / GOAL / VERIFY`. GOAL: end state + out of scope. VERIFY: commands that can fail + what passing looks like.
   Orchestrator owns file structure (FILE PLAN in code-decompose). Builders never create unplanned files or split code; if a file would exceed its budget they stop and report back.
3. One builder per unit, router's pick; no concurrent siblings in a dirty checkout. No subagents: build, self-audit.
4. Audit (auditor per Delegation), same spec, shared rubric:
   - CRITICAL data loss/security/secret leak/money · HIGH wrong on a normal path, invented API, GOAL
     unmet · MEDIUM edge input, unhandled I/O error, untested risky branch, test that cannot fail · LOW style.
   - `VERDICT: REJECT` if any CRITICAL/HIGH, any MEDIUM touching money/auth/secrets/data-loss/prod
     data, or VERIFY not run/failing; `PASS WITH FIXES` if only other MEDIUM/LOW; `PASS` only if ≤LOW.
   Re-audit until not REJECT; fix every item. Agent reports are claims: independently check tree and command output.
5. Unit check + `~/.codex/tools/check-all/check_all.sh`, real output. Commit scoped, `ml record`, `.now.md` (NOW/LAST/NEXT ≤5 lines) + STATE resume point, push.
After a handoff use $compact-prep then /clear.

## Agents
Scoped reads; full result in `.artifacts/agent-reports/<task>.md`; return ≤8 lines (verdict, change, proof, risk, next, path). No raw logs/diffs/code. One full final summary.

## Quality gates (full: ~/Downloads/awesome-harness/docs/quality-gates.md)
- Fix: reproduce via user's door; find introducing commit; list proven vs assumed; close the class.
- Design: walk re-run/resume/retry; callers by search; stale docs; crash between writes heals.
- Tests: real failure unmocked; mutation-proof; explain a red first.
- Review: fresh eyes, other model, one lens each; reproduce findings.
- Ship: real entry twice; inspect leftovers.

## Non-negotiables
- No source file over 200 lines; 300 caps pre-existing files, touching one shrinks it. Ratchet bypass only with Ro's yes.
- Preserve unrelated dirty work; never force/reset/clean/stash/restore it away.
- No unauthorized spend, production mutation, messages, or destructive action.
