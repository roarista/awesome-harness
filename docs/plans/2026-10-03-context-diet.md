# Context diet — task list, 2026-10-03

Goal: bring a session's start close to the 18.1K tokens Claude Code needs on its own. Today a
`claude -p` call starts at 36.6K, and the first call of an interactive session is about 57K (73K in
Consulting). Each task is done, verified and committed one at a time. After each one, re-run the gate below.

**Gate**, run in the repo being measured:

```
claude -p "reply ok" --model haiku --output-format json | jq '.usage|.input_tokens+.cache_read_input_tokens+.cache_creation_input_tokens'
```

**Baseline in awesome-harness:**

| Setup | Tokens |
|---|---|
| full | 36.6K |
| `--safe-mode` | 18.1K (the floor) |
| without user settings | 28.4K |
| without MCP | 31.8K |
| without the 3 plugins | 34.6K |
| hooks off | 35.7K |

**Rule for every task:** a plugin or MCP server loads only in the repos that use it. Project settings
override user settings (`managed > flag > local > project > user`, per code.claude.com/docs/en/plugins/loading).

## Progress (gate = `claude -p` tokens in awesome-harness; floor 18.1K)

| Task | State | Gate after | Notes |
|---|---|---|---|
| T1 plugins | DONE | 34.5K (−2.0K) | vercel, power-automate, frontend-design off in user settings; on via gitignored `settings.local.json` in intrn (vercel + frontend-design) and Vividlist (frontend-design). In intrn the plugins are measured loading (+1.7K). The Vercel CLI is untouched. |
| T2 connectors | DONE | 31.8K (−2.7K) | **Opt-in per project does NOT work:** a user-level `disableClaudeAiConnectors: true` or env `ENABLE_CLAUDEAI_MCP_SERVERS=false` wins over a project-level `false`/`true` (verified: Notion tool count 0 in Consulting). **Opt-out works:** connectors stay on globally, and each repo that doesn't need them has `disableClaudeAiConnectors: true` in its gitignored `.claude/settings.local.json`. Opted out: awesome-harness, forclosurehomes, free-model-router, greyrock, intrn-v2, jobs, research-method, scholarships, school, virality-pipeline, virality-trends. Left on: Consulting, Vividlist, intrn, and ~ (home). treg (user MCP) costs 0.5K and is kept. |
| T3 ponytail | DONE | 30.8K (−1.0K in `-p`; interactive also loses the re-injection after every compact) | 4-line rule appended to `~/.claude/CLAUDE.md`; plugin disabled. |

## Tasks

### T1. Plugins: off globally, on per project. Saves about 2K tokens per session. Configuration only.
- **User settings:** turn off vercel, power-automate and frontend-design.
- **Turn them back on per project:**
  - vercel in `intrn/.claude/settings.json`, the only repo with `vercel.json`;
  - frontend-design in the UI repos (intrn, Vividlist).
- **The Vercel CLI is unaffected.** It is `~/.npm-global/bin/vercel` and works without the plugin. The plugin only adds skills and an MCP.
- **Verify:** gate in awesome-harness drops by about 2K; gate in intrn still lists the vercel skills.

### T2. claude.ai connectors: off globally, on per project. Saves about 3–5K. Configuration only.
- **User settings:** `"disableClaudeAiConnectors": true`, or the env var `ENABLE_CLAUDEAI_MCP_SERVERS=false`.
- **Turn back on, with `false`:** Consulting (Notion), Vividlist and intrn (Supabase).
- **Needs a check:** whether a project-level `false` really overrides the user-level `true`. If it doesn't, fall back to per-repo `deniedMcpServers` lists.
- **Ro removes in claude.ai:** connectors he never uses anywhere, namely the sales, marketing, finance, apollo and brand-voice auth stubs. This also shortens the deferred tool-name list.
- **Verify:** gate here drops by about 4.8K; in Consulting, a Notion tool still resolves.

