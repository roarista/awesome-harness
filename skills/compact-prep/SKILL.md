---
name: compact-prep
description: Run before /compact to preserve session memory. Commits uncommitted work, syncs mulch records, updates STATE.md with resume point, pushes to origin, and confirms what will survive vs. what gets summarized. Global skill, works in any project.
---

# Compact-Prep Protocol

The orchestrator runs this skill BEFORE `/compact` to make sure no work is lost across the compaction boundary. Compaction summarizes the conversation — anything not persisted outside the chat is at risk.

## Why this exists

When `/compact` runs (or auto-fires at ~95% context), Claude reads the full conversation, writes a summary, and replaces the conversation with that summary as the new starting context. What survives:

- Project-root `CLAUDE.md` (auto-reloaded)
- Files in the working tree (auto-readable)
- `.mulch/` records (queryable via `ml prime` / `ml search`)
- Memory files in `~/.claude/projects/<project-slug>/memory/`

What does NOT reliably survive:
- Mid-session decisions the user gave you verbally
- Subtle preferences that weren't recorded
- Resume context ("we were about to do X next")
- Audit findings and fix-loop intermediate state
- Open questions you were about to ask

The skill's job is to push everything in the second list INTO the first list before compaction.

## Architecture: skill + global hook

The global PreCompact hook (`~/.claude/hooks/pre_compact_global.sh`, registered in `~/.claude/settings.json`) handles the **mechanical** half automatically on every `/compact`. It runs without LLM, so it's safe at peak context.

The hook does:
- Snapshot branch + HEAD + working-tree status
- `ml sync` if `.mulch/` is dirty and `ml` is installed
- Auto-commit ONLY tracked `.planning/STATE.md` and similar session-metadata MD files
- `git push` to origin if on a feature branch and ahead of upstream
- Write `.planning/COMPACT_HANDOFF.md` with branch, HEAD, recent commits, dirty files
- Emit a bounded "resume hint" + load-bearing context bundle that becomes part of post-compact context

