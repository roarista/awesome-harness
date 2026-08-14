# Lightweight harness plan

**Status:** IN PROGRESS — thin skill and Intrn diet shipped 2026-08-13; fresh Intrn Opus-5 start
measured 43,038 input tokens versus 56,568–61,107 in four prior sampled starts (directional, not a controlled A/B).
**Decision gate:** ADAPT what exists. Do not add another map refresher, memory store, or standing agent.

## Outcome

The default Claude session should start with one stable, cached instruction prefix and only the
tools needed for that repository. The orchestrator keeps the goal, unit contracts, and receipts;
disposable agents hold implementation detail. Success means lower uncached and total input without
reducing verified completion or increasing rework.

## Target baseline

1. One repo `CLAUDE.md` router, <=2,000 tokens, containing only repo-specific invariants, safety,
   test commands, and the compact coding loop.
2. One resume card, <=10 lines. Mulch holds durable decisions/failures; archived STATE holds history.
   Retire `.now.md`, `.northstar.md`, duplicate root/project STATE, and front-door chains only after
   their unique facts are migrated and the old files are archived.
3. `.codemap` remains SessionStart context, refreshed on HEAD-SHA drift and structural commits.
   Graphify remains the on-demand structural/blast map. No daily refresh agent.
4. `/awesomeharness` becomes a short router, not a catalog: recall -> choose search intent ->
   decompose -> one Codex builder per unit -> one independent auditor until no HIGH/CRITICAL ->
   check-all -> persist.
5. Tool routing: codemap = what exists; Mulch = prior decisions; graphify = structure/reach;
   Semgrep = exhaustive AST matches; `rg` = literal text/history; repowise CLI only for the two
   workflows that demonstrably consume it. Repowise MCP stays off.

## Why this is the smallest change

- Codemap injection and SHA-drift regeneration already exist; `agents/map-refresh.md` already owns
  structural refresh. Scheduling another agent adds tokens and staleness races.
- `/awesomeharness` is 11,534 B (~2.9k tokens) and repeats rules already present in `orient` and
  `.claude/CLAUDE.md`. Delete inventories, retired-history, stats, and duplicated procedure prose.
- The 10 live skill descriptions total 4,384 B (~1.1k tokens per listing). Rewrite them as
  trigger-only one-liners; full instructions remain on disk and load only when invoked.
- MCP exposure is the larger standing tax: prior measurement found 304 tool names, 24 used, and
  280 unused (estimated 28–56k tokens when fully exposed). Default to deferred tool search and
  explicit per-repo enablement; remove `enableAllProjectMcpServers`.
- Caching lowers price, not context occupancy. Stable byte-identical prefixes help, but duplicated
  skill injection and large maps/docs still consume the window. Shrink first, stabilize second.

## Target-repo migration

| Repo | Measured front-door burden | First cut |
|---|---:|---|
| Vividlist | ~19.7k tokens when its documented chain is followed | Merge six continuity/front-door docs into router + resume + archive; remove duplicate graphify hooks. |
| virality-pipeline | ~11.7k tokens | Merge two STATE files + `.now`/`.northstar`; remove legacy `.memory` language and keep Mulch. |
| intrn | ~31k tokens; STATE alone ~18.1k | Archive the 1,083-line STATE immediately; retain a <=10-line resume card. |

Across all three: disable unused repowise MCP registration; avoid all-project MCP enablement; make
frontend/Vercel/design plugins task-scoped; move large UI/caption skill packs to on-demand loading;
remove repeated `ml prime` and graphify additional-context hooks.

## Delivery units

### Unit 0 — measurement contract

- Capture 7 days per repo: SessionStart bytes, tool-schema bytes/count, skill-list bytes, cache
  creation/read/input tokens, subagent count/tokens, verified completion, audit rejects, and rework.
- Store the baseline outside injected docs. Define a task sample for before/after comparison.
- Gate: no percentage-saved marketing claim without this baseline.

### Unit 1 — thin `/awesomeharness` — SHIPPED

- Reduce the skill to the compact loop and tool-routing table above.
- Point to `orient`, `code-decompose`, and `compact-prep`; do not restate their bodies.
- Add idempotence: a repeat invocation returns a short “already active” receipt instead of appending
  the skill again.
- Verify: second invocation adds no full skill body; the coding/audit loop remains discoverable.

### Unit 2 — ambient surface diet — PARTIAL

- Shorten every live skill description to a trigger-only sentence.
- Disable globally unused plugins/MCPs; opt in by repo/task; keep deferred tool search enabled.
- Audit actual tool calls before each removal. Remove repowise MCP, not its two CLI consumers.
- Verify: compare tool/skill prefix size and cache diagnostics before/after.

### Unit 3 — continuity consolidation — INTRN SHIPPED

- For each target repo, inventory unique facts, migrate them to one router + resume + Mulch, archive
  historical state, then remove obsolete auto-read requirements and legacy `.memory` hooks.
- Do intrn first, then Vividlist, then virality-pipeline. One repo per commit and A/B checkpoint.
- Verify: cold-session orientation answers objective/current step/test command correctly without
  opening an archive.

### Unit 4 — map lifecycle

- Keep SessionStart SHA-drift codemap refresh and structural-change refresh; add only freshness
  telemetry/receipt if current behavior cannot be observed.
- Keep Graphify refresh on structural commits. Do not refresh on a daily timer.
- Verify: change a structural fixture, commit, and assert codemap header + graph timestamp advance.

### Unit 5 — README truth pass

- Restore `assets/benchmark-hero.jpeg` under “Historical observational benchmark (July 2026),” not
  as a current causal claim. Link `docs/BENCHMARK.md` and the later ROI/simplification audits.
- Current headline should use defensible facts: 47 -> 6 reminder/enforcement entries before the
  evidence-backed telemetry and duplicate-skill guard were restored; 6,426 transcripts measured;
  silent telemetry emits 0 bytes. Do not claim the harness currently saves 90–95% overall usage.
- Verify every number against its source and label observational/confounded results.

## Cache design

- Keep tools ordered and stable; use deferred loading for occasional MCP tools.
- Keep the top-level system/repo router byte-stable. Put volatile resume/map data after the stable
  prefix when Claude Code exposes a supported placement mechanism; do not invent unsupported hook
  cache controls.
- Treat history as append-only inside a session. Changing tools invalidates the whole prefix;
  changing system content invalidates system + messages.
- Measure `cache_creation_input_tokens` and `cache_read_input_tokens`; a high hit rate is not proof
  of a small context window.

## Acceptance criteria

- >=50% reduction in each target repo's cold-start repo prose + map + tool-schema tokens.
- Repeat `/awesomeharness` does not reinject the body.
- No unused MCP enabled globally or via `enableAllProjectMcpServers`.
- One resume artifact per repo; archive is never part of normal orientation.
- Codemap/Graphify freshness follows repository changes, not the calendar.
- Verified completion and audit-reject/rework rates are no worse than baseline.
- README distinguishes historical observational numbers from current measured behavior.

## Build order

`measurement -> thin skill -> MCP/skill descriptions -> intrn -> Vividlist -> virality -> README`

Stop after each arrow for a measured comparison. If tokens fall but rework rises, revert that unit
instead of compensating with more instructions.

## Parked prior resume item

The pre-existing uncommitted `.now.md` tracked a separate `claude-api` deny verification: confirm
the project-scoped deny blocks in a fresh session, use `shared/prompt-caching.md` directly, then
return to the grep/Semgrep 55:1 routing gap and claim check. This is preserved here rather than
silently discarded by the new resume point.
