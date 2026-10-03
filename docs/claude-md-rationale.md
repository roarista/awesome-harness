# Project CLAUDE.md rationale

History behind the terse rules in `.claude/CLAUDE.md` (moved verbatim 2026-10-03, context diet U9; that file is untracked).

## Code intelligence in this repo

**graphify (CLI)** is the map. `graphify query <name>` to resolve a label to a
node id, `explain` for a node, `path`/`affected` for reach. Measured 2026-08-04
it is the most-used tool in the harness (288 calls/30d across 6 repos, 76%
returning real output) and the import graph is genuine here-adjacent repos
(Vividlist 8,070 import edges, intrn 6,963, virality 5,433). Gotcha: the edge
list is `links` and the field is `relation`, not `type`.

**repowise (CLI only)** survives for exactly two consumers:
`tools/chains/c5-dead.sh` (`repowise dead-code`) and `tools/chains/c7-preship.sh`
(`repowise risk`). Nothing else should call it.

**The repowise MCP was removed 2026-08-04** — 23 tool calls in 30 days against
6.5 KB of this file injected every session, plus a `repowise-augment` hook that
fired 521 times in 30 days (316 of them in virality) mostly to say the index was
stale. `semgrep` answers "all the places"; graphify answers structure.

**Orientation path:** `tools/chains/c0-preflight.sh` first — it reports which
chains are trustworthy in the repo you are actually standing in.

**The `claude-api` skill is DENIED in this repo** (`.claude/settings.local.json`,
2026-08-12). It injects 852 KB / ~237K tokens in one call — with no project
language detected here it loads all 9 language trees plus 27 `shared/` files, 65
documents, `shared/model-migration.md` alone being 175 KB. This repo calls no
Anthropic API (zero `import anthropic`, zero endpoints, zero keys; all LLM calls
go through `codex exec`), so the entire Anthropic surface is two constants:
`tools/drift-replay.py:26` and `hooks/precompact-handoff.py:34`, both
`MODEL = "claude-haiku-4-5"`.

For an Anthropic API question here, **read the one relevant file directly** —
`shared/prompt-caching.md` (11 KB), `shared/models.md`, `shared/model-migration.md`
— under the bundled-skills path (version-scoped, e.g.
`/private/tmp/claude-501/bundled-skills/<version>/*/claude-api/`). Do not try to
route around the deny. If a repo genuinely builds on the Anthropic SDK, the skill
is still allowed there; this deny is project-scoped.
