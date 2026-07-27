---
name: compact-prep
description: The every-turn close for a Codex session — commit the work, record the durable lesson, update the STATE resume point and .now.md, push, and emit the CONTINUE block. Run at the end of every substantive turn and before any context compaction, so nothing that only lives in the conversation is lost. Works in any repo.
---

# compact-prep (Codex edition) — the every-turn close

> **Step 7 of THE PROCEDURE** (`~/.codex/AGENTS.md`). Anything that exists only in the conversation is at risk; this pushes it into files, git, and mulch.

## MINIMUM PATH (every turn — this is the whole skill)

```
1. commit the work
2. `ml record` the durable lesson   (syntax below; <=2 sentences)
3. REPLACE `## Active Resume Point` in .planning/STATE.md  (replace, never prepend)
4. `.now.md` — NOW / LAST_VERIFIED / NEXT, <=5 lines
5. push to origin
6. emit the CONTINUE block
```

## 1. Commit

```bash
git status --short
git log --oneline -5
```

Triage what is uncommitted:
- **Real work** (code, tests, migrations) — commit it. If on the default branch, branch first.
- **Session metadata** (`.planning/STATE.md`, `.now.md`, `.mulch/`) — commit with the work or alongside it.
- **Ambiguous / untracked WIP you did not create** — ask Ro, never sweep it in silently.

## 2. Record the durable lesson

Skip if `which ml` returns nothing (`ml` lives at `~/.npm-global/bin/ml`).

```bash
ml record <domain> --type <pattern|convention|failure|decision|reference> [required fields] --description "..."
ml sync
```

Type-specific required fields the CLI rejects without:
- `pattern` → `--name`
- `failure` → `--resolution`
- `decision` → `--title` and `--rationale`
- `convention`, `reference` → `--description` only

**Record format:** each record ≤2 sentences. Overflow (dates, exact flags, counts, evidence) goes to `.mulch/details/<slug>.md`, and you **read that detail file before acting on the record**. Full rules: `~/.codex/MEMORY_STANDARD.md`.

Record (HIGH signal): a bug that took >30min to find, with root cause and how to spot it next time; an architectural decision plus its rationale; a failure mode and its resolution; a convention this repo now follows.
Do NOT record: anything already in AGENTS.md/CLAUDE.md, transient per-run data, raw payloads, PII, or "today I learned X" with no evidence.

## 3. STATE resume point

**Replace** the `## Active Resume Point` section in `.planning/STATE.md` — never prepend a new one, or the file grows into an unreadable log. It answers exactly one question: what does the next session do first?

Keep STATE trimmed to the current workstream. Older history moves to `.planning/STATE-ARCHIVE.md` — archived, never deleted.

If the session explored more than it concluded, also write the parked ideas and open questions somewhere durable (`.planning/COMPACT_CONTEXT.md`) — half-formed thoughts are the first thing a summary loses. Keep it bounded and factual; prefer pointers to stable files over prose.

## 4. `.now.md`

At the repo root, ≤5 lines:

```
NOW: <what is in flight right now>
LAST_VERIFIED: <the last thing actually proven to work, and how>
NEXT: <the single next action>
```

## 5. Push

```bash
git push
```

## 6. CONTINUE block

End the final message with the exact resume point — the branch, the HEAD, the next action, and what was persisted. Ro reads only the final message, so this is the handoff.