### T3. Ponytail. Saves about 1.3K at every start and compact. Configuration plus 4 lines.
- Put the 4-line ladder rule in global CLAUDE.md and turn off the plugin.
- If Ro wants the plugin's `/ponytail` levels, keep it on, but only in code repos.

### T4. /clear instead of /compact. Saves about 10–20K per handoff. Builder writes the hook.
- **New flow:** `/compact-prep` → `/clear`.
  - compact-prep already persists everything to the commit, mulch, STATE and `.now.md`, and writes the CONTINUE block to `.planning/CONTINUE.md`.
  - A `SessionStart` hook with matcher `clear` injects that file (≤1.5K). It is documented: code.claude.com/docs/en/hooks.
- **What this removes:** the compact summary (about 5–15K), the pasted final summary, and the `/awesomeharness` re-prime.
- **Keep `/compact` for one case:** mid-task, when reasoning not yet written down matters. compact-prep's "AT RISK" check exists to catch exactly that.
- **Verify:** run compact-prep, then `/clear`; the first call is ≤ the floor + harness, and the agent states the NEXT step correctly without being told.

### T5. compact-prep from 17.5K to ≤3K. Builder plus audit.
- Keep MINIMUM PATH, the AT-RISK check and the CONTINUE template.
- Move the "why" text to `docs/`.

### T6. /awesomeharness from 7.9K to ≤2.5K, Claude and Codex copies. Builder plus audit.
- **Keep:** the code loop and the verdict rubric.
- **Compress:** the quality gates to 5 lines.
- **Drop:** the hook inventory, because hooks speak when they fire, and the delegation rules, which are already in CLAUDE.md.
- After T4 it is no longer needed as a re-prime. It stays as an on-demand contract only.

### T7. Memory indexes ≤3K each. Saves up to about 5K in Consulting. Builder.
- **Sizes today:** Consulting 23.6K, Vividlist 16.4K, virality 12.6K, home 11.5K, harness 7.7K.
- **Rule:** one line per memory, ≤100 characters. Drop superseded entries from the index only; the memory files stay.

### T8. Skill and agent descriptions. Saves about 3K. Builder.
- Skills: ≤160 bytes each. Agents: ≤300 bytes each; codex-audit's history essay moves into the body.
- Delete skills with 0 uses in 30 days, per harness-usage-telemetry. Ro approves the list first.

### T9. CLAUDE.md files, one home per rule. Saves about 1K.
- **Global:** delegation lives only here, in 6 lines.
- **Project (awesome-harness):** the repowise and claude-api history shrinks to 4 lines.
- **Codex `AGENTS.md`:** from 7.1K to ≤2.5K, mirroring T6.

### T10. Hooks.
- `recall-inject`: only current-project hits above a score threshold. It is injecting Clyde/Consulting memories into this repo.
- **New 200-line nudge.** When an Edit or Write leaves a source file over 200 lines, it injects one line into that agent: "`<file>` is N lines (cap 200): split into a new module before continuing."
  - This is a nudge, not a block, so there is nothing to route around. The commit ratchet remains the block.
  - A Write/Edit block was rejected because it invites Bash rewrites, per Ro's 2026-10-03 rule.

### T11. Remeasure everything.
- Run the gate in 5 repos, plus the first interactive call from the transcripts.
- **Targets:** `-p` ≤24K; interactive first call ≤40K; post-handoff start ≤ start + 1.5K.


## Unit specs, T4–T10 (one builder each, sequential, cross-family audit)

**U4 — /clear handoff**
- CONTEXT: `hooks/_hookout.py` (inject/once helpers), `scripts/merge_settings.py:24,93` (registration), `skills/compact-prep/SKILL.md`, `hooks/northstar-inject.py` (351 lines; do not grow it).
- REUSE: `_hookout.inject` and `is_product_call` / `exit_if_product`.
- CHANGE:
  - New `hooks/clear-resume.py`, ≤80 lines. On SessionStart with source `clear`, inject `<project>/.planning/CONTINUE.md` if it exists and is <48 h old, capped at 1,500 bytes. Otherwise inject `.now.md`, ≤5 lines. Otherwise inject nothing.
  - Register it in `merge_settings.py` with matcher `clear`.
  - compact-prep writes its CONTINUE block to `.planning/CONTINUE.md` and tells Ro: "then `/clear` (use `/compact` only mid-task)".
  - Install the live copy.
