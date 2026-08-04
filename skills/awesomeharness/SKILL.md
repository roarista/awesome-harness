---
name: awesomeharness
description: Boot the entire harness for this session in one command. Installs THE PROCEDURE — the standing pipeline every task follows (ORIENT -> RECALL -> UNDERSTAND -> GATE -> DECOMPOSE -> BUILD -> VERIFY -> PERSIST) — plus the canonical map of every harness component. Run at session start, mid-session, or in an already-running session.
---
<!-- MIRROR: copy of ~/.claude/skills/awesomeharness/SKILL.md (authoritative = the live ~/.claude copy). Re-sync: cp ~/.claude/skills/awesomeharness/SKILL.md skills/awesomeharness/SKILL.md -->

# awesomeharness — one-command harness boot

`hooks/caveman-discipline.sh` already injects the contract + FLOOR every SessionStart. `/awesomeharness` turns on what the floor can't deliver: THE PROCEDURE below, the component map, routing table, retired list, invocation report — for this session **and every subagent it spawns**. Skills load from disk at invoke time, so this works mid-session too.

**Running `/awesomeharness` = use ALL of the below by default for the rest of the session. Not a menu.**

---

- **Search intent, not reflex-grep:** `REPO=<repo> tools/retrieve.sh <intent> <query>` — intents `name`/`enumerate`/`exists`/`blast`/`slice`/`verify`/`history`/`diagnose`; routes to the measured winner and forces a receipt. Invariants: `tools/chains/README.md`. (80 real invocations in 14 sessions/30d — this one is used.)

## THE PROCEDURE (the spine)

```
0. ORIENT      .northstar.md + .now.md + STATE resume point (every session;
               .codemap already injected — don't re-derive repo structure by hand)
1-3. RECALL/UNDERSTAND/GATE  `orient` skill (one call) -> memgraph + mulch +
               MEMORY.md (<=5 bullets) -> front door -> both code maps
               (graphify structure/blast + repowise semantics/risk) ->
               ponytail reuse ladder -> REUSE/ADAPT/REJECT -> STOP|PLAN|BUILD
               (STOP is a real outcome: no new code)
4. DECOMPOSE   `code-decompose` -> unit specs CONTEXT/CHANGE/GOAL/VERIFY/REUSE (specs→tasks; decomposition visible, units close sequentially)
5. BUILD       `codex` subagent per unit (NOT codex:codex-rescue — forwarder,
               0 source writes ever) + BUILDER_STANDARD.md prepended. Builds
               with Edit/Write by default (codex CLI only when a unit's
               writes stay entirely inside one repo root).
               Main NEVER writes feature code.
6. VERIFY      non-builder auditor (Opus-4.8-low) per unit -> `check-all`.
               Passes only when every unit auditor = PASS, whole-change
               verifier green, and `check-all` shows no FAIL rows. Short of
               all three -> back to step 5, never step 7.
7. PERSIST     `compact-prep` -> commit, mulch record, .now.md, STATE, push
               + `scaffold-record` if passed. Optional deeper gate before a
               risky ship: `REPO=$(pwd) tools/chains/c7-preship.sh [revspec]`
               (opt-in, not part of `check-all`). CADENCE = per unit: commit +
               push the moment a unit is built AND verified. Integrate before
               pushing, NEVER force/reset — use
               `"$(git rev-parse --show-toplevel)/tools/git-sync.sh"` (absolute).
```

Steps 1-3 = skill `orient`, 4-6 = skill `code-decompose` — 2 skills plus rituals, not 8 things to remember. **Escape hatch:** trivial one-line edits / docs-only wording skip 1-4, never 0/7 — still spawn with an inline `REUSE:`/`REJECT:` verdict; that satisfies understand-gate.

Multi-step / "loop until done" objectives → wrap the procedure in **`/goal`** (SEED -> decomposition -> checklist -> cheap workers + independent verifier + hard stop).

---

## Model / agent routing

