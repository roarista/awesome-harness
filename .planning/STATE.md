# Harness Enforcement Audit State

## NOW (Summary)
Harness enforcement audit DONE + per-repo hooks stripped (reversible .harnessbak). 

KEY FINDING: External codex/glm CLI builders bypass ALL write-side hooks (only the spawning Bash line is seen) — so read-before-write gate only works for Claude Task subagents, not codex/glm CLIs.

## LAST_VERIFIED
- Cleanup stripped hooks from Vividlist/forclosure/intrn/virality (+virality local)
- All .harnessbak backed up
- Memory written: harness-enforcement-audit.md
- Global CLAUDE.md=22 lines
- repowise = codebase-intelligence platform (superset of graphify, MCP for agents, -96% tokens) — strong graphify replacement candidate

## NEXT (need Ro decision)
1. Which builder does he code with? (codex/glm CLI vs Claude Task subagent?) — determines ponytail-gate design
2. Then build top-5 strict upgrades:
   - wrap codex/glm
   - broaden irreversible-pause
   - blocking now-gate/filesize
   - graphify shell-escape
   - arm route/check-all
3. Pending work:
   - per-repo CLAUDE.md trims (Vividlist 13KB)
   - graphify-vs-repowise decision
   - de-dup double-registered hooks
