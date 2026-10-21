# Global notes

## Messages and handoff
Interactive sessions: no intermediate chat, preamble, tool narration, subagent-return or compact-prep updates. Headless jobs may narrate if asked. Write urges as one caveman line in `$CLAUDE_JOB_DIR/tmp/pending.md`; expand pending lines in the final.
Final: thorough standalone changes, verification, pending work and decisions; elsewhere stay terse.
Every turn: sync memory/mulch, STATE resume and `.now.md` (NOW/LAST_VERIFIED/NEXT, <=5 lines). Final names saved files and exact resume point.

## Models and delegation
Main stays on Anthropic; never route it through third parties via ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN or ANTHROPIC_MODEL.
Main plans/routes/reviews; builders write code; read-only auditors audit. Main edits orientation/memory and tiny harness fixes only.
Route via `~/.claude/tools/route-model.sh "<task>"` (fmr route); obey its builder/auditor/model/effort/ID; DO-NOT-LAUNCH means inline/skip. `fmr status` shows live usage. Subscription only, no API.
After audit: `cd ${FMR_HOME:-~/Downloads/free-model-router} && .venv/bin/python -m fmr outcome <id> pass|pass_with_fixes|reject|reworked|abandoned`.
Code/review: best model with room; research/mechanical: cheapest; usable quota resetting soon first. No Codex reset credits without Ro's yes. Ro's model choice wins.
Cross-family audits: Codex-built -> router's Claude auditor (`opus` agent + its model); Claude-built -> codex-audit (another Claude auditor if Codex is exhausted). While Claude is scarce the Agent gate blocks Claude subagents unless the prompt carries the router `ID:`.
Agent types: Claude build/analysis = claude; Codex build = codex. Never general-purpose/Explore. Councils: one Codex + one Claude, optional Gemini third.

## Orientation and gates
If graphify-out/graph.json exists, run graphify query|explain|path before cold source reads.
Before code/review/pre-ship claims, invoke /awesomeharness ($awesomeharness in Codex).

## Ponytail
Stop at: not needed > stdlib > native platform > installed dep > one line > minimum code.
No unrequested abstractions/scaffolding/deps. Delete over add; fewest files, shortest diff.
Keep input validation, data-loss handling, security and explicit requirements.
Non-trivial logic leaves a runnable check. Mark shortcuts `ponytail: <ceiling + upgrade path>`.
