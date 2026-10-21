---
name: awesomeharness
description: Ro's coding loop. Use on /awesomeharness or any build, refactor, audit.
---
Args = resume point; else STATE_CURRENT.md, no archives. Delegation: CLAUDE.md/AGENTS.md (router/pins). Scoped reads; `ml search` if needed; `~/.claude/tools/l1.py` and `~/.claude/tools/skeleton.py` before bodies. Graphify structure, Semgrep AST, `rg` text. Load specs/skills/MCPs only as needed.

0. Run `python3 ~/Downloads/awesome-harness/tools/state-distiller.py . --budget`. Prune (<=5 min): move detail, keep pointers/history. Only propose global/out-of-scope changes.
1. Ponytail first. Prove REUSE/ADAPT/REJECT on live files; STOP if covered.
2. Spec: CONTEXT / REUSE / CHANGE / GOAL / VERIFY. GOAL = end state/exclusions; VERIFY = fallible commands/pass criteria. Orchestrator owns FILE PLAN; builders stop/report unplanned files or budget overruns.
3. One routed builder/unit; no concurrent siblings in dirty trees. Without subagents, build/self-audit. Subagents get core rules from SubagentStart hook; don't paste into specs.
4. Distinct routed auditor, same spec:
CRITICAL: loss/security/secrets/money. HIGH: normal path wrong/invented API/unmet GOAL. MEDIUM: edge input/I/O/risky untested branch/test cannot fail. LOW: style.
VERDICT: REJECT for CRITICAL/HIGH, MEDIUM in money/auth/secrets/data-loss/prod data, or missing/failing VERIFY. PASS WITH FIXES for other MEDIUM/LOW; PASS only <=LOW. Fix every item; re-audit rejects. Check tree/output; reports are claims.
5. Unit + repo check-all, real output. Commit scoped; ml record; .now.md (NOW/LAST_VERIFIED/NEXT <=5 lines), STATE resume; push. Handoff: /compact-prep then /clear.

Satisfy `~/Downloads/awesome-harness/docs/quality-gates.md`; TS before handoff: `trellis audit . --json --baseline .artifacts/trellis/baseline.json` (exit 2 rejects); `trellis guide cleanup` to fix.
Reports: .artifacts/agent-reports/<task>.md; return <=8 lines: verdict/change/proof/risk/next/path; no logs/diffs/code. One final summary.

Never: source >200 lines (old cap 300; shrink touched; bypass needs Ro's yes); erase unrelated dirty work via force/reset/clean/stash/restore; unauthorized spend, prod mutation, messages/destruction.
