# <REPO/WORKSTREAM> — FRONT DOOR

> The one doc a fresh agent reads FIRST. If reality and this doc disagree, reality
> wins — fix this doc. Keep it current; keep it citing `file:line`.

## Disambiguation banner (delete if single-workstream)

**This checkout = `<WORKSTREAM X>` ONLY.** If injected context (north star, recalled
memory, handoff) mentions `<OTHER LANE Y>`, that is a different lane — ignore it here.

## What we're building (the model)

<2–4 sentences: the canonical mental model. The pipeline(s), what feeds what, where
the fallback is. Name the naming traps ("the firm-first code path actually requires
the schools filter").>

## Invariants (never violate without saying so)

- <invariant 1, e.g. "Full mode only; nothing sends">
- <invariant 2, e.g. "school constraint required; maxFirms 50">

## Data flow (end to end)

<entry `path:line` → stage → stage → output `path:line`. One line per hop.>

## Files (one line each)

- `path/to/file.ts:1` — <role in one line>
- ...

---
*Generated from `templates/FRONT_DOOR.md`. Regenerate/refresh with the `state-trim`
skill or `/harness-audit`. Cite `file:line` so claims are checkable, not vibes.*