- GOAL: after compact-prep then `/clear`, the new session's context contains the CONTINUE text, with nothing pasted. Out of scope: changing `/compact`.
- VERIFY: `python3 tests/test_clear_resume.py` covers 4 cases: clear + file present, stale file, `.now.md` fallback, and a non-clear source producing no output. `python3 hooks/clear-resume.py <<< '{"source":"clear","cwd":"…"}'` prints the block. merge_settings dry-run shows the new entry. The file is ≤200 lines.

**U5 — compact-prep ≤3K**
- CHANGE: `skills/compact-prep/SKILL.md` keeps MINIMUM PATH, the AT-RISK check, the CONTINUE template and the `/clear` instruction. The rationale moves to `docs/compact-prep-why.md`.
- VERIFY: `wc -c` ≤3,000; every command named in the old MINIMUM PATH still appears; `tools/skill-drift.sh` is clean after install.

**U6 — /awesomeharness ≤2.5K, both copies**
- CHANGE:
  - Keep: the code loop, the spec fields, the verdict rubric, and sub-agent discipline.
  - Compress the quality gates to 5 lines.
  - Delete: the hook inventory and the delegation rules. Delegation lives in CLAUDE.md, and for Codex in `AGENTS.md`.
- VERIFY: `wc -c` ≤2,500 for each copy; the rubric's REJECT rule is verbatim; skill-drift is clean.

**U7 — memory indexes ≤3K**
- CHANGE: rewrite `MEMORY.md` in Consulting, Vividlist, virality, home and harness. One line per memory, ≤100 characters. Superseded entries leave the index (the file stays) and are listed at the end of the report.
- VERIFY: `wc -c` ≤3,000 each; every remaining link resolves to an existing file; no memory file is deleted.

**U8 — skill and agent descriptions**
- CHANGE: user-skill `description:` ≤160 bytes; `~/.claude/agents/*.md` and repo `agents/` `description:` ≤300 bytes. History text moves into the body. Produce a list of 0-use skills for Ro; do not delete them.
- VERIFY: a byte-count script over the frontmatter; skill-drift is clean; the agent files still parse (`claude -p` agent list unchanged).

**U9 — one home per rule**
- CHANGE:
  - Global CLAUDE.md: delegation in ≤6 lines.
  - Project `.claude/CLAUDE.md`: ≤600 bytes.
  - `codex/AGENTS.md`: ≤2,500 bytes, mirroring U6.
  - Add a repo mirror `templates/global-CLAUDE.md` plus a drift check in `tools/skill-drift.sh`.
- VERIFY: byte caps; drift check clean; a grep shows each rule (200-line cap, cross-family audit, reset credits) appears exactly once per file set.

**U10 — hooks (after the hook-impact report)**
- CHANGE:
  - recall-inject: inject only hits from the current project above a score threshold.
  - New `hooks/size-nudge.py`, PostToolUse on Write and Edit: one line when a source file is over 200 lines. It never blocks.
  - Apply the KEEP/ADJUST/DELETE verdicts from `.artifacts/agent-reports/hook-impact-2026-10-03.md` once Ro agrees.
- VERIFY: per-hook tests; recall in awesome-harness no longer surfaces Consulting memories; the size nudge fires on a 201-line write and is silent at 200.

## Open / to check
- Chrome tools: whether they can be per project (the setting or flag is not yet verified). Ro uses them occasionally.
- The deferred tool-name list: no documented setting controls it. It shrinks only as connectors are removed (T2).
