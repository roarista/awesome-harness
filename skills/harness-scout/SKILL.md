---
name: harness-scout
description: Recurring "harness intelligence" pass — find harness improvements to STEAL (external) and toil to AUTOMATE (internal), proposal-only. Two modes. (A) Repetition-mine — scan Ro's recent transcripts for things he keeps hand-prompting and propose turning them into skills/hooks so he gets out of the loop. (B) Research-scout — spawn bounded research sub-agents over GitHub / AI-company frameworks / named creators (Boris Cherny, Andrej Karpathy, Peter Steinberger, Jamie West, Indie Dev Dan, …) for coding-accuracy / context-engineering / autonomy-with-quality ideas worth stealing or integrating. Use when Ro says "scout the harness", "what should we steal", "what am I repeating that should be a skill", "/harness-scout", "check what X is doing with their harness", or on a periodic improvement sweep. NEVER edits the live tree — output is a proposal report.
---

# Harness Scout — improvement intelligence (proposal-only)

The [[harness-audit]] skill looks INWARD at ONE repo and asks *"does the harness do what it says?"* (fidelity + behavioral drift). **This skill looks at IMPROVEMENT**: what should we *add* — either by stealing an external idea or by turning Ro's own repeated toil into a skill/hook. Same discipline (evidence-cited, proposal-only, fit-filtered), opposite direction.

Ro's north star for this skill: **get him out of the loop while keeping quality** — more autonomous coding that isn't slop. Every proposal must serve that, and must survive the *fit-filter* (below) — the same reasoning that killed jacobian-lens as a NON-FIT.

## Hard rules (non-negotiable)

1. **Proposal-only. Never edit any repo.** Output → `~/Downloads/HARNESS_SCOUT_<YYYY-MM-DD>.md`. Ro reviews; a normal session builds later. No hooks/skills written by this pass — it *proposes* them.
2. **Fit-filter every idea against OUR constraints — no hype.** We run **API models** (Claude / Codex 5.5 / GLM 5.2) with no weights/residual stream; Ro's machine is **low-CPU, no-VM, no-GPU** (`[[feedback_low_cpu_no_vm]]`); the harness is **ambient hooks + skills**, not a framework Ro invokes (`[[feedback_conversational_prompting]]`); ponytail governs (steal a PATTERN into a few lines, don't add a heavy dep/framework). An idea that needs GPU / open weights / a server / a big runtime is **NON-FIT — say so plainly** and move on. (Canonical NON-FIT: jacobian-lens — white-box, needs CUDA.)
3. **Evidence or it didn't happen (R1).** External claim = **URL + date**, read this run. Repetition finding = **cited transcript turns** (`file:line` of the `.jsonl`). No idea from memory or vibes. Unverifiable → mark UNKNOWN, don't ship it.
4. **Freshness: last ~30 days.** Prefer sources/repos updated in the last 30 days (`gh search repos --sort=updated pushed:>=<date>`; web results dated within a month). Older only if it's canonical/foundational. Note the date on every item so stale intel is obvious.
5. **Bounded fan-out (low-CPU).** At most a **handful** of research sub-agents, not a fleet. Prefer *reusing* existing machinery over standing up new infra: `[[deep-research]]` for the web fan-out+verify+synthesis, `youtube-research`/`ytintel` for creators who post video, `gh` CLI for GitHub. Kill any worker process trees on finish.
6. **Steal the pattern, not the repo.** Default output is "lift this idea into our ambient-hook/skill style in ~N lines", NOT "adopt framework X". Forking a heavy dep is the exception, argued explicitly, never the default.

## Mode A — Repetition-mine (INWARD: turn Ro's toil into skills/hooks)

Goal: find the things **Ro keeps hand-prompting** (or keeps having to correct/remind) that should be a skill or a hook — so he stops being in the loop for them.

1. **Corpus:** Ro's recent transcripts — `~/.claude/projects/-Users-rodrigoarista/*.jsonl` (main session, richest) + the per-repo project dirs under `~/.claude/projects/` for the 4 live repos. Last ~2–4 weeks by mtime; don't read the whole history.
2. **Signal (extract `type:"user"` messages + assistant corrections):**
   - **Repeated instructions** — the same ask/phrasing recurring across sessions ("always use subagents", "update the .now.md", "don't narrate", "process the inbox"…). Recurrence = candidate for a hook (auto-fire) or skill (one-word invoke).
   - **Recurring toil** — the same multi-step manual sequence Ro walks the agent through repeatedly.
   - **Repeated corrections** — Ro correcting the same drift again and again → candidate for an enforcement hook (the behavioral-gap pattern, cf. [[harness-audit]] rule 5).
