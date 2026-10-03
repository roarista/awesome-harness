---
name: awesomeharness
description: Activate Ro's context-light coding loop, tool routing, sub-agent discipline, verification, and persistence.
---
# awesomeharness

Args summary = resume point; else `STATE_CURRENT.md`, never archives. Delegation: CLAUDE.md.
Tools: `ml search` if needed; `~/.claude/tools/l1.py`, `skeleton.py`, then bodies; graphify structure, Semgrep AST, `rg` text.

## Code loop
1. Prove REUSE / ADAPT / REJECT on live files; STOP if existing code covers it. Ponytail ladder first.
2. Units spec `CONTEXT / REUSE / CHANGE / GOAL / VERIFY`. GOAL: observable end state + out of scope. VERIFY: commands that can fail + what passing looks like. Files ≤200 lines.
3. One builder per unit, router's pick; no concurrent siblings in a dirty checkout.
4. Audit cross-family, same spec, shared rubric:
   - CRITICAL data loss/security/secret leak/money · HIGH wrong on a normal path, invented API, GOAL
     unmet · MEDIUM edge input, unhandled I/O error, untested risky branch, test that cannot fail · LOW style.
   - `VERDICT: REJECT` if any CRITICAL/HIGH, any MEDIUM touching money/auth/secrets/data-loss/prod
     data, or VERIFY not run/failing; `PASS WITH FIXES` if only other MEDIUM/LOW; `PASS` only if ≤LOW.
   Re-audit until not REJECT; fix every item. Verify reports.
5. Unit check + repo gate, real output. Commit scoped, `ml record`, `.now.md` (NOW/LAST_VERIFIED/NEXT ≤5 lines) + STATE resume point, push.
After a handoff use /compact-prep then /clear.

## Sub-agents
Scoped reads; full result in `.artifacts/agent-reports/<task>.md`; return ≤8 lines (verdict, change, verification, risk, next, path). No raw logs/diffs/code. One full final summary.

## Quality gates (full: ~/Downloads/awesome-harness/docs/quality-gates.md)
- Fix: reproduce via user's door; find introducing commit; list proven vs assumed; close the class.
- Design: walk re-run/resume/retry; callers by search; stale docs; crash between writes heals.
- Tests: real failure unmocked; mutation-proof; explain a red first.
- Review: fresh eyes, other model, one lens each; reproduce findings.
- Ship: real entry point twice; inspect what it left behind.

## Non-negotiables
- No source file over 200 lines: split to a new module first. 300 caps pre-existing files; touching one shrinks it. Ratchet bypass only with Ro's yes.
- Preserve unrelated dirty work; never force/reset/clean/stash/restore it away.
- No unauthorized spend, production mutation, messages, or destructive action.
