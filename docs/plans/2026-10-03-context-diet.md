# Context diet — plan, 2026-10-03

Goal: a session starts with only the context it needs. Ro's complaint: about 10K tokens are gone before
the first message, and roughly 20% after two messages.

## Measured (not estimated)

**First API call per session**, read from transcripts (15 most recent per repo):

| Repo | Tokens before any work |
|---|---|
| awesome-harness | 57K |
| virality | 59K |
| Vividlist | 63K |
| Consulting | 73K |
| home | 64K |

**`claude -p "reply ok" --model haiku`** run in awesome-harness. These numbers are deterministic; repeat runs gave the same result.

| Configuration | Tokens | Difference |
|---|---|---|
| full | 36.6K | — |
| `--safe-mode` (floor: Claude Code itself) | 18.1K | **−18.5K is ours** |
| without user settings (hooks + plugins + agents) | 28.4K | −8.2K |
| without MCP servers | 31.8K | −4.8K |
| without 3 plugins (vercel, power-automate, frontend-design) | 34.6K | −2.0K |
| hooks off | 35.7K | −0.9K |

Interactive sessions add about 20K on top of `-p`: the Chrome and Claude Docs tools, the deferred-tool name
list (about 250 names, including roughly 70 auth stubs for sales, marketing, finance, apollo and brand-voice
connectors), and the first message. Typing `/context` in an interactive session shows the exact split; this plan
does not depend on it.

**Text files loaded by bytes** (about 3.7 bytes per token):

| What | Bytes | When it loads |
|---|---|---|
| user skill descriptions (19) | 8.3K | every session |
| plugin skill descriptions (58; vercel alone is 10.6K) | 15.1K | every session |
| agent descriptions (6 ours + 5 plugin) | 8.2K | every session |
| MEMORY.md: Consulting / Vividlist / virality / home / harness | 23.6K / 16.4K / 12.6K / 11.5K / 7.7K | every session in that repo |
| global CLAUDE.md + project CLAUDE.md | 3.2K + 2.4K | every session |
| ponytail plugin SessionStart injection | about 5K | every start and every compact |
| codemap | ≤2K | every start |
| `/awesomeharness` body | 7.9K | after every compact (171 times in 30 days) |
| compact-prep body | **17.5K** | every compact-prep |
| pasted final summary + CONTINUE block (as `/awesomeharness` args) | about 4–8K | after every compact |
| codex `AGENTS.md` | 7.1K | every Codex session |

## Plan (ordered by tokens saved per unit of effort)

**P1 — configuration only. Needs Ro's yes; no code; saves about 8–10K per session.**
1. Disable the vercel and power-automate plugins globally, and enable them per project where they're used. frontend-design goes per-project in UI repos.
2. Disconnect the claude.ai connectors Ro doesn't use in Claude Code (sales, marketing, finance, apollo and brand-voice auth stubs; probably Supabase, HF and treg). This is done in claude.ai's settings, which is Ro's call.
3. Replace ponytail's 5K SessionStart injection with its 4-line rule in global CLAUDE.md, and disable the plugin. If Ro prefers to keep the plugin, set `/ponytail lite` instead.

**P2 — text that loads every session. Builder plus audit; saves about 5–8K, more in Consulting.**
4. MEMORY.md indexes: at most 3K each, one line of ≤100 characters per memory. Prune superseded entries; the files themselves stay. Consulting saves about 5K tokens alone.
5. Skill descriptions: ≤160 bytes each. Delete any skill with zero uses in 30 days, measured with harness-usage-telemetry.
6. Agent descriptions: ≤300 bytes each. Drop the history essays, such as codex-audit's "HONEST CAVEAT" and the "measured 2026-08-02" text, and move them into the body or docs.
7. CLAUDE.md:
   - Global: give each rule one home. Delegation currently appears in both global CLAUDE.md and `/awesomeharness`; keep it in CLAUDE.md as 6 lines.
   - Project: cut the repowise/claude-api history to 4 lines.
8. recall-inject: inject only hits from the current project above a score threshold. Today it surfaced "clyde-servicenow" inside awesome-harness, which is pure noise.

**P3 — the re-prime after `/compact`. Saves about 8–12K per compact.**
9. `/awesomeharness` goes from 7.9K to ≤2.5K, for both the Claude and Codex copies:
   - Keep the code loop and the verdict rubric.
   - Compress the quality gates to 5 lines.
   - Drop the hook inventory, because hooks announce themselves when they fire.
   - Drop the delegation rules, which now live in CLAUDE.md.
10. compact-prep goes from 17.5K to ≤3K. Keep MINIMUM PATH plus the CONTINUE template; move the "why" text to docs.
11. One handoff, not two. compact-prep writes the CONTINUE block to `.now.md` and the handoff, and the post-compact prime reads it from there, so Ro pastes nothing (or only the CONTINUE block, never the long summary as well).
12. Codex `AGENTS.md` goes from 7.1K to ≤2.5K, mirroring point 9.

**P4 — the 200-line rule (Ro's question).**
- Today `filesize-cap` has nothing to do with 200 lines. It warns when an agent **reads** a file of 2000+ lines. The 200-line rule is enforced only by the git pre-commit ratchet, which blocks, and agents comply with it.
- Proposal: keep the commit block, and add a write-time nudge. When an Edit or Write leaves a source file over 200 lines, inject one line into **that** agent's context: "`<file>` is N lines (cap 200): split into a new module before continuing."
- A nudge can't be routed around because it doesn't block anything, and the commit gate still catches anyone who ignores it.
- A Write/Edit block was rejected: by Ro's 2026-10-03 rule, a block invites Bash rewrites, which means the hook should be deleted.

## Gate (re-run after each phase)

```
cd ~/Downloads/awesome-harness && claude -p "reply ok" --model haiku --output-format json | jq '.usage|.input_tokens+.cache_read_input_tokens+.cache_creation_input_tokens'
```

Targets: `-p` full ≤26K (from 36.6K); first interactive call ≤40K (from about 57K); re-prime after compact ≤4K
(from about 15K).
