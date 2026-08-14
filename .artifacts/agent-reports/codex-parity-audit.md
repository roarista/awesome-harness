# Compact Codex coding-parity audit

Date: 2026-08-14  
Scope: read-only audit of the tracked awesome-harness adapter, Claude hooks/skills, and existing forensic reports. This file is the requested audit artifact; no tracked file was changed.

## Verdict

The Codex adapter already carries the right *prompt-level* coding loop, but its mechanical coverage is much narrower than the wording suggests. Keep the seven useful coding capabilities, fold the redundant `caveman` skill into `awesomeharness`, and port only four silent, testable guard behaviors: destructive-command denial, direct `.northstar.md` protection, mutation-aware commit gating, and (only if a runtime probe proves the event is hookable) native-spawn contract validation. Do not reproduce Claude's reminder/injection surface.

The highest-value missing feature is not another skill: it is a native Codex builder/auditor lifecycle whose prompt, output, and dirty-tree scope are checkable. Auditors are the only workflow component with positive outcome evidence: 39/55 action-labelled audits rejected work, including 36 invented-API/schema cases (`docs/audits/2026-08-02/08-decomposition-quality.md:38-49,75-86`).

## What Codex has now

- Ponytail is already an always-on global policy, not a skill: its reuse ladder and minimum-code rules are in `codex/AGENTS.md:4-29`, and the full procedure is at `codex/AGENTS.md:31-53`. Creating a second “Ponytail Pro” skill would duplicate standing context.
- The installed skill chain is complete for ordinary coding: activation, recall, understand/gate, decompose/build/audit, deterministic verification, and persistence are routed at `codex/AGENTS.md:55-69`. The compact activation skill already requires a bounded builder, a distinct auditor, real checks, and persistence (`codex/skills/awesomeharness/SKILL.md:19-33`).
- The current Codex hook has only two matchers, Bash and `apply_patch` (`codex/hooks.json.template:1-27`). Its Bash logic recognizes external CLI builders and requires `CONTEXT/CHANGE/GOAL/VERIFY/REUSE` only when their embedded prompt appears mutating (`codex/hooks/pre_tool_use.py:28-47,82-147`).
- `apply_patch` is telemetry only; it never blocks (`codex/hooks/pre_tool_use.py:168-198`). The runtime smoke test proves only that Bash and `apply_patch` dispatch (`tests/test_codex_runtime_smoke.sh:39-69,91-100`). Installer tests likewise assert only those two matchers (`tests/test_codex_install.sh:44-57`).

## Current hook and subagent gaps

1. **Native Codex subagents bypass the external-builder contract.** The guard recognizes `codex exec`, `glm --edit`, and the companion CLI (`codex/hooks/pre_tool_use.py:82-101`); it does not inspect native `spawn_agent`, `followup_task`, or returned reports. Yet policy says to use native Codex subagents (`codex/AGENTS.md:50-53,94-95`). Whether Codex repo hooks expose these collaboration tool calls is not proven by any fixture or runtime test. Probe first; do not claim enforcement before a recorded event.
2. **No lifecycle pairing.** Nothing proves every non-trivial builder gets a distinct read-only auditor, that the auditor saw the same unit spec, or that FAIL is fixed and re-audited. Those requirements exist only in prose (`codex/skills/code-decompose/SKILL.md:37-58`).
3. **No return-contract enforcement.** The activation skill requires a durable report and an eight-line decision packet (`codex/skills/awesomeharness/SKILL.md:31-33`), but hooks do not inspect native spawn prompts or returns. This matters: 548/852 historical returns exceeded 15 lines, median 3,448 characters; only about 24% of vocabulary and 2.49% of 3-grams appeared in the parent's next message (`docs/audits/2026-08-02/03-subagent-dump-economics.md:39-69`).
4. **No scope-preservation check around a delegated unit.** A current Mulch failure record says a Codex agent reverted files outside its two-file unit. The workflow says preserve dirty work (`codex/skills/awesomeharness/SKILL.md:35-40`) but captures no before/after status manifest.
5. **`.northstar.md` is not protected from direct patches.** Protection runs only for recognized external builder commands (`codex/hooks/pre_tool_use.py:130-147`); direct `apply_patch` merely logs. This contradicts the global rule that the agent must ask before changing the objective (`codex/AGENTS.md:82-84`).
6. **No destructive-shell or pre-commit verification guard.** The Codex adapter does not carry the Claude survivor behaviors for irreversible commands or check-all-before-commit. Historical compliance was weak: check-all ran in 7/22 coding sessions and before roughly 18% of commits, while 7/22 sessions ended with dirty source work (`docs/audits/2026-08-02/12-procedure-compliance.md:127-156`).

