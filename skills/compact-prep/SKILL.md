---
name: compact-prep
description: "Run before /clear (or mid-task /compact): commit, mulch record, STATE + .now.md, push, write .planning/CONTINUE.md."
---

# Compact-Prep

Why, and the full protocol (mulch field rules, STATE trim, resurface agent): `docs/compact-prep-why.md` in awesome-harness.

## MINIMUM PATH

Touched files: `python3 ~/.claude/tools/turn-files.py --session <session_id>`.

```
1. commit the work (real work only; ask before committing ambiguous files)
2. `ml record <domain> --type <...> --description "..."` the durable lesson (<=2 sentences; overflow -> .mulch/details/<slug>.md), then `ml sync`
3. REPLACE `## Active Resume Point` in the repo's STATE file (.planning/STATE.md or STATE_CURRENT.md; use the existing one; never prepend)
4. `.now.md`: NOW/LAST_VERIFIED/NEXT, <=5 lines
5. push: `bash "$(git rev-parse --show-toplevel)/tools/git-sync.sh" -m "<what>"` (never force; skip on main or no upstream; ask first)
6. write the CONTINUE block to `.planning/CONTINUE.md`
```

## AT-RISK check

Before step 6, print:

```
## Ready to clear
SURVIVES: branch <name> @ <sha> (pushed?), N commits, M mulch records, STATE file + .now.md updated
AT RISK (said in chat, not yet persisted): <list, or "none">
```

If AT RISK is non-empty, ask: "These N things were only said in chat. Persist them first?"

## CONTINUE template

Write to `.planning/CONTINUE.md` (overwrite; <=1,500 bytes, the hook caps it there). Fill every line from real state; drop a line only if N/A.

```
=== CONTINUE ===
Keep going: resume from NEXT below.
NORTH STAR: <the fixed objective, one line>
NOW: <the current step, one line>
BRANCH: <name> @ <short-sha> | <pushed | dirty: files>
DONE THIS SESSION: <2-4 bullets>
NEXT: <the ONE concrete next action, with exact file paths or commands>
OPEN DECISIONS (need me): <list, or "none">
DON'T REDO: <dead ends already tried>
POINTERS: STATE file ## Active Resume Point · <memory/ml domains/files>
===
```

A vague line ("continue the work") is not specific enough: name the file, the command, the decision.

## Then tell Ro

"Handoff saved to `.planning/CONTINUE.md`. Now `/clear` (use `/compact` only mid-task)."

After `/clear`, the `clear-resume.py` SessionStart hook injects CONTINUE.md (<48 h old), so nothing is pasted. Use `/compact` only mid-task, when reasoning not yet written down matters; then also paste the block as the first message after it.

Skip this skill for a trivial conversational session. Do not compact or clear with a silent broken build: fix it or record it in the STATE file first.

## Former description (moved from frontmatter, context diet U8)

Run before /clear (or /compact mid-task) to preserve session memory. Commits work, records mulch, updates STATE.md and .now.md, pushes, writes .planning/CONTINUE.md.
