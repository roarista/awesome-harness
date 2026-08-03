---
name: harness-intel
description: Recurring harness intelligence pass, proposal-only, two modes. (A) AUDIT — map one repo's harness (CLAUDE.md, front-door docs, mulch, STATE, agent specs) against the REAL codebase and produce a fidelity/behavioral drift report. (B) SCOUT — mine Ro's recent transcripts for repeated toil to automate, and research external ideas (GitHub, AI-lab frameworks, YouTube creators, newsletters) worth stealing. Use when Ro says "audit the harness", "/harness-audit", "scout the harness", "what should we steal", "what am I repeating that should be a skill", "check <repo> for drift", or on a periodic improvement sweep. NEVER edits the live tree — output is always a report Ro reviews.
---

<!-- MIRROR: copy of ~/.claude/skills/harness-intel/SKILL.md (authoritative = the live ~/.claude copy). Re-sync: cp ~/.claude/skills/harness-intel/SKILL.md skills/harness-intel/SKILL.md -->

# harness-intel — audit (inward) + scout (outward), proposal-only

Two directions, one discipline: evidence-cited, proposal-only, fit-filtered, never edits the live tree. **AUDIT** asks "does the harness do what it says?" (fidelity + behavioral drift) for ONE named repo. **SCOUT** asks "what should we add?" — either by turning Ro's repeated toil into a skill/hook, or stealing an external idea. Pick the mode from Ro's phrasing; if ambiguous, ask.

## Hard rules (both modes, non-negotiable)
1. **Proposal-only. Never edit the target repo, or any repo.** AUDIT output -> `~/Downloads/HARNESS_DRIFT_<repo>_<date>.md`. SCOUT output -> `~/Downloads/HARNESS_SCOUT_<date>.md`. Ro reviews; a normal session applies/builds later.
2. **One cheap read-only agent at a time** (low-CPU, no VM — `[[feedback-low-cpu-no-vm]]`). Don't fan out N agents. Kill worker process trees on finish.
3. **Evidence or it didn't happen (R1).** Every finding cites `file:line` / transcript / URL+date / command output read THIS run. Unverifiable -> UNKNOWN, never guessed.
4. **Don't race live sessions.** Reading is fine; never write, branch, push, or run `ml compact`/`prune` against a repo whose loop may be appending. Note if the tree is dirty.
5. **Fit-filter every idea against OUR constraints (SCOUT) / every fix against real evidence (AUDIT) — no hype, no ungrounded brainstorm.** We run API models (Claude/Codex 5.5), low-CPU no-VM no-GPU hardware, ambient hooks+skills not a framework. An idea needing GPU/weights/server/heavy runtime is NON-FIT, say so. A fix with no cited drift/bad-behavior is speculation, capped at 3 bullets in a fenced `## Out-of-scope observations (speculative)` section, never in the findings table.

## Mode A — AUDIT (inward: one repo vs reality)

**Inputs:** target repo path (resolve nicknames: intrn -> `~/Downloads/intrn`; Vividlist/Previz -> `~/Downloads/Vividlist`; forclosurehomes -> `~/Downloads/forclosurehomes`; virality -> `~/Downloads/virality-pipeline`). Cross-repo baseline: `~/.claude/projects/-Users-rodrigoarista/memory/global_orchestration_rules.md`.

1. **Scope.** `cd` in, `git status --porcelain | head` (dirty tree = propose now, apply when clean), record branch/worktree.
2. **Deterministic pre-pass (no agent).** `python3 ~/.claude/tools/check-all/claudemd_drift.py <repo>` (dead doc pointers) and `python3 ~/.claude/tools/claudemd-trim.py <repo>` (KEEP/TRIM/DELETE/STALE-WRONG line classification, propose-only, omit `--refresh` on a live tree). Confirm `<repo>/graphify-out/graph.json` is fresh (`graphify diagnose`); tell the step-3 agent to query it, not cold-grep.
3. **Spawn ONE read-only mapper agent** with the repo path + step-2 output. It checks, each with `file:line` evidence: CLAUDE.md claims vs code reality; front-door freshness (`.planning/STATE.md` current/oversized >200KB?); model-routing accuracy (Codex codes, Sonnet reviews, no stale Sonnet-coder specs); loop/skill conventions; mulch health (200/domain cap, duplicates); MCP/tool bloat; dead-doc burial. **Beyond docs — behavioral verification** (a claim is only true if it FIRES): wired-vs-firing (hook in `settings.json` AND appears in last ~5 transcripts?), rules-claimed-vs-obeyed (e.g. does main edit source despite "orchestrator delegates"? cite turns), claimed-numbers-vs-reality (token/compaction win still holding?), injected-context health. Unverifiable this pass -> UNKNOWN.
4. **Synthesize** `~/Downloads/HARNESS_DRIFT_<repo>_<date>.md`: Summary (N drifts, severity split, tree-clean status) -> Findings table (kind: fidelity-drift | behavioral-gap -> evidence -> proposed fix -> severity BLOCKER/HIGH/LOW -> confidence) -> Proposed edits (concrete before/after) -> Idle-only queue (mulch compaction, STATE rotation) -> Apply checklist -> optional speculative section (<=3 bullets).
5. **Hand back:** report path, headline drift count, single highest-value fix. Apply nothing.
6. **Record (optional):** if a recurring drift pattern emerged, `ml record` it when idle.

