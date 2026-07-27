---
name: awesomeharness
description: Boot the FULL harness in one command. Run at the start of a session (or any time behavior has drifted) to load orientation, re-assert the operating rules with force, announce which guardrails are armed, and route the work correctly. Activates on "/awesomeharness", "boot the harness", "load the harness", "scale up", or the first substantive request of a cold/post-compaction session. This is the on-demand activation layer; the hooks are the always-on floor.
---

# awesomeharness — one-command harness boot

The hooks enforce a floor automatically, but a lot of the harness is *behavioral* — it only happens if the agent actually does it. `/awesomeharness` is the switch that turns the whole thing on for this session (and every subagent it spawns). Run it, then work normally.

A skill file is read from disk at invoke time, so **`/awesomeharness` works in an already-running session** — just type it. (It cannot add new hooks to a live process; it activates the behavioral layer + rituals and announces the floor.)

## What to do when invoked

Do these in order, fast, then report a 6-8 line "harness up" confirmation and get to the actual task.

### 1. Orient (never skip)
- Read `.northstar.md` (the one-line destination) and `.now.md` (NOW / LAST_VERIFIED / NEXT). If either is missing, ask Ro for the one-sentence destination and write it before deep work.
- Run the `recall` skill (or let recall-inject surface it) for task-relevant durable memory. Verify anything recalled against the live tree before acting on it.

### 2. Re-assert the operating rules (with force — these decay)
- **Message discipline / caveman:** ZERO intermediate chat. Call tools silently. Urge to narrate → one caveman line to `$CLAUDE_JOB_DIR/tmp/pending.md`, never chat. The ONLY chat output is ONE thorough final summary per turn (Ro reads only that).
- **Ponytail:** laziest solution that works — YAGNI → stdlib → native → installed dep → one line. Delete > add. Shortest diff. No speculative abstraction.
- **Orchestrate, don't build:** main routes and reviews; it does not write feature/app code. Code writes → a **codex** subagent; **Opus 4.8 (low effort)** audits. Councils / second opinions = **Opus-4.8-low + Codex-5.5** (optional 3rd: the `gemini` subagent). Main may directly edit only orientation files (`.now`/`.northstar`/STATE/memory) and tiny harness tweaks.
- **Main stays on Anthropic:** never set `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_MODEL` to a third party for the main session.
- **Compaction-safe every turn:** update `.now.md` (≤5 lines) + the STATE resume point, sync memory; state in the final message what was saved and the exact resume point.

### 3. Before writing any code — reflexes
- **Run `codebase-first`** — the single orient pipeline: front door → **map (graphify for structure/blast + repowise for how/why/risk, used together, refresh first)** → ponytail reuse ladder → REUSE/ADAPT/REJECT table → **STOP/PLAN/BUILD** gate. It owns map-selection + blast radius; ponytail is the always-on lens over it.
- **Then `code-decompose`** consumes that gate + gap: unit specs (CONTEXT/CHANGE/GOAL/VERIFY/REUSE) in a disposable subagent → codex builds each → a non-builder audits. It *calls* codebase-first, it does not re-describe it.

### 4. For a multi-step objective — use `/goal`
For "loop until done" / autonomous multi-step work, prefer the **`goal`** skill (strong SEED → maximal decomposition → verifiable checklist → cheap workers + independent verifier + hard stop conditions, interruptible) over hand-prompting each step. Give it detailed success criteria and an explicit "come to Ro if blocked" escape.

Other harness skills on tap (invoke by name when relevant): **harness-scout** / **harness-audit** (proposal-only: steal-worthy ideas + repo-drift reports, never edit the tree), **state-trim** (shrink STATE.md to the active workstream), **check-all** (the readiness gate below).

### 5. Close the turn
- Run the **compact-prep** ritual (commit → record → update `.now.md`/STATE → push) before stopping.

## The floor that's already armed (announce, don't re-implement)

These fire automatically via hooks — name them so the session knows the guardrails:
- **BLOCKING:** reread-guard, filesize-cap, now-gate, main-edit-guard (`MAIN_EDIT_GUARD=enforce` — main can't edit code), builder-fence (`BUILDER_FENCE=enforce`), northstar-protect, irreversible-pause, compact-prep-gate, check-all-commit-gate (per-repo opt-in). graphify-gate + route-only-gate are armed but fire only in a graphify repo / a repo with a `.route-only` marker.
- **ADVISORY (always-on nudges):** caveman-discipline, northstar-inject, harness-enforce (anti-decay), recall-inject, coding-routing-guard, post-agent-guard, token-discipline, graphify-blindspot, manifest-guard (warn), session-checkpoint, harness-usage-telemetry, precompact-handoff, pre_compact_global, senduserfile-path-echo, voice-dictation-nudge.
- **Deterministic gate:** `check-all` (lint / type / test). **CHECK G = Semgrep SAST is ADVISORY** — it *suggests* ERROR-severity bug/security patterns (prints each + why to consider), it does NOT block. `SEMGREP_STRICT=1` makes it gate.

## Do NOT route to these (retired / dead — excluded on purpose)
- **GLM / `glm` subagent + CLI** — retired (out of credits). Never an auditor/council/second-opinion option; use Opus-4.8-low instead.
- **`cc-gemini-plugin` (`gemini-agent`)** — dead (expects a missing `gemini` binary). The real non-Claude voice is the **`gemini` subagent** / `tools/gemini-opencode.sh` (Gemini via opencode). ⚠️ Google treats third-party Gemini-CLI-OAuth as a ToS gray area — throwaway account, overflow not primary.
- **zai / z.ai coding plugin** — dead provider (registered marketplace, not enabled).
- **old ctxproxy** — dropped from new-session config; kept running only as a legacy bridge for frozen old sessions. Not part of the active harness.

## Ponytail note
`/awesomeharness` is announcement + rituals + orientation. It deliberately does NOT re-implement what the hooks already enforce or what the individual skills already do — it invokes them. If a section here starts duplicating a skill, delete it and point at the skill.