`tools/route-model.sh "<task>"` picks agent/model/effort (Ro's override wins), default MEDIUM. Code writes -> **`codex`** (NOT `codex:codex-rescue`, forwarder, zero writes). Audits -> **`codex-audit`** default; **Opus 4.8 low** only as escalation on irreversible work. Councils = Opus-4.8-low + Codex-5.5 (optional 3rd: `gemini`). Spawn mechanics: `docs/HOW_TO_CALL_BUILDERS.md`.

---

## The full map — what the harness has, and what composes with what

Six systems; pieces within each row already wired together — **use the system, not the part.**

### 1. ORIENT + anti-drift
`.northstar.md` · `.now.md` · `.planning/STATE.md` · `templates/FRONT_DOOR.md` · `.codemap` (`tools/codemap.py`, ~1.9k tokens, `path|LOC|symbols` + `#HUB`/`#BIN`/`#DOC`; `hooks/codemap-inject.py` prints at SessionStart, regenerates on `@sha` drift; kill `CODEMAP_INJECT=off`) · STATE-trim in `compact-prep` · `state-distiller.py`.
**Enforced by:** northstar-inject, northstar-protect (BLOCK), now-gate (BLOCK), codemap-inject. **Step 0.**

### 2. MEMORY
**memgraph** + **`orient` Part A** (1-3 lookups) · recall-inject hook · **mulch** (`ml prime`/`ml sync`) · MEMORY_STANDARD.md · **`tools/finding.sh`** (`.findings/<session>/<id>.md`, append-only; `record`/`get`/`list`/`search`) · scaffold-ledger · precompact-handoff.
**One loop:** `prime -> recall -> decide -> record -> handoff -> recall`. `tools/git-sync.sh` is the step-7 push: commit, integrate, push, never force/reset; untracked/conflicts = hard STOP. **Steps 1 and 7.**

### 3. UNDERSTAND-BEFORE-YOU-CODE
**`orient` Part B** owns this layer — front door, both code maps, reuse ladder, blast radius, STOP/PLAN/BUILD gate. Inside it: **graphify** (`update` then `query`/`explain`/`path` + `graphify-blast.sh`; real import graph in the big repos — only awesome-harness is degenerate (imports=1); edge key `links`, field `relation` not `type`) **AND repowise** (per-repo, needs `.mcp.json` + index; else fall back to graphify) **AND semgrep** (complete-set enumeration). Use together: repowise locates/risk, graphify confirms structure/blast, semgrep answers "all the places."
**Enforced by:** understand-gate, graphify-gate (BLOCK), graphify-blindspot, reread-guard (BLOCK), token-discipline. **Steps 1-3.**

### 4. BUILD
**`code-decompose`** (unit specs -> cheap coder per unit -> rotating auditor) · BUILDER_STANDARD.md · ponytail · **`check-all`** (typecheck/lint/test/file-size/TODO/dup + Semgrep SAST ADVISORY, `SEMGREP_STRICT=1` to gate) · 8-line return contract baked into `~/.claude/agents/{codex,codex-audit,opus,gemini}.md` — overflow to `tools/finding.sh record`.
**Enforced by:** main-edit-guard, builder-fence, coding-routing-guard, post-agent-guard, route-only-gate, filesize-cap, manifest-guard, irreversible-pause, check-all-commit-gate. **Steps 4-6.**

### 5. TOKEN DISCIPLINE
caveman discipline · tool-search · token-discipline hook · reread-guard (BLOCK) · filesize-cap · autocompact @60% · stable-files handoff · compact-prep STATE-trim · router slimming · session-checkpoint · `.codemap`. Cross-cutting.

### 6. SELF-IMPROVEMENT
harness-coach (weekly miner) · **`harness-intel`** (Mode A drift, Mode B repetition-mine + research scout via launchd; folds old `harness-audit`/`harness-scout`) · harness-enforce · harness-usage-telemetry · drift-replay · scaffold-ledger · `tools/claudemd-trim.py` (propose-only) · `tools/open-findings.sh` (`OPEN_FINDINGS=0` to kill). **All propose-only. None edit the tree.**

---

## Do NOT route to these (retired / dead)
- **GLM / `glm` subagent + CLI** — retired (out of credits). Never auditor/council; use Opus-4.8-low.
- **`cc-gemini-plugin` (`gemini-agent`)** — dead (missing binary). Real non-Claude voice is `gemini` subagent / `tools/gemini-opencode.sh`.
- **zai / z.ai coding plugin** — dead provider.
- ~~graphify for import-graph questions~~ — RETIRED 2026-08-04, false in every real repo (only
  awesome-harness has imports=1). Most-used tool in the harness (288 calls/30d, 6 repos). Use it.

## Live skill roster (exactly these 10 — anything else stale)
`awesomeharness` `check-all` `code-decompose` `compact-prep` `goal` `harness-intel` `notes-inbox` `orient` `ui-console-debug` `youtube-research`. `codebase-first`/`recall`/`state-trim`/`harness-audit`/`harness-scout` are NOT skills — folded into `orient`/`compact-prep`/`harness-intel`.

## What to do when invoked
1. Run the orientation contract (`.northstar.md` + `.now.md` + STATE resume point); route any write to a cheap (haiku) sub-agent.
2. Run `orient` Part A for task-relevant memory. Verify anything recalled against the live tree.
3. Bootstrap this repo's `.findings/` (idempotent, safe outside git):
   `git rev-parse --is-inside-work-tree >/dev/null 2>&1 && { mkdir -p .findings; command grep -qxF '.findings/' .gitignore 2>/dev/null || echo '.findings/' >> .gitignore; }`
   First boot in THIS repo: `REPO=$(pwd) tools/chains/c0-preflight.sh` — reports which chains are trustworthy here before trusting any verdict.
4. Report "harness up" as exactly these 7 lines, no hook-name enumeration:
```
NORTH STAR: …
NOW: …
RECALL: <=2 bullets
PROCEDURE: armed (0-7)
FLOOR: blocking hooks armed, understand-gate=warn
FINDINGS: .findings/ ready (N prior)
NEXT: <the task>
```
5. From then on: **every code task walks THE PROCEDURE.** Announce the step only in the final summary, never mid-turn.

## Ponytail note
Router: announcement + procedure + map. Invokes hooks/skills, never re-implements. Duplicating a skill here -> delete, point at the skill.
