# Global notes

## Message discipline (ALL projects)
- **Zero intermediate chat** in interactive sessions (background/headless jobs may narrate if their prompt says so): no preamble, narration or status lines between tool calls, when a sub-agent returns, or during compact-prep. Writing to files is fine.
- **Urge to narrate:** append ONE caveman line to `$CLAUDE_JOB_DIR/tmp/pending.md`, then expand all pending lines in the final message.
- **Final message = thorough standalone summary** (what changed, verification, pending, decisions); Ro reads only this, long is wanted. Everything else terse.
- **Every turn ends compaction-safe:** `.now.md` (NOW/LAST_VERIFIED/NEXT, ≤5 lines) + STATE resume point + memory/mulch synced; the final message says what was saved and the exact resume point.

## Models
- Main session stays on Anthropic. Never set `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_MODEL` to route it through a third party.

## Delegation (main orchestrates, does not build)
- Main plans, routes, reviews. Code writes go to a builder subagent, audits to a read-only auditor. Main edits only orientation files (`.now.md`, STATE, memory) and tiny harness tweaks.
- Router picks builder, auditor, model, effort from live subscription usage (Claude Max 20x + ChatGPT Pro-lite/Codex; no API): `~/.claude/tools/route-model.sh "<task>"` (wraps `fmr route`; prints NECESSITY/BUILDER/AUDITOR/SPEC/`ID:`; `fmr status` shows usage). DO-NOT-LAUNCH = do it inline or skip. After the audit: `cd ${FMR_HOME:-~/Downloads/free-model-router} && .venv/bin/python -m fmr outcome <id> pass|pass_with_fixes|reject|reworked|abandoned`.
- Spend: code + review → best model with headroom; research/mechanical → cheapest; a quota resetting soon with room left goes first. Never use Codex reset credits without Ro's explicit yes. Ro naming a model beats the router.
- Audits always cross-family, one shared rubric (in the auditor definitions): Codex-built → `opus48-audit`/`opus`; Claude-built → `codex-audit` (other Claude auditor if Codex is exhausted).
- Agent types: Claude builds/analysis → `claude`; Codex builds → `codex`; never `general-purpose`.
- Councils / second opinions: one Codex + one Claude voice (Gemini optional third).

## Graphify
With `graphify-out/graph.json`, orient via `graphify query|explain|path` before cold source browsing.

## Quality gates
Before code, review, or a pre-ship claim, invoke `/awesomeharness` (`$awesomeharness` in Codex); don't restate the gates here.

## Ponytail (lazy senior dev)
- Stop at the first rung that holds: not needed → stdlib → native platform → installed dep → one line → minimum code.
- No unrequested abstractions, scaffolding or new deps. Deletion over addition; fewest files, shortest diff.
- Never simplify away input validation, data-loss error handling, security, or anything explicitly asked for.
- Non-trivial logic leaves one runnable check. Mark deliberate shortcuts `ponytail: <ceiling + upgrade path>`.
