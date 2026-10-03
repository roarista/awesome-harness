# `$awesomeharness` in Codex: usage over the last 30 days (2026-09-02 to 2026-10-02)

Read-only analysis, 2026-10-02. Data: `~/.codex/sessions/2026/**/rollout-*.jsonl`, filtered to files dated 2026-09-02 or later (4,167 rollouts parsed), plus `~/.codex/logs_2.sqlite` (which covers 2026-09-23 onward only). Scripts: `/tmp/ahx/scan.py` and `/tmp/ahx/err.py`. Line numbers below are JSONL line numbers inside each rollout.

## Verdict

The skill is used heavily, but almost entirely by **implicit loads**. It is listed in nearly every rollout. The model `sed`s SKILL.md in 37% of rollouts (1,550 of 4,167), mostly in non-interactive builder runs, because AGENTS.md tells it to. **Explicit human use (`$awesomeharness`) began only on 2026-10-02**, in two codex-tui threads in `~/Downloads/Consulting`, for 8 turns. In both threads the procedure was only partly followed: route-model.sh, `claude -p`, subagents and tests were all used, but GOAL / DONE-WHEN was stated **0 times** in 133 assistant messages. No skill-loader errors were found anywhere.

## 1. Rollouts in the window

Total: **4,167**. By originator: codex_exec 2,921 · Claude Code (app-server / plugin) 1,213 · codex-tui 30 · Codex Desktop 3.

By cwd (top): virality-pipeline 1,614 · Consulting 331 · jobs 200 · scholarships 80 · school 60 · free-model-router 46 · virality-trends 39 · `~` 32 · boat 30 · awesome-harness 12 · other small directories account for the rest.

By day, the volume is concentrated on 09-28 (559), 09-29 (528) and 09-30 (1,053).

## 2. Explicit invocations (a user-role message mentions awesomeharness)

33 rollouts and 63 messages match the raw text. They split three ways.

**A. Human-typed (`$awesomeharness` in the TUI): 2 parent threads, 8 turns, all on 2026-10-02 UTC, all in `~/Downloads/Consulting`.**

| rollout | line | timestamp (UTC) | message |
|---|---|---|---|
| `2026/10/01/rollout-2026-10-01T20-37-41-01a0fa42-...jsonl` | L593 | 10-02 16:27:08 | "ve los slash commands de claude como /compact-prep y /awesomeharness y bajalos..." (the request to port the skill, not an invocation) |
| same | L809 | 10-02 16:51:00 | `$awesomeharness "Compact-prep listo..."` |
| same | L1500 | 10-02 17:32:38 | `$awesomeharness **CONTINUE** ...` |
| same | L1787 | 10-02 17:44:05 | `$awesomeharness "Sí, **Claude Code + Foundry**..."` |
| `2026/10/02/rollout-2026-10-02T11-27-45-01a0fd71-...jsonl` | L9 | 10-02 16:43:52 | `$awesomeharness Vamos bien, pero estoy atorado...` |
| same | L446 | 10-02 17:08:22 | `$awesomeharness "Tu respuesta llegó..."` |
| same | L873 | 10-02 17:24:55 | `$awesomeharness "Corregí la codificación..."` |
| same | L1788 | 10-02 18:35:23 | `$awesomeharness "**Encontré por qué falló**..."` |
| same | L2293 | 10-02 19:07:02 | `$awesomeharness Tienes razón: ...` |

Each `$awesomeharness` turn is followed two lines later by a Codex-injected `<skill><name>awesomeharness</name><path>/Users/rodrigoarista/.codex/skills/awesomeharness/SKILL.md</path>...` user item containing 5,984 chars (for example L811 and L11). **This is Codex's native explicit-load mechanism, and it worked all 8 times.**

Note: 5,984 chars matches neither the current SKILL.md (6,600 chars, synced 14:27 local) nor the backup (5,024 chars, Aug 17). All 8 injections happened between 11:43 and 14:07 local, so they loaded an intermediate version, probably the 11:27 local sync. The skill directory mtime is 11:27, which matches Ro's "bajalos" request at 16:27 UTC. **The current 14:27 version has not yet been loaded by any session.**

