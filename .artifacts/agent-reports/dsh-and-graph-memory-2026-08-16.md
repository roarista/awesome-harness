# DeepSeek Harness + the two Glitch Cat artifacts — full exploration & integration plan
2026-08-16 · exploration only, nothing installed or changed

## 1. DeepSeek Harness (`dsh`) — what it actually is

Verified from the repo (`deepseek-ai/deepseek-harness`, master, pushed 2026-08-13, MIT, TypeScript,
7,412 tracked files excluding node_modules: `packages/` 3,748, `.agents/` 2,078, `docs/` 324).

- **Everything-is-a-plugin, literally.** It runs on vendored **Cordis** (a DI/plugin framework with
  reversible effects). The model adapter, the tool registry, the session log and *the agent loop
  itself* are plugins. `dsh --profile web --dump-config` prints the whole boot tree, and any row can
  be replaced by a `cordis.patch.yml` layer.
- **Composition model:** profile → ordered bundles → profile patch → home patch → `--patch` overlay.
  `dsh-base` (models, tools, persistence, sandbox, approval) is layer 0; `dsh-web-app` and
  `dsh-headless` sit on top.
- **Capability seams** are the core idea worth learning: every capability = Service Definition +
  Provider(s) + Consumer(s). Swap `ctx.fs` + `ctx.subprocess` to E2B and Bash/PTY/LSP all move with
  it, no forks. Same for `ctx.subagents`, `ctx.shell`, `ctx.compaction`, `ctx.llm`.
- **Session log is the single source of truth**, with a hard invariant: *model-visible ⟺ logged*.
  Anything that reaches a model request must be reconstructable from the append-only log. That is a
  stronger version of what we keep trying to enforce with `.now.md`/STATE by hand.
- **Turn/step/round vocabulary**, waterfall extension points (`agent/pre-step`, `agent/request`,
  `llm/stream`, `tools/pre|execute|post`), plus `agent/turn-stopping`.
- **It already speaks our dialect.** `packages/hooks/hooks-claude-code` runs *our existing
  `.claude/hooks.json` command hooks* on its own interception points (`UserPromptSubmit` →
  `agent/pre-step`, `PreToolUse` → `tools/pre-execute`, etc.), and `packages/subagent/` ships
  `subagent-codex` and `subagent-claude-code` providers. There is also `packages/hooks/hooks-codex`.
- **Efficiency:** the README makes **no** performance claim. `BENCHMARK.md` is three lines pointing
  at the Python SDK. "More efficient" is not a measured property of dsh — it is an *architectural*
  claim (replaceable parts, one seam swap moves the world). Treat the efficiency story as unproven.
- **Status:** developer preview, "THERE WILL BE COMPATIBILITY-BREAKING CHANGES", session format
  version pinned at 0 with no compatibility promise, backends reject old on-disk formats.

### Verdict on dsh: do not migrate. Steal two things, watch the third.
Migrating means replacing Claude Code (our whole harness — 47 live hooks, skills, agents, router)
with a preview-stage TS monorepo whose stated policy is to break formats freely. It duplicates what
we already have and adds a build system we would own.

What is genuinely worth taking:
1. **The seam discipline** (Definition/Provider/Consumer, never one role) as the shape for our own
   tool routing — our `tools/route-model.sh` is already a Definition+Consumer with no explicit
   provider registry.
2. **`model-visible ⟺ logged`** as a harness invariant. We have the opposite failure mode on record:
   `procedure-does-not-run.md`, `green-exit-code-was-a-dispatch-receipt.md`.
3. **Watch, don't adopt:** if DeepSeek pricing ever matters, our hook layer ports for free through
   `dsh-hooks-claude-code`. That is the cheap-optionality reason to keep an eye on it, nothing more.

## 2. Artifact A — "The Quality Gates: 26 prompts that make AI code actually work"

Read in full (26 gates, five phases: before you touch code / attack the design / tests that can't
lie / review that finds things / before it ships). Each gate is a prompt plus the real defect that
earned it.

**Where we already are strong:** prior-art and enumeration chains (`c2-prior-art.sh`, `c3-enumerate.sh`)
cover gates 5, 7, 12 (sibling sweep, consumer sweep, flow-not-pattern trace). Two-model review
(gate 18/19) is our council. `check-all` covers the pre-ship battery. `understand-gate.py` is gate 1's
cousin.

**Genuine gaps, in value order:**
- **Gate 15 — mutation-proof every test.** Grepped the whole repo: zero mutation testing anywhere
  (`mutation` appears only in unrelated prose). Every one of our "auditor PASS" claims rests on tests
  nobody has ever watched go red. This is the single highest-yield addition, and it lines up exactly
  with our own measured lesson `verified-where-it-cannot-fail.md`.
- **Gate 16 — hollow-proof:** "would this test be green on the broken version?" One line in the
  auditor spec.
- **Gate 4 — guarantee register** before a rework (their number: a rework would have broken 44 of 196
  guarantees). We have no equivalent; our reworks rely on the auditor noticing.
- **Gate 20 — "no findings" must show its work.** Our auditors are allowed to return a bare PASS.
  This is `auditor-caught-the-silent-empty.md` again: a silent empty read as success.
