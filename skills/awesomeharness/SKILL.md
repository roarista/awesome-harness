---
name: awesomeharness
description: Activate Ro's context-light coding loop, tool routing, sub-agent discipline, verification, and persistence.
---

# awesomeharness

Contract for the rest of the session. Typically invoked right after /compact with the previous final
summary as args: **that summary is your resume point** — continue from it. Hooks already inject
`.codemap`, `.now.md` and the north star where present; do not reload them. Read `STATE_CURRENT.md`
only if the args do not say where we were; never historical STATE or archives.

## Route (tools)

- Recall is auto-injected each prompt; add a targeted `ml search <term>` only if needed. Repowise: CLI
  only where a named chain uses it, never its MCP. Load specs/skills/MCPs only when needed.
- Zoom before source: `~/.claude/tools/l1.py <area>`, then `~/.claude/tools/skeleton.py <file>`; bodies last.
- Structure/reach: graphify query/explain/path. All AST occurrences: Semgrep. Literal text/history: `rg` / git.

## Delegation (main orchestrates, does not build)

- **Router decides builder, auditor, model, effort:** `~/.claude/tools/route-model.sh "<task>"` (wraps
  free-model-router `fmr route`; prints NECESSITY, BUILDER, AUDITOR, SPEC, and an `ID:`). DO-NOT-LAUNCH
  means do it without a launch or skip it. After the audit, record the receipt:
  `cd ${FMR_HOME:-~/Downloads/free-model-router} && .venv/bin/python -m fmr outcome <id> pass|pass_with_fixes|reject|reworked|abandoned`.
- **Ro naming a model beats the router.** Spend: code + review → best model with headroom; research/
  mechanical → cheapest; a quota resetting soon goes first. **Never use Codex reset credits without Ro's yes.**
- **Agent types:** Claude builds/analysis → `claude`; Codex builds → `codex`; audits → `codex-audit`,
  `opus`, or `opus48-audit`. `general-purpose` (and Explore) are blocked by `claude-spawn-gate`.
- Main edits directly ONLY orientation files (`.now.md`, STATE, memory) and tiny harness tweaks.

## Code loop

1. Prove REUSE / ADAPT / REJECT against live files; STOP if existing behavior covers it. Ponytail
   ladder first: not needed → stdlib → native platform → installed dep → one line → minimum code.
2. Decompose maximally into units, each spec `CONTEXT / REUSE / CHANGE / GOAL / VERIFY`. GOAL names
   the observable end state and what is out of scope; VERIFY is the proof: commands that can fail and
   what passing looks like. Each unit fits one builder and leaves every touched file ≤200 lines.
3. One builder per unit, the router's pick. Never run sibling builders concurrently in a dirty checkout.
4. **Audit cross-family, always** (Codex-built → Claude auditor; Claude-built → `codex-audit`, or the
   other Claude auditor if Codex is exhausted), same spec, shared rubric:
   - CRITICAL data loss/security/secret leak/money · HIGH wrong on a normal path, invented API, GOAL
     unmet · MEDIUM edge input, unhandled I/O error, untested risky branch, test that cannot fail · LOW style.
   - `VERDICT: REJECT` if any CRITICAL/HIGH, any MEDIUM touching money/auth/secrets/data-loss/prod
     data, or VERIFY not run/failing; `PASS WITH FIXES` if only other MEDIUM/LOW; `PASS` only if ≤LOW.
   Fix and re-audit until VERDICT ≠ REJECT, then fix every listed item. Agent reports are claims:
   independently check the tree and command output.
5. Run the unit check and repo gate; claims require real output. Commit scoped files, `ml record`
   learning, update `.now.md` (NOW / LAST_VERIFIED / NEXT, ≤5 lines) + STATE resume point, push.
   Before /compact run `/compact-prep`.

## Enforcement that is real (outside this skill)

- **git pre-commit** (per-repo shim of `~/Downloads/awesome-harness/tools/git-hooks/pre-commit`):
  blocks staged source files over the 200-line ratchet, then runs `check-all --fast` where the repo
  has `.check-all.json`. Bypass (`--no-verify`, `SKIP_RATCHET=1`) only with Ro's yes.
- Hooks in `~/.claude/settings.json` (some messages still say "always Codex"/"glm auditor"; CLAUDE.md
  and the router win). Blocking: `route-only-gate` (main source edits in `.route-only` repos),
  `bash-write-fence` (source writes via Bash), `irreversible-pause` (rm -rf, force-push, DROP/TRUNCATE),
  `northstar-protect` (eroding `.northstar.md`), `claude-spawn-gate`, `graphify-gate` (Read/Grep until a
  graphify call), `compact-prep-gate` (Stop unless `.now.md` was just updated), `skill-reinject-guard`
  (Skill-tool reloads only). Injecting: `codemap-inject`, `caveman-discipline`, `manifest-guard`,
  `northstar-inject` (north star + `.now.md` each prompt), `recall-inject`, `harness-enforce`,
  `coding-routing-guard`, `post-agent-guard`. Nudges: `now-gate`, `graphify-blindspot`, `reread-guard`,
  `token-discipline`, `filesize-cap`, `session-checkpoint`. Also `harness-usage-telemetry` and
  PreCompact `pre_compact_global.sh` + `precompact-handoff`.

## Sub-agent discipline

Every spawn prompt says: scoped reads, light context, be concise; write the full result to
`.artifacts/agent-reports/<task>.md`; return ≤8 decision-complete lines (verdict, change/finding,
verification, risk, next, report path). Never paste raw logs, diffs, code or research into the parent.
The orchestrator stays silent while agents run, then gives one complete final summary.

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
- No unauthorized spend, production mutation, messages, or destructive action. Main session stays on Anthropic.
- Re-invoking this skill reloads the body by design (typed /awesomeharness bypasses the reinjection
  guard, and after /compact a reload is correct).

Source: `~/Downloads/awesome-harness/skills/awesomeharness/SKILL.md`; live copy drift-checked by
`bash ~/Downloads/awesome-harness/tools/skill-drift.sh`.