**B. Forked subagent threads that inherited the parent's message: 13 rollouts, all Consulting, 10-02 12:07–13:28 local.** session_meta has `forked_from_id` = 01a0fa42 or 01a0fd71 and `thread_source: subagent`. Examples: `rollout-2026-10-02T12-07-31-01a0fd95-da62...`, `...T12-09-16-01a0fd97-723b...`, `...T13-28-43-01a0fde0-311b...`. These are not new human invocations.

**C. Machine-written prompts that only mention the skill: 18 rollouts.**
- 9 are weekly CLAUDE.md-audit `codex exec` runs at `~`, on Mondays at 09:00 (09-07, 09-14, 09-21, 09-28, two per day).
- 2 are harness-scout runs at `/` (09-07 13:00 and 09-28 13:00). They paste the skill body as context.
- 3 are virality-pipeline C23 builder prompts (09-04 14:59–15:03, Claude Code originator).
- 1 is the 09-07 HARNESS_SCOUT build in `/private/tmp`.
- 3 are in awesome-harness (10-01): gate-adherence ×2, and the route-model→fmr delegation in `rollout-2026-10-01T15-26-58-01a0f926...` and `...T15-42-42-01a0f934...`.

## 3. Implicit loads

- **Skill listed** in the `<skills_instructions>` developer message in **4,160 of 4,167** rollouts. The listing path is the alias `r0/awesomeharness/SKILL.md` in 4,145 rollouts and the absolute `~/.codex/skills/...` path in 15. Seven rollouts have no skills block (09-09, 09-15, 09-16 and 10-02, 1–3 each).
- **SKILL.md read by a tool call** (typically an early `sed -n '1,240p' /Users/rodrigoarista/.codex/skills/awesomeharness/SKILL.md`, around rollout line 14): **1,550 rollouts, 1,589 calls.**
  - By originator: codex_exec 865 of 2,921 · Claude Code 676 of 1,213 · tui 8 of 30 · Desktop 1 of 3.
  - By repo: virality-pipeline 1,121 · Consulting 150 · jobs 121 · scholarships 42 · school 24 · virality-trends 23 · free-model-router 10.
  - Reads happen every active day from 09-02 to 10-02. Peaks: 09-28 (210), 09-30 (188), 09-15 (167).
  - Examples: `2026/09/02/rollout-2026-09-02T12-26-10-01a06328-...jsonl` L14 and `2026/10/02/rollout-2026-10-02T13-08-42-01a0fdcd-...jsonl` L15.
- The driver is AGENTS.md, which names the skill as the home of the 26 quality gates and says "Load that skill for any build, review, or pre-ship claim" (`~/.codex/AGENTS.md:74`). It also lists the skill as the "session activation" row (`:60`).

## 4. Errors

- **Skill load errors: none found.**
  - No `error`, `warning` or `stream_error` event_msg in any of the 4,167 rollouts mentions the skill. There were zero such events at all.
  - In `logs_2.sqlite` (09-23 onward) the WARN rows containing "skill" are 114, all plugin icon-path warnings (`ignoring interface.icon_small/large: icon path with '..'`) and plugin_skill_warmup noise. None mention awesomeharness, frontmatter or length.
  - The 343 "skill" hits from the first loose regex were false positives (file content that happens to contain "error" or "not found", for example `cat: .northstar.md: No such file`).
- **route-model.sh / fmr in real use: 9 calls, all exit 0, all with valid fmr routing output.**
  - 4 calls in thread 01a0fa42: L3239, L3255, L3448, L3652.
  - 5 calls in thread 01a0fd71: L2411, L2492 (that one only `ls`-ed the script), L2602, L2636 and one more.
  - Output looks like `NECESSITY: LAUNCH / BUILDER: claude-opus-5-5 via opus ... / AUDITOR: none / SKILLS: check-all`.
  - Observation: "audit" tasks route to `BUILDER: opus ... AUDITOR: none`, so the auditor arrives as the builder slot. That is worth a glance but is not an error.
