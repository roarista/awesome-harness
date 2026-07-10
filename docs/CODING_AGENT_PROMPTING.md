# Prompting Coding Sub-Agents (Codex 5.5 / GLM 5.2)

How the orchestrator (Claude Code main session) should **prompt a coding sub-agent so it
produces correct, in-scope, convention-matching code** — without the coder having to explore
the whole repo, and without bloating anyone's context.

This is the *how-to-prompt* companion to the pieces that already exist. It does not repeat them:

- **`~/.claude/BUILDER_STANDARD.md`** — the correctness/boundary ruleset you *prepend* to every coder prompt (smallest diff, validate at trust boundaries, no swallowed errors, leave one runnable check). Don't restate it; paste it.
- **`skills/code-decompose/SKILL.md`** — the decompose → cheap-coder → auditor pattern and the `CONTEXT/CHANGE/GOAL/VERIFY` unit spec. This doc is how to *word* each unit's prompt.
- **`~/.claude/hooks/coding-routing-guard.sh`** — the routing policy already emitted on every `Task` spawn (builder = Codex 5.5, auditor = GLM 5.2 or any non-builder; run `graphify` + `graphify-blast` first). Don't re-derive routing here.
- **`README.md` → "Better code from cheaper models"** and **graphify** — why a scoped code-map query is ~8–15× cheaper than cold-reading the file.

**One-line thesis:** *the more of the map you hand down, the cheaper the model you can trust.*
Decomposition is the expensive thinking done once; execution is the cheap step done at volume
([code-decompose](../skills/code-decompose/SKILL.md)). Everything below is about making the
hand-down complete enough that a cheap coder needs zero judgment and zero exploration.

---

## 1. Give the coder the MAP, not the maze

A coder that has to *discover* the codebase burns tokens, drifts, and hallucinates APIs. Agent
performance rises sharply once the model has a mental map of the system before it edits — but
that map should be handed to it, not re-derived by it. More context is *not* better: past a
point, "context rot" degrades attention and recall (Anthropic, *Effective context engineering*).
So the orchestrator — which already knows the codebase from graphify — pre-computes the map and
passes only the relevant slice.

Before spawning the builder, the orchestrator gathers (per `coding-routing-guard.sh`):

- **`graphify query`/`explain`/`path`** — does the thing already exist? where does it live? what
  calls it? Pass the scoped subgraph with `file:line` anchors, *not* the files.
- **`~/.claude/tools/graphify-blast.sh <files>`** — the blast radius: impacted symbols/neighbors
  of what's about to change, so the coder edits a hub knowing its callers.
- **Exact file + line anchors** the unit touches (`path/to/file.py:120-155`), and the **1–3
  existing patterns to imitate** (name them: "match the error handling in `db/users.py:40`").

Rule of thumb: *if the coder would have to grep or open a file you didn't name to do the unit,
your prompt is under-specified.* Hand it the anchors instead. The coder should still read the
few files you named (BUILDER_STANDARD: "read the files you touch + their neighbors first") — you
are narrowing *what* it reads, not telling it to skip reading.

---

## 2. Scope & decompose into small verifiable units

Break the build into the **smallest independently-verifiable pieces**, one coder per unit, each
a self-contained `CONTEXT / CHANGE / GOAL / VERIFY` spec ([code-decompose](../skills/code-decompose/SKILL.md)).
Do this in a **decomposer subagent** so the heavy code-reading never touches the orchestrator's
context.

Find the sweet spot — decomposition has *two* failure modes:

- **Too big:** "build the entire feature" → huge diffs, inconsistent, unreviewable, higher error
  rate (error rate climbs sharply past ~300 generated lines).
- **Too small:** 15 micro-prompts → the coder loses architectural coherence; pieces are each
  correct but don't fit (mismatched interfaces, duplicated logic) and *you* become the
  integration layer — the hardest part.

Practical sizing: 1–3 files with existing tests → one unit is fine. 5+ files or a *new* pattern →
plan first, then 2–3 units. Split any unit whose VERIFY you can't state concretely *before*
coding — a unit without a runnable check is not ready. Structure the CHANGE as a **numbered
list** of requirements; agents track numbered lists far more reliably than prose, and you can
check each off in audit.

GPT-class coders (Codex 5.5) are **thorough and literal** by default — they over-explore and
sometimes over-engineer. Tight scope *is* the control: name the files, cap the surface, and say
"only make changes directly requested or clearly necessary" (OpenAI, *GPT-5 prompting guide*;
Cursor had to *tone down* prompts, not push for more).

---

## 3. Convey "here's how this codebase already does X — match it"

The single highest-value thing the orchestrator adds over the coder's blind view is
**convention grounding**. The coder must not reinvent or fight local patterns. In each unit's
CONTEXT, spell out:

- **The existing pattern to copy**, by anchor: "logging goes through `log.py:get_logger`, see
  `services/foo.py:12` for the call shape — match it." Grounding predictions in a real reference
  (retrieved API + example) is the research-backed defense against hallucinated APIs.
