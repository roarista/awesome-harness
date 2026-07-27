---
name: recall
description: Retrieve durable memory fast instead of grepping scattered markdown. Use when you need prior context on a topic ("what do we know about X", "have we decided Y"), at the start of substantive work to load task-relevant memory, or before proposing something that may already be recorded. Backed by the memgraph full-text index over Ro's global memory plus mulch for per-repo records.
---

# recall — fast memory retrieval

> **Step 1 of THE PROCEDURE** (`~/.codex/AGENTS.md`). Two stores, two CLIs, both plain command-line tools a Codex session can run directly.

## Global memory — memgraph

```bash
python3 ~/.claude/tools/memgraph/mem.py query "<topic>" [-k N]   # full-text search, ranked — your main verb
python3 ~/.claude/tools/memgraph/mem.py graph <name>             # a record's neighbors (links, supersedes)
python3 ~/.claude/tools/memgraph/mem.py list [--type user|feedback|project|reference]
python3 ~/.claude/tools/memgraph/mem.py rebuild                  # refresh the index after memory files change
```

The index lives next to the script (`~/.claude/tools/memgraph/out/`), which is why the path points there even from a Codex session — there is one index, shared. If `out/memindex.sqlite` is missing, run `python3 ~/.claude/tools/memgraph/build.py` first.

Flow: `query` → read the top hit's name/description/path → Read the file only if the record is load-bearing → optionally `graph <name>` to pull the one linked record you need.

## Per-repo memory — mulch

In a repo with `.mulch/`:

```bash
ml prime            # load the repo's records at the start of substantive work
ml search "<topic>" # targeted lookup
```

`ml` is at `~/.npm-global/bin/ml`. If it is not on PATH, call it by that full path.

## Session ritual

- **Before planning substantive work:** query the task's topic in both stores. Load the specific decisions and failure modes that apply.
- **Before proposing something new:** query it first — avoid re-deciding what is already recorded, and avoid building what already exists.
- **At the close:** if a durable lesson emerged, record it (`compact-prep` step 2), then `mem.py rebuild` if you wrote a global memory file.

## Guardrails

- **Read budget: ≤5 file reads per recall.** Hop card-by-card (`query` → top hit → one `graph` hop). If 5 reads have not answered it, narrow the query rather than widening the reads.
- Retrieval is read-only. Never mutate a memory record as a side effect of a query.
- Dangling `[[name]]` links are expected — they mark a not-yet-written record, signal rather than error.