- **fmr failures appear only in deliberate tests on 10-01** (`rollout-2026-10-01T15-49-29-01a0f93a...`): `ROUTER: fmr unavailable (exit 255)` at L55 and L94, and `(timeout)` at L133, L215 and L262. These were fault-injection probes with a fake `.tmp-route-audit` venv. Also seen: `sysmond service not found` / `pgrep: Cannot get process list` (sandbox noise).
- **Other harness errors from the 10-01 build:**
  - `fatal: Unable to create .../awesome-harness/.git/index.lock: Operation not permitted` (`rollout-2026-10-01T15-42-42-01a0f934...` L120). This is the sandbox blocking git commit, not fmr.
  - One exec was `Rejected` by sandbox policy (L61).
- **"receipt not recorded"** (the fmr receipts.py fallback message): **0 rollouts.** `writable_roots`: only in the harness's own docs and prompts. No runtime failures.
- **route-model.sh probe (run by me, harmless modes only):**
  - With no args: prints usage and exits 2.
  - With `FMR_DISABLE=1` and a dummy task: `NECESSITY: LAUNCH / AGENT: general-purpose / MODEL: sonnet`, exit 0.
  - I did not run it with fmr enabled, because `fmr route` appends to `~/.local/state/free-model-router/decisions.jsonl` (`free-model-router/fmr/receipts.py:9`), which is a write.
  - `~/.codex/tools/route-model.sh` is byte-identical to the repo's `tools/route-model.sh`, and the fmr venv python exists.

## 5. AGENTS.md and config overlap

- `~/.codex/AGENTS.md` is byte-identical to `awesome-harness/codex/AGENTS.md` (7,055 B). `~/.codex/skills/awesomeharness/SKILL.md` is byte-identical to `awesome-harness/codex/skills/awesomeharness/SKILL.md`.
- AGENTS.md already carries THE PROCEDURE outline (steps 1–7, around lines 30–45) and a skills table (`:56-65`). It points to the skill for the gates (`:74`), the router (`:77`) and the `$awesomeharness` invocation (`:97`).
- So the two are **partly redundant**. AGENTS.md has the skeleton, and the skill has the detail: GOAL / NOT-GOAL / DONE-WHEN / PROOF at SKILL.md:26, REUSE/ADAPT/REJECT at :27, the unit format at :30, and the 26 gates. The implicit `sed` in 37% of rollouts is AGENTS.md pulling the skill in, so in builder runs the skill is effectively always-on regardless of `$awesomeharness`.
- `~/.codex/config.toml`: there is **no hook that injects awesomeharness**, and no skills config.
  - `[hooks.state]` (:343–402) tracks only per-repo `.codex/hooks.json` pre_tool_use and subagent_start/stop hooks for Vividlist, intrn, virality-pipeline and forclosurehomes.
  - `notify` (:7) is the Computer Use turn-ended client.
  - There is no `~/.codex/hooks*`. The repo has `codex/hooks/` and `codex/hooks.json.template`, but nothing global is wired.

## 6. Behaviour after an explicit invocation (the 2 human threads)

| thread | assistant msgs after invocation | GOAL / DONE-WHEN | STOP/PLAN/BUILD or REUSE words | route-model.sh | `claude -p` | spawn_agent | test-like commands |
|---|---|---|---|---|---|---|---|
| 01a0fa42 (from L809) | 53 | 0 / 0 | 2 | 5 | 5 | 17 | 39 |
| 01a0fd71 (from L9) | 80 | 0 / 0 | 0 | 4 | 4 | 7 | 22 |

The routing, delegation and testing parts of the skill are followed. Its step 1 (state `GOAL / NOT-GOAL / DONE-WHEN / PROOF`, SKILL.md:26) is never done in visible output, in English or Spanish. This matches the existing memory note "the harness optimizes route because DONE and PROOF are missing".

Counting caveats:
- "test-like" is a regex over tool-call text (pytest, npm test, check-all, and so on), so it overcounts.
- Spawn counts include forks.

## Bottom line

- **Loaded:** yes. It is listed in 99.8% of rollouts, read implicitly in 37%, and explicitly injected 8 times, with zero errors.
- **Explicitly used by Ro:** 8 turns, in 2 Consulting TUI threads, all on 2026-10-02, the day it was synced. There was nothing in the 29 days before that.
- **Not yet loaded:** the 14:27 version.