The hook does NOT do:
- Commit source code, tests, or migrations (could include untracked WIP)
- Write `ml record` entries (needs judgment about what's durable)
- Update STATE.md `## Active Resume Point` with the next-step narrative
- Decide what verbal-only decisions or non-current project context need rescuing

That's what **this skill** is for. If the hook is enough for the session (mechanical-only), skip the skill. If the session had judgment-heavy work — audits, founder decisions, fix-loop reasoning — run this skill BEFORE typing `/compact` to capture the LLM-judgment half, then let the hook handle the mechanical wrap.

## The protocol — run in order

### 1. Snapshot the current state

Run in parallel:

```bash
git status --short
git log --oneline @{u}..HEAD 2>/dev/null || git log --oneline -10
git rev-parse --abbrev-ref HEAD
```

Show the user:
- Current branch
- Number of commits ahead of upstream (if tracking)
- Untracked/modified files

### 2. Triage uncommitted changes

Look at git status output. Three buckets:

- **Real work** (code, tests, migrations) — needs to commit BEFORE compact, or it stays uncommitted across the boundary and the next-session you may not realize it was in-flight.
- **Session metadata** (`.planning/STATE.md`, `.mulch/`, planning docs, session logs) — usually stays as working-tree changes; they're session artifacts.
- **Ambiguous** — ask the user.

If real work is uncommitted, explicitly ask: "Should I commit these N files before compaction?" Don't auto-commit silently — the user's mental model of "what's done" should match git.

### 3. Update mulch (if `ml` CLI is available)

Skip this section if `which ml` returns nothing.

```bash
~/.npm-global/bin/ml learn 2>&1 | head -40
```

Look at the "Suggested domains" and "Changed files" output. For each genuinely durable learning from this session — vendor cost corrections, schema gotchas, failed patterns, architectural decisions, reusable workflows — record it:

```bash
ml record <domain> --type <pattern|convention|failure|decision|reference> [type-specific required fields] --description "..."
```

> **Record format:** keep each record ≤2 sentences; overflow (dates, exact flags, event trace, counts, evidence) → `.mulch/details/<slug>.md`, and **read that detail file before acting on the record**. Full rules: `MEMORY_STANDARD.md`.

Type-specific required fields (gotchas the CLI will reject without):
- `pattern` requires `--name`
- `failure` requires `--resolution`
- `decision` requires `--title` and `--rationale`
- `convention` requires only `--description`
- `reference` requires only `--description`

What to record (HIGH signal):
- A bug that took >30min to find — root cause + how to spot it next time
- An audit finding the founder confirmed as load-bearing
- A workflow pattern that worked across multiple agents (e.g., parallel build + cherry-pick merge)
- A decision the founder made on an architectural question

What NOT to record:
- Anything already in CLAUDE.md
- Transient per-run data, raw vendor payloads, PII
- "Today I learned X" without evidence

Then sync:

```bash
~/.npm-global/bin/ml sync
```

This validates records and commits `.mulch/` changes. The commit goes on the current branch.

### 3b. Resurface the whole conversation (sub-agent) — for long, judgment-heavy sessions

Compaction's summary is biased toward the END of the conversation; early ideas, parked/half-formed thoughts, and things merely "being considered" are the first to vanish. For a long session, spawn ONE sub-agent (Sonnet is fine) to read the full transcript and resurface them, so they survive into the next terminal.

- Transcript path: `~/.claude/projects/<project-slug>/<session-id>.jsonl` (the session's own JSONL; read in chunks if large).
- Brief the agent to WRITE a concise `.planning/CONVERSATION_RESURFACE_<date>.md` with: mission + why; founder decisions made this session (each with the one-line why); **things being CONSIDERED / parked ideas (even half-formed)**; open questions; any capability/asset ledger discussed; key artifacts produced (paths). Tell it to be faithful — list unresolved items under Considering/Open, never as Decisions.
- Have it RETURN only ~8 bullets; the detail lives in the file. Then reference that file from the resume point (step 5) and from `COMPACT_CONTEXT.md` retrieval pointers.

This is the LLM-judgment complement to the mechanical handoff — use it whenever a session explored more than it concluded.

### 4. Preserve load-bearing context

Compaction often preserves the active task but loses adjacent context that is still essential to the project. Before updating the resume point, decide whether any non-current but load-bearing context needs to be carried forward.

Use the smallest durable home that fits:

- `.planning/STATE.md -> ## Active Resume Point` for the immediate next action.
- `.planning/STATE.md -> ## Essential Project Context` for short project invariants.
- `.planning/COMPACT_CONTEXT.md` for larger adjacent context that must survive every compact even when it is not today's objective.
- `ml record` for reusable cross-session lessons, decisions, failures, or conventions.

If `.planning/COMPACT_CONTEXT.md` is needed, keep it bounded and factual:

```markdown
# Compact Context

## Always Preserve

- <project invariant, user decision, deferred workstream, or architectural context>

## Current Non-Main Threads

- <important side thread that should not disappear just because it is not active>

## Retrieval Pointers

- <file paths, memory record names, reports, or commands to reload deeper context>
```

Ponytail: do not dump the whole project. Keep only things a fresh agent would otherwise miss and that would cause wrong work if forgotten. Prefer pointers over prose when the source file is stable.

The global hook copies `.planning/COMPACT_CONTEXT.md` plus matching STATE.md sections into `.planning/COMPACT_HANDOFF.md` and echoes them into the post-compact context.

For Ro's coding pipeline repos, the default load-bearing context includes the harness-improvement queue mined from Notion:

- Graphify / CodeGraph: graph-over-vector codebase maps, queried before cold grep when `graphify-out/graph.json` exists.
- Deterministic gates: `check-all`, CLAUDE/AGENTS drift checks, coverage/file-size/TODO/duplication checks.
- Agent rituals: start with state + memory + graph orientation; end with verification + durable memory + graph update.
- Frontend verification: Chrome DevTools MCP plus Playwright for UI-heavy repos.
- Later loop: Night Watch only after the gates and graph are trusted.

Source pointers to preserve rather than re-summarize: `~/Downloads/NOTION_WORKFLOW_MINING_2026-06-16.md`, `~/Downloads/HARNESS_BUILD_PLAN_2026-06-16.md`, and `~/.claude/projects/-Users-rodrigoarista/memory/project_harness_notion_mining.md`.

### 5. Update STATE.md with the resume point (if `.planning/STATE.md` exists)

**Delegate this write to a cheap sub-agent (haiku) — don't do it in the orchestrator (Ro's rule: the main terminal shouldn't burn context on housekeeping).** Hand the sub-agent the turn's changes + decisions; it opens the file and does steps below, then returns a one-line confirm.

**REPLACE the `## Active Resume Point` section in place — do NOT prepend a new block.** STATE.md bloats (140KB+) because agents stack `Resume Point #36 … #35 … #34` every turn without pruning. There is exactly ONE Active Resume Point; overwrite it. If real history must be kept, move the superseded block to `.planning/STATE-ARCHIVE.md`, not inline. Keep the live section TERSE/caveman — a fresh agent's briefing, not a log.

Find the `## Active Resume Point` section (or create it at the top). Write the resume point as if briefing a fresh agent with no chat history:

```markdown
## Active Resume Point

**Last updated:** <today's date>
**Branch:** <branch>
**HEAD:** <short sha>
**Status:** <one line — "Wave 7 PASS, ready for Wave 8" / "Mid-fix-loop, 3 of 5 items done" / etc.>

**Current workstream:** <one paragraph>

**Next concrete step:** <specific action with file paths or commands>

**Open questions for founder:** <list>

**Blocked on:** <if anything>

**Manual founder follow-ups pending:** <migrations to apply, env flags to flip, etc.>
```

The bar: a brand-new Claude agent reading STATE.md should be able to resume without conversation history. If they'd be lost, the resume point isn't specific enough.

### 6. Verification (light — don't burn time)

Skip if the project has no test suite or if the session was conversation-only.

```bash
npx tsc --noEmit 2>&1 | tail -5    # only if typescript
npx jest <touched-test-suites> 2>&1 | tail -5    # only if jest
```

Goal: confirm baseline is the same as start of session. If new failures appeared during session, document them in STATE.md "Known failures" — don't silently push broken state.

### 7. Push to origin (if upstream tracking + clean enough)

```bash
git push origin <current-branch>
```

Skip if:
- No upstream tracking (would require `-u` flag — ask the user first)
- Branch is `main` or `master` — ask the user first
- Uncommitted real work still in working tree (step 2 should have caught this)

### 8. Final output — TWO parts

Emit both, in this order.

**Part A — readiness audit** (short; so the user knows nothing is lost):

```
## Ready to compact
SURVIVES (verified): branch <name> @ <HEAD> (pushed?), N commits, M mulch records, STATE.md resume point updated, CLAUDE.md unchanged
SUMMARIZED (fine): audit findings + fix-loop steps (in commits), decisions (in mulch/STATE.md)
AT RISK (said in chat, not yet persisted): <list, or "none">
```

If "AT RISK" is non-empty, ASK before compacting: "These N things were only said in chat. Persist them first?"

**Part B — the CONTINUE block** (this is the point of the skill).

Emit a single fenced block, self-contained, written to be **pasted as the FIRST
message of the next session**. Not a file reference — the literal text the user
copies. Fill every line from real session state; drop a line only if truly N/A.

```
=== CONTINUE (paste as the first message of the next session) ===
Keep going — resume from NEXT below.

NORTH STAR: <the fixed objective, one line>
NOW: <the current step, one line>
BRANCH: <name> @ <short-sha> — <pushed | dirty: files>
DONE THIS SESSION: <2–4 bullets of what actually changed / was decided>
NEXT: <the ONE concrete next action, with exact file paths or commands>
OPEN DECISIONS (need me): <list, or "none">
DON'T REDO: <dead ends already tried, so the next session doesn't repeat them>
POINTERS: STATE.md ## Active Resume Point · <memory/ml domains/files to reload>
===
```

Keep it under ~20 lines. It should let a cold agent resume with zero chat
history. If a line would be vague ("continue the work"), it's not specific
enough — name the file, the command, the decision.

### Why this format — the paste-forward method

Do NOT put the handoff in the same message as `/compact`. When you do, it gets
folded into the summarization pass and diluted. Instead:

1. Run this skill → it prints the CONTINUE block.
2. Copy the CONTINUE block.
3. Run `/compact` with **no message**; let it come back.
4. Paste the CONTINUE block as the **first message** of the fresh session, then
   "keep going."

Pasted as the first user message, the block arrives as a high-salience, un-
summarized instruction the model treats as a direct order — which is why agents
resume far more accurately this way than when the handoff is buried in the
`/compact` turn. The `.handoff.md` file (written automatically by the PreCompact
hook) is the backstop; the pasted CONTINUE block is the primary channel.

## When NOT to run this skill

- Trivial conversational session (no code changes, no decisions) — skip; compact will be fine.
- Mid-build with uncommitted in-progress code — the user probably wants to keep going, not compact yet. Suggest waiting.
- A failing test or broken build state — push the failure and document it in STATE.md, or fix it first. Don't compact with a silent broken state.

## Notes for the orchestrator running this skill

- **Don't add work to the protocol mid-run.** This is a discipline check, not a refactoring opportunity. If you notice tech debt or a follow-up task, queue it for the post-compact session via STATE.md, not via "let me just clean this up first."
- **Don't write a multi-page handoff doc.** STATE.md gets read on every session start. Big files get truncated. Keep the resume point under 30 lines.
- **The user knows you can't capture everything.** They invoked this skill because they want a CLEAN compact boundary, not a perfect one. A short, accurate STATE.md beats a long, comprehensive one that lies.
