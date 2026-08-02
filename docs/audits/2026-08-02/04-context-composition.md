# 04 — Context Composition: what actually fills the main agent's window

Read-only forensics over `~/.claude/projects/*.jsonl`. No source touched.

**Corpus.** 3,785 JSONL files / 2.36 GB total. Main-agent transcripts (project-root
`<sessionid>.jsonl`, sidechains excluded) = 1,181 files / 437 MB across
virality-pipeline, Vividlist, Consulting, awesome-harness, intrn.

**Critical stratification.** 1,143 of those 1,181 are *batch* sessions
(virality-pipeline pipeline invocations, 1–2 prompts, no context-window problem).
The population Ro is actually complaining about — **interactive main-agent sessions
(>= 3 user prompts) — is 22 sessions**, median **~50 user turns / 255 API calls each**.
Every number below is that 22-session cohort unless marked otherwise.

**Two measurement caveats, stated up front.**
1. `thinking` blocks are persisted with the text stripped (signature only), so
   assistant thinking is **not measurable from disk** and reads as 0%. Treat it as
   an unknown ~2–8% and do not conclude "thinking is free".
2. Pasted images are stored as base64. Counting base64 chars/4 makes them look like
   64% of everything, which is wrong — an image bills ~1,500 tokens, not ~170,000.
   117 images across the whole cohort ≈ **175 K tokens total, i.e. negligible**.
   All primary tables below are **ex-image**. This is exactly the "loudest thing"
   the brief warned about; it is not the biggest thing.

---

## 1. COMPOSITION — ranked

Chars→tokens at /4. `RAW` = tokens appended to the transcript over the session.
`AMPLIFIED` = tokens × API calls remaining after the item appeared — i.e. tokens
actually re-sent (see §5). Percentages ex-image.

| # | Source | RAW ktok (cohort) | raw % | AMPLIFIED Mtok·calls | amp % |
|---|--------|------:|------:|------:|------:|
| 1 | **user_message (typed + injected user blocks)** | 1,504 | 17.6% | 594.8 | **17.8%** |
| 2 | **STATIC PREAMBLE** (system prompt + tool schemas + MCP instructions + CLAUDE.md) | 1,128 | 13.2% | 494.7 | **14.8%** |
| 3 | tool_result: **Bash** | 847 | 9.9% | 370.5 | 11.1% |
| 4 | tool_use params: **Task/subagent** (prompts we send out) | 908 | 10.6% | 312.4 | 9.3% |
| 5 | tool_use params: **Bash** (heredocs!) | 719 | 8.4% | 294.4 | 8.8% |
| 6 | **HOOK: hook_additional_context** (UserPromptSubmit — northstar/recall/handoff) | 696 | 8.1% | 269.4 | 8.1% |
| 7 | tool_result: **Task/subagent** (what they return) | 531 | 6.2% | 200.8 | 6.0% |
| 8 | assistant_text | 513 | 6.0% | 171.4 | 5.1% |
| 9 | **HOOK: PreToolUse:Agent** (routing policy) | 445 | 5.2% | 153.9 | 4.6% |
| 10 | attachment: **skill_listing** | 319 | 3.7% | 122.8 | 3.7% |
| 11 | tool_use params: Edit/Write | 308 | 3.6% | 121.7 | 3.6% |
| 12 | attachment: file (@-attached / auto) | 193 | 2.3% | 86.3 | 2.6% |
| 13 | HOOK: SessionStart:compact | 110 | 1.3% | 49.0 | 1.5% |
| 14 | tool_result: **Read** | 155 | 1.8% | 39.9 | 1.2% |
| 15 | tool_result: MCP | 12 | 0.1% | 10.3 | 0.3% |
| 16 | tool_result: Edit/Write | 19 | 0.2% | 7.9 | 0.2% |
| — | tool_result: Grep/Glob | ~0 | ~0% | ~0 | ~0% |
| — | assistant_thinking | **unmeasurable** (stripped on disk) | — | — | — |
| — | `<system-reminder>` text blocks | 0.4 | 0.0% | — | 0.0% |

Per-session share, **median / p90** (own denominator per session):

| Source | median | p90 |
|---|---:|---:|
| tool_use params (all tools) | 23.9% | 26.9% |
| tool_result (all tools) | 20.5% | 27.6% |
| **hook-injected (all our hooks)** | **14.5%** | **28.7%** |
| user_message | 13.5% | 24.7% |
| — of which tool_result:Bash | 9.0% | 18.1% |
| — of which tool_result:Task/subagent | 5.7% | 15.4% |
| assistant_text | 5.0% | 8.5% |
| attachment:skill_listing | 3.6% | 6.0% |
| tool_result:Read | 0.7% | 6.2% |
| tool_result:Edit/Write | 0.1% | 0.4% |

