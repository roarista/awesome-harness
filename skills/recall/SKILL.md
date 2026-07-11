---
name: recall
description: Retrieve the right durable memory fast, instead of grepping scattered markdown. Use when you need prior context on a topic ("what do we know about X", "have we decided Y", "/recall Z"), at the start of substantive work to load task-relevant memory, or before proposing something that may already be recorded. Backed by the memgraph FTS index over Ro's memory records.
---

# recall — fast memory retrieval (graph + full-text index)

Ro's durable memory is many markdown records. The harness injects the `MEMORY.md` index + a few auto-recalled records each session, but that's the *index*, not the full bodies, and it won't surface everything relevant to a specific task. This skill queries the **memgraph** index to pull the right record(s) in 1–3 lookups instead of grepping `~/.claude` and mulch cold.

## Tools (already built)
- Indexer: `python3 /Users/rodrigoarista/.claude/tools/memgraph/build.py` — rebuilds `out/graph.json`, `out/memindex.sqlite` (FTS5), `out/graph.html`.
- Query CLI: `python3 /Users/rodrigoarista/.claude/tools/memgraph/mem.py`
  - `mem.py query "<text>" [-k N]` — full-text search, ranked. Your main verb.
  - `mem.py graph <name>` — show a record's neighbors (links in/out, supersedes/superseded-by). Use to follow related context.
  - `mem.py list [--type user|feedback|project|reference]` — enumerate records.
  - `mem.py rebuild` — refresh the index after memory files change.

## How to use it

**Quick recall (default — do this inline, it's cheap):**
1. Run `python3 /Users/rodrigoarista/.claude/tools/memgraph/mem.py query "<topic from the task>"`.
2. Read the top hit(s) — the CLI prints name, type, description, path. If a record looks load-bearing, Read its file for the full body.
3. Optionally `mem.py graph <name>` to pull in linked records (a decision often links to the feedback that shaped it).

**Heavy recall (many hits, need several full bodies):** spawn ONE `Explore` subagent to run the queries, Read the matched records, and return just the synthesized answer — keeps the orchestrator context light (the same explorer-subagent gate we use for code search). Don't dump 10 record bodies into the main context.

**Keep the index fresh:** after you Write or meaningfully edit a memory record, run `mem.py rebuild` so retrieval reflects it. (Cheap; stdlib only.)

## Session ritual (begin / middle / end)
- **Begin substantive work:** `mem query` the task's topic before planning — load the specific decisions/feedback that apply, not just the MEMORY.md one-liners.
- **Before proposing something new:** `mem query` it first — avoid re-deciding what's already recorded (and avoid the "it already exists" trap, `[[feedback-verify-already-exists]]`).
- **End / before compaction:** if a durable lesson emerged, Write the memory record, then `mem rebuild`.

## Guardrails
- **Read budget:** cap retrieval at ≤5 file reads per recall — hop card-by-card (`mem query` → top hit → `mem graph` to the one linked record you need) rather than bulk-reading memory; if 5 reads don't answer it, narrow the query, don't widen the reads.
- Read-only retrieval; never mutate memory records as a side effect of a query.
- If `out/memindex.sqlite` is missing, run `build.py` first.
- Dangling links are expected for not-yet-written records (a `[[name]]` with no file marks a TODO memory). `mem graph` flags them — they're signal, not error.
- CPU is tight (`[[low-cpu-avoid-vms-and-heavy-local-compute]]`): prefer inline `mem query` over spawning agents for single lookups.