- **Gate 25 — run it twice, then inspect the artifacts left behind**, not the output. Directly
  addresses `green-exit-code-was-a-dispatch-receipt.md`.
- Gates 9/10/11 (kill mid-step, degrade the environment, real-world inputs) matter for our launchd /
  TCC / path-with-spaces history.

## 3. Artifact B — "Applying Knowledge Graphs" (the "better than grep" one)

The thing better than grep is **not** a search tool — it is **push instead of pull**:

- **Pull** (what we do): the model greps and reads during the turn. Cost grows with corpus, accuracy
  depends on model.
- **Push**: a `UserPromptSubmit` hook queries a fact graph in ~2 ms with **zero LLM calls** and
  injects the answer path as `additionalContext` before the model wakes.
- Tier 1 is deliberately tiny: **3 SQLite tables** (entities / relations / aliases), **1 recursive
  CTE** for the walk, **1 hook**, ~250 lines, no server, no key.
- Identity is *computed*, not matched: `uuid5(type + normalised name)`, so the same entity in two docs
  collapses to one node and re-extraction merges instead of duplicating.
- Their measured result on a 3-hop trap (rule in one file, person in another, cover in a third, no
  shared vocabulary): search → Haiku **wrong**, Sonnet correct but 5 searches/8 file reads/13 calls,
  Fable 5 correct in 20 s. Graph → **all three correct, 0 tool calls, ~400 tokens fixed at any corpus
  size**. Caveats they state honestly: lexical seeding misses unknown vocabulary, top-k crowding on
  dense hubs, tier move past a few hundred thousand edges.
- Repo: `github.com/Glitch-Cat-Club/graph-memory-starter`. n=1 corpus, one question, six runs — the
  *mechanism* generalises, the numbers are theirs.

### What this means for us — we already built it and it is switched off

Verified this session:
- `hooks/recall-inject.py` **is** exactly this mechanism: a `UserPromptSubmit` hook that queries
  `~/.claude/tools/memgraph/out/memindex.sqlite` and injects top memory hits.
- It is **not wired**. Live `~/.claude/settings.json` has 6 hooks: `SessionStart` (codemap-inject),
  4× `PreToolUse`, 1× `PostToolUse`. **No `UserPromptSubmit` entry at all.**
- The index has **3 rows**, last built **2026-08-11**, while this repo's `memory/` alone holds ~35
  memories. `memgraph/out/graph.json` is 1.9 KB.
- So our retrieval is: pull-only, plus a stale 3-fact index nobody queries. Exactly the failure class
  in `wire-what-exists-before-building.md`.
- Our memgraph is also **FTS-only, one hop**: it indexes name+description and follows `[[wikilinks]]`.
  It has no typed entities/relations and no recursive walk, so a multi-hop question
  ("who approves X in March") cannot be answered by it even when the facts are all present.

## 4. Integration plan — ranked, smallest diff first

**U1. Wire the hook we already have.** Add one `UserPromptSubmit` entry for `recall-inject.py` to
`~/.claude/settings.json` and rebuild the index (`memgraph/build.py`) over all project memory dirs,
not just the most recently modified one (`_default_memdir()` currently picks exactly one). Cost: one
JSON block + one cron/SessionStart rebuild. This alone turns 3 stale facts into ~all of them and
makes recall automatic. **Verify by:** a prompt naming a known memory shows the injected counts line.

**U2. Give memgraph the two jobs.** Add `relations` (source, target, predicate) + `aliases` beside the
existing FTS table, `uuid5(type+name)` ids, and the recursive-CTE walk from the artifact. Keep FTS as
the seeder. ~150 lines on top of what exists, still one SQLite file. **Verify by:** planting our own
3-hop trap out of real harness facts (e.g. "who audits a codex build" → codex builder → codex-audit →
read-only sandbox) and checking the walk returns the chain with zero tool calls.

**U3. Mutation-proof + hollow-proof the auditors.** Add gate 15/16/20 to the `codex-audit` and `opus`
agent specs: for each test claimed as proof, make the change that should break it, watch it fail by
name, revert; and a PASS must list what was attacked and found sound. Diff is prose in 2 agent files,
and it attacks the exact defect class our own audits keep finding.

**U4. Gate 25 into `check-all`:** run the target twice and diff the artifacts it left behind, not its
stdout. One shell step in `c7-preship.sh`.

**U5. dsh: watch only.** No migration. If we ever want it, the entry cost is `configPath:
./.claude/hooks.json` in a `cordis.yml` — our hooks are already the compatible dialect. Revisit only
if (a) it tags a release, or (b) DeepSeek token economics beat our Codex credits.

**Skipped deliberately:** ast-grep/comby (the artifact's "better than grep" is push retrieval, not a
matcher; `semgrep` + `graphify` already answer "all the places" and "structure"); Tier 2/3 graph
engines (we are ~35 facts, not 350k); porting anything from dsh's TypeScript.

## 5. Honesty notes
- dsh efficiency claims: **none exist in the repo.** Anyone who says dsh is "much more efficient" is
  extrapolating from the architecture.
- The graph-memory numbers are one corpus, one question, six runs, self-reported by the author.
- Nothing in this report was installed, wired, or edited. U1–U4 are proposals.