**Rank, plain English.** The window is filled by (1) a large fixed preamble paid on
every call, (2) what *we send out* — user prompts, subagent prompts, Bash command
bodies — more than by what comes back, (3) Bash output, and (4) our own hooks.
`Read` and `Grep` are near-zero: Claude Code already spills oversized tool results
to `tool-results/*.txt` on disk. Read-bloat is not the problem here.

---

## 2. GROWTH CURVE

Real token counts from `message.usage` (`input_tokens + cache_read + cache_creation`),
median across the 22 sessions, keyed by user-turn index.

| turn | median ctx tok | p90 | max |
|---:|---:|---:|---:|
| **first API call of session** | **57,563** | 96,966 | 102,879 |
| 1 | 85,923 | 125,561 | 144,306 |
| 2 | 83,124 | 146,902 | 150,986 |
| 3 | 105,791 | 165,421 | 203,616 |
| 4 | 154,945 | 216,066 | 247,124 |
| 6 | 142,865 | 218,267 | 275,654 |
| 8 | 190,946 | 242,896 | 305,013 |
| 9 | 244,214 | 305,795 | 324,336 |
| 13 | 173,656 | 191,814 | 293,642 |
| 18 | 258,490 | 275,160 | 278,432 |
| 25 | 220,133 | 301,783 | 315,018 |
| 40 | 168,460 | 274,873 | 298,050 |
| 56 | 251,131 | 277,938 | 284,996 |
| 90 | 361,809 | 366,042 | 366,364 |

The curve **saws** after turn ~10 because compaction keeps resetting it (§6);
the *underlying* accretion is **linear at roughly +15–20 K tokens per user turn**,
not accelerating.

Turn-1 context by project (the fixed floor before any work happens):

| project | median turn-1 ctx | max |
|---|---:|---:|
| awesome-harness | **42,850** | 54,583 |
| intrn | 55,783 | 77,411 |
| Consulting | 55,801 | 58,062 |
| Vividlist | 68,039 | 98,039 |
| virality-pipeline | **80,342** | **102,879** |

**Crossing points (median session).** Against a 200 K working window:
50 % (100 K) is crossed at **turn 3**; 80 % (160 K) at **turn 6–7**.
Against the empirically observed ceiling where compaction actually fires (~250 K):
crossed at **turn ~9** median, **turn ~4** at p90.

The single most important line in this whole report: **a session starts at 43–103 K
tokens (median 57.5 K) with zero work done.** That is 22–50 % of a 200 K window
consumed by the preamble before the first character of Ro's request.

---

## 3. BIGGEST SINGLE ITEMS — there is no monster

Top individual payloads across the interactive cohort. **The largest single item in
the entire corpus is 14.8 K tokens.** There is no unbounded `git log`, no `ls -R`,
no 3,000-line Read. Claude Code's tool-result spill-to-file already caps that class:
only **3** tool_results in the whole cohort exceed 30 K chars (7.5 K tok).

| ktok | kind | detail |
|---:|---|---|
| 14.8 | `tool_use:Agent` | subagent prompt — "You are writing 4 new markdown research files into an existing Obsidian consulting vault…" (Consulting) |
| 14.3 | `tool_use:Bash` | `cat > "…/_knowledge/tech-patterns/microsoft-stack/15-lo-que-faltaba-entender.md" <<'EOF'` — **file body written through a Bash heredoc** |
| 13.4 | `tool_use:Write` | scratch file write (Consulting) |
| 13.3 | user_block | **awesomeharness SKILL BODY** re-injected |
| 12.5 | `tool_use:Write` | same file as row 2, written again via Write |
| 11.6 | `tool_use:Agent` | subagent prompt, "Write TWO new markdown files into…" |
| 11.1–9.0 | user_block ×7 | **awesomeharness SKILL BODY**, re-injected again and again |
| 10.2 | user_typed | `/awesomeharness` slash-command expansion |
| 9.9 | `tool_result:Read` | `~/Downloads/meeting_transcript_2026-07-21.md` (legitimately large source doc) |
| 9.1 | `tool_use:Bash` | `mkdir -p …/.scratch/viz && cat > …` — another heredoc file body |
| 9.0 | user_typed | `"This session is being continued from a previous conversation…"` — **compact summary** |
| 7.5–4.8 | attach:skill_listing ×8 | full skill catalogue, re-injected 5.5×/session |
| 7.1 | `tool_result:Bash` | `ml search "open plan" 2>&1 \| head -30; echo …; ml search "room separation"…` (Vividlist) — already `head`-bounded, still 7 K |
| 5.7 | `tool_result:Read` | `~/.claude/jobs/12bbb61a/tmp/products_discovery_api_openapi_doc_discovery.md` |
| 3 items | `tool_result:Read` >30 K chars | the only oversized Reads in the cohort: a meeting transcript, `S2_STRATEGY_PLANNING.md`, `TARGET_PIPELINE.html` |