**Audit-cadence sweeps, not hot-path — run as part of an AUDIT pass, not per-task:** `REPO=<repo> tools/chains/c5-dead.sh [min-confidence]` (dead-code, safe-to-delete candidates) and `REPO=<repo> tools/chains/c6-vestigial.sh` (declared-but-never-used dependencies).

**When NOT to run AUDIT:** mid-implementation of an unrelated task; a repo with no harness yet; as an auto-fixer.

## Mode B — SCOUT (outward: what to add)

North star: get Ro out of the loop while keeping quality.

**Sub-mode A1 — Repetition-mine (toil -> skill/hook).**
1. Corpus: `~/.claude/projects/-Users-rodrigoarista/*.jsonl` + the live repos' project dirs, last ~2-4 weeks.
2. Signal: repeated instructions (recurrence = hook/skill candidate), recurring manual sequences, repeated corrections (-> enforcement hook, the behavioral-gap pattern).
3. Classify: already covered by an existing skill/hook (list first, don't re-propose) vs new. Cite turns.
4. Rank by loop-exit value = (frequency) x (mechanizable) - (slop risk).

**Sub-mode B1 — Research-scout (external steal).**
- **Read prior reports first** — the 4 most recent `~/Downloads/HARNESS_SCOUT_*.md`; tag findings `[NEW]` or `[REPEAT n + STATUS]`; don't re-propose an unlabelled prior finding.
- **GitHub, last 30 days:** `gh search repos --sort=updated 'claude code agent harness'` etc, README-only, no clone/execution, <=5 repos per area (harness/agent eng, agent memory/context, token reduction, prompt eng, notable-this-week).
- **AI-lab frameworks:** what Anthropic/OpenAI/Cognition published recently, OSS liftable.
- **Creators:** route to `youtube-research`/`ytintel` per the PRIMARY/SECONDARY/ADJACENT channel list (Jaymin West, IndyDevDan, Simon Scrapes, etc — full list in prior HARNESS_SCOUT reports; refresh from Ro's @yummapp subs occasionally).
- **Newsletters:** Gmail MCP search `from:(morningbrew OR "the rundown") newer_than:7d`.
- **Notion idea inbox:** `📥 Video Inbox` DB, Status=New, grouped by Project — reuse the existing `notes-inbox` pipeline, don't rebuild it.
- Reuse `deep-research` (or, if the Vividlist symlink is broken, note that and do a bounded direct web fan-out) for heavy web fan-out+verify+synthesis.
- Fit-filter each candidate -> **STEAL** (lift into a hook/skill in ~N lines) / **INTEGRATE** (OSS worth adding, argue dep cost) / **WATCH** (not now) / **NON-FIT** (state the GPU/weights/server blocker).

**Output** `~/Downloads/HARNESS_SCOUT_<date>.md`: Summary -> A. Repetition->automate table -> B. External steal-worthy table (grouped by theme) -> C. Creator intel -> GitHub radar (per area, README-only) -> Ranked "build next" shortlist (top 3-5, one-line why + effort). Report lands in `~/Downloads/`, auto-indexed into recall via `~/.claude/tools/memgraph/sources.txt`'s `HARNESS_*` glob.

**Cadence:** on demand; A1 already folds into `harness-coach`'s weekly log-audit rather than a second cron. B1 (web research) is token-heavy — run when asked, bounded.

**When NOT to run SCOUT:** mid-implementation of an unrelated task; as an auto-applier; to chase one tool Ro already decided on.
