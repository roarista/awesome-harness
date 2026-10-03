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

## Open / to check
- Chrome tools: whether they can be per project (the setting or flag is not yet verified). Ro uses them occasionally.
- The deferred tool-name list: no documented setting controls it. It shrinks only as connectors are removed (T2).