## Include: compact, coding-value surface

### Skills/policy

1. **Keep `awesomeharness` as the single explicit session command.** It is already only 40 lines and contains the decision-critical route and code loop (`codex/skills/awesomeharness/SKILL.md:8-40`). Add no second “pro” command.
2. **Keep Ponytail in `AGENTS.md`; do not make it a skill.** It is an always-on coding lens and should not require invocation (`codex/AGENTS.md:4-29,71-84`). If context size must shrink, compact this block in place while preserving reuse ladder, safety exceptions, and the one runnable check.
3. **Keep `recall`, `codebase-first`, `code-decompose`, `check-all`, and `compact-prep`, loaded on demand.** They correspond exactly to the procedure router (`codex/AGENTS.md:55-66`). Their responsibilities are distinct and have measured relevance: recall/understand/auditor were observed in 91%/95%/77% of coding sessions, while check-all and push were the important failures (`docs/audits/2026-08-02/12-procedure-compliance.md:197-225`).
4. **Fold/delete the separate `caveman` skill.** Its builder/auditor, real-verification, graphify, and message-discipline rules duplicate `awesomeharness` and `code-decompose` (`codex/skills/caveman/SKILL.md:8-25`; `codex/skills/awesomeharness/SKILL.md:19-40`). One activation skill is smaller and less ambiguous.
5. **Optionally add compact `harness-intel` and `ui-console-debug` only as task-triggered skills.** `harness-intel` materially audits code/harness drift; `ui-console-debug` adds a real browser-observation loop for UI defects. Neither belongs in standing policy or the normal coding path. Compress each to routing, authority boundary, proof, and output contract rather than copying the 8 KB/2.7 KB Claude bodies.

### Hooks/backstops, in priority order

1. **Port the corrected irreversible-command detector into the existing Python hook.** It should be silent on pass, command-structure based, fail-open internally, and deny destructive operations or require explicit authority. This is safety, not a behavioral reminder. The old audit initially saw no attributable blocks (`docs/audits/2026-08-02/07-hook-effectiveness.md:40-52`), but the current STATE corrects that corpus limitation: the guard blocked a real destructive delete twice; retain only the corrected command-matching implementation.
2. **Protect `.northstar.md` on every writable path Codex exposes.** Extend direct `apply_patch` inspection beyond telemetry, and test both an actual target edit and harmless mention. Keep objective changes authority-gated, matching `codex/AGENTS.md:82-84`.
3. **Gate `git commit` on a real fast repository gate in opted-in repos.** Parse an executable `git commit` segment, run `check-all --fast`, deny only on a hard failure, and stay silent otherwise. Do not port Claude's phantom-edit timestamp machinery: its own source documents the Bash-write blind spot (`hooks/check-all-commit-gate.sh:8-16,71-80`). A direct commit-time gate is smaller and observes the state that will actually be committed.
4. **Probe native collaboration events, then enforce the spawn contract if supported.** Add a disposable runtime fixture analogous to the current Bash/patch smoke test. If the hook receives `spawn_agent`, require bounded scope, `CONTEXT/REUSE/CHANGE/GOAL/VERIFY`, a read-only auditor role where applicable, report path, and <=8-line return shape. If native events are not emitted, keep this in the skill and use a tiny tracked session ledger rather than pretending a hook can enforce it.
5. **Add a before/after dirty-scope assertion to the orchestrator workflow.** Before a builder: record `git status --porcelain=v1 -z` and the unit's allowed paths. After it: reject unapproved path changes before starting the auditor. This directly targets the recorded cross-unit revert failure and is more valuable than generic “do not touch” prose.

