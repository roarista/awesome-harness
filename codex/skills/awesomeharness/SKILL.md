---
name: awesomeharness
description: Activate Ro's context-light coding procedure, evidence-led tool routing, bounded builder/auditor delegation, verification, and persistence. Use when Ro invokes awesomeharness or /awesomeharness, or for substantive implementation, refactors, and audits in an awesome-harness repository.
---

# awesomeharness

Contract for the rest of the session. If invoked with a pasted summary (typically after compaction),
**that summary is your resume point** — continue from it. Otherwise read `.northstar.md`, `.now.md`,
and `STATE_CURRENT.md` when present; never routine-load historical STATE or archives.

## Route (tools)

- Recall: targeted `ml search <term>` or one domain prime; do not prime everything.
- Inventory: the repo `.codemap` when present. Zoom before reading source:
  `~/Downloads/awesome-harness/tools/l1.py <area>` (files+LOC+entrypoints) then
  `~/Downloads/awesome-harness/tools/skeleton.py <file>` (signatures only). Open a body only when needed.
- Structure/reach: graphify query/explain/path. All AST occurrences: Semgrep. Literal text/history: `rg` / git.
- Load specs, skills, MCPs, and plugins only when the task needs them.

## Delegation (main orchestrates, does not build)

Route every launch with `~/.codex/tools/route-model.sh "<task>"` (delegates to free-model-router's `fmr route`; prints NECESSITY, BUILDER, AUDITOR, SPEC and an `ID:`; record results with `cd ${FMR_HOME:-~/Downloads/free-model-router} && .venv/bin/python -m fmr outcome <id> pass|pass_with_fixes|reject|reworked|abandoned`). Launch the builder and auditor it names with the model and effort it gives: a Codex-family model as a native Codex subagent, a Claude-family model via `claude -p --model <model>`. Audits are always cross-family. Codex reset credits are never consumed without Ro's explicit yes. In read-only sandboxes (or without `writable_roots` for `~/.local/state/free-model-router` in config.toml) the receipt cannot be written (stderr says so); rerun with escalated permissions when the outcome must be recorded.

- **Ro naming a model beats the router.** Spend: code + review get the best model with headroom;
  research/mechanical get the cheapest; a quota resetting soon with room left goes first.
- DO-NOT-LAUNCH means do it without a launch or skip it. Main edits directly only orientation files
  (`.now.md`, STATE, memory) and tiny harness tweaks. Do not emulate Claude-specific agent types.

## Code loop

1. Prove `REUSE / ADAPT / REJECT` against live files; stop if existing behavior covers the goal.
   Ponytail ladder first: not needed → stdlib → native platform → installed dep → one line → minimum code.
2. Decompose maximally into units, each spec `CONTEXT / REUSE / CHANGE / GOAL / VERIFY`. GOAL names
   the observable end state and what is out of scope; VERIFY is the proof: commands that can fail and
   what passing looks like. Each unit fits one builder and leaves every touched file ≤200 lines.
3. One builder per unit, the router's pick; wait for it. Never run sibling builders concurrently in a
   dirty checkout. Main-agent ability is not a reason to skip the builder or the audit.
4. **Audit cross-family, always**, same spec, shared rubric:
   - CRITICAL data loss/security/secret leak/money · HIGH wrong on a normal path, invented API, GOAL
     unmet · MEDIUM edge input, unhandled I/O error, untested risky branch, test that cannot fail · LOW style.
   - `VERDICT: REJECT` if any CRITICAL/HIGH, any MEDIUM touching money/auth/secrets/data-loss/prod
     data, or VERIFY not run/failing; `PASS WITH FIXES` if only other MEDIUM/LOW; `PASS` only if ≤LOW.
   Fix and re-audit until VERDICT ≠ REJECT, then fix every listed item. Agent reports are claims:
   independently inspect the tree and verification output.
5. Run the unit check and repository gate (`$check-all` before shipping); claims require real output.
6. Commit scoped files, `ml record` durable learning, update `.now.md` (NOW / LAST_VERIFIED / NEXT,
   ≤5 lines) and the STATE resume point, push. Before compaction run `$compact-prep`.

If subagents are unavailable, keep the separation sequentially: finish the spec, build, then re-read
the diff with independent-auditor eyes.

## Enforcement that is real (outside this skill)

- **git pre-commit** (per-repo shim of `~/Downloads/awesome-harness/tools/git-hooks/pre-commit`):
  blocks staged source files over the 200-line ratchet, then runs `check-all --fast` where the repo
  has `.check-all.json`. Bypass (`--no-verify`, `SKIP_RATCHET=1`) only with Ro's yes.
- **Native Codex hooks** (opt-in per repo `.codex/hooks.json`, from `~/.codex/awesome-harness/hooks/`):
  `pre_tool_use.py` on Bash/apply_patch denies builder launches missing the unit-contract headings,
  edits that erode `.northstar.md`, and irreversible commands (rm -rf, force-push, `git reset --hard`, `git clean -fd`);
  `subagent.py` injects SubagentStart context and checks the SubagentStop receipt (one retry).
  Direct `apply_patch` by main is advisory, not blocked. Other rituals are the main agent's job.

## Agent discipline

Every delegated prompt requires scoped reads and a complete report at `.artifacts/agent-reports/<task>.md`.
Return only a decision-complete summary of at most eight lines with verdict, evidence, verification,
risk, next action, and report path — never raw logs or diffs.

## Quality gates

Every green is a claim — a passing test, an empty review, a design that "looks right". Make each earn
itself (the gates below, from Glitch Cat Club, Aug 16; each is a defect that got past someone).

- **Before a fix:** reproduce through the exact door the user used. Treat the report as a symptom and
  re-check what it claims is fine. Find the introducing commit, how long it was live, what a user sees.
  Before a rework, list every promised behaviour as proven-by-test / proven-by-history / assumed. Sweep
  for siblings — a fix closes the class or it isn't closed.
- **Attack the design first:** walk it as if built (first run, re-run, resume, retry after failure). List
  every caller by search, not judgment. Grep docs for sentences the change makes untrue. Ask what a
  death between two writes leaves and whether the next run heals it. Try disk-full, no network, slow
  machine, synced folders; real inputs (spaces, quotes, CRLF). The right rework deletes more than it adds.
- **Tests that can't lie:** one test produces the failure the way the machine does — no mocking the
  broken part. Mutation-proof: break it, watch it fail by name, revert. Explain a red before touching it.
- **Review that finds things:** no memory of writing it, then a different model, one lens each (data
  loss / races / green by construction / simpler rewrite). "No findings" lists what was attacked.
  Reproduce a finding before acting on it and before dismissing it. If a fix was wrong, stop and explain
  why every earlier gate missed it.
- **Before it ships:** walk the whole flow through the real entry point; run it twice, then inspect the
  files and data it left behind, not the output.

## Non-negotiables

- Minimum code; no speculative abstractions or dependencies.
- **Hard cap: no source file over 200 lines.** A unit that would cross it is split first — new module,
  not a longer file. 300 is a ceiling only pre-existing files may sit at, and touching one means
  shrinking it. The pre-commit ratchet enforces this; it is a build constraint, not style.
- Preserve unrelated dirty work; never force/reset/clean/stash/restore it away.
- No unauthorized spend, production mutation, messages, or destructive action.
- Keep progress terse and the final summary complete.

Source: `~/Downloads/awesome-harness/codex/skills/awesomeharness/SKILL.md`; live copy drift-checked by
`bash ~/Downloads/awesome-harness/tools/skill-drift.sh`.