**Necessary?**
- The heredoc Bash writes (rows 2, 10) are **avoidable** — the entire file body sits
  in `tool_use.input.command` *and* is often re-written via `Write` moments later
  (rows 2 and 5 are the same file, ~27 K tokens for one file).
- The awesomeharness skill body (rows 4, 7) is **necessary once, paid 3× per session**.
- The subagent prompts (rows 1, 6) are necessary — but note we spend **more tokens
  briefing subagents (908 ktok) than they return (531 ktok)**.
- The Reads are legitimate.

---

## 4. HOOK / INJECTION OVERHEAD — our own harness

Per interactive session, mean:

| injection | fires/session | tok/fire | **tok/session** |
|---|---:|---:|---:|
| `hook_additional_context` (UserPromptSubmit: northstar-inject / recall-inject / RESUME HANDOFF) | 155.6 | 203 | **31,661** |
| `HOOK:PreToolUse:Agent` (ROUTING POLICY — "main orchestrates, codex builds, opus audits") | 48.1 | 421 | **20,235** |
| `HOOK:SessionStart:compact` | 13.0 | 384 | 5,009 |
| `HOOK:SessionStart:startup` | 3.9 | 388 | 1,516 |
| `HOOK:SessionStart:resume` | 8.3 | 151 | 1,250 |
| `hook_system_message` | 5.8 | 222 | 1,279 |
| `HOOK:SessionStart:clear` / `:fork` | 1.2 | ~350 | 404 |
| **HARNESS HOOK SUBTOTAL** | **~236** | — | **61,354 tok/session** (median 39,595) |
| `attachment:skill_listing` (CC built-in, inflated by our ~20 custom skills) | 5.5 | 2,636 | 14,496 |
| `attachment:file` | 7.6 | 1,157 | 8,780 |
| `attachment:nested_memory` | 0.4 | 2,501 | 910 |
| `<system-reminder>` blocks | — | — | ~20 |

**Share: hooks are 15.7 % of raw session tokens and 15.0 % of amplified tokens
(both ex-image); median per-session hook share 14.5 %, p90 28.7 %.**

Note `PreToolUse:Agent`: a **static, unchanging routing policy** re-pasted 48 times
per session at 421 tok each. It is identical every time. Same for the bulk of
`hook_additional_context` — the RESUME HANDOFF block is re-injected on essentially
every user prompt (155 fires vs ~50 turns, so >1 per turn).

Verdict: at ~61 K tok/session the hooks cost roughly **one full extra session boot**.
They are not the #1 line item, but they are the #1 line item *we control outright*.

---

## 5. REPETITION / AMPLIFICATION — the number that matters

Transcripts are append-only and re-sent on every API call. Median interactive
session = **255 API calls**. An item added at call *k* is paid **(255 − k)** more times.

Cohort totals: **8,570 ktok raw → 3,347 Mtok·calls amplified (ex-image)**.
Mean amplification factor ≈ **390×**.

Ranked offenders by amplified cost (ex-image), from §1:

| rank | offender | amp % | why it's expensive |
|---:|---|---:|---|
| 1 | user_message + injected user blocks | 17.8% | includes the **re-injected awesomeharness skill body and compact summaries**, added *mid-session* at call 167/253/279/359/402/697/737 — each one then re-sent for the rest of the run |
| 2 | **STATIC PREAMBLE** | 14.8% | 57.5 K tok present from call 0, therefore multiplied by **all 255** calls. Worst amplification factor in the system. |
| 3 | tool_result:Bash | 11.1% | ~9 % of every session, forever |
| 4 | tool_use:Task/subagent | 9.3% | briefing text |
| 5 | tool_use:Bash | 8.8% | heredoc file bodies |
| 6 | HOOK:hook_additional_context | 8.1% | 155 small injections, each amplified |
| 7 | tool_result:Task/subagent | 6.0% | |
| 9 | HOOK:PreToolUse:Agent | 4.6% | |
| 10 | attachment:skill_listing | 3.7% | 2.6 K tok × 5.5 injections |

**Re-injection census** (identical text, injected more than once in the same session):

