---
name: awesomeharness
description: Boot the entire harness for this session in one command. Reads orientation, re-asserts the operating rules, and installs THE PROCEDURE — the standing pipeline every task follows (ORIENT -> RECALL -> UNDERSTAND -> GATE -> DECOMPOSE -> BUILD -> VERIFY -> PERSIST). Also the canonical map of every harness component and which ones compose. Run at session start, mid-session, or in an already-running session.
---

# awesomeharness — one-command harness boot

The hooks enforce a floor automatically. Most of the harness is **behavioral** — it only happens if the agent does it. `/awesomeharness` turns the whole thing on for this session **and every subagent it spawns**.

Skills load from disk at invoke time, so **this works in an already-running session**. (It cannot add new *hooks* to a live process; it activates the behavioral layer + rituals and announces the floor.)

**Running `/awesomeharness` means: use ALL of the below, by default, for the rest of the session. Not a menu — the default operating mode.**

---

## THE PROCEDURE (the spine — follow it for every non-trivial task)

```
0. ORIENT      .northstar.md + .now.md + STATE resume point        (every session)
1. RECALL      `recall` skill -> memgraph + mulch + MEMORY.md       (before deciding)
2. UNDERSTAND  `codebase-first` -> front door -> BOTH code maps
               (graphify structure/blast + repowise semantics/risk,
               refreshed) -> ponytail reuse ladder -> REUSE/ADAPT/REJECT
3. GATE        STOP | PLAN | BUILD  (STOP is a real outcome: no new code)
4. DECOMPOSE   `code-decompose` -> unit specs CONTEXT/CHANGE/GOAL/VERIFY/REUSE
5. BUILD       codex subagent per unit (+ BUILDER_STANDARD.md prepended).
               Main NEVER writes feature code.
6. VERIFY      non-builder auditor (Opus-4.8-low) per unit -> `check-all`
7. PERSIST     `compact-prep` -> commit, mulch record, .now.md, STATE, push
               + `scaffold-record` if it passed (capture the approach)
```

Steps 2-3 are one skill (`codebase-first`), 4-6 are one skill (`code-decompose`) — the procedure is 2 skills plus rituals, not 8 things to remember. **Escape hatch:** genuinely trivial one-line edits and docs-only wording skip 2-4, never 0/1/7.

Multi-step / "loop until done" objectives → wrap the whole procedure in **`/goal`** (SEED -> maximal decomposition -> verifiable checklist -> cheap workers + independent verifier + hard stop conditions).

---

## The operating rules (re-assert with force — these decay)

- **Message discipline / caveman:** ZERO intermediate chat. Call tools silently. Urge to narrate -> ONE caveman line to `$CLAUDE_JOB_DIR/tmp/pending.md`, never chat. The ONLY chat output is ONE thorough, standalone final summary per turn (Ro reads only that).
- **Ponytail (always-on lens, not a step):** laziest solution that works — YAGNI -> stdlib -> native -> installed dep -> one line. Delete > add. Shortest diff. No speculative abstraction.
- **Orchestrate, don't build:** main routes and reviews. Code writes -> **codex** subagent; **Opus 4.8 (low effort)** audits. Councils / second opinions = **Opus-4.8-low + Codex-5.5** (optional 3rd: the `gemini` subagent). Default subagent effort = MEDIUM. Main may directly edit only `.now`/`.northstar`/STATE/memory and tiny harness tweaks.
- **Main stays on Anthropic:** never set `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_MODEL` to a third party for the main session.
- **Compaction-safe every turn:** update `.now.md` (<=5 lines) + STATE resume point, sync memory/mulch; state in the final message what was saved and the exact resume point.
- **Memory standard:** mulch records <=2 sentences, overflow -> `.mulch/details/<slug>.md`; **read the detail file before you diagnose.** STATE trimmed to current scope, history archived never deleted.

---

## The full map — what the harness has, and what composes with what

Six systems. Within each row, the pieces are already wired to each other; **use the system, not the individual part.**

