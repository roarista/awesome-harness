---
name: awesomeharness
description: Boot the entire harness for this session in one command. Reads orientation, re-asserts the operating rules, and installs THE PROCEDURE — the standing pipeline every task follows (ORIENT -> RECALL -> UNDERSTAND -> GATE -> DECOMPOSE -> BUILD -> VERIFY -> PERSIST). Also the canonical map of every harness component and which ones compose. Run at session start, mid-session, or in an already-running session.
---

<!-- MIRROR: copy of ~/.claude/skills/awesomeharness/SKILL.md (authoritative = the live ~/.claude copy). Re-sync: cp ~/.claude/skills/awesomeharness/SKILL.md skills/awesomeharness/SKILL.md -->
# awesomeharness — one-command harness boot

The hooks enforce a floor automatically. Most of the harness is **behavioral** — it only happens if the agent does it. `/awesomeharness` turns the whole thing on for this session **and every subagent it spawns**. Skills load from disk at invoke time, so this works in an already-running session (it can't add new *hooks* to a live process — it activates the behavioral layer + rituals).

**Running `/awesomeharness` means: use ALL of the below, by default, for the rest of the session. Not a menu — the default operating mode.**

---

## NON-NEGOTIABLE

1. **Start from `.codemap`, not exploratory search.** `hooks/codemap-inject.py` already printed the whole repo (files/LOC/symbols, `#HUB`/`#BIN`/`#DOC`) at SessionStart. Grepping/`find`/`ls` to learn what exists is waste — the map is a map, not proof, so a load-bearing claim still needs a real read or semgrep hit.
2. **State the search INTENT and go through `tools/retrieve.sh`.** Never reflex-grep.
3. **"All the places where X" is a semgrep question, never a grep question.** `~/.local/bin/semgrep` is the only tool measured to return a COMPLETE set; `tools/retrieve.sh enumerate` routes to it with a COUNT. Trap: a rule pattern containing `:` must be QUOTED in the YAML or the config is silently invalid — 0 results, 2 errors, no crash.
4. **Main orchestrates and never writes feature code.** Code writes go to the `codex` subagent.
5. **Every spawn carries a full unit spec; every return obeys the 8-line contract.** The contract lives IN the agent definitions (`~/.claude/agents/{codex,codex-audit,opus,gemini}.md`) — no need to retype it, unit spec is still the caller's job. Overflow -> `tools/finding.sh record`; return only the id + one-line summary.
6. **A claim about repo state carries its receipt** — the exact command and its real output — or it does not enter a commit, handoff, or summary.
7. **Every turn ends compaction-safe:** `.now.md` + STATE resume point updated, memory/mulch synced, final message names what was saved.

---

## THE PROCEDURE (the spine)

```
0. ORIENT      .northstar.md + .now.md + STATE resume point (every session;
               .codemap already injected — don't re-derive repo structure by hand)
1-3. RECALL/UNDERSTAND/GATE  `orient` skill (one call) -> memgraph + mulch +
               MEMORY.md (<=5 bullets) -> front door -> both code maps
               (graphify structure/blast + repowise semantics/risk) ->
               ponytail reuse ladder -> REUSE/ADAPT/REJECT -> STOP|PLAN|BUILD
               (STOP is a real outcome: no new code)
4. DECOMPOSE   `code-decompose` -> unit specs CONTEXT/CHANGE/GOAL/VERIFY/REUSE
5. BUILD       `codex` subagent per unit (NOT codex:codex-rescue — forwarder,
               0 source writes ever) + BUILDER_STANDARD.md prepended.
               Main NEVER writes feature code.
6. VERIFY      non-builder auditor (Opus-4.8-low) per unit -> `check-all`.
               Passes only when every unit auditor = PASS, whole-change
               verifier green, and `check-all` shows no FAIL rows. Short of
               all three -> back to step 5, never step 7.
7. PERSIST     `compact-prep` -> commit, mulch record, .now.md, STATE, push
               + `scaffold-record` if it passed. CADENCE = per unit: commit +
               push the moment a unit is built AND verified. Integrate before
               pushing, NEVER force/reset — use
               `"$(git rev-parse --show-toplevel)/tools/git-sync.sh"` (absolute).
```

Steps 1-3 are one skill (`orient`), 4-6 are one skill (`code-decompose`) — 2 skills plus rituals, not 8 things to remember. **Escape hatch:** trivial one-line edits and docs-only wording skip 1-4, never 0/7 — still spawn with an inline `REUSE:`/`REJECT:` verdict; that satisfies understand-gate.

Multi-step / "loop until done" objectives → wrap the procedure in **`/goal`** (SEED -> decomposition -> checklist -> cheap workers + independent verifier + hard stop).

---

## Operating rules (re-assert with force — these decay)

**Invoking this skill mid-session RE-ASSERTS the SessionStart floor** — the remedy when discipline has decayed, because the boot block is out of recent context by then. The per-turn hook line is only a recall pointer; the full contract is stated here.

- **Caveman:** ZERO intermediate chat between/alongside tool calls. Call tools silently. Urge to narrate -> ONE caveman line to `$CLAUDE_JOB_DIR/tmp/pending.md`, never chat.
- **Final-summary shape:** exactly ONE chat message per turn, thorough and standalone — changes, verification, pending, decisions. Expand every `pending.md` line into it.
- **Compaction-safe close, every turn (`compact-prep`):** `.now.md` + STATE resume point updated, memory/mulch synced, final message names what was saved. Route those writes to a cheap (haiku) sub-agent.
- **Orientation contract:** read `.northstar.md` + `.now.md` + STATE resume point before deep work. Missing north star -> ask Ro for the destination first.
- **Ponytail:** laziest solution that works — YAGNI -> stdlib -> native -> installed dep -> one line.
- **Search intent, not reflex-grep:** `REPO=<repo> tools/retrieve.sh <intent> <query>` — intents `name`/`enumerate`/`exists`/`blast`/`slice`/`verify`/`history`/`diagnose`; routes to the empirical winner, forces a receipt. Invariants: `tools/chains/README.md`.
- **Model routing:** `tools/route-model.sh` picks agent/model/effort (Ro's override wins); spawn mechanics in `docs/HOW_TO_CALL_BUILDERS.md`.
- **Orchestrate, don't build:** code writes -> **`codex`** subagent (NOT `codex:codex-rescue` — forwarder, zero writes ever). Audits -> **`codex-audit`** by default; **Opus 4.8 low** only as escalation on irreversible work (money/auth/credentials/data-loss). Councils = Opus-4.8-low + Codex-5.5 (optional 3rd: `gemini`). Default effort MEDIUM. `bash-write-fence` blocks main's Bash writes too (kill `BASH_WRITE_FENCE=off`).
- **Main stays on Anthropic:** never point `ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN`/`ANTHROPIC_MODEL` at a third party.
- **Memory standard:** mulch <=2 sentences, overflow -> `.mulch/details/<slug>.md` — read the detail file before diagnosing.
- **Spawn discipline:** `spawn-necessity` checks every spawn against `tools/route-model.sh`; silent unless `DO-NOT-LAUNCH` or a mismatch; asks once at spawn #8. Kill `SPAWN_NECESSITY=off`.

---

## The full map — what the harness has, and what composes with what

Six systems; pieces within each row already wired together — **use the system, not the part.**

### 1. ORIENT + anti-drift
`.northstar.md` · `.now.md` · `.planning/STATE.md` · `templates/FRONT_DOOR.md` · `.codemap` (`tools/codemap.py` — whole repo, ~1.9k tokens, `path|LOC|symbols` by directory + `#HUB`/`#BIN`/`#DOC`; `hooks/codemap-inject.py` prints at SessionStart, regenerates on `@sha` drift; kill `CODEMAP_INJECT=off`) · STATE-trim folded into `compact-prep` · `state-distiller.py`.
**Enforced by:** northstar-inject, northstar-protect (BLOCK), now-gate (BLOCK), codemap-inject. **Step 0.**

### 2. MEMORY
**memgraph** + **`orient` Part A** (1-3 lookups) · recall-inject hook · **mulch** (`ml prime`/`ml sync`) · MEMORY_STANDARD.md · **`tools/finding.sh`** (findings ledger, `.findings/<session>/<id>.md`, append-only; `record`/`get`/`list`/`search`) · scaffold-ledger · precompact-handoff.
**One loop:** `prime -> recall -> decide -> record -> handoff -> recall`. `tools/git-sync.sh` is the step-7 push: commit, integrate, push, never force/reset; untracked/conflicts = hard STOP. **Steps 1 and 7.**

### 3. UNDERSTAND-BEFORE-YOU-CODE
**`orient` Part B** owns this layer — front door, both code maps, reuse ladder, blast radius, STOP/PLAN/BUILD gate. Inside it: **graphify** (`update` then `query`/`explain`/`path` + `graphify-blast.sh`; `graph.json` has almost no import graph — `imports_from=1` vs `contains=498`/`calls=303`/`references=62` — never ask it "what is a hub"; edge key `links` not `edges`) **AND repowise** (per-repo, needs `.mcp.json` + index; else fall back to graphify) **AND semgrep** (complete-set enumeration). Use together: repowise locates/risk, graphify confirms structure/blast, semgrep answers "all the places."
**Enforced by:** understand-gate, graphify-gate (BLOCK), graphify-blindspot, reread-guard (BLOCK), token-discipline. **Steps 1-3.**

### 4. BUILD
**`code-decompose`** (unit specs -> cheap coder per unit -> rotating auditor) · BUILDER_STANDARD.md · ponytail · **`check-all`** (typecheck/lint/test/file-size/TODO/dup + Semgrep SAST ADVISORY, `SEMGREP_STRICT=1` to gate) · 8-line return contract, baked into `~/.claude/agents/{codex,codex-audit,opus,gemini}.md` — overflow to `tools/finding.sh record`.
**Enforced by:** main-edit-guard, builder-fence, coding-routing-guard, post-agent-guard, route-only-gate, filesize-cap, manifest-guard, irreversible-pause, check-all-commit-gate. **Steps 4-6.**

### 5. TOKEN DISCIPLINE
caveman discipline · tool-search (`ENABLE_TOOL_SEARCH`) · token-discipline hook · reread-guard (BLOCK) · filesize-cap · autocompact @60% · stable-files handoff · compact-prep STATE-trim · router slimming · session-checkpoint · `.codemap` (front-loads structure so step-0 doesn't burn tokens re-deriving it). Cross-cutting.

### 6. SELF-IMPROVEMENT
harness-coach (weekly transcript miner) · **`harness-intel`** (Mode A drift report, Mode B repetition-mine + research scout via launchd; folds the old `harness-audit`/`harness-scout` skills) · harness-enforce · harness-usage-telemetry · drift-replay · scaffold-ledger · `tools/claudemd-trim.py` (propose-only CLAUDE.md diet, staged not loaded) · `tools/open-findings.sh` (`OPEN_FINDINGS=0` to kill).
**All propose-only. None edit the tree.**

---

## The floor that's already armed (announce, don't re-implement)

- **BLOCKING (exit 2):** reread-guard · filesize-cap · now-gate · main-edit-guard · builder-fence · bash-write-fence (`BASH_WRITE_FENCE=off` to kill) · northstar-protect · irreversible-pause · compact-prep-gate · check-all-commit-gate. graphify-gate + route-only-gate armed but fire only in a graphify repo / `.route-only` repo.
- **Scope limit:** main-edit-guard/route-only-gate cover `Write|Edit|MultiEdit` ONLY. `bash-write-fence` is a nudge not a sandbox; real backstop is `builder-fence.postflight()`'s diff review + the audit step. For true enforcement use a `deny` permission rule or a pre-commit hook.
- **ADVISORY:** caveman-discipline · northstar-inject · harness-enforce · recall-inject · coding-routing-guard · understand-gate (`warn`; `UNDERSTAND_GATE=enforce` -> BLOCK) · post-agent-guard · token-discipline · graphify-blindspot · manifest-guard · session-checkpoint · harness-usage-telemetry · precompact-handoff · abs-path-nudge · phantom-edit-guard · skill-reinject-guard · spawn-necessity (`SPAWN_NECESSITY=off`).

## Do NOT route to these (retired / dead)
- **GLM / `glm` subagent + CLI** — retired (out of credits). Never auditor/council; use Opus-4.8-low.
- **`cc-gemini-plugin` (`gemini-agent`)** — dead (missing binary). Real non-Claude voice is `gemini` subagent / `tools/gemini-opencode.sh`.
- **zai / z.ai coding plugin** — dead provider.
- **graphify for "what is a hub" / import-graph questions** — see system 3; use repowise or semgrep.

## Live skill roster (exactly these 10 — anything else is stale)
`awesomeharness` `check-all` `code-decompose` `compact-prep` `goal` `harness-intel` `notes-inbox` `orient` `ui-console-debug` `youtube-research`. `codebase-first`/`recall`/`state-trim`/`harness-audit`/`harness-scout` are NOT skills — folded into `orient`, `compact-prep`, `harness-intel`.

## What to do when invoked
1. Run the orientation contract (`.northstar.md` + `.now.md` + STATE resume point); route any write to a cheap (haiku) sub-agent.
2. Run `orient` Part A for task-relevant memory. Verify anything recalled against the live tree.
3. Report "harness up" as exactly these 6 lines, no more, no hook-name enumeration:
```
NORTH STAR: …
NOW: …
RECALL: <=2 bullets
PROCEDURE: armed (0-7)
FLOOR: blocking hooks armed, understand-gate=warn
NEXT: <the task>
```
4. From then on: **every code task walks THE PROCEDURE.** Announce the step only in the final summary, never mid-turn.

## Ponytail note
This file is a **router**: announcement + procedure + map. It does not re-implement what hooks or skills already do — it invokes them. If a section starts duplicating a skill, delete it and point at the skill.
