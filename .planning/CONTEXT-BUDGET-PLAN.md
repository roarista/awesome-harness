# Context budget — why it stacks, and the plan

**Status:** PLAN ONLY, nothing built. Ro asked to plan before building ("claramente puede salir muy mal").
**Research:** `.scratch/research-context-offload.md` (measured numbers, not adjectives).

## Why the context "multiplies" (Ro's question)

The context window is not a working set that gets swapped. It is an **append-only
transcript** re-sent in full on every single turn. Nothing ever leaves it until a compact.

So a 700-word subagent report is not paid once. It is paid on that turn, and again on
every turn after it, until compaction. That is the "se hace stack up… es exponencial"
Ro noticed. It is not exponential — it is **linear in tokens but quadratic in cost**,
because turn N re-sends everything from turns 1..N-1.

Consequence: the cheapest token is the one never written into the transcript. Deleting
something later does not refund it. **Only what never enters the main transcript is free.**

## Q1 — Findings ledger

**Verdict: mulch already does 99% of this. Do NOT build a store.**

Measured: a 350-line / 37,082-byte finding recorded with `ml record`, retrieved with
`ml query --format compact` → **217 bytes (~55 tokens) = 0.6% of the full record**,
including the auto-generated id (`mx-f0d85e`). `ml ready` ≈ 120 bytes.
That IS "15 lines + an ID" — working today, no new code.

**The one real gap: no fetch-by-ID.** `ml query`/`ml search` have no `--id`;
`ml search mx-f0d85e` returns "No records matching"; `--format ids` is documented but
rejected at runtime (v0.7.0 bug). Records are one-JSON-per-line, so a ~1-line
jq/python fetch closes it. **That alias is the entire build.**

Also: **awesome-harness has no `.mulch/`** (8 other repos do). `ml init` needed here.

Rejected after measurement: memgraph/recall (cross-session topic memory — wrong layer),
`.scratch/` (honest baseline but no id, no index, no session scoping), phantom-edit.jsonl,
the reports dir.

### Proposed shape (per session, Ro's design)
- Session opens (`/awesomeharness` or post-compact) → a session tag, e.g. `s-<short>`.
- Subagent finishes → `ml record findings "<full 400 lines>" --tag s-<short>` → gets an id.
- Subagent's reply to the orchestrator: ≤15 lines + `mulch: mx-f0d85e`.
- Orchestrator wants the detail → `ml get mx-f0d85e` (the alias to build).
- Compaction survives it: the ledger is on disk, not in the transcript.

**Open question for Ro:** who writes the 15-line summary? If the subagent writes both the
full record and the summary, the summary is self-reported — the same self-verification
problem we already distrust. Cheapest honest option: the subagent writes the record; the
summary is mechanical (verdict + file list + VERIFY exit codes), not prose.

## Q2 — Per-file summaries so the orchestrator reads meaning, not code

**Verdict: PARTIALLY solved, and the repo already half-solved it by hand.**

Repowise `get_context` measured on 4 real files: **5,689 vs 10,736 tokens = 47% saving**
(not the 37% its guide claims). All `verified: true`. BUT **3 of 4 self-flag
`mostly_full: true`** ("a direct Read costs little more"), and repowise's *meaning* layer
is EMPTY in this repo: `get_overview` → "No overview generated yet.", `get_answer` →
empty answer, low confidence. Its only per-file summary is mechanical:
*"northstar-inject.py: functions _looks_like_project, bump, git_context (+4 more)."*
That is a signature list, not meaning. Graphify is worse here: no `graphify query`
subcommand exists, and `graphify explain` returns a 110-byte card with zero prose.

**What already works, for free:** every Python file in this repo carries a hand-written
4–37 line module docstring stating the problem, the rationale, and the rejected
alternatives. Drift-free by construction (it lives in the file it describes). This is
exactly Ro's "hashtag al principio que explique el código". **It already exists.**
The missing piece is a one-liner that harvests those docstrings into one digest.

**The load-bearing warning against the auto-generated version:** a 2026 study found
LLM-generated AGENTS.md files **cut task success ~2% while raising cost ~23%**.
Auto-summaries that restate signatures are a NET NEGATIVE. Only human-written
non-obvious information (why, constraints, rejected paths) pays for itself — which is
precisely what the existing docstrings contain and what a generator cannot invent.

**So: harvest what humans wrote. Do not generate summaries.**

Drift is the known killer. Best prior art if we ever need enforcement:
`fiberplane/drift` (XxHash3 over tree-sitter-normalized AST, exits 1 in CI) and
Swimm Auto-sync (auto-fix on rename/move, escalate to a human on a real change).
Ro's rule stands: **the code is the truth; the markdown must be audited against it.**

## Ranked plan (cheapest first, each independently shippable)

1. **`ml get <id>` alias** (~1 line) + `ml init` here. Unlocks the whole ledger. XS.
2. **Report contract already shipped** (docs §5b + opus.md): ≤15 lines, detail to a file.
   Point it at mulch ids once step 1 exists.
3. **Docstring digest** — one command that prints every module docstring in the repo.
   Orchestrator reads that instead of opening files. S. No generation, no drift.
4. **Orchestrator read discipline** — `get_context` skeleton or a line range instead of a
   full Read; `repowise distill` for noisy commands. Behavioral, zero code.
5. **Repowise's meaning layer is unbuilt here** — decide whether to generate the wiki.
   Given the −2%/+23% study, do this LAST and only if 1–4 prove insufficient.

**Not doing:** a new findings store, auto-generated per-file summaries, splitting code
files into "summary" and "code" sections (would break every tool that reads them).