## Exclude

- **All reminder/injection hooks:** caveman-discipline, coding-routing-guard, post-agent-guard, manifest-guard, phantom-edit-guard, generic northstar injection, and zero-observation behavioral guards. The measured hook audit found 366 repeated routing/post-agent reminders with no demonstrated causal effect and recommended cutting/demoting them (`docs/audits/2026-08-02/07-hook-effectiveness.md:54-66,76-93`).
- **Codemap injection as a default Codex hook.** Code understanding is already routed through the project router, injected map when available, Graphify, Semgrep, and `rg` (`codex/skills/awesomeharness/SKILL.md:10-17`; `codex/skills/codebase-first/SKILL.md:10-24`). Reinjecting map prose adds standing context; generate/update it as an explicit tool step when stale.
- **Claude-only spawn-type/model gates.** `claude-spawn-gate.py` blocks Claude agent names based on Claude cost data (`hooks/claude-spawn-gate.py:1-29`). Codex should use native roles and bounded tasks, not emulate `general-purpose`, `Explore`, `opus`, or Claude plugin routing.
- **`goal` in the default coding pack.** Autonomous multi-step loops are useful only on explicit request and are not needed to understand/build/audit ordinary code. If retained globally, install it as an optional task-triggered skill, not part of awesomeharness activation.
- **`notes-inbox`, `youtube-research`.** They are content/research pipelines, not coding-quality capabilities.
- **A full copy of Claude `orient`.** Codex already has recall plus codebase-first. The Claude skill itself says the merge was motivated by invocation counts in a different runtime; copying its 9.7 KB body would duplicate the current Codex router rather than improve it.
- **Repeated skill reinjection or mid-session reminders.** Hook text becomes context tax. The state records a measured reduction from 30.2 to 8.5 ktok/session after silence-by-default; the earlier audit found reminder compliance weak (`.planning/STATE.md:35-50`; `docs/audits/2026-08-02/07-hook-effectiveness.md:54-74`).

## Minimum implementation sequence

1. Runtime-probe whether native `spawn_agent`/return events are hook-visible; record exact payloads without prompt content.
2. Extend the single Codex Python hook with isolated, self-tested decisions for destructive Bash, direct northstar patching, and commit-time `check-all --fast`.
3. If spawn events are visible, add spawn-contract validation and a builder/auditor ledger. If not, implement only the ledger in the orchestration skill and document the honest boundary.
4. Fold `caveman` into `awesomeharness`; optionally add compact, on-demand `harness-intel` and `ui-console-debug`.
5. Expand installer and disposable runtime tests for every matcher and allow/deny path. Run the repository gate and one real bounded Codex builder→auditor trial before claiming parity.

## Risks

- Hook matchers/payloads for native collaboration tools are currently unproven. Designing enforcement before the runtime probe risks dead configuration.
- Destructive-command regexes can invert into mention matching; use the corrected shell-structure parser and include quoted text, heredoc, comment, and benign-mention fixtures.
- A commit hook can be expensive or disruptive; make it opt-in per repository, fast, silent on pass, and block only hard failures.
- Native subagents share a dirty checkout. The lifecycle must serialize builders and validate changed paths; a prompt alone did not prevent a prior Codex agent from reverting unrelated work.

## Verification performed

Read and cross-checked the current Codex policy, seven installed skill sources, hook template and implementation, installer/runtime tests, live Claude hook registration template, relevant hook sources, repository STATE, Mulch search result, and four forensic audits. No code or tests were changed or run because this assignment was a read-only design audit.