| repeated payload | mean ×/session | mean tok/session | worst session |
|---|---:|---:|---|
| awesomeharness skill body | 3.0× | **18,378** | 15× / 97,859 tok (virality `12bbb61a`) |
| compact summary ("This session is being continued…") | 2.5× | **15,575** | 10× / 70,331 tok (Vividlist `10096718`) |
| skill_listing | 5.5× | **14,496** | 16× / 37,614 tok (virality `a891d580`) |
| **total duplicated text** | — | **~48,449 tok/session** | 186 K tok in the worst session |

Nearly **50 K tokens per session are byte-identical text we already sent**, and every
copy is then amplified across the remaining calls. Note the top-amplified individual
items in §3 are dominated by exactly these three payloads.

---

## 6. COMPACTION

16 sessions corpus-wide carry `compact_boundary` markers; within the interactive
cohort, **20 of 22 sessions compacted** — **52 measured drops**, up to **20
compactions in one session** (Vividlist `10096718`, 113 turns).

| metric | value |
|---|---:|
| median context immediately **before** compaction | **251,383 tok** |
| median context immediately **after** | **99,711 tok** |
| median recovered | **~60 %** (range 52–83 %) |
| largest observed pre-compaction context | 366,364 tok (virality `a891d580`, turn 95) |
| smallest pre-compaction trigger | 208,948 tok (intrn `775e6ad1`) |
| recorded trigger | **`manual` on 54/54** — every single one |

**Trigger: not the model, us.** Every compaction in the cohort is `trigger: "manual"`,
i.e. `/compact` fired deliberately (compact-prep / the harness / Ro), consistently in
a tight **209 K–366 K** band. Auto-compaction never fires.

**What compaction actually buys.** It drops you to a ~100 K floor, not to zero — and
that floor is exactly §2's preamble (57.5 K) plus the re-injected compact summary
(~6 K), skill_listing (~2.6 K), and SessionStart hooks. So one compaction recovers
~150 K of usable window ≈ **8–10 turns at +15–20 K/turn**, and then you pay it again.
In `12bbb61a` that cycle ran **18 times**.

---

## 7. THE THREE CUTS THE DATA SUPPORTS

Ranked by tokens saved per interactive session (and by amplified cost).

### CUT 1 — Shrink the static preamble (tool schemas / MCP servers)
**Saves ~25–40 K tok/session, amplified across all 255 calls ≈ 14.8 % of everything.**
Turn-1 context ranges 42.8 K (awesome-harness) → 80.3 K (virality-pipeline) → 102.9 K
max. That **~40 K spread is pure per-project configuration**, not work. The heavy
projects load Canva, Figma, Gamma, Gmail, Calendar, Drive, HuggingFace, Notion,
PubMed, Supabase, n8n, Vercel, sparktoro, repowise and claude-in-chrome. Deferred
tool schemas already help; the fix is to make **every project match awesome-harness's
42 K floor** by enabling MCP servers per-project instead of globally.
This is the highest-leverage cut because the preamble has the maximum possible
amplification factor (present from call 0).

### CUT 2 — Stop re-injecting identical text
**Saves ~48 K tok/session (up to 186 K in the worst session).**
Three payloads, all byte-identical on repeat:
- awesomeharness skill body — 3.0×/session, 18.4 K tok. Make `/awesomeharness`
  idempotent per session: if already installed, inject a 200-token acknowledgment.
- skill_listing — 5.5×/session, 14.5 K tok. Re-injected on every SessionStart
  *including post-compact*. It should survive compaction, not be re-pasted.
- compact summary — 2.5×/session, 15.6 K tok, re-injected on top of itself.

### CUT 3 — Trim the two hot hooks
**Saves ~35–45 K tok/session of the 61 K hook budget (15.0 % amplified).**
- `PreToolUse:Agent` ROUTING POLICY: 48 fires × 421 tok = 20.2 K, **static and
  identical every time**. Move it into the agent definitions / system prompt once,
  or cut it to a 1-line reminder → saves ~18 K.
- `hook_additional_context` (RESUME HANDOFF + northstar + recall): 155.6 fires ×
  203 tok = 31.7 K, firing **more than once per user turn**. Rate-limit to once per
  turn and diff-suppress unchanged content → saves ~20 K.

### Runner-up (cheap, worth doing)
Ban **file bodies inside Bash heredocs** (`cat > file <<'EOF'`). Two of the top-10
largest single items are heredocs, one of them duplicated by a subsequent `Write` of
the same file (~27 K tokens for one file). Use `Write`; it costs the body once.
`tool_use:Bash` is 8.8 % of amplified cost.

### What NOT to cut
`Read`, `Grep`/`Glob`, `Edit/Write` results, and MCP results are **all under 1.5 %
amplified each** — Claude Code's spill-to-file already solved oversized tool output.
Pasted images look like 64 % if you count base64 chars but are ~175 K tokens across
the entire cohort. Both are the loud things, not the big things.