### 1. ORIENT + anti-drift *(where are we, and are we still going there)*
`.northstar.md` (OBJECTIVE/DONE_WHEN/NOT_NOW, re-injected every turn) · `.now.md` (NOW/LAST_VERIFIED/NEXT) · `.planning/STATE.md` resume point · `templates/FRONT_DOOR.md` (the single read-first doc) · **state-trim** (STATE bloat -> archive) · `state-distiller.py` (deterministic cap, manual CLI).
**Enforced by:** northstar-inject (every turn), northstar-protect (BLOCK: agent can't edit its own goal), now-gate (BLOCK), new-project nudge.
**Procedure step 0.** These are one file-set with one job — read all three at boot, update all three at close.

### 2. MEMORY *(start warm, never re-derive)*
**memgraph** (FTS + link graph over markdown memory) · **`recall` skill** (1-3 lookups, the front end to memgraph) · recall-inject hook (auto-surfaces 1-3 records/turn) · **mulch** (per-repo decisions/conventions/failures; `ml prime` / `ml sync`) · **MEMORY_STANDARD.md** (the write conventions) · **scaffold-ledger** (`scaffold-record.py` — captures the *approach* that passed, promote-on-beat) · **precompact-handoff** (7-field handoff + monotonic ratchet + stable-files list).
**These are ONE loop:** `prime -> recall -> decide -> record -> distill -> handoff -> recall`. Anti-drift and memory are the same system viewed from two ends — memory is what makes step 0 cheap.
**Procedure steps 1 and 7.**

### 3. UNDERSTAND-BEFORE-YOU-CODE *(the pre-code map)*
**`codebase-first`** owns this entire layer — front door, both code maps, the ponytail reuse ladder, downstream contract, blast radius, the empirical probe, and the STOP/PLAN/BUILD gate.
Inside it: **graphify** (deterministic structural graph — `update` then `query`/`explain`/`path`, + `graphify-blast.sh` for blast radius) **AND repowise** (semantic/risk/history MCP — `get_answer`/`get_context`/`search_codebase`/`get_symbol`/`get_why`/`get_risk`). **Use both together: repowise to locate + understand + gauge risk, graphify to confirm exact structure + blast.** Refresh first; neither is authority — verify load-bearing claims against real source ranges.
**Enforced by:** graphify-gate (BLOCK in graphify repos), graphify-blindspot (advisory: editing a hub whose callers you never opened), reread-guard (BLOCK), token-discipline.
**Procedure steps 2-3.** Do not chain graphify/repowise/blast by hand — `codebase-first` sequences them.

### 4. BUILD *(better code from cheaper models)*
**`code-decompose`** (unit specs -> one cheap coder per unit -> rotating non-builder auditor) · **BUILDER_STANDARD.md** (<40-line correctness/boundary ruleset prepended to every coder prompt) · **ponytail** (the lens over all of it) · **`check-all`** (deterministic gate: typecheck/lint/test/file-size/TODO/dup + **Semgrep SAST as ADVISORY** — it suggests ERROR-severity patterns with reasons, never blocks; `SEMGREP_STRICT=1` to gate).
**Enforced by:** main-edit-guard (BLOCK — main cannot edit code), builder-fence (BLOCK), coding-routing-guard, post-agent-guard, route-only-gate, filesize-cap (BLOCK), manifest-guard, irreversible-pause (BLOCK), check-all-commit-gate.
**Procedure steps 4-6.**

### 5. TOKEN DISCIPLINE *(pay for less of the same thing)*
caveman/message discipline · **tool-search** (MCP schema deferral, `ENABLE_TOOL_SEARCH`) · token-discipline hook (warns on the 3rd full re-read) · reread-guard (BLOCK) · filesize-cap · autocompact @ 60% · stable-files handoff ("already seen, don't re-read") · state-trim/distiller · router slimming (CLAUDE.md stays a router, not an encyclopedia — cache-prefix stability is where ~90% of the savings live) · session-checkpoint (>=150 calls / >=25 errors / same command 3x -> re-scope nudge).
**Cross-cutting** — applies to every step.

### 6. SELF-IMPROVEMENT *(the harness improves itself, proposal-only)*
**harness-coach** (weekly deterministic transcript miner -> ranked report tagged NEW/IMPROVE/ALREADY-COVERED) · **harness-scout** (repetition-mine + external research scout; daily via `run-harness-scout.sh` + launchd `StartInterval`, once-per-day guard, fires on wake) · **harness-audit** (per-repo drift report vs the real codebase) · harness-enforce (anti-decay re-injection) · harness-usage-telemetry · drift-replay (measure a candidate judge before building it) · scaffold-ledger (verify -> capture -> recall -> beat -> replace).
**All propose-only. None of them edit the tree.** Reports land in `~/Downloads/`.

---

## The floor that's already armed (announce, don't re-implement)

- **BLOCKING (exit 2):** reread-guard · filesize-cap · now-gate · main-edit-guard (`MAIN_EDIT_GUARD=enforce`) · builder-fence (`BUILDER_FENCE=enforce`) · northstar-protect · irreversible-pause · compact-prep-gate · check-all-commit-gate (per-repo opt-in). graphify-gate + route-only-gate are armed but fire only in a graphify repo / a `.route-only` repo.
- **ADVISORY:** caveman-discipline · northstar-inject · harness-enforce · recall-inject · coding-routing-guard · post-agent-guard · token-discipline · graphify-blindspot · manifest-guard · session-checkpoint · harness-usage-telemetry · precompact-handoff · pre_compact_global · abs-path-nudge · senduserfile-path-echo · phantom-edit-guard (`log`).

## Do NOT route to these (retired / dead — excluded on purpose)
- **GLM / `glm` subagent + CLI** — retired (out of credits). Never an auditor/council option; use Opus-4.8-low.
- **`cc-gemini-plugin` (`gemini-agent`)** — dead (missing binary). The real non-Claude voice is the **`gemini` subagent** / `tools/gemini-opencode.sh`.
- **zai / z.ai coding plugin** — dead provider.
- **ctxproxy** — removed entirely (it broke Remote Control). Do not reintroduce.

## What to do when invoked

1. Read `.northstar.md` + `.now.md` (+ STATE resume point). Missing north star -> ask Ro for the one-sentence destination and write it before deep work.
2. Run `recall` for task-relevant memory. Verify anything recalled against the live tree.
3. Report a **6-8 line "harness up"** confirmation: north star, current NOW, what recall surfaced, the procedure is armed, which floor hooks are live. Then get to the actual task.
4. From then on: **every code task walks THE PROCEDURE.** Announce the step you're on only in the final summary, never mid-turn.

## Ponytail note
This file is a **router**: announcement + procedure + map. It does not re-implement what the hooks enforce or what the individual skills do — it invokes them. If a section starts duplicating a skill, delete it and point at the skill.