- **Local naming / structure / error style** to mirror (BUILDER_STANDARD already says "match
  local naming, structure, and error style" — your job is to *point at the exemplar*).
- **What already exists to reuse** — helper, test harness, fixture — so the coder reaches for it
  instead of writing a new one (ponytail: reuse before writing). graphify `query` is how you
  find these cheaply.

If there is a `scaffold-<category>.md` from a prior successful build (surfaces via `recall`),
pass its verified approach as the starting point — don't let the coder re-invent it.

---

## 4. Constraints & standard (prepend, don't paraphrase)

Every coder prompt = **`BUILDER_STANDARD.md` verbatim** + the unit spec + explicit negative
constraints. Negative constraints prevent the most common drift; enumerate them:

- **No invented APIs / deps.** "Use only symbols that exist in the named files or the repo's
  current dependencies. If you need something that isn't there, STOP and report — do not invent
  it." Type/reference errors and failing tests are the signals that catch hallucinated calls, so
  demand they run (§5).
- **Smallest diff.** "Do not refactor, rename, reformat, or touch code outside the named
  anchors. No new config, flags, env vars, or abstractions not in the spec." (Codex over-engineers
  without this.)
- **Match style** (§3), don't impose your own.
- **One correct interpretation.** GPT-5-class models are extremely literal; vague or
  contradictory instructions degrade their reasoning. Make CHANGE unambiguous; if the spec is
  ambiguous, the coder picks the *least-invasive* reading and states the assumption (BUILDER_STANDARD).

---

## 5. Require a runnable check per unit, then audit against the spec

**Verification is the highest-leverage practice** — giving the coder a way to verify its own work
(a test, a lint/typecheck that returns OK/FAIL, a screenshot) is what turns "looks right" into
"is right" (Anthropic, *Claude Code best practices*). The VERIFY is defined **before** coding, in
the spec. Two non-negotiables in the coder prompt:

1. **Run VERIFY and paste the real output verbatim.** Demand evidence, not assertions —
   "the test passes" without the run is a hallucinated-progress red flag. If it couldn't run,
   say exactly what is unverified and why (BUILDER_STANDARD).
2. **Solve the general case, not the test.** "Implement for all valid inputs; do not hard-code to
   pass the specific test cases." Tests verify correctness; they don't define the solution.

**Audit loop:** a **non-builder model (GLM 5.2)** audits Codex 5.5's diff against *that unit's own*
`CONTEXT/CHANGE/GOAL/VERIFY` — not against vibes ([code-decompose](../skills/code-decompose/SKILL.md) Phase 4).
The auditor gets the **same spec** + the diff and answers: does it match CHANGE exactly (nothing
extra, nothing missing)? does it achieve GOAL incl. edge cases? did VERIFY *genuinely* pass (show
the output)? any hallucinated API / violated convention? Returns PASS/FAIL + findings tied to
spec lines. On FAIL, hand the finding back to a coder; fail twice → orchestrator takes it
directly (don't spin a third worker). Commit/branch from a clean state before each unit so a bad
diff is a `git checkout` away, not surgery.

---

## 6. Ready-to-fill PROMPT TEMPLATE (paste per unit)

```
<PASTE ~/.claude/BUILDER_STANDARD.md VERBATIM HERE>

You are executing exactly ONE unit. Implement only this. Do not expand scope.

── UNIT <n>: <one-line title> ─────────────────────────────────────────────
CONTEXT (the map — you should NOT need to explore beyond this):
  Files/anchors you will touch:
    - <path/to/file.ext:START-END>  — <what's there now>
  Existing pattern to MATCH (copy this shape, don't invent your own):
    - <path/to/exemplar.ext:LINE>   — <naming/error/logging style to mirror>
  Reuse (already exists — use it, don't rewrite):
    - <helper / fixture / dep name @ anchor>
  Blast radius (callers/neighbors of what you change — don't break these):
    - <from graphify-blast: symbol @ file:line>

CHANGE (numbered, one correct interpretation):
  1. <precise edit>
  2. <precise edit>

GOAL (what must be true when done, and why — resolve any ambiguity toward this):
  <outcome + rationale>

VERIFY (run this; paste the real output verbatim in your report):
  $ <exact command>
  Expected: <observable result / file state>

CONSTRAINTS:
  - Use ONLY symbols in the named files or current repo deps. Invent no API/dep —
    if something's missing, STOP and report; do not fabricate it.
  - Smallest diff: no refactor/rename/reformat/config/flags/abstractions beyond CHANGE.
  - Match local style (see exemplar). Solve the general case, not just the test.

REPORT: files changed · VERIFY output (verbatim) · assumptions made · remaining risk.
```

**Auditor prompt** = the *same* UNIT block above + the coder's diff + code-decompose Phase-4
checklist. Auditor is a non-builder (GLM 5.2); it grades the diff against the spec lines and
returns PASS/FAIL + findings.

---

## Sources

- Anthropic — [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (context rot; curate the smallest useful context, not the most).
- Anthropic — [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices) (explore → plan → code → commit; verification is highest-leverage; demand evidence; skip planning for one-line diffs).
- Anthropic — [How Anthropic teams use Claude Code](https://www-cdn.anthropic.com/58284b19e702b49db9302d5b6f135ad8871e7658.pdf) (clean git state, commit hygiene, subagents for exploration).
- OpenAI — [GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide) (agentic eagerness; GPT-5 is literal; bound exploration/tool calls; "only changes directly requested"; Cursor toned prompts *down*).
- [Agentic Coding Best Practices — 2026](https://abdus-muwwakkil.medium.com/agentic-coding-best-practices-fc167be3f7d5) (decomposition sweet spot; ~300-line/5-file heuristics; numbered requirements; negative constraints; git safety net; hallucinated-progress signals). *Practitioner guide — treat numeric thresholds as rules of thumb.*
- [A Systematic Literature Review of Code Hallucinations in LLMs](https://arxiv.org/pdf/2511.00776) (grounding via retrieved API references + iterative context as a primary hallucination-mitigation strategy).