3. **Classify each candidate:** already covered by an existing skill/hook? (list them first, don't re-propose). If not → propose **skill** (Ro-invokable / ambient trigger) or **hook** (auto-fire, no invoke — preferred, since Ro barely invokes skills). Cite the repeated turns as evidence.
4. Rank by *loop-exit value* = (how often Ro does it by hand) × (how mechanizable) − (slop risk if automated). High-frequency + low-slop-risk first.

## Mode B — Research-scout (OUTWARD: what to steal / integrate)

Goal: surface external ideas that improve **coding accuracy, context engineering, autonomy-with-quality**, plus **open-source we could integrate**. Spawn bounded research agents; each returns candidates with URL+date and a fit verdict.

**Query set (curate per run; bound it):**
- **GitHub, last 30 days** — `gh search repos --sort=updated 'claude code agent harness'`, `'context engineering llm agent'`, `'coding agent autonomy'`, `'agent skills hooks'`, `pushed:>=<date>`. Fetch the top few READMEs; extract the mechanism.
- **AI-company / lab frameworks** — what Anthropic / OpenAI / Cognition / etc. published recently on agent harnesses, context engineering, tool use, sub-agent orchestration. Anything OSS we could lift.
- **Named creators (harness watch-list) → route to `youtube-research`/`ytintel`, NOT Twitter.** These people live on YouTube + social, and **X is not reliably scrapable without auth** (Ro's call: don't try to scrape Twitter). So for each creator, run the `youtube-research` skill / `ytintel` to pull their recent videos + transcripts, and only fall back to `WebFetch` on their GitHub (sort repos by updated) / blog. If nothing attributable is found, mark **UNKNOWN** — never invent.
  - **Boris Cherny**, **Andrej Karpathy**, **Peter Steinberger**, **Jaymin West**, **IndieDevDan (disler)** — + any new name Ro drops.
- **News intel → Ro's newsletter emails (last 7 days).** Ro gets daily AI newsletters — **The Rundown AI**, **Morning Brew** (has AI items), + one more — that are the freshest signal (Twitter is the real hub but unscrapable, so email is the proxy). Read the last 7 days of those senders and extract anything harness/agent/coding-relevant. **Wiring (pending Ro's setup):** no iCloud-Mail MCP exists → the lazy path is Ro forwards those 3 senders (iCloud Mail rule) to a Gmail he connects, then this pass reads them via the **Gmail MCP** (`mcp__claude_ai_Gmail__search_threads` on `from:(rundown OR morningbrew OR …) newer_than:7d`). Alt: IMAP with an iCloud app-specific password (Ro creates it; the agent never types the credential).
- **Idea inbox → Notion "New — <project>" folders.** Ro parks social-media ideas he never implements in Notion (migrating from iCloud Notes → Notion for the MCP). Per-project folders named `New — <project>`. This pass reads them, transcribes any pasted videos → markdown, brainstorms how each applies to that project, and returns a per-project "focus / prompts to paste" summary — nudging Ro to actually implement. **Reuse the existing `[[notes-inbox]]` / notes-pipeline** infra (Notion + `~/Notes` mirror + video transcription) — extend it with the per-project New-folders + a triage/suggest step; do NOT build a new pipeline. ⚠️ Notion MCP historically pointed at the WRONG workspace → verify the target, use Notion REST if the MCP is mis-scoped.
- **Reuse `[[deep-research]]`** for any heavy web fan-out+adversarial-verify+synthesis rather than hand-rolling searches.

**For each candidate, fit-filter (rule 2) → verdict:**
- **STEAL** — pattern we lift into a hook/skill in ~N lines. Sketch the integration (which hook/file, roughly).
- **INTEGRATE** — OSS worth actually adding (argue the dep cost vs ponytail).
- **WATCH** — promising but not now (why).
- **NON-FIT** — needs GPU / weights / server / heavy runtime, or clashes with ambient-hooks/low-CPU. State the blocker in one line.

## Output — the report

`~/Downloads/HARNESS_SCOUT_<YYYY-MM-DD>.md`:
1. **Summary** — headline count per mode; the single highest-value "build next".
2. **A. Repetition → automate** — table: repeated pattern → cited turns → propose skill|hook → loop-exit value → slop risk.
3. **B. External steal-worthy** — table: idea → source (URL+date) → verdict (STEAL/INTEGRATE/WATCH/NON-FIT) → integration sketch. Group by theme (accuracy / context-eng / autonomy / OSS).
4. **C. Creator intel** — per creator: what's new in their harness (URL+date), and our applicability.
5. **Ranked "build next" shortlist** — top 3–5 across both modes, each with a one-line why + rough effort. Proposal-only; Ro picks.

The report lands in `~/Downloads/`, which `~/.claude/tools/memgraph/sources.txt` globs → auto-indexes into recall on the next `mem rebuild`. Prefix `HARNESS_SCOUT_` (already covered by the `HARNESS_*` glob).

## Cadence
On demand. Do **not** stand up new standing infra speculatively (ponytail) — `harness-coach` already runs a weekly launchd log-audit; if Ro wants scout periodic, **fold Mode A into harness-coach** rather than adding a second cron. Mode B (web research) is token-heavy → run it when Ro asks, or bounded, not on every cron.

## When NOT to use
- Mid-implementation of an unrelated task (this is a periodic sweep, not a blocker).
- As an auto-applier — it is structurally proposal-only. Building anything it proposes is a separate, explicit step (and, per Ro's routing default, goes to a codex/glm sub-agent).
- To chase a single named tool Ro already decided on — just research that directly.
